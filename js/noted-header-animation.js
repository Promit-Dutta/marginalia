/* ================================================================
   notes-header-animation.js
   Animated geometric network for the Marginal Notes hero section.

   Palette:
     · Sage-green edges + primary nodes  (echoes the landscape hills)
     · Warm amber accent nodes (~11%)    (echoes the house-window glow)
     · Dim sage nodes (~25%)             (background depth)
     · Faint triangle fills              (geometric richness)

   Pure Canvas 2D. No dependencies. IIFE wrapped.
   · Pauses via IntersectionObserver when scrolled off-screen.
   · Redraws on resize via ResizeObserver.
   · Respects prefers-reduced-motion (single static frame).
================================================================ */
(function () {
  'use strict';

  /* ── Tunable constants ───────────────────────────────────── */
  var NUM_NODES = 68;
  var MAX_DIST  = 168;   /* px — max distance for an edge to appear   */
  var SPEED     = 0.19;  /* px/frame — max node velocity              */

  /* ── Palette (always rendered on the dark hero background) ─
     Sage  → edge lines + most nodes
     Amber → ~11% accent nodes, mirrors the SVG house-window glow
     Dim   → ~25% nodes, creates depth / distance variation       */
  var SR = 122, SG = 168, SB = 84;   /* sage  */
  var AR = 232, AG = 166, AB = 38;   /* amber */
  var DR = 72,  DG = 104, DB = 48;   /* dim   */

  /* ── Cached squared max distance ────────────────────────── */
  var MD2 = MAX_DIST * MAX_DIST;

  /* ─────────────────────────────────────────────────────────
     init() — called once the DOM is ready.
     All state is local to this closure.
  ───────────────────────────────────────────────────────── */
  function init() {
    var canvas = document.getElementById('notes-cv');
    if (!canvas) return;

    var ctx;
    try { ctx = canvas.getContext('2d'); } catch (e) { return; }
    if (!ctx) return;

    /* ── Node pool ─────────────────────────────────────────── */
    var nodes = [];

    function buildNodes(W, H) {
      nodes = [];
      for (var i = 0; i < NUM_NODES; i++) {
        var roll   = Math.random();
        var accent = roll < 0.11;
        var dim    = !accent && roll > 0.72;
        var spd    = SPEED * (0.40 + Math.random() * 0.60);
        var ang    = Math.random() * 6.2832;
        nodes.push({
          x:    Math.random() * W,
          y:    Math.random() * H,
          vx:   Math.cos(ang) * spd,
          vy:   Math.sin(ang) * spd,
          r:    accent ? 2.7 : dim ? 1.4 : 2.0,
          cr:   accent ? AR  : dim ? DR  : SR,
          cg:   accent ? AG  : dim ? DG  : SG,
          cb:   accent ? AB  : dim ? DB  : SB,
          glow: accent,
        });
      }
    }

    /* ── Canvas sizing ─────────────────────────────────────── */
    function fit() {
      var p = canvas.parentElement;
      canvas.width  = p ? p.offsetWidth  : (window.innerWidth  || 800);
      canvas.height = p ? p.offsetHeight : 260;
    }

    /* ── Advance node positions one tick ───────────────────── */
    function step() {
      var W = canvas.width, H = canvas.height;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;
        /* soft boundary — nodes bounce 20px outside the visible edge
           so they never abruptly vanish at the canvas border         */
        if (n.x < -20)    n.vx =  Math.abs(n.vx);
        if (n.x > W + 20) n.vx = -Math.abs(n.vx);
        if (n.y < -20)    n.vy =  Math.abs(n.vy);
        if (n.y > H + 20) n.vy = -Math.abs(n.vy);
      }
    }

    /* ── Render one frame ──────────────────────────────────── */
    function render() {
      var W  = canvas.width;
      var H  = canvas.height;
      var nn = nodes.length;
      ctx.clearRect(0, 0, W, H);

      /* ── Edges + triangle fills ─────────────────────────── */
      for (var i = 0; i < nn - 1; i++) {
        var ni = nodes[i];
        for (var j = i + 1; j < nn; j++) {
          var nj   = nodes[j];
          var dxij = ni.x - nj.x;
          var dyij = ni.y - nj.y;
          var d2ij = dxij * dxij + dyij * dyij;
          if (d2ij > MD2) continue;

          var tij = 1 - Math.sqrt(d2ij) / MAX_DIST; /* closeness 0→1 */

          /* Triangle fills — only bother for fairly close pairs
             (tij > 0.40 means the edge is in the inner 60% of MAX_DIST).
             This keeps the O(n³) triangle search cheap in practice.    */
          if (tij > 0.40) {
            for (var k = j + 1; k < nn; k++) {
              var nk   = nodes[k];
              var dxik = ni.x - nk.x, dyik = ni.y - nk.y;
              if (dxik * dxik + dyik * dyik > MD2) continue;
              var dxjk = nj.x - nk.x, dyjk = nj.y - nk.y;
              if (dxjk * dxjk + dyjk * dyjk > MD2) continue;

              var tik  = 1 - Math.sqrt(dxik * dxik + dyik * dyik) / MAX_DIST;
              var tjk  = 1 - Math.sqrt(dxjk * dxjk + dyjk * dyjk) / MAX_DIST;
              var tMin = tij < tik ? (tij < tjk ? tij : tjk)
                                   : (tik < tjk ? tik : tjk);

              ctx.beginPath();
              ctx.moveTo(ni.x, ni.y);
              ctx.lineTo(nj.x, nj.y);
              ctx.lineTo(nk.x, nk.y);
              ctx.closePath();
              /* very faint sage fill — adds geometric body without noise */
              ctx.fillStyle = 'rgba(105,150,62,' + (tMin * 0.058) + ')';
              ctx.fill();
            }
          }

          /* Edge line — opacity + width both scale with closeness */
          ctx.beginPath();
          ctx.moveTo(ni.x, ni.y);
          ctx.lineTo(nj.x, nj.y);
          ctx.strokeStyle = 'rgba(' + SR + ',' + SG + ',' + SB + ',' + (tij * 0.37) + ')';
          ctx.lineWidth   = tij * 0.90 + 0.15;
          ctx.stroke();
        }
      }

      /* ── Nodes ─────────────────────────────────────────────
         Amber nodes get a radial glow + outer ring.
         All nodes get a filled circle.                        */
      for (var i = 0; i < nn; i++) {
        var n = nodes[i];

        if (n.glow) {
          /* Radial halo — mimics the warm amber window glow in the SVG */
          var gr = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 8);
          gr.addColorStop(0,    'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.52)');
          gr.addColorStop(0.30, 'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.11)');
          gr.addColorStop(1,    'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0)');
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 8, 0, 6.2832);
          ctx.fillStyle = gr;
          ctx.fill();
        }

        /* Filled circle */
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, 6.2832);
        ctx.fillStyle = 'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.90)';
        ctx.fill();

        /* Outer ring for accent nodes — gives them a star-like quality */
        if (n.glow) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r + 1.5, 0, 6.2832);
          ctx.strokeStyle = 'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.26)';
          ctx.lineWidth = 0.7;
          ctx.stroke();
        }
      }
    }

    /* ── Animation loop ────────────────────────────────────── */
    var paused     = false;
    var loopActive = false;

    function loop() {
      if (paused) { loopActive = false; return; }
      step();
      render();
      requestAnimationFrame(loop);
    }

    function startLoop() {
      if (!loopActive) {
        loopActive = true;
        requestAnimationFrame(loop);
      }
    }

    /* ── Pause when the hero is off-screen (CPU saving) ────── */
    if (typeof IntersectionObserver !== 'undefined') {
      new IntersectionObserver(function (entries) {
        paused = !entries[0].isIntersecting;
        if (!paused) startLoop();
      }, { threshold: 0.05 }).observe(canvas);
    }

    /* ── Rebuild on resize ─────────────────────────────────── */
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(function () {
        fit();
        buildNodes(canvas.width, canvas.height);
      }).observe(canvas.parentElement || canvas);
    } else {
      window.addEventListener('resize', function () {
        fit();
        buildNodes(canvas.width, canvas.height);
      });
    }

    /* ── Kick off ──────────────────────────────────────────── */
    fit();
    buildNodes(canvas.width, canvas.height);

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      render(); /* single static frame — no RAF loop */
    } else {
      startLoop();
    }
  }

 /* ── DOM-ready guard ───────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      requestAnimationFrame(init);
    });
  } else {
    requestAnimationFrame(init);
  }

})();
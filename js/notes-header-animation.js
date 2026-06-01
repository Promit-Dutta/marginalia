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

  /* ── Palette ────────────────────────────────────────────────
     Sage  → edge lines + most nodes
     Amber → ~11% accent nodes (echoes the SVG house-window glow)
     Dim   → ~25% nodes, creates depth                            */
  var SR = 122, SG = 168, SB = 84;   /* sage  */
  var AR = 232, AG = 166, AB = 38;   /* amber */
  var DR = 72,  DG = 104, DB = 48;   /* dim   */

  var MD2 = MAX_DIST * MAX_DIST;

  /* ─────────────────────────────────────────────────────────
     init() — called once the DOM is ready.
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
      var w = (p && p.offsetWidth)  || window.innerWidth  || 800;
      var h = (p && p.offsetHeight) || 260;
      if (w > 0) canvas.width  = w;
      if (h > 0) canvas.height = h;
    }

    /* ── Advance positions one tick ─────────────────────────── */
    function step() {
      var W = canvas.width, H = canvas.height;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;
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

      /* Edges + triangle fills */
      for (var i = 0; i < nn - 1; i++) {
        var ni = nodes[i];
        for (var j = i + 1; j < nn; j++) {
          var nj   = nodes[j];
          var dxij = ni.x - nj.x;
          var dyij = ni.y - nj.y;
          var d2ij = dxij * dxij + dyij * dyij;
          if (d2ij > MD2) continue;
          var tij = 1 - Math.sqrt(d2ij) / MAX_DIST;

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
              ctx.fillStyle = 'rgba(105,150,62,' + (tMin * 0.058) + ')';
              ctx.fill();
            }
          }

          ctx.beginPath();
          ctx.moveTo(ni.x, ni.y);
          ctx.lineTo(nj.x, nj.y);
          ctx.strokeStyle = 'rgba(' + SR + ',' + SG + ',' + SB + ',' + (tij * 0.37) + ')';
          ctx.lineWidth   = tij * 0.90 + 0.15;
          ctx.stroke();
        }
      }

      /* Nodes */
      for (var i = 0; i < nn; i++) {
        var n = nodes[i];
        if (n.glow) {
          var gr = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 8);
          gr.addColorStop(0,    'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.52)');
          gr.addColorStop(0.30, 'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.11)');
          gr.addColorStop(1,    'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0)');
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 8, 0, 6.2832);
          ctx.fillStyle = gr;
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, 6.2832);
        ctx.fillStyle = 'rgba(' + n.cr + ',' + n.cg + ',' + n.cb + ',0.90)';
        ctx.fill();
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
    var loopLive   = false; /* set true once first frame draws        */

    function loop() {
      loopLive = true;
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

    /* ── kickOff ─────────────────────────────────────────────
       Retries via rAF until the canvas has real dimensions.
       This handles the case where layout hasn't committed yet
       on the first rAF tick (e.g. slow first paint, FOUC).    */
    function kickOff() {
      fit();
      if (canvas.width < 2 || canvas.height < 2) {
        /* Parent not laid out yet — wait one more frame and retry */
        requestAnimationFrame(kickOff);
        return;
      }
      buildNodes(canvas.width, canvas.height);
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        render();
      } else {
        startLoop();
      }
    }

    /* ── IntersectionObserver — pause when scrolled off-screen ─
       Two guards:
         ioInitDone  — skips the initial synchronous callback
                       that fires on .observe() before the first
                       rAF tick (may report isIntersecting:false
                       because the canvas had no layout yet).
         loopLive    — prevents IO from pausing the animation
                       before the first frame has actually drawn,
                       even if a rapid second callback fires.    */
    if (typeof IntersectionObserver !== 'undefined') {
      var ioInitDone = false;
      new IntersectionObserver(function (entries) {
        if (!ioInitDone) { ioInitDone = true; return; }
        var visible = entries[0].isIntersecting;
        /* Only allow a pause AFTER the loop has drawn at least one frame.
           Before that, a spurious isIntersecting:false from an unsettled
           layout must not kill the animation permanently.               */
        if (loopLive || visible) {
          paused = !visible;
          if (!paused) startLoop();
        }
      }, { threshold: 0.05 }).observe(canvas);
    }

    /* ── ResizeObserver — rebuild nodes on resize ────────────
       Also restarts the loop if it died during a zero-dim init. */
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(function () {
        fit();
        if (canvas.width > 0 && canvas.height > 0) {
          buildNodes(canvas.width, canvas.height);
          /* If loop never started (zero-dim at init time), start it now */
          if (!loopActive && !paused &&
              !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            startLoop();
          }
        }
      }).observe(canvas.parentElement || canvas);
    } else {
      window.addEventListener('resize', function () {
        fit();
        buildNodes(canvas.width, canvas.height);
      });
    }

    /* ── Kick off ──────────────────────────────────────────── */
    kickOff();
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
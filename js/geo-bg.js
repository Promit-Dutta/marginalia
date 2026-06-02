/* ================================================================
   geo-bg.js — Isometric tessellated line-grid animation.
   Canvas is position:fixed at z-index:-2, below the landscape SVG.
   A CSS mask in geo-bg.css restricts the VISIBLE zone to the lower
   portion of the viewport (below the about card → footer).

   Progressive reveal:
     Lines appear from canvas-centre outward. Lines RIGHT at the
     expanding front draw bright/thick (alpha ≈ 0.90, 3px).
     Lines already revealed settle quickly to their steady-state
     alpha (0.28–0.42). The user sees a luminous ring expanding
     outward before the grid "settles" into its ambient shimmer.

   Steady-state shimmer:
     Each line's alpha oscillates gently via a slow travelling wave.
     Lines near the bottom of the visible zone are slightly brighter.

   Slow rotation: full visual cycle ≈ 52 s (3-fold symmetry means
   60° ≡ original, so period = 60° / rot_speed).

   Mobile: larger cells, lighter lines, same quality.
   Respects prefers-reduced-motion (single fully-revealed frame).
================================================================ */
(function () {
  'use strict';

  /* ── Palette ──────────────────────────────────────────────── */
  var BG = '#040c1a';          /* deep navy background             */
  var LR = 80, LG = 148, LB = 255; /* soft blue lines             */

  /* ── Tuning ───────────────────────────────────────────────── */
  var CELL_D     = 52;         /* cell spacing desktop (px)        */
  var CELL_M     = 70;         /* cell spacing mobile  (px)        */
  var ROT_SPD    = 2.0e-5;     /* rad/ms — full visual cycle ≈52 s */
  var PULSE      = 2.6e-4;     /* shimmer wave angular speed       */
  var REVEAL_SPD = 58;         /* px / s — outward reveal radius   */
  var FRONT_W    = 1.8;        /* cells behind front for fade zone */

  /* ── Bootstrap ────────────────────────────────────────────── */
  function init () {
    var canvas = document.getElementById('geo-bg');
    if (!canvas) return;
    var ctx;
    try { ctx = canvas.getContext('2d'); } catch (e) { return; }
    if (!ctx) return;

    var W = 0, H = 0, mob = false;
    var loopActive = false, paused = false, loopLive = false;
    var startTs = null;

    /* ── Sizing ─────────────────────────────────────────────── */
    function fit () {
      W   = canvas.width  = window.innerWidth  || 800;
      H   = canvas.height = window.innerHeight || 600;
      mob = W <= 640;
    }

    /* ── Render one frame ───────────────────────────────────── */
    function render (ts) {
      if (startTs === null) startTs = ts;
      var elapsed  = ts - startTs;
      var revealR  = (elapsed / 1000) * REVEAL_SPD;
      var cell     = mob ? CELL_M : CELL_D;
      var CX       = W * 0.5;
      var CY       = H * 0.5;
      var maxR     = Math.sqrt(W * W + H * H) * 0.5;
      var allDone  = revealR >= maxR + cell * 2;
      var rot      = ts * ROT_SPD;
      var sinRot   = Math.sin(rot);
      var cosRot   = Math.cos(rot);
      var reach    = maxR + cell * 3;
      var n        = Math.ceil(reach / cell) + 2;

      /* ── Background ─────────────────────────────────────── */
      ctx.fillStyle = BG;
      ctx.fillRect(0, 0, W, H);

      /* ── Three isometric line families: 0°, 60°, 120° ───── */
      var FAM = [0, Math.PI / 3, 2 * Math.PI / 3];

      ctx.save();
      ctx.translate(CX, CY);
      ctx.rotate(rot);

      for (var fi = 0; fi < 3; fi++) {
        var a   = FAM[fi];
        var cdx = Math.cos(a), cdy = Math.sin(a);
        var pdx = Math.cos(a + Math.PI * 0.5);
        var pdy = Math.sin(a + Math.PI * 0.5);

        for (var i = -n; i <= n; i++) {

          /* Perpendicular distance from grid centre to this line.
             Rotation preserves distances, so this equals its
             screen-space distance from canvas centre. */
          var perpDist = Math.abs(i) * cell;

          /* Skip lines not yet inside the reveal front */
          var distToFront = allDone ? cell * 1000 : revealR - perpDist;
          if (distToFront < 0) continue;

          /* frontPhase: 0 = right at the bright front
                         1 = (FRONT_W cells) behind the front, fully settled */
          var frontPhase = Math.min(1.0, distToFront / (cell * FRONT_W));

          /* Shimmer: slow wave per line & family                  */
          var wave = 0.5 + 0.5 * Math.sin(ts * PULSE + i * 0.44 + fi * 2.09);

          /* Screen Y of this line's representative point,
             for vertical brightness gradient                      */
          var rotX   = pdx * i * cell;
          var rotY   = pdy * i * cell;
          var scrnY  = CY + rotX * sinRot + rotY * cosRot;
          /* yFrac: 0 at top-of-visible-zone (≈55%H), 1 at bottom */
          var yFrac  = Math.max(0, Math.min(1, (scrnY - H * 0.52) / (H * 0.48)));
          var yBoost = yFrac * 0.18;

          /* Alpha: very bright at reveal front, settles to steady */
          var steadyA = (mob ? 0.22 : 0.28) + wave * 0.14 + yBoost;
          var alpha   = 0.92 * (1 - frontPhase) + steadyA * frontPhase;

          /* Line width: thick at front, thinner at steady state   */
          var steadyW = mob ? (0.55 + wave * 0.18) : (0.82 + wave * 0.26);
          var lw      = (mob ? 2.4 : 3.2) * (1 - frontPhase) + steadyW * frontPhase;

          ctx.beginPath();
          ctx.moveTo(rotX - cdx * reach, rotY - cdy * reach);
          ctx.lineTo(rotX + cdx * reach, rotY + cdy * reach);
          ctx.strokeStyle = 'rgba(' + LR + ',' + LG + ',' + LB + ',' +
                            Math.min(alpha, 0.93).toFixed(3) + ')';
          ctx.lineWidth   = Math.max(0.3, lw);
          ctx.stroke();
        }
      }

      ctx.restore();
    }

    /* ── Animation loop ─────────────────────────────────────── */
    function loop (ts) {
      loopLive = true;
      if (paused) { loopActive = false; return; }
      render(ts);
      requestAnimationFrame(loop);
    }

    function startLoop () {
      if (!loopActive) { loopActive = true; requestAnimationFrame(loop); }
    }

    /* kickOff — waits for real layout dimensions              */
    function kickOff () {
      fit();
      if (W < 2 || H < 2) { requestAnimationFrame(kickOff); return; }
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        /* Single fully-revealed static frame */
        startTs = -(Math.sqrt(W * W + H * H) / REVEAL_SPD) * 1000;
        render(0);
      } else {
        startLoop();
      }
    }

    /* ── Page Visibility API — pause on hidden tab ───────────── */
    document.addEventListener('visibilitychange', function () {
      paused = document.hidden;
      if (!paused) startLoop();
    });

    /* ── IntersectionObserver (mostly a no-op for fixed canvas) */
    if (typeof IntersectionObserver !== 'undefined') {
      var ioInit = false;
      new IntersectionObserver(function (entries) {
        if (!ioInit) { ioInit = true; return; }
        var vis = entries[0].isIntersecting;
        if (loopLive || vis) { paused = !vis; if (!paused) startLoop(); }
      }, { threshold: 0.01 }).observe(canvas);
    }

    /* ── ResizeObserver — re-fit on viewport change ──────────── */
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(function () {
        fit();
        if (!loopActive && !paused &&
            !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
          startLoop();
        }
      }).observe(document.documentElement);
    } else {
      window.addEventListener('resize', fit);
    }

    requestAnimationFrame(kickOff);
  }

  /* ── DOM-ready guard ────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
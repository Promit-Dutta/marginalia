/* ================================================================
   geo-bg.js — Isometric tessellated line-grid animation.
   Renders onto #geo-bg (position:fixed, z-index:-2), sitting
   behind the landscape SVG.  Where the landscape's CSS mask
   fades to transparent, this canvas shows through — forming the
   animated dark-blue field behind the about section and footer.

   Pattern: three families of parallel lines at 0°, 60°, 120°,
   producing the classic isometric / zig-zag tessellation.
     · Lines reveal outward from the canvas centre on first load
     · The whole grid rotates slowly (≈ 165 s per full revolution)
     · Individual lines shimmer with a slow travelling wave-pulse
     · Mobile: larger cell spacing, lighter lines, same quality
     · Pauses on hidden tab (Page Visibility API)
     · Single static frame on prefers-reduced-motion
================================================================ */
(function () {
  'use strict';

  /* ── Palette ──────────────────────────────────────────────── */
  var BG = '#040c1a';
  var LR = 72, LG = 135, LB = 235;   /* line RGB — soft blue   */

  /* ── Tuning ───────────────────────────────────────────────── */
  var CELL_D     = 54;      /* grid spacing desktop (px)          */
  var CELL_M     = 72;      /* grid spacing mobile (px)           */
  var ROT_SPD    = 3.8e-5;  /* rad / ms  ≈ full turn every 165 s  */
  var PULSE      = 3.2e-4;  /* shimmer wave angular speed         */
  var REVEAL_SPD = 190;     /* px / s — outward reveal radius     */

  /* ── Bootstrap ────────────────────────────────────────────── */
  function init() {
    var canvas = document.getElementById('geo-bg');
    if (!canvas) return;
    var ctx;
    try { ctx = canvas.getContext('2d'); } catch (e) { return; }
    if (!ctx) return;

    var W = 0, H = 0, mob = false;
    var loopActive = false, paused = false, loopLive = false;
    var startTs = null;           /* first rAF timestamp for reveal */

    /* ── Sizing ─────────────────────────────────────────────── */
    function fit() {
      W   = canvas.width  = window.innerWidth  || 800;
      H   = canvas.height = window.innerHeight || 600;
      mob = W <= 640;
    }

    /* ── Render one frame ───────────────────────────────────── */
    function render(ts) {
      if (startTs === null) startTs = ts;
      var elapsed = ts - startTs;

      /* Expand reveal radius from 0 until it covers the whole canvas */
      var revealR    = (elapsed / 1000) * REVEAL_SPD;
      var maxR       = Math.sqrt(W * W + H * H) * 0.5;
      var allVisible = revealR >= maxR;

      /* Background */
      ctx.fillStyle = BG;
      ctx.fillRect(0, 0, W, H);

      var cell  = mob ? CELL_M : CELL_D;
      var rot   = ts * ROT_SPD;
      var CX    = W * 0.5;
      var CY    = H * 0.5;
      /* Reach: half-diagonal + padding so lines cover every corner */
      var reach = maxR + cell * 4;
      var n     = Math.ceil(reach / cell) + 2;

      ctx.save();
      ctx.translate(CX, CY);
      ctx.rotate(rot);

      /*
        Three isometric line families — 0°, 60°, 120°.
        For each family we compute:
          cdx, cdy  — unit vector along the line direction
          pdx, pdy  — unit vector perpendicular (used to offset lines)
        Line i is offset by (i * cell) along the perpendicular.
        The perpendicular distance from centre is therefore |i| * cell.
      */
      var FAM = [0, Math.PI / 3, 2 * Math.PI / 3];

      for (var fi = 0; fi < 3; fi++) {
        var a   = FAM[fi];
        var cdx = Math.cos(a);
        var cdy = Math.sin(a);
        var pdx = Math.cos(a + Math.PI * 0.5);
        var pdy = Math.sin(a + Math.PI * 0.5);

        for (var i = -n; i <= n; i++) {
          /* Perpendicular distance from centre (rotated frame) */
          var dist = Math.abs(i) * cell;

          /* Skip lines beyond the expanding reveal front */
          if (!allVisible && dist > revealR) continue;

          /* Smooth fade at the reveal leading edge */
          var revealFade = allVisible
            ? 1.0
            : Math.min((revealR - dist) / (cell * 1.8), 1.0);

          /* Shimmer: sine wave travelling along the perpendicular axis */
          var wave  = 0.5 + 0.5 * Math.sin(ts * PULSE + i * 0.44 + fi * 2.09);

          /* Lighter on mobile to avoid visual noise on small screens */
          var alpha = (mob ? 0.055 + wave * 0.090
                           : 0.065 + wave * 0.130) * revealFade;
          var lw    =  mob ? 0.40  + wave * 0.20
                           : 0.48  + wave * 0.36;

          var ox = pdx * i * cell;
          var oy = pdy * i * cell;

          ctx.beginPath();
          ctx.moveTo(ox - cdx * reach, oy - cdy * reach);
          ctx.lineTo(ox + cdx * reach, oy + cdy * reach);
          ctx.strokeStyle = 'rgba(' + LR + ',' + LG + ',' + LB + ',' +
                            alpha.toFixed(3) + ')';
          ctx.lineWidth   = lw;
          ctx.stroke();
        }
      }

      ctx.restore();
    }

    /* ── Animation loop ─────────────────────────────────────── */
    function loop(ts) {
      loopLive = true;
      if (paused) { loopActive = false; return; }
      render(ts);
      requestAnimationFrame(loop);
    }

    function startLoop() {
      if (!loopActive) { loopActive = true; requestAnimationFrame(loop); }
    }

    /* ── kickOff — waits for real layout dimensions ─────────── */
    function kickOff() {
      fit();
      if (W < 2 || H < 2) { requestAnimationFrame(kickOff); return; }
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        /* Render a single fully-revealed static frame */
        var diag = Math.sqrt(W * W + H * H);
        startTs  = -(diag / REVEAL_SPD) * 1000;
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

    /* ── IntersectionObserver — fixed canvas, rarely fires ────── */
    if (typeof IntersectionObserver !== 'undefined') {
      var ioInit = false;
      new IntersectionObserver(function (entries) {
        if (!ioInit) { ioInit = true; return; }
        var vis = entries[0].isIntersecting;
        if (loopLive || vis) { paused = !vis; if (!paused) startLoop(); }
      }, { threshold: 0.01 }).observe(canvas);
    }

    /* ── ResizeObserver — rebuild on viewport change ─────────── */
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

    /* ── Start ──────────────────────────────────────────────── */
    requestAnimationFrame(kickOff);
  }

  /* ── DOM-ready guard ────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
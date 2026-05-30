(function () {
  'use strict';

  /* ── Overlay ─────────────────────────────────────────────── */
  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  /* ── Refs ─────────────────────────────────────────────────── */
  var dropdowns = Array.from(document.querySelectorAll('.nav-has-dropdown'));
  var navToggle  = document.getElementById('nav-toggle');
  var mainNav    = document.getElementById('main-nav');

  /* ── Dropdown helpers ─────────────────────────────────────── */
  function openDD(dd) {
    dd.classList.add('is-open');
    var btn = dd.querySelector('.nav-dropdown-btn');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
  function closeDD(dd) {
    dd.classList.remove('is-open');
    var btn = dd.querySelector('.nav-dropdown-btn');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
  function closeAll() { dropdowns.forEach(closeDD); }

  /* ── Mobile nav open / close ──────────────────────────────── */
  function openMobileNav() {
    if (mainNav) mainNav.classList.add('nav-open');
    overlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }
  function closeMobileNav() {
    if (mainNav) mainNav.classList.remove('nav-open');
    overlay.classList.remove('visible');
    document.body.style.overflow = '';
    if (navToggle) navToggle.checked = false;
    closeAll();
  }

  /* ── Reset on every page show (fixes bfcache restoration) ── */
  window.addEventListener('pageshow', function () {
    closeMobileNav();
  });

  /* ── Hamburger checkbox drives open/close ─────────────────── */
  if (navToggle) {
    navToggle.addEventListener('change', function () {
      if (this.checked) { openMobileNav(); }
      else              { closeMobileNav(); }
    });
  }

  /* ── Desktop: hover opens / closes dropdown panels ─────────── */
  dropdowns.forEach(function (dd) {
    dd.addEventListener('mouseenter', function () {
      if (window.innerWidth >= 769) openDD(dd);
    });
    dd.addEventListener('mouseleave', function () {
      if (window.innerWidth >= 769) closeDD(dd);
    });
  });

  /* ── Desktop + mobile: click / keyboard on dropdown buttons ── */
  dropdowns.forEach(function (dd) {
    var btn = dd.querySelector('.nav-dropdown-btn');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var already = dd.classList.contains('is-open');
      closeAll();
      if (!already) openDD(dd);
    });
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { closeAll(); btn.blur(); }
    });
  });

  /* ── Click outside closes dropdowns ──────────────────────── */
  document.addEventListener('click', closeAll);
  document.querySelectorAll('.nav-dropdown-panel').forEach(function (p) {
    p.addEventListener('click', function (e) { e.stopPropagation(); });
  });

  /* ── Escape closes everything ─────────────────────────────── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeAll(); closeMobileNav(); }
  });

  /* ── Overlay tap closes mobile nav ──────────────────────────- */
  overlay.addEventListener('click', closeMobileNav);

})();
(function () {
  'use strict';
  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);
  var dropdowns = Array.from(document.querySelectorAll('.nav-has-dropdown'));
  var navToggle  = document.getElementById('nav-toggle');
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
  dropdowns.forEach(function (dd) {
    dd.addEventListener('mouseenter', function () {
      if (window.innerWidth >= 769) openDD(dd);
    });
    dd.addEventListener('mouseleave', function () {
      if (window.innerWidth >= 769) closeDD(dd);
    });
  });
  document.addEventListener('click', closeAll);
  document.querySelectorAll('.nav-dropdown-panel').forEach(function (p) {
    p.addEventListener('click', function (e) { e.stopPropagation(); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll();
  });
  if (navToggle) {
    navToggle.addEventListener('change', function () {
      if (this.checked) { overlay.classList.add('visible'); }
      else { overlay.classList.remove('visible'); closeAll(); }
    });
    overlay.addEventListener('click', function () {
      navToggle.checked = false;
      overlay.classList.remove('visible');
      closeAll();
    });
  }
})();
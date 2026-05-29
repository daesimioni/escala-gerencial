/**
 * Escala de Sobreaviso — UI Interactions
 * Sidebar toggle, keyboard shortcuts, mobile enhancements
 */
(function () {
  'use strict';

  // ── Sidebar Toggle ──────────────────────────────────────────
  window.toggleSidebar = function () {
    var sidebar = document.getElementById('appSidebar');
    var overlay = document.getElementById('sidebarOverlay');
    if (sidebar && overlay) {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('show');
    }
  };

  window.closeSidebar = function () {
    var sidebar = document.getElementById('appSidebar');
    var overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
  };

  // ── Keyboard Shortcuts ──────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    // Don't intercept when typing in inputs
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable) return;

    // Arrow Left/Right for month navigation
    if (e.key === 'ArrowLeft') {
      var prevBtn = document.querySelector('a[href*="calendario_mes"] .bi-chevron-left, a.btn .bi-chevron-left');
      if (prevBtn) { e.preventDefault(); prevBtn.closest('a').click(); }
    }
    if (e.key === 'ArrowRight') {
      var nextBtn = document.querySelector('a[href*="calendario_mes"] .bi-chevron-right, a.btn .bi-chevron-right');
      if (nextBtn) { e.preventDefault(); nextBtn.closest('a').click(); }
    }

    // Escape closes modals
    if (e.key === 'Escape') {
      closeSidebar();
    }

    // Ctrl+B toggles sidebar
    if (e.ctrlKey && e.key === 'b') {
      e.preventDefault();
      toggleSidebar();
    }
  });

  // ── Auto-dismiss alerts ─────────────────────────────────────
  var alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      var btn = alert.querySelector('.btn-close');
      if (btn) btn.click();
    }, 5000);
  });

  // ── Confirm destructive actions ─────────────────────────────
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-confirm]');
    if (btn) {
      var msg = btn.getAttribute('data-confirm') || 'Tem certeza?';
      if (!confirm(msg)) {
        e.preventDefault();
        e.stopPropagation();
      }
    }
  });
})();

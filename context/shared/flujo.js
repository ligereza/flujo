/* flujo.js — utilidades compartidas del hub (vanilla, sin dependencias).
   Enlazar con ruta relativa (script clasico, NO type=module, para que
   funcione con doble clic bajo file://):
     <script src="shared/flujo.js"></script>
   Expone window.Flujo con: escapeHTML, fetchJSON, useDemo, toast,
   setState/render helpers y trapFocus para el modal. */
(function (global) {
  'use strict';

  // --- seguridad: escapar SIEMPRE datos dinamicos antes de innerHTML ---
  function escapeHTML(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // --- modo demo: doble clic (file://) o ?demo=1 -> usar datos embebidos ---
  function useDemo() {
    try {
      if (global.location && global.location.protocol === 'file:') return true;
      return new URLSearchParams(global.location.search).has('demo');
    } catch (e) { return true; }
  }

  // --- fetch que SI falla en HTTP 4xx/5xx (fetch nativo no rechaza ahi) ---
  async function fetchJSON(path, opts) {
    var r = await fetch(path, opts || {});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var ct = r.headers.get('content-type') || '';
    return ct.indexOf('application/json') >= 0 ? r.json() : r.text();
  }

  // --- toast no bloqueante (reemplaza alert) ---
  function toast(msg, type) {
    var c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      document.body.appendChild(c);
    }
    var t = document.createElement('div');
    t.className = 'toast' + (type === 'error' ? ' error' : '');
    t.textContent = msg; // textContent: seguro
    c.appendChild(t);
    setTimeout(function () { t.remove(); }, 3500);
  }

  // --- foco-trap para el modal (accesibilidad) ---
  function trapFocus(modal, onClose) {
    var sel = 'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])';
    function onKey(e) {
      if (e.key === 'Escape') { onClose && onClose(); return; }
      if (e.key !== 'Tab') return;
      var f = Array.prototype.slice.call(modal.querySelectorAll(sel));
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    modal.addEventListener('keydown', onKey);
    return function () { modal.removeEventListener('keydown', onKey); };
  }

  // --- formato moneda CLP (para costos del rider) ---
  function clp(n) {
    var v = Number(n) || 0;
    try { return v.toLocaleString('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }); }
    catch (e) { return '$' + v.toLocaleString('es-CL'); }
  }

  // --- marca el enlace de nav que corresponde a la pagina actual ---
  function markActiveNav() {
    try {
      var here = (location.pathname.split('/').pop() || '').toLowerCase();
      document.querySelectorAll('.nav a[href]').forEach(function (a) {
        var target = (a.getAttribute('href') || '').split('/').pop().toLowerCase();
        if (target && target === here) a.setAttribute('aria-current', 'page');
      });
    } catch (e) {}
  }

  // --- fecha/hora legible (para footers / "ultima actualizacion") ---
  function now() {
    var d = new Date();
    var p = function (x) { return ('0' + x).slice(-2); };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
           ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  global.Flujo = {
    escapeHTML: escapeHTML,
    useDemo: useDemo,
    fetchJSON: fetchJSON,
    toast: toast,
    trapFocus: trapFocus,
    clp: clp,
    markActiveNav: markActiveNav,
    now: now
  };

  // auto-marcar nav activa al cargar
  if (document.readyState !== 'loading') markActiveNav();
  else document.addEventListener('DOMContentLoaded', markActiveNav);
})(window);

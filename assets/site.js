/* GTASTUCE VICE – petits comportements communs à toutes les pages. */
(function () {
  var root = document.documentElement;
  /* Couper / réactiver les animations (mémorisé sur l'appareil) */
  var mt = document.querySelectorAll('.motion-toggle');
  var sync = function () {
    var off = root.classList.contains('no-motion');
    mt.forEach(function (b) { b.setAttribute('aria-pressed', String(off)); b.textContent = off ? 'Réactiver les animations' : 'Couper les animations'; });
    var tk = document.querySelector('.ticker'); if (tk && off) tk.classList.add('paused');
    var tb = document.querySelector('.tk-toggle'); if (tb && off) { tb.setAttribute('aria-pressed', 'true'); tb.textContent = 'Lecture'; }
  };
  mt.forEach(function (b) {
    b.addEventListener('click', function () {
      var off = !root.classList.contains('no-motion');
      root.classList.toggle('no-motion', off);
      try { localStorage.setItem('gtv_motion', off ? 'off' : 'on'); } catch (e) {}
      sync();
    });
  });
  sync();
  /* Bandeau défilant : pause / lecture */
  var tb = document.querySelector('.tk-toggle');
  if (tb) tb.addEventListener('click', function () {
    var tk = document.querySelector('.ticker'), p = !tk.classList.contains('paused');
    tk.classList.toggle('paused', p); tb.setAttribute('aria-pressed', String(p)); tb.textContent = p ? 'Lecture' : 'Pause';
    tb.setAttribute('aria-label', p ? 'Relancer le bandeau défilant' : 'Mettre en pause le bandeau défilant');
  });
  /* Dates relatives sur l'accueil (« il y a 3 h ») + badge NOUVEAU, à partir des dates écrites dans la page */
  if (document.getElementById('feed')) {
    document.querySelectorAll('.meta time[datetime]').forEach(function (t) {
      var d = new Date(t.getAttribute('datetime')), m = Math.round((Date.now() - d) / 60000);
      if (isNaN(m) || m < 0) return;
      var txt = m < 1 ? "à l'instant" : m < 60 ? 'il y a ' + m + ' min' : m < 1440 ? 'il y a ' + Math.round(m / 60) + ' h' : (Math.round(m / 1440) === 1 ? 'hier' : null);
      if (txt) { t.title = t.textContent; t.textContent = txt; }
      if (m < 720 && !t.parentNode.querySelector('.new')) t.insertAdjacentHTML('beforebegin', '<span class="new">NOUVEAU</span>');
    });
  }
})();

/* ---------- Carte des secrets : zoom et déplacement (boutons, double-clic, pincement, Ctrl + molette, glisser) ---------- */
(function () {
  document.querySelectorAll('[data-map]').forEach(function (fig) {
    var svg = fig.querySelector('svg'); if (!svg) return;
    var B = { x: 0, y: 0, w: 400, h: 500 }, v = { x: 0, y: 0, w: 400, h: 500 }, MIN = 70;
    var anim = null;
    function apply() {
      svg.setAttribute('viewBox', v.x + ' ' + v.y + ' ' + v.w + ' ' + v.h);
      var k = B.w / v.w, s = Math.pow(1 / k, 0.65);
      svg.querySelectorAll('.pg').forEach(function (g) { g.setAttribute('transform', 'scale(' + s + ')'); });
      svg.querySelectorAll('.lbl text').forEach(function (t) { t.style.fontSize = (13 * Math.pow(1 / k, 0.75)) + 'px'; });
      fig.classList.toggle('zoomed', k > 1.05);
    }
    function clamp() {
      v.w = Math.min(B.w, Math.max(MIN, v.w)); v.h = v.w * B.h / B.w;
      v.x = Math.min(B.x + B.w - v.w, Math.max(B.x, v.x)); v.y = Math.min(B.y + B.h - v.h, Math.max(B.y, v.y));
    }
    function to(t) { // transition douce vers t (sauf si les animations sont coupées)
      if (anim) cancelAnimationFrame(anim);
      var reduce = document.documentElement.classList.contains('no-motion') || matchMedia('(prefers-reduced-motion: reduce)').matches;
      var f = { x: v.x, y: v.y, w: v.w }, t0 = performance.now();
      (function step(now) {
        var p = reduce ? 1 : Math.min(1, (now - t0) / 280), e = 1 - Math.pow(1 - p, 3);
        v.x = f.x + (t.x - f.x) * e; v.y = f.y + (t.y - f.y) * e; v.w = f.w + (t.w - f.w) * e; v.h = v.w * B.h / B.w; apply();
        if (p < 1) anim = requestAnimationFrame(step);
      })(t0);
    }
    function zoomAt(factor, cx, cy, smooth) {
      var w = Math.min(B.w, Math.max(MIN, v.w / factor)), h = w * B.h / B.w;
      var t = { x: cx - (cx - v.x) * (w / v.w), y: cy - (cy - v.y) * (h / v.h), w: w };
      var save = { x: v.x, y: v.y, w: v.w, h: v.h }; v.x = t.x; v.y = t.y; v.w = t.w; v.h = h; clamp(); t = { x: v.x, y: v.y, w: v.w };
      v.x = save.x; v.y = save.y; v.w = save.w; v.h = save.h;
      if (smooth) to(t); else { v.x = t.x; v.y = t.y; v.w = t.w; v.h = t.w * B.h / B.w; apply(); }
    }
    function pt(ev) { var r = svg.getBoundingClientRect(); return { x: v.x + (ev.clientX - r.left) / r.width * v.w, y: v.y + (ev.clientY - r.top) / r.height * v.h }; }
    fig.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-zoom]'); if (!b) return;
      if (b.dataset.zoom === 'reset') to({ x: 0, y: 0, w: 400 });
      else zoomAt(b.dataset.zoom === 'in' ? 1.6 : 1 / 1.6, v.x + v.w / 2, v.y + v.h / 2, true);
    });
    svg.addEventListener('dblclick', function (ev) { ev.preventDefault(); var p = pt(ev); zoomAt(1.8, p.x, p.y, true); });
    svg.addEventListener('wheel', function (ev) { if (!ev.ctrlKey && !ev.metaKey) return; ev.preventDefault(); var p = pt(ev); zoomAt(ev.deltaY < 0 ? 1.25 : 0.8, p.x, p.y, false); }, { passive: false });
    var ptrs = {}, last = null, pinch = null, moved = 0;
    svg.addEventListener('pointerdown', function (ev) { ptrs[ev.pointerId] = { x: ev.clientX, y: ev.clientY }; moved = 0; last = { x: ev.clientX, y: ev.clientY }; });
    svg.addEventListener('pointermove', function (ev) {
      if (!ptrs[ev.pointerId]) return; ptrs[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      var ids = Object.keys(ptrs), r = svg.getBoundingClientRect();
      if (ids.length === 2) {
        var a = ptrs[ids[0]], b = ptrs[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) { var c = pt({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 }); zoomAt(d / pinch, c.x, c.y, false); }
        pinch = d; ev.preventDefault(); return;
      }
      if (v.w >= B.w) return; // pas de déplacement sans zoom : la page défile normalement
      var dx = ev.clientX - last.x, dy = ev.clientY - last.y; moved += Math.abs(dx) + Math.abs(dy);
      if (moved > 4) { if (!svg.hasPointerCapture(ev.pointerId)) svg.setPointerCapture(ev.pointerId); v.x -= dx / r.width * v.w; v.y -= dy / r.height * v.h; clamp(); apply(); }
      last = { x: ev.clientX, y: ev.clientY };
    });
    function up(ev) { delete ptrs[ev.pointerId]; if (Object.keys(ptrs).length < 2) pinch = null; }
    svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', up);
    svg.addEventListener('click', function (ev) { if (moved > 6) { ev.preventDefault(); ev.stopPropagation(); } }, true);
    fig.gtvZoomTo = function (x, y) { var w = 150; var t = { x: x - w / 2, y: y - w * 1.25 / 2 + 20, w: w }; var s = { x: v.x, y: v.y, w: v.w, h: v.h }; v.x = t.x; v.y = t.y; v.w = w; v.h = w * 1.25; clamp(); t = { x: v.x, y: v.y, w: v.w }; v.x = s.x; v.y = s.y; v.w = s.w; v.h = s.h; to(t); };
    fig.gtvReset = function () { to({ x: 0, y: 0, w: 400 }); };
    apply();
  });
})();

/* ---------- Liste des secrets : recherche, statut, zone, « masquer les trouvés » ; repères de la carte ---------- */
(function () {
  var list = document.getElementById('eggs'); if (!list || !document.querySelector('.hunt-grid')) return;
  var eggs = [].slice.call(list.querySelectorAll('.egg')), q = document.getElementById('egg-q'), hide = document.getElementById('egg-hide');
  var out = document.getElementById('egg-count'), empty = document.querySelector('.empty-eggs'), fig = document.querySelector('.hunt-grid [data-map]');
  var state = { st: 'all', zone: null };
  var norm = function (s) { return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
  function filter() {
    var words = norm(q ? q.value : '').split(/\s+/).filter(Boolean), n = 0;
    eggs.forEach(function (e) {
      var txt = norm(e.textContent), ok = (state.st === 'all' || e.dataset.st === state.st) && (!state.zone || e.dataset.zone === state.zone)
        && words.every(function (w) { return txt.indexOf(w) >= 0; }) && !(hide && hide.checked && e.classList.contains('found'));
      e.hidden = !ok; if (ok) n++;
    });
    document.querySelectorAll('.egg-group').forEach(function (g) { g.hidden = !g.querySelector('.egg:not([hidden])'); });
    if (empty) empty.hidden = n > 0;
    var filtered = state.st !== 'all' || state.zone || words.length || (hide && hide.checked);
    if (out) out.textContent = filtered ? n + ' secret' + (n > 1 ? 's' : '') + ' affiché' + (n > 1 ? 's' : '') + ' sur ' + eggs.length : '';
  }
  window.gtvEggFilter = filter;
  function showTop() { // après un filtre, la liste raccourcit : on garde ses résultats à l'écran
    var m = document.querySelector('.hunt-main'), r = m && m.getBoundingClientRect();
    if (r && (r.top < 0 || r.top > innerHeight)) m.scrollIntoView({ block: 'start' });
  }
  if (q) q.addEventListener('input', filter);
  if (hide) hide.addEventListener('change', filter);
  document.querySelectorAll('.hunt-tools .chip').forEach(function (b) {
    b.addEventListener('click', function () { state.st = b.dataset.st;
      document.querySelectorAll('.hunt-tools .chip').forEach(function (c) { c.setAttribute('aria-pressed', String(c === b)); }); filter(); showTop(); });
  });
  document.querySelectorAll('.zbtn').forEach(function (b) {
    b.addEventListener('click', function () {
      var on = state.zone !== b.dataset.zone; state.zone = on ? b.dataset.zone : null;
      document.querySelectorAll('.zbtn').forEach(function (c) { c.setAttribute('aria-pressed', String(on && c === b)); });
      if (fig && fig.gtvZoomTo) { if (on && b.dataset.x) fig.gtvZoomTo(+b.dataset.x, +b.dataset.y + 25); else fig.gtvReset(); }
      filter();
      var g = document.querySelector('.egg-group[data-zone="' + b.dataset.zone + '"]');
      if (on && g && innerWidth < 900) g.scrollIntoView({ block: 'start' }); else showTop();
    });
  });
  function reveal(id) { // repère cliqué : on affiche le secret, on l'ouvre et on y place le focus
    var c = document.getElementById('egg-' + id); if (!c) return;
    if (c.hidden) { state.st = 'all'; state.zone = null; if (q) q.value = ''; if (hide) hide.checked = false;
      document.querySelectorAll('.hunt-tools .chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x.dataset.st === 'all')); });
      document.querySelectorAll('.zbtn').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); }); filter(); }
    var d = c.querySelector('details'); if (d) d.open = true;
    c.scrollIntoView({ block: 'center' }); var f = c.querySelector('.check') || c.querySelector('summary'); if (f) f.focus({ preventScroll: true });
    c.classList.add('flash'); setTimeout(function () { c.classList.remove('flash'); }, 1600);
  }
  document.addEventListener('click', function (ev) { var p = ev.target.closest('.map .pin'); if (!p) return; ev.preventDefault(); reveal(p.dataset.id); });
  if (location.hash.indexOf('#egg-') === 0) setTimeout(function () { reveal(location.hash.slice(5)); }, 50);
  filter();
})();

/* ---------- Chasse aux secrets, version simple (23/11) : Carte | Liste, fiche au toucher d'un repère ---------- */
(function () {
  var H = document.querySelector('.hunt2'); if (!H) return;
  var hd = document.querySelector('header'); function hh() { if (hd) H.style.setProperty('--hh', hd.offsetHeight + 'px'); } hh(); addEventListener('resize', hh);
  var panes = { map: H.querySelector('[data-pane=map]'), list: H.querySelector('[data-pane=list]') }, segs = H.querySelectorAll('.seg button');
  var sheet = document.getElementById('h2sheet'), body = document.getElementById('h2body');
  function view(v) {
    panes.map.hidden = v !== 'map'; panes.list.hidden = v !== 'list';
    segs.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.v === v)); });
    if (v !== 'map') close();
    if (H.getBoundingClientRect().top < 0) H.scrollIntoView({ block: 'start' });
  }
  function open(id, zoom) {
    var egg = document.getElementById('egg-' + id); if (!egg) return;
    var d = egg.querySelector('details'), found = egg.classList.contains('found');
    body.innerHTML = '<div class="egg-top">' + egg.querySelector('.egg-top').innerHTML + '</div><h3>' + egg.querySelector('h4').innerHTML + '</h3>'
      + (d ? [].slice.call(d.children).filter(function (x) { return x.tagName !== 'SUMMARY'; }).map(function (x) { return x.outerHTML; }).join('') : '')
      + (H.dataset.check === '1' ? '<button type="button" class="h2check' + (found ? ' on' : '') + '" data-id="' + id + '">' + (found ? '✓ Trouvé' : '✅ Je l\'ai trouvé') + '</button>' : '');
    sheet.hidden = false;
    H.querySelectorAll('.map .pin').forEach(function (p) { p.classList.toggle('sel', p.dataset.id === id); });
    var fig = H.querySelector('[data-map]'), pin = H.querySelector('.map .pin[data-id="' + id + '"]');
    if (zoom && fig && fig.gtvZoomTo && pin) { var m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(pin.getAttribute('transform')); if (m) fig.gtvZoomTo(+m[1], +m[2]); }
  }
  function close() { sheet.hidden = true; H.querySelectorAll('.map .pin.sel').forEach(function (p) { p.classList.remove('sel'); }); }
  H.addEventListener('click', function (ev) {
    var t = ev.target;
    var vb = t.closest('[data-v]'); if (vb) { view(vb.dataset.v); return; }
    var tm = t.closest('.tomap'); if (tm) { view('map'); open(tm.dataset.id, true); return; }
    var pin = t.closest('.map .pin'); if (pin) { ev.preventDefault(); open(pin.dataset.id); return; }
    if (t.closest('.h2x')) { close(); return; }
    var sb = t.closest('.h2check'); if (sb) { var c = document.querySelector('#egg-' + sb.dataset.id + ' .check'); if (c) { c.click(); open(sb.dataset.id); } }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  var eggs = [].slice.call(H.querySelectorAll('.egg')), hide = document.getElementById('egg-hide');
  function sync() {
    var n = eggs.filter(function (e) { return e.classList.contains('found'); }).length, el = document.getElementById('h2n');
    if (el) { el.textContent = n + '/' + eggs.length; document.getElementById('h2fill').style.width = (eggs.length ? n / eggs.length * 100 : 0) + '%'; }
    if (hide) { eggs.forEach(function (e) { e.hidden = hide.checked && e.classList.contains('found'); });
      H.querySelectorAll('.egg-group').forEach(function (g) { g.hidden = !g.querySelector('.egg:not([hidden])'); }); }
  }
  if (hide) hide.addEventListener('change', sync);
  new MutationObserver(sync).observe(H, { subtree: true, attributes: true, attributeFilter: ['class'] });
  sync();
  if (location.hash.indexOf('#egg-') === 0) setTimeout(function () { open(location.hash.slice(5), true); }, 80);
})();

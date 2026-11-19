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

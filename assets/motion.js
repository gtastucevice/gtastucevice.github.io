/* GTASTUCE VICE – motion design. Léger, sans librairie. */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Palmiers en silhouette dans la une (accueil) */
  var une = document.querySelector('.une');
  if (une && !une.querySelector('.palms')) {
    var palm = function (x, h, s) {
      var top = 360 - h, fr = '';
      [[-70, 10], [-35, -18], [0, -26], [35, -18], [70, 10], [-55, 32], [55, 32]].forEach(function (f) {
        fr += '<path d="M' + x + ' ' + top + ' q' + (f[0] * .5 * s) + ' ' + (f[1] - 30) * s + ' ' + f[0] * s + ' ' + (f[1] + 10) * s +
          ' q' + (-f[0] * .45 * s) + ' ' + (-18 * s) + ' ' + (-f[0] * s) + ' ' + (-(f[1] + 10) * s) + 'z"/>';
      });
      return '<path d="M' + (x - 4 * s) + ' 360 Q' + (x - 14 * s) + ' ' + (top + h * .5) + ' ' + x + ' ' + top +
        ' L' + (x + 5 * s) + ' ' + top + ' Q' + (x - 6 * s) + ' ' + (top + h * .5) + ' ' + (x + 6 * s) + ' 360z"/>' + fr;
    };
    var svg = '<svg class="palms" viewBox="0 0 520 360" preserveAspectRatio="xMaxYMax meet" aria-hidden="true"><g fill="#0B0420">' +
      palm(380, 300, 1.15) + palm(470, 230, .9) + palm(300, 190, .7) + '</g></svg>';
    une.insertAdjacentHTML('afterbegin', svg);
  }

  if (reduce || document.documentElement.classList.contains('no-motion')) return;
  document.documentElement.classList.add('mo');

  /* Parallaxe douce sur le soleil et les palmiers */
  if (une) {
    var ticking = false;
    addEventListener('scroll', function () {
      if (ticking) return; ticking = true;
      requestAnimationFrame(function () {
        var y = Math.min(scrollY, 600);
        une.style.setProperty('--sy', y + 'px');
        ticking = false;
      });
    }, { passive: true });
  }

  /* Apparition au défilement */
  var SEL = '.post,.mini,.lead,.fact,.egg,h2.sec,.score,.map,.topics a,.duo video,.nl-in,.propose,article.full>img';
  if (!('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px', threshold: .08 });
  var prep = function (root) {
    var groups = new Map();
    root.querySelectorAll(SEL).forEach(function (el) {
      if (el.classList.contains('rv')) return;
      var p = el.parentElement, i = groups.get(p) || 0; groups.set(p, i + 1);
      el.style.setProperty('--d', Math.min(i, 6) * 0.07 + 's');
      el.classList.add('rv'); io.observe(el);
    });
  };
  prep(document);
  /* Un élément qui reçoit le focus clavier s'affiche tout de suite (il restait invisible pendant l'animation) */
  document.addEventListener('focusin', function (ev) { var el = ev.target.closest && ev.target.closest('.rv'); if (el) el.classList.add('in'); });
  /* Ce qui est rendu plus tard (filtres, chasse aux secrets) s'affiche directement, sans rejouer l'animation */
  var ready = false; setTimeout(function () { ready = true; }, 1500);
  new MutationObserver(function (ms) {
    ms.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        if (!ready) { prep(n.parentElement || document); return; }
        [n].concat([].slice.call(n.querySelectorAll ? n.querySelectorAll(SEL) : [])).forEach(function (el) {
          if (el.matches && el.matches(SEL)) el.classList.add('rv', 'in');
        });
      });
    });
  }).observe(document.body, { childList: true, subtree: true });

  /* Chasse aux secrets : « tampon » sur le secret coché + score qui rebondit */
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.check'); if (!b) return;
    var id = b.dataset.id;
    setTimeout(function () {
      var c = document.getElementById('egg-' + id), sc = document.getElementById('sc');
      if (c && c.classList.contains('found')) { c.classList.remove('stamp'); void c.offsetWidth; c.classList.add('stamp'); }
      if (sc) { sc.classList.remove('bump'); void sc.offsetWidth; sc.classList.add('bump'); }
    }, 0);
  }, true);
})();

/* Vico : bulle mot à mot, encadrés qui apparaissent au défilement */
(function () {
  var html = document.documentElement;
  if (!html.classList.contains('mo')) return;
  document.querySelectorAll('.vico-guide .bulle').forEach(function (b) {
    var i = 0;
    b.querySelectorAll('[data-w]').forEach(function (el) {
      el.innerHTML = el.textContent.split(' ').map(function (w) { return '<span class="bt" style="--i:' + (i++) + '">' + w + '</span>'; }).join(' ');
    });
  });
  var boxes = document.querySelectorAll('.vico-box');
  if (!('IntersectionObserver' in window)) { boxes.forEach(function (b) { b.classList.add('in'); }); return; }
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { threshold: .25 });
  boxes.forEach(function (b) { io.observe(b); });
})();

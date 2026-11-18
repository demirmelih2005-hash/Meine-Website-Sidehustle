/* Kleine Helfer für die Kunden-Websites. Läuft ohne Bibliotheken und ohne Tracking. */
(function () {
  var doc = document.documentElement;
  doc.classList.remove('no-js');

  // Menü auf dem Handy
  var toggle = document.querySelector('.menu-toggle'), nav = document.getElementById('nav');
  function menu(auf) {
    if (!toggle || !nav) return;
    nav.classList.toggle('open', auf);
    document.body.classList.toggle('menu-open', auf);
    toggle.setAttribute('aria-expanded', auf ? 'true' : 'false');
  }
  if (toggle && nav) {
    toggle.addEventListener('click', function () { menu(!nav.classList.contains('open')); });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) menu(false); });
    nav.addEventListener('focusout', function (e) { if (nav.classList.contains('open') && !nav.contains(e.relatedTarget) && e.relatedTarget !== toggle) menu(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('open')) { menu(false); toggle.focus(); } });
    window.addEventListener('resize', function () { if (window.innerWidth > 900) menu(false); });
  }

  // Kopfzeile bekommt beim Scrollen eine Linie, Schwebe-Knopf erscheint (aber nicht über Abschluss-Band und Fußbereich)
  var header = document.querySelector('.site-header'), floatBtn = document.querySelector('.float-cta');
  var verdeckt = false;
  function onScroll() {
    var y = window.scrollY || 0;
    if (header) header.classList.toggle('scrolled', y > 8);
    if (floatBtn) floatBtn.classList.toggle('show', y > 420 && !verdeckt);
  }
  if (floatBtn && 'IntersectionObserver' in window) {
    var sichtbar = new Set();
    var io = new IntersectionObserver(function (eintraege) {
      eintraege.forEach(function (en) { if (en.isIntersecting) sichtbar.add(en.target); else sichtbar.delete(en.target); });
      verdeckt = sichtbar.size > 0; onScroll();
    });
    document.querySelectorAll('.cta-band, .site-footer').forEach(function (el) { io.observe(el); });
  }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // Öffnungszeiten: Status und heutiger Tag, immer nach Kölner Uhrzeit
  var dataEl = document.getElementById('oeffnungszeiten');
  if (!dataEl) return;
  var zeiten; try { zeiten = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var KURZ = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
  var now = new Date(), teile = {};
  try {
    new Intl.DateTimeFormat('de-DE', { timeZone: 'Europe/Berlin', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(now).forEach(function (p) { teile[p.type] = p.value; });
  } catch (e) {}
  var wd = teile.weekday ? KURZ.indexOf(teile.weekday.replace('.', '').slice(0, 2)) : (now.getDay() + 6) % 7;
  if (wd < 0) wd = (now.getDay() + 6) % 7;
  var mins = teile.hour ? parseInt(teile.hour, 10) * 60 + parseInt(teile.minute, 10) : now.getHours() * 60 + now.getMinutes();
  function toMin(s) { var a = s.split(':'); return parseInt(a[0], 10) * 60 + parseInt(a[1], 10); }

  document.querySelectorAll('.hours tr[data-tag="' + wd + '"]').forEach(function (r) { r.classList.add('today'); r.setAttribute('aria-current', 'date'); });

  function status() {
    var gestern = zeiten[(wd + 6) % 7];
    if (gestern && toMin(gestern[1]) <= toMin(gestern[0]) && mins < toMin(gestern[1]))
      return { offen: true, text: 'Jetzt geöffnet · bis ' + gestern[1] + ' Uhr' };
    var h = zeiten[wd];
    if (h) {
      var von = toMin(h[0]), bis = toMin(h[1]); if (bis <= von) bis += 1440;
      if (mins >= von && mins < bis) return { offen: true, text: 'Jetzt geöffnet · bis ' + h[1] + ' Uhr' };
      if (mins < von) return { offen: false, text: 'Heute ab ' + h[0] + ' Uhr geöffnet' };
    }
    for (var i = 1; i <= 7; i++) {
      var d = (wd + i) % 7, z = zeiten[d];
      if (z) return { offen: false, text: 'Geschlossen · ' + (i === 1 ? 'morgen' : KURZ[d]) + ' ab ' + z[0] + ' Uhr' };
    }
    return null;
  }
  var s = status();
  if (!s) return;
  document.querySelectorAll('[data-status]').forEach(function (el) {
    el.hidden = false;
    el.classList.toggle('closed', !s.offen);
    var t = el.querySelector('span'); if (t) t.textContent = s.text;
  });
})();

/* Keep reading position across the language switch (#145): EN/VI heading
 * ids differ, so the switcher href carries the section index (`?section=N`
 * plus the real `#fragment`); the counterpart scrolls to its Nth section
 * when the fragment has no match there. No-JS behaviour is unchanged
 * (counterpart top). No redirects; the query is dropped after landing.
 */
(function () {
  var PARAM = 'section';
  var SEL = '.post-content h2[id], .post-content h3[id]';
  var TOP = 120; // a heading counts as current once past this viewport offset
  function list() {
    return Array.prototype.slice.call(document.querySelectorAll(SEL));
  }
  function byId(id) {
    try { return document.getElementById(decodeURIComponent(id)); }
    catch (e) { return null; }
  }
  // Fragment pointing at a section wins, else nearest section above the
  // viewport; -1 means top: switch plainly, like without JS.
  function current(ix) {
    var h = (location.hash || '').slice(1);
    if (h) return ix.indexOf(byId(h));
    var y = window.scrollY || window.pageYOffset || 0;
    var best = -1;
    for (var i = 0; i < ix.length; i++) {
      if (ix[i].getBoundingClientRect().top + y <= y + TOP) best = i;
      else break;
    }
    return best;
  }
  function baseOf(href) {
    var cut = href.length;
    var q = href.indexOf('?');
    var h = href.indexOf('#');
    if (q !== -1) cut = Math.min(cut, q);
    if (h !== -1) cut = Math.min(cut, h);
    return href.slice(0, cut);
  }
  // Rewrite the switcher href so even a new-tab open carries the position.
  // The click handler runs before navigation, so a plain left-click needs
  // no preventDefault; modifier-clicks reuse the last scroll refresh.
  function refresh(link, ix) {
    var at = current(ix);
    var base = baseOf(link.getAttribute('href'));
    if (at < 0 || at >= ix.length) {
      if (link.getAttribute('href') !== base) link.setAttribute('href', base);
      return;
    }
    link.setAttribute('href', base + '?' + PARAM + '=' + at + '#' + ix[at].id);
  }
  function enhance(link) {
    if (!list().length) return;
    var ticking = false;
    function later() {
      ticking = false;
      refresh(link, list());
    }
    function schedule() {
      if (!ticking) {
        ticking = true;
        (window.requestAnimationFrame || setTimeout)(later);
      }
    }
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('hashchange', schedule);
    link.addEventListener('click', function () { refresh(link, list()); });
    schedule();
  }
  // Counterpart landing: a matching fragment already scrolled natively, so
  // only drop the query; otherwise the Nth section is the parallel
  // translation of the section left behind, so scroll there and adopt its
  // real anchor. Anything unusable lands at top, exactly like today.
  function land() {
    var params;
    try { params = new URLSearchParams(location.search); }
    catch (e) { return; }
    if (!params.has(PARAM)) return;
    var at = parseInt(params.get(PARAM), 10);
    params.delete(PARAM);
    var rest = params.toString();
    var stem = location.pathname + (rest ? '?' + rest : '');
    var h = (location.hash || '').slice(1);
    var clean = stem + location.hash;
    if (!(h && byId(h))) {
      var ix = list();
      if (at >= 0 && at < ix.length) {
        ix[at].scrollIntoView();
        clean = stem + '#' + ix[at].id;
      } else {
        clean = stem;
      }
    }
    try { history.replaceState(null, '', clean); }
    catch (e) {}
  }
  function run() {
    land();
    var link = document.querySelector('.lang-switcher');
    if (link) enhance(link);
  }
  window.SiteUtils.onReady(run);
})();

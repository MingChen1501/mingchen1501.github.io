/* Shared helpers (#246): one clipboard-copy, DOM-ready and lang-sniff for
 * the deferred scripts. No dependency, no build step. Loads first with the
 * `?v=` token like every other fixed-URL asset (#61).
 */
(function () {
  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else { fn(); }
  }
  function isVietnamese() {
    var lang = (document.documentElement.lang || 'en').toLowerCase();
    return lang === 'vi' || lang.indexOf('vi-') === 0;
  }
  function fallbackCopy(text, done) {
    var area = document.createElement('textarea');
    area.value = text;
    area.readOnly = true;
    area.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(area);
    area.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(area);
    done();
  }
  function copyText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else { fallbackCopy(text, done); }
  }
  window.SiteUtils = { onReady: onReady, isVietnamese: isVietnamese, copyText: copyText };
})();

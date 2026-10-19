/* Copy-code button (#126): wraps each `pre > code`, adds a localized button.
 * No JS means no button. Clipboard API with a textarea fallback.
 */
(function () {
  var lang = (document.documentElement.lang || 'en').toLowerCase();
  var vi = lang === 'vi' || lang.indexOf('vi-') === 0;
  var COPY = vi ? 'Sao chép mã' : 'Copy code';
  var DONE = vi ? 'Đã sao chép' : 'Copied';
  function setLabel(btn, label) {
    btn.textContent = label;
    btn.setAttribute('aria-label', label);
  }
  function fallback(text, done) {
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
  function write(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
    } else { fallback(text, done); }
  }
  function enhance(code) {
    var pre = code.parentNode;
    if (pre.parentNode.className === 'copy-code') return;
    var wrap = document.createElement('div');
    wrap.className = 'copy-code';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-code__button';
    setLabel(btn, COPY);
    wrap.appendChild(btn);
    var timer = null;
    btn.addEventListener('click', function () {
      write(code.innerText || code.textContent, function () {
        setLabel(btn, DONE);
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () { setLabel(btn, COPY); }, 2000);
      });
    });
  }
  function run() { document.querySelectorAll('pre > code').forEach(enhance); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else { run(); }
})();

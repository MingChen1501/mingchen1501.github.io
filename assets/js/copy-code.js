/* Copy-code button (#126): wraps each `pre > code`, adds a localized button.
 * No JS means no button. Copy, DOM-ready and lang sniff via `site-utils.js`.
 */
(function () {
  var Utils = window.SiteUtils;
  var vi = Utils.isVietnamese();
  var COPY = vi ? 'Sao chép mã' : 'Copy code';
  var DONE = vi ? 'Đã sao chép' : 'Copied';
  function setLabel(btn, label) {
    btn.textContent = label;
    btn.setAttribute('aria-label', label);
  }
  function write(text, done) {
    Utils.copyText(text, done);
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
  Utils.onReady(run);
})();

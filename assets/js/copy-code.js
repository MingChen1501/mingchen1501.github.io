/* Copy-code button (#126, #257): wraps each `pre > code`, adds a localized button.
 * No JS means no button. Copy, DOM-ready and lang sniff via `site-utils.js`.
 * Success feedback is announced through a per-block polite live region (#257)
 * reusing the DONE strings; the button itself stays outside any live region
 * so one copy announces exactly once.
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
    var status = document.createElement('p');
    status.className = 'copy-code__status visually-hidden';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    wrap.appendChild(status);
    var timer = null;
    btn.addEventListener('click', function () {
      write(code.innerText || code.textContent, function () {
        setLabel(btn, DONE);
        status.textContent = DONE;
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () {
          setLabel(btn, COPY);
          status.textContent = '';
        }, 2000);
      });
    });
  }
  function run() { document.querySelectorAll('pre > code').forEach(enhance); }
  Utils.onReady(run);
})();

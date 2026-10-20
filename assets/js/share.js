/* Share row (#222): copy-link plus the Web Share API where supported.
 * The X / Facebook / LinkedIn intent links are plain anchors and work
 * without JS. This script only wires the two buttons:
 * - copy: Clipboard API with a textarea + execCommand fallback (same shape
 *   as `assets/js/copy-code.js`), then the localized confirmation from
 *   `data-copied-label` on the button and in the `role="status"` line;
 * - native share: the `data-share-native-item` row stays `hidden` unless
 *   `navigator.share` exists, so browsers without it never see a dead
 *   control. A dismissed sheet (AbortError) stays silent.
 */
(function () {
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
  function writeText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else { fallbackCopy(text, done); }
  }
  function run() {
    document.querySelectorAll('.share').forEach(function (section) {
      var status = section.querySelector('.share__status');
      var copy = section.querySelector('.share__copy');
      if (copy) {
        var url = copy.getAttribute('data-share-url');
        var idle = copy.textContent;
        var doneLabel = copy.getAttribute('data-copied-label') || 'Copied';
        var timer = null;
        copy.addEventListener('click', function () {
          writeText(url, function () {
            copy.textContent = doneLabel;
            copy.setAttribute('aria-label', doneLabel);
            if (status) status.textContent = doneLabel;
            if (timer) clearTimeout(timer);
            timer = setTimeout(function () {
              copy.textContent = idle;
              copy.setAttribute('aria-label', idle);
              if (status) status.textContent = '';
            }, 2000);
          });
        });
      }
      var nativeItem = section.querySelector('[data-share-native-item]');
      var native = section.querySelector('.share__native');
      if (nativeItem && native && navigator.share) {
        var shareUrl = native.getAttribute('data-share-url');
        var shareTitle = native.getAttribute('data-share-title') || '';
        nativeItem.hidden = false;
        native.addEventListener('click', function () {
          try {
            var result = navigator.share({ title: shareTitle, text: shareTitle, url: shareUrl });
            if (result && result.catch) result.catch(function () {});
          } catch (e) {}
        });
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else { run(); }
})();

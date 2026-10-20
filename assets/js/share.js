/* Share row (#222, #244): copy-link plus the Web Share API where supported.
 * The X / Facebook / LinkedIn intent links are plain anchors and work
 * without JS. This script only wires the two buttons:
 * - copy: the `data-share-copy-item` row ships `hidden` and is revealed
 *   here, so without JS there is no dead control (a `noscript` fallback
 *   shows the canonical URL as a plain link instead). Copying uses the
 *   Clipboard API with a textarea + execCommand fallback (shared
 *   `site-utils.js` helper, #246), then the localized confirmation from
 *   `data-copied-label` on the button and in the `role="status"` line;
 * - native share: the `data-share-native-item` row stays `hidden` unless
 *   `navigator.share` exists, so browsers without it never see a dead
 *   control. A dismissed sheet (AbortError) stays silent.
 */
(function () {
  var Utils = window.SiteUtils;
  function writeText(text, done) {
    Utils.copyText(text, done);
  }
  function run() {
    document.querySelectorAll('.share').forEach(function (section) {
      var status = section.querySelector('.share__status');
      var copyItem = section.querySelector('[data-share-copy-item]');
      var copy = section.querySelector('.share__copy');
      if (copyItem && copy) {
        copyItem.hidden = false;
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
  Utils.onReady(run);
})();

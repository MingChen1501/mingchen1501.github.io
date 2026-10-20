/* Lazy-load the content images (#86).
 *
 * Rule: inside every content block (.post-content / .page-content /
 * article.post) the FIRST image stays eager (it can be the LCP element) and
 * every following image becomes lazy. An image that already declares a
 * loading mode (e.g. the sidebar thumbnails) is never touched.
 */
(function () {
  var boxes = '.post-content, .page-content, article.post';
  function mark() {
    document.querySelectorAll(boxes).forEach(function (box) {
      box.querySelectorAll('img').forEach(function (img, i) {
        if (img.hasAttribute('loading')) return;
        img.setAttribute('loading', i === 0 ? 'eager' : 'lazy');
      });
    });
  }
  window.SiteUtils.onReady(mark);
})();

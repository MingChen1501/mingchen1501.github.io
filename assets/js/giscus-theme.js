/* Giscus theme sync (#258): repaint the comment iframe on the site theme.
 *
 * Giscus boots from the embed's `data-theme` (OS setting, the no-JS fallback
 * matching the `auto` skin), while the rest of the page follows the #220
 * toggle (`html[data-theme]` + localStorage). This deferred script closes
 * that gap without reloading the iframe:
 *
 * - it primes the embed's `data-theme` to the site-mapped Giscus theme
 *   (`data-light-theme`/`data-dark-theme` on the embed script, from
 *   `site.giscus.light_theme`/`dark_theme`), so a lazily-booted iframe
 *   starts on the right theme;
 * - it sends the Giscus `setConfig { theme }` postMessage to
 *   `iframe.giscus-frame` on every later flip — toggle clicks and live OS
 *   changes alike are observed through the `html[data-theme]` attribute the
 *   toggle owns, so there is no coupling to `theme-toggle.js` internals;
 * - a capturing `load` listener re-sends right when the lazy iframe
 *   finishes loading, covering boots that happen after this script ran.
 *
 * Without Giscus on the page the script returns immediately; when the
 * iframe is absent or `postMessage` is unavailable it silently keeps the
 * `data-theme` fallback. No dependencies, no framework — same shape as
 * `nav-toggle.js`.
 */
(function () {
  var embed = document.querySelector('script[src*="giscus.app"]');
  if (!embed) return;

  var ORIGIN = 'https://giscus.app';
  var lightTheme = embed.getAttribute('data-light-theme') || 'light';
  var darkTheme = embed.getAttribute('data-dark-theme') || 'dark';

  function siteTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? 'dark'
      : 'light';
  }

  function giscusTheme() {
    return siteTheme() === 'dark' ? darkTheme : lightTheme;
  }

  function prime() {
    try {
      embed.setAttribute('data-theme', giscusTheme());
    } catch (e) {
      /* Read-only DOM: the configured data-theme fallback stays. */
    }
  }

  function send() {
    try {
      var frame = document.querySelector('iframe.giscus-frame');
      if (!frame || !frame.contentWindow || !frame.contentWindow.postMessage) {
        return;
      }
      frame.contentWindow.postMessage(
        { giscus: { setConfig: { theme: giscusTheme() } } },
        ORIGIN
      );
    } catch (e) {
      /* Giscus unavailable: the primed data-theme fallback stays. */
    }
  }

  function sync() {
    prime();
    send();
  }

  sync();

  document.addEventListener(
    'load',
    function (event) {
      var target = event.target;
      if (
        target &&
        target.classList &&
        target.classList.contains('giscus-frame')
      ) {
        send();
      }
    },
    true
  );

  if ('MutationObserver' in window) {
    new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        if (mutations[i].attributeName === 'data-theme') {
          sync();
          break;
        }
      }
    }).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
  }
})();

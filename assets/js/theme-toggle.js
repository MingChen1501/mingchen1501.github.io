/* Theme toggle (#220): light/dark mode with OS-preference default.
 *
 * `_includes/head.html` runs a tiny inline bootstrap before first paint that
 * sets `html[data-theme]` from `localStorage` (or `prefers-color-scheme` on
 * first visit); this deferred script owns the `.theme-toggle` header button
 * from there on:
 *
 * - syncs `aria-pressed` plus the localized `aria-label`/`title` (carried as
 *   `data-label-dark`/`data-label-light`) with the painted theme, at load and
 *   on every flip;
 * - flips the theme on click and persists the explicit choice in
 *   `localStorage`, so it survives reloads and navigation;
 * - follows live OS changes only while the reader has no stored choice.
 *
 * No dependencies, no framework — same shape as `nav-toggle.js`.
 */
(function () {
  var STORAGE_KEY = 'theme';
  var button = document.querySelector('.theme-toggle');
  var media = window.matchMedia('(prefers-color-scheme: dark)');

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? 'dark'
      : 'light';
  }

  function readStored() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function sync() {
    if (!button) return;
    var dark = currentTheme() === 'dark';
    button.setAttribute('aria-pressed', dark ? 'true' : 'false');
    var label = dark
      ? button.getAttribute('data-label-light')
      : button.getAttribute('data-label-dark');
    if (label) {
      button.setAttribute('aria-label', label);
      button.setAttribute('title', label);
    }
  }

  if (button) {
    button.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (e) {
        /* Storage blocked: the theme still applies to this page. */
      }
      sync();
    });
  }

  function onSystemChange() {
    var stored = readStored();
    if (stored === 'light' || stored === 'dark') return;
    document.documentElement.setAttribute(
      'data-theme',
      media.matches ? 'dark' : 'light'
    );
    sync();
  }

  if (media.addEventListener) {
    media.addEventListener('change', onSystemChange);
  } else if (media.addListener) {
    media.addListener(onSystemChange);
  }

  sync();
})();

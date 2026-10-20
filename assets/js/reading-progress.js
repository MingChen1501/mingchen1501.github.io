/* Reading progress + back-to-top (#224): progressive enhancement for post
 * pages only. `_layouts/post.html` ships both controls with the `hidden`
 * attribute, so readers without JS see neither a dead 0% bar nor a dead
 * button; this script reveals the bar and drives both at runtime:
 *
 * - progress: the bar width (and `aria-valuenow`) tracks the article scroll
 *   position 0-100%. Pages shorter than the viewport have no scroll range
 *   (`max <= 0`) and report a full/complete 100% instead of dividing by
 *   zero or sticking at 0%.
 * - back-to-top: the button unhides past `SHOW_AFTER_PX` of scroll and
 *   returns to the top on activation — smooth-scrolled, unless the reader
 *   asked for reduced motion (`prefers-reduced-motion`), which jumps
 *   instantly. The pill keeps its native `<button>` keyboard behavior and
 *   focus; `hidden` keeps it out of the tab order while below threshold.
 * - labels follow the page language in the markup itself (`post_lang` in
 *   the layout renders "Back to top" / "Về đầu trang"), so the script
 *   carries no locale logic.
 */
(function () {
  var SHOW_AFTER_PX = 600;

  function run() {
    var track = document.querySelector('.reading-progress');
    var bar = document.querySelector('.reading-progress__bar');
    var button = document.querySelector('.back-to-top');
    if (!track || !bar || !button) {
      return;
    }

    var reduced = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function progress() {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = max > 0 ? window.scrollY / max : 1;
      if (ratio < 0) {
        ratio = 0;
      }
      if (ratio > 1) {
        ratio = 1;
      }
      var pct = Math.round(ratio * 100);
      bar.style.width = pct + '%';
      bar.setAttribute('aria-valuenow', String(pct));
    }

    function visibility() {
      button.hidden = window.scrollY < SHOW_AFTER_PX;
    }

    var scheduled = false;
    function update() {
      if (scheduled) {
        return;
      }
      scheduled = true;
      function apply() {
        scheduled = false;
        progress();
        visibility();
      }
      if (window.requestAnimationFrame) {
        window.requestAnimationFrame(apply);
      } else {
        apply();
      }
    }

    button.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
    });

    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    track.hidden = false;
    update();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();

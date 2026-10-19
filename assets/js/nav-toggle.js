/* Accessible mobile nav disclosure (#114).
 *
 * The header toggle is a real `<button aria-expanded aria-controls>` and the
 * menu is its panel. Markup ships open so readers without JS keep the full
 * menu; this script collapses it on small screens, toggles it on click, and
 * closes it on Escape (returning focus to the trigger).
 *
 * The toggle is only rendered on small screens (CSS hides it on desktop), so
 * its own visibility is the breakpoint — no duplicated media query here.
 */
(function () {
  var toggle = document.querySelector('.site-nav .nav-toggle');
  if (!toggle) return;
  var panel = document.getElementById(toggle.getAttribute('aria-controls'));
  if (!panel) return;
  function isMobile() {
    return window.getComputedStyle(toggle).display !== 'none';
  }
  function setOpen(open) {
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    panel.hidden = !open;
  }
  if (isMobile()) setOpen(false);
  toggle.addEventListener('click', function () {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isMobile() && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
})();

/* Accessible mobile nav disclosure (#114, #384).
 *
 * The header toggle is a real `<button aria-expanded aria-controls>` and the
 * menu is its panel. Markup ships collapsed (`aria-expanded="false"`, panel
 * `hidden`) and CSS under `html.js` keeps it shut through first paint, so
 * the menu never flashes open on slow loads; readers without JS match
 * `html.no-js` instead and keep the full menu. This script only opens the
 * panel from there: click toggles, Escape closes (returning focus), and
 * crossing to desktop marks it open so `aria-expanded` never contradicts
 * the always-visible desktop panel.
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
  // Desktop shows the panel by CSS even while `hidden` lingers, so mark it
  // open for AT; on mobile the shipped collapsed state is already correct.
  if (!isMobile()) setOpen(true);
  toggle.addEventListener('click', function () {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isMobile() && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  // Breakpoint crossings: entering desktop forces the open state so
  // `aria-expanded` never claims a visible panel is collapsed; returning
  // to mobile keeps the reader's last state, which is already consistent.
  window.addEventListener('resize', function () {
    if (!isMobile()) setOpen(true);
  });
})();

/* ToC phone FAB model (#383): the sheet module (split from `toc-spy.js`
 * in #417; the drag gesture lives in `toc-fab-drag.js`).
 *
 * On phone layouts the INLINE ToC goes away entirely: `_layouts/post.html`
 * ships a floating button + bottom sheet (both `hidden`, so no-JS readers
 * keep the inline collapsed ToC as fallback), and this module hides the
 * inline mount via `html.toc-fab-on`, moves its nav into the sheet slot,
 * reveals the button, and drives the decorative progress ring from the
 * article's own scrollable range (0% above the body, 100% at its end; the
 * label text carries the same value for AT). The desktop sidebar stays
 * open. Keyed off the visible mount, never a hardcoded width.
 *
 * Contract with the core (always loaded first): the core marks rows in
 * its own click listener (registered first, same task) and publishes
 * `window.TocSpy.core` (`mark`/`apply`/`schedule`). This module refreshes
 * through it on open, repaints the ring inside its tick (same tick, no
 * extra listener), registers `window.TocSpy.sheet` (`fab`, `sheet`,
 * `toggle`, `progress`) for that tick and the drag module, and adds its
 * own per-nav listener for row taps inside the sheet (shut, focus return,
 * `hashchange` arming — Firefox resets focus to the body as the
 * navigation lands). Without the core or the FAB markup this module is a
 * no-op and `TocSpy.sheet` stays null. The sheet shuts on its close
 * button, its backdrop, and Esc; focus moves into it on open and returns
 * to the button on close. The `role="dialog" aria-modal="true"` panel
 * traps Tab over rendered stops only (no `tabindex` juggling); while open
 * the covered landmarks go `inert` + `aria-hidden`, restored on every
 * close path. Auto-expansion never moves focus.
 *
 * Focus-ring modality (#400): the programmatic `fab.focus()` return after
 * a pointer close can still match `:focus-visible` in some engines, so
 * pointer-initiated closes mark the button with `toc-fab--no-focus-ring`
 * (a CSS rule outranking the accent without moving DOM focus) and the next
 * keydown drops the mark, keeping the visible ring for keyboard closes.
 */
(function () {
  var RING_C = 125.66;

  function run() {
    var core = window.TocSpy && window.TocSpy.core;
    if (!core) {
      return;
    }
    var navs = document.querySelectorAll('.post-toc__nav');
    if (!navs.length) {
      return;
    }
    // Phone FAB model (#383): on phone layouts the open inline list fills
    // most of the first viewport, so the inline mount goes away and the
    // floating button + sheet take over. Keyed off the visible mount,
    // never a hardcoded width; no-JS still ships the inline list (the
    // `toc-fab-on` class below is JS-only). The inline nav node itself
    // moves into the sheet slot, so the spy keeps marking the same nodes
    // with the same observer and tick — no second subscription anywhere.
    var fab = document.querySelector('[data-toc-fab]');
    var sheet = document.querySelector('[data-toc-sheet]');
    var slot = sheet ? sheet.querySelector('[data-toc-slot]') : null;
    if (!fab || !sheet || !slot) {
      return;
    }
    var ring = fab.querySelector('[data-toc-ring]');
    var fabLabel = fab.querySelector('[data-toc-fab-label]');
    var fabBase = fabLabel
      ? fabLabel.getAttribute('data-toc-fab-base') || ''
      : '';
    var closeBtn = sheet.querySelector('[data-toc-close]');
    var panel = sheet.querySelector('.toc-sheet__panel');
    var backdrop = sheet.querySelector('[data-toc-backdrop]');
    var article = document.querySelector('.post-content');
    var inlineMount = document.querySelector('.post-toc-mount--inline');
    var phone = !!inlineMount &&
      !(window.getComputedStyle(inlineMount).display === 'none');
    if (!phone) {
      return;
    }
    var inlineNav = inlineMount.querySelector('.post-toc__nav');
    if (inlineNav) {
      slot.appendChild(inlineNav);
    }
    document.documentElement.classList.add('toc-fab-on');
    fab.hidden = false;

    function fabProgress() {
      if (!ring || !fabLabel || !article || fab.hidden) {
        return;
      }
      var rect = article.getBoundingClientRect();
      var height = article.offsetHeight || rect.height;
      var start = rect.top + window.scrollY;
      var end = start + height - window.innerHeight;
      var ratio;
      if (end <= start) {
        ratio = window.scrollY >= start ? 1 : 0;
      } else {
        ratio = (window.scrollY - start) / (end - start);
        if (ratio < 0) {
          ratio = 0;
        }
        if (ratio > 1) {
          ratio = 1;
        }
      }
      var pct = Math.round(ratio * 100);
      ring.style.strokeDashoffset = String(RING_C * (1 - ratio));
      fabLabel.textContent = fabBase + ', ' + pct + '%';
    }

    // Row-tap focus return (#383): the tapped hash arms the return;
    // the `hashchange` listener below consumes it. Open/close disarm.
    var rowHash = null;

    // Covered landmarks: named explicitly because the sheet lives in the
    // article — inerting a shared ancestor would silence the panel too.
    // The FAB stays out (its own toggle; the trap keeps keyboard focus
    // inside, so inerting it would only yank the AT context).
    var COVERED_SELECTORS =
      '.site-header, .post-header, .post-content, .post-sidebar, ' +
      '.share, .comments';

    function setBackgroundModal(modal) {
      Array.prototype.forEach.call(
        document.querySelectorAll(COVERED_SELECTORS),
        function (el) {
          if (modal) {
            el.setAttribute('inert', '');
            el.setAttribute('aria-hidden', 'true');
          } else {
            el.removeAttribute('inert');
            el.removeAttribute('aria-hidden');
          }
        }
      );
    }

    // Tab trap (#383 review): the `aria-modal` panel owns Tab while open,
    // wrapping first-to-last over rendered stops only (`hidden` branches
    // never tab). Native links and buttons; the tab order stays untouched.
    var TRAP_SELECTOR = 'a[href], button:not([disabled])';

    function trapTab(event) {
      if (!panel) {
        return;
      }
      var stops = Array.prototype.filter.call(
        panel.querySelectorAll(TRAP_SELECTOR),
        function (el) {
          return el.getClientRects().length > 0;
        }
      );
      if (!stops.length) {
        event.preventDefault();
        return;
      }
      var first = stops[0];
      var last = stops[stops.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    function openSheet() {
      if (!sheet.hidden) {
        return;
      }
      rowHash = null;
      sheet.hidden = false;
      fab.setAttribute('aria-expanded', 'true');
      // Inert first: the opener (the FAB) is covered too, so focusing
      // the panel before this would blur right back out.
      setBackgroundModal(true);
      core.apply();
      if (closeBtn) {
        closeBtn.focus();
      }
    }

    // Focus-ring modality (#400): a programmatic focus return after a
    // pointer close can still match `:focus-visible`, so track the last
    // input modality and mark pointer-closed buttons instead.
    var pointerClose = false;
    document.addEventListener('pointerdown', function () {
      pointerClose = true;
    }, true);
    document.addEventListener('keydown', function () {
      pointerClose = false;
      fab.classList.remove('toc-fab--no-focus-ring');
    }, true);

    function returnFocusToFab() {
      if (pointerClose) {
        fab.classList.add('toc-fab--no-focus-ring');
      } else {
        fab.classList.remove('toc-fab--no-focus-ring');
      }
      fab.focus();
    }

    function closeSheet(refocus) {
      if (sheet.hidden) {
        return;
      }
      rowHash = null;
      sheet.hidden = true;
      fab.setAttribute('aria-expanded', 'false');
      // Restore before refocusing: the button is covered while open.
      setBackgroundModal(false);
      if (refocus !== false) {
        returnFocusToFab();
      }
    }

    function toggleSheet() {
      if (sheet.hidden) {
        openSheet();
      } else {
        closeSheet();
      }
    }

    // Register for the core tick and the drag module. Set before wiring
    // so no handler can observe a half-built sheet.
    window.TocSpy.sheet = {
      fab: fab,
      sheet: sheet,
      toggle: toggleSheet,
      progress: fabProgress
    };

    // Row taps inside the open sheet: the core listener (registered
    // first, same task) already marked the row — shut the sheet, hand
    // focus back, and arm the return for when the fragment lands
    // (Firefox resets focus to the body after this task, #383).
    Array.prototype.forEach.call(navs, function (nav) {
      nav.addEventListener('click', function (event) {
        var target = event.target;
        var link = target.closest
          ? target.closest('a[href^="#"]')
          : null;
        if (!link || !nav.contains(link)) {
          return;
        }
        if (!sheet.contains(link)) {
          return;
        }
        closeSheet(false);
        returnFocusToFab();
        rowHash = link.getAttribute('href');
      });
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        closeSheet();
      });
    }
    if (backdrop) {
      backdrop.addEventListener('click', function () {
        closeSheet();
      });
    }
    document.addEventListener('keydown', function (event) {
      if (sheet.hidden) {
        return;
      }
      if (event.key === 'Tab') {
        trapTab(event);
        return;
      }
      if (event.key === 'Escape' || event.key === 'Esc') {
        closeSheet();
      }
    });
    // The tapped fragment lands after the tap task: refocus then
    // (Firefox resets focus to the body). Pending tap only (#383).
    window.addEventListener('hashchange', function () {
      if (rowHash !== null && window.location.hash === rowHash) {
        rowHash = null;
        returnFocusToFab();
      }
    });

    // The core's initial `apply` ran before this module revealed the
    // button, so its ring paint was skipped: schedule one now that the
    // FAB is visible. Identical first paint, same tick as the spy.
    core.schedule();
  }

  window.TocSpy = window.TocSpy || {};
  if (!('sheet' in window.TocSpy)) {
    window.TocSpy.sheet = null;
  }
  window.SiteUtils.onReady(run);
})();

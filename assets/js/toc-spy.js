/* ToC nested disclosure with scroll-spy (#345) and the phone FAB model
 * (#383). `_includes/post-toc.html` renders a NESTED list (children
 * `<ul>`s as real descendants of their parent `<li>`) starting FULLY
 * EXPANDED (`<details open>`, every branch `aria-expanded="true"`, no
 * `hidden`): without JS every level is visible and every anchor works.
 * This script owns collapsing/auto-expansion: init collapses every branch
 * (H2-only default; `hidden` keeps shut subtrees out of the a11y tree).
 * On phone layouts the INLINE copy goes away entirely: `_layouts/post.html`
 * ships a floating button + bottom sheet (both `hidden`, so no-JS readers
 * keep the inline collapsed ToC from #382 as their fallback), and this
 * script — the same one, no second observer — hides the inline mount via
 * `html.toc-fab-on`, moves its nav into the sheet slot, reveals the
 * button, and drives the decorative progress ring from the article's own
 * scrollable range (0% above the body, 100% at its end; the label text
 * carries the same value for AT). The desktop sidebar copy stays open.
 * The scroll-spy rule (last heading past the viewport top wins; offset
 * from the measured `.site-header` height when sticky/fixed, else a small
 * slack — the header is non-sticky, pinned by a static guard) marks one
 * row per mount (`aria-current="location"`, sidebar plus sheet together),
 * auto-expands the active branch plus ancestors, collapses auto-opened
 * branches on leave unless pinned by hand (`data-manual` survives until
 * the next explicit toggle), and keeps the active row inside the sheet via
 * the moved nav's own scrollTop (the page itself never moves).
 * Triggers: `IntersectionObserver` plus a passive rAF-throttled
 * scroll/resize fallback; link clicks mark immediately and shut the
 * sheet. The sheet shuts on its close button, its backdrop, and Esc;
 * focus moves into it on open and returns to the button on close — a
 * row tap returns focus at once and again on `hashchange` (Firefox
 * resets focus to the body as the navigation lands). The panel keeps
 * `role="dialog" aria-modal="true"` with a real focus trap rather than
 * dropping to a plain disclosure: a modal promise without a trap lets
 * Tab wander behind the backdrop, which is worse for AT users than no
 * dialog role — and the trap is one keydown branch over the panel's own
 * links and buttons (no second subscription, no `tabindex` juggling),
 * so it cannot drift out of sync. While open, the covered landmarks go
 * `inert` (tab order + a11y tree where implemented) and `aria-hidden`
 * (older AT), restored on every close path.
 * Opening the sheet never moves focus by itself beyond that handoff, and
 * auto-expansion never moves focus at all. Anchor jumps stay instant, so
 * there is nothing for `prefers-reduced-motion` to disable here (the ring
 * transition is pinned in CSS). Real `<button>` toggles give Enter/Space
 * natively; `tabindex` and the desktop outer `details[open]` are never
 * touched.
 *
 * Draggable FAB experiment (#401): on phone layouts the button drags
 * with pointer/touch input and snaps to the nearest horizontal edge on
 * release (left by default, right stacked above back-to-top via
 * `.toc-fab--right`), persisted in `localStorage` with a left default
 * and a silent fallback when storage is unavailable. A press that moves
 * within FAB_DRAG_THRESHOLD_PX still counts as a tap and opens the
 * sheet; a longer move never opens it (its click is swallowed). Drag is
 * pointer-only by design: keyboard users keep the unchanged native
 * button (Tab-reachable, Enter/Space-operable) resting at the default
 * edge, so no separate keyboard drag path is needed. Dragging never
 * touches the sheet, the trap, or the ring — it only flips the edge
 * class while the sheet stays shut. A native drag tripped by a FAB
 * press (article images under the floating button stay draggable) is
 * swallowed while the press is in flight, so it cannot pointercancel
 * the gesture.
 */
(function () {
  var EDGE_PX = 24;
  var RING_C = 125.66;

  function headerOffset() {
    var header = document.querySelector('.site-header');
    if (!header) {
      return EDGE_PX;
    }
    var position = window.getComputedStyle
      ? window.getComputedStyle(header).position
      : 'static';
    if (position === 'sticky' || position === 'fixed') {
      return Math.ceil(header.getBoundingClientRect().height) + EDGE_PX;
    }
    return EDGE_PX;
  }

  function setBranch(toggle, list, open) {
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    var showLabel = toggle.getAttribute('data-label-show');
    var hideLabel = toggle.getAttribute('data-label-hide');
    if (showLabel && hideLabel) {
      toggle.setAttribute('aria-label', open ? hideLabel : showLabel);
    }
    list.hidden = !open;
  }

  function run() {
    var navs = document.querySelectorAll('.post-toc__nav');
    if (!navs.length) {
      return;
    }
    // One entry per target id, gathering every mount's link for it, so a
    // single recompute marks both copies together. Links whose target is
    // missing stay out (a row with no section marks nothing).
    var entries = [];
    var byId = {};
    Array.prototype.forEach.call(navs, function (nav) {
      Array.prototype.forEach.call(
        nav.querySelectorAll('a[href^="#"]'),
        function (link) {
          var id = link.getAttribute('href').slice(1);
          var entry = byId[id];
          if (!entry) {
            var heading =
              id && document.getElementById(decodeURIComponent(id));
            if (!heading) {
              return;
            }
            entry = { id: id, heading: heading, links: [] };
            byId[id] = entry;
            entries.push(entry);
          }
          entry.links.push(link);
        }
      );
    });
    if (!entries.length) {
      return;
    }

    // Collapse every branch list on load: the default view is H2 only.
    // The static markup ships expanded (no-JS contract), so this is the
    // single place that hides anything.
    Array.prototype.forEach.call(navs, function (nav) {
      Array.prototype.forEach.call(
        nav.querySelectorAll('.post-toc__toggle'),
        function (toggle) {
          var list = document.getElementById(
            toggle.getAttribute('aria-controls')
          );
          if (!list) {
            return;
          }
          setBranch(toggle, list, false);
        }
      );
    });

    // Phone FAB model (#383): the open inline list fills most of the first
    // phone viewport (audit 2026-10-22: 510px, 73% of 700px), so on phone
    // layouts the inline mount goes away and the floating button + sheet
    // take over. Keyed off the visible mount, never a hardcoded width; the
    // desktop sidebar copy stays open, and no-JS still ships the inline
    // list (the `toc-fab-on` class below is JS-only). The inline nav node
    // itself moves into the sheet slot, so the spy keeps marking the same
    // nodes — one `aria-current` per visible mount, same observer, same
    // rAF tick, no second subscription anywhere.
    var fab = document.querySelector('[data-toc-fab]');
    var sheet = document.querySelector('[data-toc-sheet]');
    var slot = sheet ? sheet.querySelector('[data-toc-slot]') : null;
    var ring = fab ? fab.querySelector('[data-toc-ring]') : null;
    var fabLabel = fab ? fab.querySelector('[data-toc-fab-label]') : null;
    var fabBase = fabLabel
      ? fabLabel.getAttribute('data-toc-fab-base') || ''
      : '';
    var closeBtn = sheet ? sheet.querySelector('[data-toc-close]') : null;
    var panel = sheet ? sheet.querySelector('.toc-sheet__panel') : null;
    var backdrop = sheet
      ? sheet.querySelector('[data-toc-backdrop]')
      : null;
    var article = document.querySelector('.post-content');
    var inlineMount = document.querySelector('.post-toc-mount--inline');
    var phone = !!inlineMount &&
      !(window.getComputedStyle(inlineMount).display === 'none');
    var fabOn = !!(fab && sheet && slot && phone);
    if (fabOn) {
      var inlineNav = inlineMount.querySelector('.post-toc__nav');
      if (inlineNav) {
        slot.appendChild(inlineNav);
      }
      document.documentElement.classList.add('toc-fab-on');
      fab.hidden = false;
    }

    function fabProgress() {
      if (!fabOn || !ring || !fabLabel || !article || fab.hidden) {
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

    // Covered landmarks (#383 review): named explicitly because the
    // sheet itself lives in the article — inerting a shared ancestor
    // would silence the panel too. The FAB stays out: it is the sheet's
    // own toggle (it owns the panel via `aria-controls` and click
    // toggles it shut), and the Tab trap already keeps keyboard focus
    // inside — inerting it would only yank the AT context from its label.
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

    // Tab trap (#383 review): the `aria-modal` panel owns Tab while
    // open, wrapping first-to-last both ways over rendered stops only
    // (collapsed branches are `hidden`, so their rows never tab). Every
    // stop is a native link or button; the tab order itself stays
    // untouched.
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
      if (!fabOn || !sheet.hidden) {
        return;
      }
      rowHash = null;
      sheet.hidden = false;
      fab.setAttribute('aria-expanded', 'true');
      // Inert first: the opener (the FAB) is covered too, so focusing
      // the panel before this would blur right back out.
      setBackgroundModal(true);
      apply();
      if (closeBtn) {
        closeBtn.focus();
      }
    }

    // Focus-ring modality (#400): the programmatic `fab.focus()` return
    // after a pointer close can still match `:focus-visible` in some
    // engines, leaving the accent ring stuck on the FAB (tapping the FAB
    // itself to close was the reported path). Track the last input
    // modality instead of guessing from the engine: pointer-initiated
    // closes mark the button with `toc-fab--no-focus-ring` (a CSS rule
    // that outranks the `:focus-visible` accent without moving DOM
    // focus), and the next keydown drops the mark so keyboard closes
    // keep their visible ring. Clicks with no pointer behind them
    // (keyboard activation, assistive tech) default to the ring.
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
      if (!fabOn || sheet.hidden) {
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

    var activeId = null;

    function mark(id) {
      if (id === activeId || !byId[id]) {
        return;
      }
      activeId = id;
      for (var i = 0; i < entries.length; i++) {
        var on = entries[i].id === id;
        for (var j = 0; j < entries[i].links.length; j++) {
          if (on) {
            entries[i].links[j].setAttribute('aria-current', 'location');
          } else {
            entries[i].links[j].removeAttribute('aria-current');
          }
        }
      }
    }

    // Expand the active branch and its ancestors in one mount; collapse
    // branches the auto logic opened that no longer hold the active row.
    // Branches the reader pinned by hand (`data-manual`) are never
    // touched: manual intent wins until the next explicit toggle.
    function syncBranches(nav, id) {
      var activeLink = null;
      var links = nav.querySelectorAll('a[href^="#"]');
      for (var i = 0; i < links.length; i++) {
        if (links[i].getAttribute('href') === '#' + id) {
          activeLink = links[i];
          break;
        }
      }
      Array.prototype.forEach.call(
        nav.querySelectorAll('.post-toc__toggle'),
        function (toggle) {
          if (toggle.getAttribute('data-manual') === 'true') {
            return;
          }
          var list = document.getElementById(
            toggle.getAttribute('aria-controls')
          );
          if (!list) {
            return;
          }
          var holdsActive = !!activeLink && list.contains(activeLink);
          var open = toggle.getAttribute('aria-expanded') === 'true';
          if (holdsActive && !open) {
            setBranch(toggle, list, true);
            toggle.setAttribute('data-auto', 'true');
          } else if (
            !holdsActive &&
            open &&
            toggle.getAttribute('data-auto') === 'true'
          ) {
            setBranch(toggle, list, false);
            toggle.removeAttribute('data-auto');
          }
        }
      );
      // Bounded sheet panel (#383, as #377 before it): the moved nav caps
      // with its own scroll. Nudge ONLY the panel's scrollTop — the page
      // itself never moves (the #345 no-page-move rule still holds).
      if (activeLink && nav.scrollHeight > nav.clientHeight + 1) {
        var panel = nav.getBoundingClientRect();
        var cell = activeLink.getBoundingClientRect();
        if (cell.top < panel.top) {
          nav.scrollTop -= panel.top - cell.top + 8;
        } else if (cell.bottom > panel.bottom) {
          nav.scrollTop += cell.bottom - panel.bottom + 8;
        }
      }
    }

    function apply() {
      var line = window.scrollY + headerOffset();
      var active = entries[0];
      for (var i = 0; i < entries.length; i++) {
        var top =
          entries[i].heading.getBoundingClientRect().top + window.scrollY;
        if (top <= line) {
          active = entries[i];
        } else {
          break;
        }
      }
      // A short tail section may never reach the viewport top: once the
      // page is scrolled to the end, the last heading counts as current.
      var atEnd = window.innerHeight + window.scrollY >=
        document.documentElement.scrollHeight - 2;
      var id = atEnd ? entries[entries.length - 1].id : active.id;
      mark(id);
      Array.prototype.forEach.call(navs, function (nav) {
        syncBranches(nav, id);
      });
      // The ring keeps tracking while the sheet stays shut: same tick, no
      // extra listener, reads batched above before the style write.
      fabProgress();
    }

    var scheduled = false;
    function schedule() {
      if (scheduled) {
        return;
      }
      scheduled = true;
      function flush() {
        scheduled = false;
        apply();
      }
      if (window.requestAnimationFrame) {
        window.requestAnimationFrame(flush);
      } else {
        flush();
      }
    }

    Array.prototype.forEach.call(navs, function (nav) {
      nav.addEventListener('click', function (event) {
        var target = event.target;
        var toggle = target.closest
          ? target.closest('.post-toc__toggle')
          : null;
        if (toggle && nav.contains(toggle)) {
          // Manual toggle: flip the branch and pin it, so the auto logic
          // leaves it alone until the next explicit toggle.
          var list = document.getElementById(
            toggle.getAttribute('aria-controls')
          );
          if (!list) {
            return;
          }
          var open = toggle.getAttribute('aria-expanded') === 'true';
          setBranch(toggle, list, !open);
          toggle.setAttribute('data-manual', 'true');
          toggle.removeAttribute('data-auto');
          return;
        }
        var link = target.closest
          ? target.closest('a[href^="#"]')
          : null;
        if (!link || !nav.contains(link)) {
          return;
        }
        // Mark at once so the click feels immediate; a row tap inside
        // the open sheet also shuts it: hide, focus the button, and arm
        // the return for when the fragment lands — Firefox resets focus
        // to the body after this task (#383).
        var rowHref = link.getAttribute('href');
        mark(rowHref.slice(1));
        if (fabOn && sheet.contains(link)) {
          closeSheet(false);
          returnFocusToFab();
          rowHash = rowHref;
        }
      });
    });

    if (fabOn) {
      // Draggable FAB experiment (#401): pointer drag moves the button
      // and release snaps to the nearest horizontal edge (left default;
      // right stacks above back-to-top via `.toc-fab--right`, so the two
      // never overlap). The edge persists in `localStorage`; anything
      // missing or foreign falls back to the default, and an unavailable
      // store fails silent. A press moving within FAB_DRAG_THRESHOLD_PX
      // stays a tap (its click still toggles the sheet); beyond it the
      // press is a drag and its click is swallowed, so a drag never
      // opens the sheet. Keyboard users keep the native button behaviour
      // unchanged (Tab-reachable, Enter/Space-operable at the default
      // edge); drag never touches the sheet, the trap, or the ring.
      var FAB_DRAG_THRESHOLD_PX = 10;
      var FAB_EDGE_STORAGE_KEY = 'toc-fab-edge';
      var FAB_DEFAULT_EDGE = 'left';
      function applyFabEdge(edge) {
        fab.classList.toggle('toc-fab--right', edge === 'right');
        fab.style.transform = '';
      }
      try {
        var fabStoredEdge = window.localStorage.getItem(FAB_EDGE_STORAGE_KEY);
        applyFabEdge(
          fabStoredEdge === 'left' || fabStoredEdge === 'right'
            ? fabStoredEdge
            : FAB_DEFAULT_EDGE
        );
      } catch (fabEdgeReadErr) {
        applyFabEdge(FAB_DEFAULT_EDGE);
      }
      var fabDown = false;
      var fabDragged = false;
      var fabStartX = 0;
      var fabStartY = 0;
      var fabSwallowClick = false;
      function fabDragEnd(event) {
        if (!fabDown) {
          return;
        }
        fabDown = false;
        fab.classList.remove('toc-fab--dragging');
        fab.style.transform = '';
        if (!fabDragged) {
          return;
        }
        fabDragged = false;
        fabSwallowClick = true;
        if (!event || event.type === 'pointercancel') {
          return;
        }
        var edge = event.clientX > window.innerWidth / 2 ? 'right' : 'left';
        applyFabEdge(edge);
        try {
          window.localStorage.setItem(FAB_EDGE_STORAGE_KEY, edge);
        } catch (fabEdgeWriteErr) {}
      }
      fab.addEventListener('pointerdown', function (event) {
        if (event.pointerType === 'mouse' && event.button !== 0) {
          return;
        }
        fabDown = true;
        fabDragged = false;
        fabStartX = event.clientX;
        fabStartY = event.clientY;
        fab.style.transform = '';
        try {
          fab.setPointerCapture(event.pointerId);
        } catch (fabCaptureErr) {}
      });
      fab.addEventListener('pointermove', function (event) {
        if (!fabDown) {
          return;
        }
        var fabDx = event.clientX - fabStartX;
        var fabDy = event.clientY - fabStartY;
        if (!fabDragged) {
          if (Math.hypot(fabDx, fabDy) <= FAB_DRAG_THRESHOLD_PX) {
            return;
          }
          fabDragged = true;
          fab.classList.add('toc-fab--dragging');
        }
        fab.style.transform = 'translate(' + fabDx + 'px, ' + fabDy + 'px)';
      });
      fab.addEventListener('pointerup', fabDragEnd);
      fab.addEventListener('pointercancel', fabDragEnd);
      // A press that starts on the FAB can still trip the browser's
      // native drag-and-drop (the article's linked images are draggable
      // and may sit under the floating button): the `dragstart` would
      // pointercancel the gesture mid-drag. Swallow only a native drag
      // that starts while a FAB press is in flight, so image/link
      // dragging elsewhere on the page keeps working.
      document.addEventListener('dragstart', function (event) {
        if (fabDown) {
          event.preventDefault();
        }
      });
      fab.addEventListener('click', function () {
        // A click ends any press (including synthetic pointerdown
        // sequences without a matching pointerup), so stale drag state
        // can never leak into the next gesture.
        fabDown = false;
        fab.classList.remove('toc-fab--dragging');
        if (fabSwallowClick) {
          fabSwallowClick = false;
          return;
        }
        if (sheet.hidden) {
          openSheet();
        } else {
          closeSheet();
        }
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
        if (!fabOn || sheet.hidden) {
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
    }

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function () {
        schedule();
      });
      for (var k = 0; k < entries.length; k++) {
        observer.observe(entries[k].heading);
      }
    }
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    apply();
  }

  window.SiteUtils.onReady(run);
})();

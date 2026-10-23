/* ToC nested disclosure with scroll-spy (#345): the core module.
 *
 * `_includes/post-toc.html` renders a NESTED list (children `<ul>`s as
 * real descendants of their parent `<li>`) starting FULLY EXPANDED, so
 * without JS every level is visible and every anchor works. This module
 * owns collapsing/auto-expansion (H2-only default; `hidden` keeps shut
 * subtrees out of the a11y tree) and the scroll-spy: the last heading
 * past the viewport top wins (offset from the measured `.site-header`
 * height when sticky/fixed, else a small slack), marking one row per
 * mount (`aria-current="location"`), auto-expanding the active branch
 * plus ancestors, collapsing auto-opened branches on leave unless pinned
 * by hand (`data-manual` survives until the next explicit toggle), and
 * keeping the active row inside the sheet via the moved nav's own
 * scrollTop (the page itself never moves). Triggers: one
 * `IntersectionObserver` plus a passive rAF-throttled scroll/resize
 * fallback; link clicks mark immediately. Anchor jumps stay instant, so
 * `prefers-reduced-motion` needs nothing here; real `<button>` toggles
 * give Enter/Space natively and `tabindex` is never touched.
 *
 * Split (#417): the phone FAB model lives in `toc-sheet.js` (button +
 * sheet + ring + focus) and the drag gesture in `toc-fab-drag.js`. This
 * module stays phone-agnostic: it publishes `window.TocSpy.core`
 * (`mark`/`apply`/`schedule`) for the sheet to call back into, and never
 * reads `window.TocSpy.sheet`, so the core works with the sheet absent.
 */
(function () {
  var EDGE_PX = 24;

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
    // single recompute marks all copies together. Links whose target is
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
      // extra listener, reads batched above before the style write. The
      // sheet owns the ring (`toc-sheet.js`); without it there is nothing
      // to paint.
      var sheetApi = window.TocSpy && window.TocSpy.sheet;
      if (sheetApi) {
        sheetApi.progress();
      }
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

    // Publish the core for the sheet module (open-sheet refresh, ring
    // repaint, row-tap marking in the core's own first listener).
    window.TocSpy.core = {
      mark: mark,
      apply: apply,
      schedule: schedule
    };

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
        // Mark at once so the click feels immediate. A row tap inside
        // the open sheet additionally shuts it — owned by `toc-sheet.js`
        // in its own listener below this one.
        mark(link.getAttribute('href').slice(1));
      });
    });

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

  window.TocSpy = window.TocSpy || {};
  window.TocSpy.core = null;
  window.TocSpy.sheet = null;
  window.SiteUtils.onReady(run);
})();

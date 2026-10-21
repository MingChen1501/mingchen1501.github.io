/* Table of contents scroll-spy (#345): progressive enhancement for the
 * automatic ToC on post pages. `_includes/post-toc.html` renders the list
 * expanded with plain anchors (both mounts: inline for phones, sidebar for
 * desktop), so without JS the ToC is fully usable; this script only marks
 * the row for the section currently being read:
 *
 * - rule: the last heading whose top has passed the viewport top wins (the
 *   site header is not sticky, so only a small `EDGE_PX` slack keeps a
 *   heading sitting exactly on the edge stable). One deterministic rule
 *   drives every trigger, so adjacent sections never flicker. At the very
 *   end of the page the last heading stays active even when a short tail
 *   section never reaches the viewport top.
 * - mark: `aria-current="location"` on the active link in BOTH mounts
 *   (the CSS active style keys off the attribute, so there is no second
 *   mechanism to drift). Exactly one row per mount is ever marked: above
 *   the first heading the first row counts as current.
 * - triggers: an `IntersectionObserver` over the headings recomputes on
 *   every crossing, plus a passive rAF-throttled scroll/resize listener
 *   that covers browsers without `IntersectionObserver` and any shift the
 *   observer misses. Clicking a ToC link marks its row immediately (the
 *   default anchor jump is instant — no smooth scrolling is added, so
 *   there is nothing for `prefers-reduced-motion` to disable).
 * - keyboard: links stay plain anchors in tab order; the script never
 *   touches `tabindex`, focus, or the `details[open]` state.
 */
(function () {
  var EDGE_PX = 24;

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

    function apply() {
      var line = window.scrollY + EDGE_PX;
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
      mark(atEnd ? entries[entries.length - 1].id : active.id);
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
        var link = event.target.closest
          ? event.target.closest('a[href^="#"]')
          : null;
        if (!link || !nav.contains(link)) {
          return;
        }
        // The anchor jump is instant; mark the row now instead of waiting
        // for the next scroll event so the click feels immediate.
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

  window.SiteUtils.onReady(run);
})();

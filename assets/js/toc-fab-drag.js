/* Draggable phone ToC button (#401): the drag module (split from
 * `toc-spy.js` in #417; the sheet model lives in `toc-sheet.js`).
 *
 * Pointer/touch drags snap to the nearest horizontal edge on release
 * (left default, right stacked above back-to-top via `.toc-fab--right`),
 * persisted in `localStorage` with a left default and a silent fallback
 * when storage is unavailable. A press moving within
 * FAB_DRAG_THRESHOLD_PX stays a tap (its click toggles the sheet); a
 * longer move is a drag and its click is swallowed, so a drag never opens
 * the sheet. Drag is pointer-only by design: keyboard users keep the
 * unchanged native button (Tab-reachable, Enter/Space-operable) at the
 * default edge, so no keyboard drag path exists. Dragging never touches
 * the sheet, the trap, or the ring — only the edge class while the sheet
 * stays shut. A native drag tripped by a FAB press (draggable article
 * images under the button) is swallowed in flight, so it cannot
 * pointercancel the gesture.
 *
 * Contract: `toc-sheet.js` (always loaded first) registers
 * `window.TocSpy.sheet` (`fab`, `sheet`, `toggle`) when the phone FAB
 * model is active, null otherwise. Without it this module stands down and
 * the button keeps its native toggle behaviour.
 */
(function () {
  function run() {
    var api = window.TocSpy && window.TocSpy.sheet;
    if (!api) {
      return;
    }
    var fab = api.fab;
    // Draggable FAB (#401): pointer drag moves the button, release snaps
    // to the nearest edge. Within FAB_DRAG_THRESHOLD_PX a press stays a
    // tap; beyond it the click is swallowed so a drag never opens the
    // sheet. Keyboard users keep the native button unchanged.
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
      // A pointercancelled drag leaves fabSwallowClick set (its click
      // never fires): reset it here or it would eat the next tap (#401).
      fabSwallowClick = false;
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
    // A native drag tripped by a FAB press (draggable article images may
    // sit under the button) would pointercancel the gesture mid-drag:
    // swallow only drags starting while a FAB press is in flight.
    document.addEventListener('dragstart', function (event) {
      if (fabDown) {
        event.preventDefault();
      }
    });
    fab.addEventListener('click', function () {
      // A click ends any press, so stale drag state never leaks into the
      // next gesture.
      fabDown = false;
      fab.classList.remove('toc-fab--dragging');
      if (fabSwallowClick) {
        fabSwallowClick = false;
        return;
      }
      api.toggle();
    });
  }

  window.TocSpy = window.TocSpy || {};
  window.SiteUtils.onReady(run);
})();

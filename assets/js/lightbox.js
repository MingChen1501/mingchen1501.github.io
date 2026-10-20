/* Accessible image lightbox (#223): progressive enhancement over post
 * content images. Without JS the images stay plain images (no dead
 * controls); with JS every informative `.post-content` image becomes a
 * keyboard-operable trigger that opens the full-resolution source in an
 * accessible overlay with its alt/caption text.
 *
 * - Triggers: `.post-content img` with a non-empty `alt`, excluding
 *   decorative repeats (`aria-hidden="true"`, #147) and images already
 *   wrapped in a link (clicking those must keep navigating). The trigger is
 *   the image itself (`tabindex` + `role="button"`), so enhancement adds no
 *   box and cannot shift layout.
 * - Source: `currentSrc || src` — the same file the page already loads, so
 *   no new image variants are generated. Local files and external
 *   attachment URLs (#195) work the same way.
 * - Caption: the parent `<figure class="post-figure">` caption when the
 *   image has one, otherwise the alt text.
 * - Dialog: built once at runtime, `role="dialog"` + `aria-modal="true"`
 *   with an accessible name; Esc closes and returns focus to the invoking
 *   image; Left/Right arrows move prev/next within the post (hidden for a
 *   single image); Tab is trapped inside while open; body scroll is locked.
 * - Touch: a horizontal swipe moves prev/next (optional nicety, same code
 *   path as the arrow keys). No animation anywhere, so there is nothing
 *   for `prefers-reduced-motion` to disable — the stylesheet only removes
 *   transitions defensively.
 * - Labels follow `<html lang>` (English default, Vietnamese `vi*`).
 */
(function () {
  var lang = (document.documentElement.lang || 'en').toLowerCase();
  var vi = lang === 'vi' || lang.indexOf('vi-') === 0;
  var TEXT = vi
    ? {
        viewer: 'Trình xem ảnh',
        trigger: 'Xem ảnh đầy đủ',
        close: 'Đóng',
        prev: 'Ảnh trước',
        next: 'Ảnh tiếp theo',
      }
    : {
        viewer: 'Image viewer',
        trigger: 'View full-size image',
        close: 'Close',
        prev: 'Previous image',
        next: 'Next image',
      };
  var SWIPE_MIN_PX = 40;

  var triggers = [];
  var overlay = null;
  var dialogImage = null;
  var dialogCaption = null;
  var dialogCounter = null;
  var closeButton = null;
  var prevButton = null;
  var nextButton = null;
  var currentIndex = 0;
  var invokingTrigger = null;
  var savedBodyOverflow = '';
  var touchStartX = null;

  function isInformative(img) {
    // Decorative repeats carry aria-hidden (#147) or an empty alt; linked
    // images keep their navigation behaviour and stay out of the set.
    if (img.getAttribute('aria-hidden') === 'true') return false;
    var alt = img.getAttribute('alt');
    if (alt === null || alt === '') return false;
    if (img.closest('a')) return false;
    return true;
  }

  function captionFor(img) {
    var figure = img.closest('figure');
    if (figure) {
      var caption = figure.querySelector('figcaption');
      if (caption && caption.textContent.trim() !== '') {
        return caption.textContent.trim();
      }
    }
    return img.getAttribute('alt') || '';
  }

  function focusableElements() {
    return [closeButton, prevButton, nextButton].filter(function (button) {
      return button && !button.hidden;
    });
  }

  function render() {
    var trigger = triggers[currentIndex];
    var img = trigger.img;
    dialogImage.setAttribute('src', img.currentSrc || img.src);
    dialogImage.setAttribute('alt', img.getAttribute('alt') || '');
    var caption = captionFor(img);
    dialogCaption.textContent = caption;
    dialogImage.setAttribute('aria-label', caption);
    dialogCounter.textContent = currentIndex + 1 + ' / ' + triggers.length;
    var single = triggers.length < 2;
    prevButton.hidden = single;
    nextButton.hidden = single;
  }

  function open(index, invoking) {
    currentIndex = index;
    invokingTrigger = invoking || null;
    render();
    overlay.hidden = false;
    savedBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButton.focus();
  }

  function close() {
    overlay.hidden = true;
    document.body.style.overflow = savedBodyOverflow;
    touchStartX = null;
    if (invokingTrigger && document.contains(invokingTrigger)) {
      invokingTrigger.focus();
    }
    invokingTrigger = null;
  }

  function move(delta) {
    if (triggers.length < 2) return;
    currentIndex =
      (currentIndex + delta + triggers.length) % triggers.length;
    render();
    closeButton.focus();
  }

  function onDialogKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      move(-1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      move(1);
    } else if (event.key === 'Tab') {
      // Trap focus inside the dialog while it is open.
      var focusables = focusableElements();
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.className = 'lightbox';
    overlay.hidden = true;

    var backdrop = document.createElement('div');
    backdrop.className = 'lightbox__backdrop';
    backdrop.setAttribute('data-close', 'true');
    overlay.appendChild(backdrop);

    var dialog = document.createElement('div');
    dialog.className = 'lightbox__dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    // The accessible name is the localized viewer label (stable across
    // navigation); the caption below is the description, announced again
    // on every prev/next move.
    dialog.setAttribute('aria-label', TEXT.viewer);
    dialog.setAttribute('aria-describedby', 'lightbox-caption');
    overlay.appendChild(dialog);

    closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'lightbox__close';
    closeButton.textContent = TEXT.close;
    closeButton.setAttribute('aria-label', TEXT.close);
    dialog.appendChild(closeButton);

    prevButton = document.createElement('button');
    prevButton.type = 'button';
    prevButton.className = 'lightbox__prev';
    prevButton.textContent = '‹';
    prevButton.setAttribute('aria-label', TEXT.prev);
    dialog.appendChild(prevButton);

    var figure = document.createElement('figure');
    figure.className = 'lightbox__figure';
    dialog.appendChild(figure);

    dialogImage = document.createElement('img');
    dialogImage.className = 'lightbox__image';
    dialogImage.setAttribute('alt', '');
    figure.appendChild(dialogImage);

    dialogCaption = document.createElement('figcaption');
    dialogCaption.className = 'lightbox__caption';
    dialogCaption.id = 'lightbox-caption';
    figure.appendChild(dialogCaption);

    dialogCounter = document.createElement('p');
    dialogCounter.className = 'lightbox__counter';
    dialogCounter.setAttribute('aria-live', 'polite');
    figure.appendChild(dialogCounter);

    nextButton = document.createElement('button');
    nextButton.type = 'button';
    nextButton.className = 'lightbox__next';
    nextButton.textContent = '›';
    nextButton.setAttribute('aria-label', TEXT.next);
    dialog.appendChild(nextButton);

    closeButton.addEventListener('click', close);
    prevButton.addEventListener('click', function () {
      move(-1);
    });
    nextButton.addEventListener('click', function () {
      move(1);
    });
    backdrop.addEventListener('click', close);
    overlay.addEventListener('keydown', onDialogKeyDown);
    dialogImage.addEventListener('touchstart', function (event) {
      if (event.touches.length === 1) {
        touchStartX = event.touches[0].clientX;
      }
    });
    dialogImage.addEventListener('touchend', function (event) {
      if (touchStartX === null) return;
      var endX = event.changedTouches[0].clientX;
      var delta = endX - touchStartX;
      touchStartX = null;
      if (delta <= -SWIPE_MIN_PX) move(1);
      else if (delta >= SWIPE_MIN_PX) move(-1);
    });

    document.body.appendChild(overlay);
  }

  function enhance(img, index) {
    img.classList.add('lightbox-trigger');
    img.setAttribute('tabindex', '0');
    img.setAttribute('role', 'button');
    img.setAttribute(
      'aria-label',
      TEXT.trigger + ': ' + (img.getAttribute('alt') || '')
    );
    img.addEventListener('click', function () {
      open(index, img);
    });
    img.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open(index, img);
      }
    });
  }

  function run() {
    var images = document.querySelectorAll('.post-content img');
    images.forEach(function (img) {
      if (!isInformative(img)) return;
      triggers.push({ img: img });
    });
    if (triggers.length === 0) return;
    buildOverlay();
    triggers.forEach(function (trigger, index) {
      enhance(trigger.img, index);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();

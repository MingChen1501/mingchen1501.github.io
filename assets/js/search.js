/* Offline client-side search (#221): filters the build-time `/search.json`
 * index (title, description, URL, lang, tags, date — no post bodies) entirely
 * in the reader's browser. No plugin, no external service, no SDK, no
 * dependency. The script loads only on the search pages (`_includes/
 * search.html`); the index itself is fetched lazily on top of that, so no
 * other page pays for either.
 *
 * Matching is diacritics-insensitive (Vietnamese tones and `đ` fold to their
 * ASCII base), so `ca phe` finds `cà phê`. Every query word must occur
 * somewhere (AND); a title hit scores above a description/tag hit, and
 * results in the page language rank above the other language. Counts and the
 * no-results state are announced through the `role="status"` region in the
 * markup; `?q=` deep-links a query (and preserves a no-JS form submit),
 * mirrored back on input via `history.replaceState` (cleared when empty)
 * so filtered views stay shareable. Focus stays desktop-only: coarse
 * pointers / narrow screens skip it, no mobile keyboard-pop.
 */
(function () {
  var TITLE_HIT = 3;
  var TEXT_HIT = 2;

  function norm(text) {
    return (text || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd');
  }

  function tokens(query) {
    return norm(query).split(/[^a-z0-9]+/).filter(function (w) { return w; });
  }

  function entryText(entry) {
    return {
      title: norm(entry.title),
      desc: norm(entry.description),
      tags: (entry.tags || []).map(norm).join(' ')
    };
  }

  // Every token must occur in at least one field; title hits outscore the
  // rest. Returns -1 when a token matches nothing.
  function scoreText(text, words) {
    var total = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (text.title.indexOf(w) !== -1) total += TITLE_HIT;
      else if (text.desc.indexOf(w) !== -1) total += TEXT_HIT;
      else if (text.tags.indexOf(w) !== -1) total += TEXT_HIT;
      else return -1;
    }
    return total;
  }

  function compare(lang) {
    return function (a, b) {
      var aLocal = a.entry.lang === lang ? 0 : 1;
      var bLocal = b.entry.lang === lang ? 0 : 1;
      if (aLocal !== bLocal) return aLocal - bLocal;
      if (a.score !== b.score) return b.score - a.score;
      if (a.entry.date !== b.entry.date) return a.entry.date < b.entry.date ? 1 : -1;
      return 0;
    };
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderItem(entry, lang) {
    var item = el('li', 'search__item');
    var link = el('a', 'search__link');
    link.href = entry.url;
    link.textContent = entry.title || entry.url;
    item.appendChild(link);
    var meta = el('p', 'search__meta');
    meta.appendChild(el('span', 'search__lang', (entry.lang || lang).toUpperCase()));
    if (entry.date) meta.appendChild(document.createTextNode(' · ' + entry.date));
    if (entry.tags && entry.tags.length) {
      meta.appendChild(document.createTextNode(' · ' + entry.tags.join(', ')));
    }
    item.appendChild(meta);
    if (entry.description) item.appendChild(el('p', 'search__desc', entry.description));
    return item;
  }

  function fill(template, name, value) {
    return (template || '').split(name).join(value);
  }

  function init() {
    var root = document.getElementById('site-search');
    if (!root) return;
    var form = document.getElementById('site-search-form');
    var input = document.getElementById('site-search-input');
    var guidance = document.getElementById('site-search-guidance');
    var status = document.getElementById('site-search-status');
    var list = document.getElementById('site-search-results');
    var empty = document.getElementById('site-search-empty');
    if (!form || !input || !guidance || !status || !list || !empty) return;

    var lang = root.getAttribute('data-lang') || 'en';
    var foundOne = root.getAttribute('data-found-one') || '';
    var foundMany = root.getAttribute('data-found-many') || '';
    var noResults = root.getAttribute('data-no-results') || '';
    var loadError = root.getAttribute('data-load-error') || '';
    var index = null;

    function showGuidance() {
      guidance.hidden = false;
      list.textContent = '';
      empty.hidden = true;
      empty.textContent = '';
      status.textContent = '';
    }

    function run(query) {
      var words = tokens(query);
      if (!words.length) {
        showGuidance();
        return;
      }
      guidance.hidden = true;
      list.textContent = '';
      if (!index) return;
      var hits = [];
      for (var i = 0; i < index.length; i++) {
        var entry = index[i];
        var s = scoreText(entryText(entry), words);
        if (s >= 0) hits.push({ entry: entry, score: s });
      }
      hits.sort(compare(lang));
      if (!hits.length) {
        empty.textContent = fill(noResults, '{q}', query.trim());
        empty.hidden = false;
        status.textContent = empty.textContent;
        return;
      }
      empty.hidden = true;
      empty.textContent = '';
      for (var j = 0; j < hits.length; j++) {
        list.appendChild(renderItem(hits[j].entry, lang));
      }
      var message = hits.length === 1
        ? foundOne
        : fill(foundMany, '{n}', String(hits.length));
      status.textContent = message;
    }

    // Mirror the query into `?q=` with replaceState (shareable, no
    // history spam); empty clears it. Path (EN/VI) is untouched.
    function syncUrl(query) {
      try {
        var url = new URL(window.location.href);
        var q = (query || '').trim();
        if (q) url.searchParams.set('q', q);
        else url.searchParams.delete('q');
        history.replaceState(null, '', url.pathname + url.search + url.hash);
      } catch (e) {}
    }

    // Desktop-only focus: coarse pointers / narrow screens skip it, so
    // phones never get a keyboard-pop on load.
    function shouldAutofocus() {
      try {
        var mm = window.matchMedia;
        if (mm && (mm('(pointer: coarse)').matches || mm('(max-width: 768px)').matches)) return false;
      } catch (e) {}
      return true;
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      run(input.value);
      syncUrl(input.value);
    });
    input.addEventListener('input', function () {
      run(input.value);
      syncUrl(input.value);
    });
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && input.value) {
        input.value = '';
        run('');
        syncUrl('');
        input.focus();
      }
    });

    // A no-JS submit (or a shared link) lands here with `?q=`; pick it up so
    // the query runs without typing.
    var params = null;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      params = null;
    }
    var preset = params ? (params.get('q') || '') : '';
    if (preset) input.value = preset;

    fetch(root.getAttribute('data-index-url'), { credentials: 'same-origin' })
      .then(function (response) {
        if (!response.ok) throw new Error('index ' + response.status);
        return response.json();
      })
      .then(function (data) {
        index = Array.isArray(data) ? data : [];
        root.setAttribute('data-loaded', 'true');
        run(input.value);
      })
      .catch(function () {
        root.setAttribute('data-loaded', 'error');
        status.textContent = loadError;
      });

    if (shouldAutofocus()) input.focus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

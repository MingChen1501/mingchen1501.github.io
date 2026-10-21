# ADR-004: Series posts with language-neutral keys

- Status: proposed
- Date: 2026-10-21
- Context: a **Series** post type is coming — decide the shape now so later
  posts only add front matter, not template rewrites (#346). Phase 1 is this
  ADR plus the data-model record; Phase 2 (separate issues, after acceptance)
  implements the nav block, the series index pages, and the guards. No
  retro-fitting of old posts. No template/JS/CSS change in this issue.
- Decision:
  - 1. Front matter contract. A series installment declares
    `series: <key>` plus `series_order: <int>` (1-based position in the
    series). `<key>` is kebab-case and language-neutral (e.g.
    `jekyll-mastery`). There is no per-post `series_title`: the series'
    localized title and description live in a new `_data/series_labels.yml`
    (canonical key → `en`/`vi` titles, `slug_en`/`slug_vi` (provisional
    pending Q1: shared vs split slugs), `description_en`/`description_vi`,
    plus `coming_soon_en`/`coming_soon_vi` labels for unlinked gap positions),
    mirroring `tag_labels.yml`, so
    templates never hold copy. Validation is strict, never inferred: a post
    with `series` but no `series_order` fails the build guard (CI red) — the
    order is never derived from the date, because date-derived ordering is
    implicit and fragile (backdated evergreen posts already need the #328
    date constraint). Likewise `series_order` without `series`, a
    non-positive/non-integer order, or a duplicate order within one
    (series, language) all fail. A post belongs to at most one series:
    `series` is a scalar key; the array form is out of scope and Phase 2
    validators must reject a sequence value. A series may launch with a
    single published
    post (part 1) unless the owner answers Q2 otherwise; the no-orphan
    guard only requires the key to exist in
    `series_labels.yml` and vice versa.
  - 2. Identity and i18n. The series key is language-neutral: EN
    (`site.posts`) and VI (`site.vi_posts`) twins share the key, matched
    through the existing `lang`/`ref` pipeline (ADR-003). `series_order`
    must match across languages — the EN and VI twins of one installment
    carry the same position number, pinned by a parity guard. Partial
    translation is allowed: VI may lag behind EN. This is the same class of
    problem as #93/#172, and the rule is the same — never cross-link, never
    404: the series nav and the series index always render within the
    reader's language; positions with no published twin in that language are
    skipped by prev/next and shown as unlinked "coming soon" labels
    (localized copy from `coming_soon_en`/`coming_soon_vi` in
    `series_labels.yml`) on the index, never linked
    into the other language. The per-post language switcher keeps its
    existing #93 fallback behavior unchanged. "Part N of M" numbering is
    global, not per-language: N is the global `series_order` (identical in
    both languages) and M is the highest published order in the reader's
    language (a maximum, never a count), so gaps at or below M render as
    unlinked coming-soon labels without renumbering and a "Part 5 of 3"
    can never occur.
  - 3. Rendering contract. Series nav block: `<nav class="series-nav">`
    ("Part N of M", prev/next links with installment titles, link to the
    series index) placed inside `.post-main` in `_layouts/post.html`,
    directly after the `share.html` include and before the comments section.
    It belongs to the article flow, so it sits in the main column; the
    Tags/Related sidebar is untouched and series posts keep its normal
    behavior. Series index pages live at `/series/<slug>/` plus
    `/vi/series/<slug>/` (slugs from `series_labels.yml`), on a new
    `_layouts/series.html` mirroring `tag.html`, listing that language's
    installments in `series_order` with titles and dates. Series
    installments are normal posts: they keep appearing in the home list,
    tag pages, search, and feeds.
  - 4. Interaction with existing features. Multi-tag posts (#343):
    orthogonal — the series nav is independent of tags and the Related-posts
    sidebar stays tag based (union over all tags, #343). Curated tag list (#344): series index
    pages are separate from tag pages; no template copy is shared. Nested
    ToC (#345): the nav block sits outside `.post-content`, so heading
    scraping and ToC mount counts are unaffected. RSS/sitemap/JSON-LD: the
    series index pages enter the sitemap as normal pages; RSS is unchanged
    (installments are already listed as posts); Phase 2 adds `isPartOf`
    (pointing at the series index URL) plus `position` (`series_order`) to
    the post JSON-LD, pinned by a guard. Content-only CI classification
    (#229): `series_labels.yml` follows `tag_labels.yml` — full suite, since
    templates render nav/index copy from it — while series front matter on
    posts stays on the content-only path; `script/classify-content-only`
    gains the new mapping in Phase 2.
  - 5. Guard plan (Phase 2 e2e, planned files).
    `tests/e2e/test_series_nav.py` (ordering: the index lists strictly by
    `series_order` and each nav block's "Part N of M" agrees with it;
    prev/next titles: the first installment has no prev, the last has no
    next, middle installments link both with the correct titles).
    `tests/e2e/test_series_i18n.py` (EN/VI parity: twins share key and
    order; lagging-VI behaviour: missing twins are skipped by prev/next and
    shown as unlinked coming-soon labels; no cross-language links, never
    cross-linked, never 404). Orphan/strict-validation cases: every
    `series` key used by a published post exists in `series_labels.yml`
    and vice versa; missing/reverse/non-integer/non-positive/duplicate
    orders fail, and a sequence (array) `series` value fails. Index
    completeness: every published installment of
    that language appears, and no other post does.
- Consequences: Phase 2 posts only add two front-matter keys plus one data
  entry — no template rewrites. Strict validation trades a little authoring
  friction for ordering guarantees the guards can pin. Lagging translations
  stay explicit ("coming soon") instead of silently renumbering either
  language. What must be revisited: the open questions below; the data-model
  Series section (`data-model.md`) is the living record once this ADR is
  accepted.
- Open questions (owner, one pass):
  - 1. Slugs: shared slug for both languages, or `slug_en`/`slug_vi` split
    like the `doi-song`/`life` tag precedent?
  - 2. Is a single-post series launch acceptable, or should the guard require
    ≥2 published installments before the nav renders?
  - 3. "Coming soon" placeholder: unlinked label (proposed) or hidden until
    the translation lands?
  - 4. JSON-LD shape: `isPartOf` → series index URL plus `position` — enough,
    or also a full `CreativeWorkSeries` node on the index page?
  - 5. Should series index pages appear in the navbar/sitemap indexes
    alongside tags, or stay reachable only from the nav block?

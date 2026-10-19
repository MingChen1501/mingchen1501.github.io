---
name: Jekyll Post
description: Bilingual post authoring, front matter, taxonomy, post URLs, and comments for the site. Use when writing or editing a post, taxonomy page, or anything about post layout and tags.
trigger: "Writing or editing a site post, taxonomy page, front matter, tags, bilingual ref/lang, or post URLs: read this skill first."
---

# Write a new post

## Workflow

1. Get the post title + publish date (default today).
2. Create an ascii slug: lowercase, no diacritics, words joined with `-`. File name:
   `_posts/YYYY-MM-DD-<slug>.md`.
3. Read `references/front-matter.md`, then write front matter + body content in
   that file's language. Front matter must include `tags: [one-of-4-pillars]`
   and `description` (~120-155 chars) per the 4-pillar taxonomy. If the tag has
   no page yet, add `tags/<tag>.md` (+ `vi/tags/<tag>.md`) and the `tags.md`
   entries too (the post page's tag chips link to `/tags/<tag>/`).
4. If the post adds images, place them under `assets/img/<post-slug>/` and run
   `script/check-images` — rules live in the `jekyll-assets` skill (each file
   <= 500KB, `assets/img/` total <= 6MB).
5. Run `bundle exec jekyll build --trace` to make sure the post renders.
6. Open the matching post file under `_site/` to check the title/date. Note the homepage
   has `show_excerpts: true`, so the opening paragraph appears on the homepage — keep
   the opening concise.

Do not commit the `_site/` directory (already in `.gitignore`).

## Bilingual authoring (#93, #97)

- **English default** in `_posts/` (served at `/`); **Vietnamese** in the
  `site.vi_posts` collection (`_vi_posts/`, served at `/vi/...`).
- Every post carries `lang:` (`en`/`vi`) and a shared `ref:` linking the two
  translations (drives the header switcher + hreflang); every post ships a real
  translation in both languages (no `translation_pending` marker, no
  `fallback_vi` stubs — the layout/include banner plumbing stays wired for any
  future untranslated post). English slugs must never reuse old Vietnamese
  slugs (redirect stubs would collide).
- Posts live in `_posts/` (EN) / `_vi_posts/` (VI) with filenames like
  `YYYY-MM-DD-slug-ascii.md`, body content in that file's language, slug in
  lowercase ASCII without diacritics joined with `-`. Vietnamese collection
  docs also declare `date: YYYY-MM-DD` (their names carry no date) and
  `redirect_from:` the pre-#93 URL(s) so old links keep working.
- Minimal front matter: `layout: post`, `lang`, `ref`, `title`; Ming's posts
  also add `author: Ming Chen`; to disable comments on that post set
  `comments: false`.

## Taxonomy (#26, #44)

- Every post picks tags from the 4 content pillars only
  (`backend-production`, `ai-agent`, `linux-tooling`, `doi-song`), 1 tag per
  post and at most 4 tags/post; always include a short translated `description`
  (~120-155 chars) so `jekyll-seo-tag` renders a proper meta description.
  Copy-paste template lives in the README "Writing a new post (mingchen.id.vn
  taxonomy)" section and `references/front-matter.md`.
- Each pillar has a front-matter-only page in both languages — `tags/<tag>.md`
  (`layout: tag`, `tag: <pillar>`, `permalink: /tags/<tag>/`, `lang: en`,
  `ref: tag-<pillar>`) and `vi/tags/<tag>.md` (`permalink: /vi/tags/<tag>/`,
  `lang: vi`, same `ref`) — because GitHub Pages builds with `--safe` (no
  archive/tagging plugin). A new tag needs both pages plus both `tags.md`
  entries — `tests/e2e/test_post_layout_markup.py` guards this.
- Static pages use `layout: page` + `permalink`; to add a page to the top nav,
  add its path to `minima.nav_pages` in `_config.yml`. The `/tags/` page
  (`tags.md`) is already listed there and is the index of the 4 pillars.
- Post pages render a secondary column with the post's tags + posts sharing
  its first tag in the page's language (`_layouts/post.html`,
  `_includes/post-tags.html`, styles in
  `_sass/minima/custom-styles.scss`, the index over the `_sass/minima/custom/`
  partials). The home post list renders the same chips
  per item (via the include's optional `class` parameter, #47), linking inside
  the page's language (`/tags/` vs `/vi/tags/`).

## Comments and sidebar

- Comments use Giscus (`comments.provider: giscus`); only rendered in
  production (`JEKYLL_ENV=production`), unless `comments.dev: true`. Do not
  break the logic in `_layouts/post.html` and `_includes/comments.html` — the
  E2E tests depend on it.
- List sidebar (#58, reworked in #63): the home list (`/`, `/page2/…`) and the
  Vietnamese home (`/vi/`) plus the tag pages (`/tags/<tag>/`,
  `/vi/tags/<tag>/`) wrap their list in the same shell (`.site-layout` >
  `.site-main` + `aside.site-sidebar`) fed by ONE include,
  `_includes/site-sidebar.html`: the highlighted posts — the slugs listed per
  language (`en:` / `vi:`) in `_data/highlights.yml` (#64), in file order, at
  most 5, with title + date + thumbnail (falling back to the 5 newest posts of
  that language when the list is empty/missing) — and every tag as a row
  collapsed by default (`<details>` without `open`): a chip-styled, non-link
  label plus the post count, showing at most 3 posts of that language once
  opened (the label is a plain `<span>` — links are invalid inside `<summary>`,
  #114 — and the row's tag-page link lives in the opened panel). Headings are
  English on English pages (`Featured`, `Latest posts`, `Topics`) and
  Vietnamese on Vietnamese pages (`Bài nổi bật`, `Bài mới nhất`, `Chủ đề`).
  Keep the aside AFTER `.site-main` in the DOM, keep the list/home/post chips
  coming from `_includes/post-tags.html` (no forked chip markup; the sidebar
  summary label only reuses the `.tag-chip` class), never crop or upscale a
  thumbnail (capped `max-width`/`max-height` box, no `object-fit`, `padding: 0`
  — the `img` reset in `_base.scss` distorts a two-`max-*` box), do not add
  `thumb-*` files, and keep the column inside its height budget (short rows, no
  `max-height`/`overflow-y` inner scrollbar; it is pinned only where it fits).
  Post pages keep their own secondary column (#45). The header language
  switcher lives in the header, never in the sidebar, so it cannot break the
  sidebar budget.
- `site.url` must match `CNAME` (keeps canonical/SEO/feed correct).

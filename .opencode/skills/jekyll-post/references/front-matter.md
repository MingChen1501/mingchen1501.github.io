# Front matter for posts (bilingual since #93: English default, Vietnamese option)

Minimal template (copy, then change `title`). Every post ships in **both**
languages with a real translation in each file, linked by a shared `ref`
(`tests/e2e/test_i18n.py` fails otherwise). The `fallback_vi: true` stub
mechanism from phase 1 is retired — no stub remains; the layout/include banner
plumbing stays wired in case a future post lands untranslated:

```yaml
---
layout: post
lang: en            # `en` in `_posts/`, `vi` in `_vi_posts/`
ref: my-post-key    # same key in both files — drives the switcher + hreflang
author: Ming Chen
title: "Your post title"
tags: [linux-tooling]
description: "One short sentence (120-155 chars) summarising the post for SEO and social previews."
---
```

- `_posts/YYYY-MM-DD-english-slug.md` — the English version (default language,
  served at `/`, paginated, in the Atom feed). Slug must differ from the
  Vietnamese slug so the old-URL redirect stub and the English page never claim
  the same output path.
- `_vi_posts/vietnamese-slug.md` — the Vietnamese version, with `date:
  YYYY-MM-DD` and `redirect_from: [/YYYY/MM/DD/old-url.html, ...]` pointing at
  the pre-#93 URL(s) so old links 301 to `/vi/...`.
- A post landing without a translation yet may set `fallback_vi: true` to reuse the
  Vietnamese body under the fallback banner instead of a missing counterpart
  (English-only is acceptable going forward; Vietnamese-only is not, since
  English is the default). There is no `translation_pending` marker.

## Common fields

| Field | Meaning |
|---|---|
| `layout: post` | Required — uses `_layouts/post.html` (includes date/author meta and comments). |
| `title` | Required — rendered as `<h1>` (the layout already applies `escape`, so write naturally). |
| `author` | Author name. Ming's posts use `author: Ming Chen`. |
| `date` | Defaults to the `YYYY-MM-DD` in the file name. Only add it for a specific time, e.g. `2026-10-17 08:00:00 +0700`. |
| `modified_date` | Updated date — the layout adds an "Updated:" line. |
| `tags` | Required — exactly one (max 4) of the 4 content pillars: `backend-production`, `ai-agent`, `linux-tooling`, `doi-song`. Drives the `/tags/` index, the post page's secondary tag column and the `/tags/<tag>/` page. |
| `description` | Required — ~120-155 chars; rendered as `<meta name="description">` by `jekyll-seo-tag`. |
| `fallback_vi: true` | Retired stub mechanism (phase 1): reuse the Vietnamese body under the fallback banner when a translation is still pending. No stub remains since PR B; never combined with a translated body. |
| (no field) | Highlighting is configured in `_data/highlights.yml` (#64, per-language `en:` / `vi:` lists since #93): add the post's slug to that language's ordered list to feature it in the list sidebar's highlight block. No per-post front matter flag. |
| `comments: false` | Disable comments for this post only (posts have Giscus by default). |

## Taxonomy rules (#26)

- Tags must come from the 4 pillars only; free-form tags are not allowed.
- At most 4 tags per post; in practice posts use exactly 1 pillar tag.
- `description` is required (not optional) — missing it makes the meta description
  fall back to the post excerpt or the site description instead of a post-specific
  summary.
- See README "Writing a new post (mingchen.id.vn taxonomy)" for the canonical template.
- A brand-new tag (rare: the pillars are fixed) also needs `tags/<tag>.md`
  (`layout: tag`, `tag: <pillar>`, `permalink: /tags/<tag>/`) plus its entry in
  `tags.md`, otherwise the tag chip on the post 404s — and, since #93, the
  Vietnamese mirror `vi/tags/<tag>.md` (`permalink: /vi/tags/<tag>/`) plus its
  `vi/tags.md` entry, otherwise the Vietnamese chip 404s.
  `tests/e2e/test_post_layout_markup.py` fails when a published post uses a tag
  with no page in its language.

## Real example in this repo

See `_posts/2026-10-14-setting-up-ai-coding-agent-orchestration.md` (English)
and `_vi_posts/setup-ai-coding-agent-orchestration.md` (Vietnamese): concise
front matter (`lang`, shared `ref`, `tags: [ai-agent]`, translated
`description`) + Markdown content with `##` headings.

## Excerpt note

The homepage enables `show_excerpts: true`, so Jekyll uses the first paragraph as the summary.
Keep the opening paragraph short; do not open with a long blockquote or code block.

# Front matter for posts

Minimal template (copy, then change `title`):

```yaml
---
layout: post
author: Ming Chen
title: "Your post title"
tags: [linux-tooling]
description: "One short sentence (120-155 chars) summarising the post for SEO and social previews."
---
```

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
| (no field) | Highlighting is configured in `_data/highlights.yml` (#64): add the post's slug to that ordered list to feature it in the list sidebar's "Bài nổi bật" block. No per-post front matter flag. |
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
  `tags.md`, otherwise the tag chip on the post 404s.
  `tests/e2e/test_post_layout_markup.py` fails when a published post uses a tag
  with no page.

## Real example in this repo

See `_posts/2026-10-14-setup-ai-coding-agent-orchestration.md`: concise front
matter (`tags: [ai-agent]`, `description`) + Vietnamese Markdown content with
`##` headings.

## Excerpt note

The homepage enables `show_excerpts: true`, so Jekyll uses the first paragraph as the summary.
Keep the opening paragraph short; do not open with a long blockquote or code block.

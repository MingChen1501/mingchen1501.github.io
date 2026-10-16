# Front matter for posts

Minimal template (copy, then change `title`):

```yaml
---
layout: post
title: "Post title"
author: Ming Chen
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
| `categories` / `tags` | Classification, e.g. `categories: [doi-song]`. Optional. |
| `comments: false` | Disable comments for this post only (posts have Giscus by default). |

## Real example in this repo

See `_posts/2026-10-14-setup-ai-coding-agent-orchestration.md`: concise 3-line
front matter + Vietnamese Markdown content with `##` headings.

## Excerpt note

The homepage enables `show_excerpts: true`, so Jekyll uses the first paragraph as the summary.
Keep the opening paragraph short; do not open with a long blockquote or code block.

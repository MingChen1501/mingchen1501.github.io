# Product scope

Status: active. Source of truth for what this site is and is not.

This site is Ming's personal bilingual (EN/VI) blog at `mingchen.id.vn`,
forked from the Jekyll minima theme and deployed with GitHub Pages from
`master`. See `docs/architecture/overview.md` for the area map.

## In scope

- Bilingual essays and notes: English posts in `_posts/`, Vietnamese
  translations in the `_vi_posts` collection (`/vi/...`), cross-linked by
  `lang`/`ref` front matter.
- Tag taxonomy driven by `_data/tag_labels.yml`, tag index pages, and the
  home sidebar highlights (`_data/highlights.yml`).
- Reader experience: theme toggle, lazy images, lightbox, copy-code,
  reading progress, share intents, Giscus comments on posts.
- Feeds and discovery: `jekyll-feed`, `jekyll-seo-tag`, sitemap, `llms.txt`.

## Out of scope

- No custom Jekyll plugins: Pages builds with `--safe`, so i18n and all
  dynamic behaviour are Liquid plus vanilla JS only.
- No search backend: static client-side search was removed in #349.
- No accounts, no analytics, no webfonts, no third-party runtime except
  the Giscus embed on post pages (see `docs/architecture/privacy-csp.md`).
- No Content-Security-Policy by deliberate decision (#329); no uptime or
  support commitments (see `support/sla.md`, stub).

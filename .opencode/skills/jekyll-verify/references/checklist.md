# Checklist of common site breakages

Check by eye after build + tests are green, since some bugs only appear in production.

## Comments (Giscus)

- `_config.yml` keeps `giscus.repo`, `repo_id`, `category_id` intact — a wrong value means
  comment threads fail to load (the Giscus backend returns 403).
- The 3-branch logic in `_includes/comments.html` must stay intact: `giscus` when IDs
  are present, legacy Disqus fallback, render nothing when the provider is `none`.
- The environment gate in `_layouts/post.html` must stay: only render comments when
  `JEKYLL_ENV=production` or `site.comments.dev == true`.
- A post with `comments: false` must show `.comments-disabled-message`, not the
  thread.

## Config and nav

- `url` in `_config.yml` must match the `CNAME` file; do not hardcode another domain.
- `minima.nav_pages` only lists real page files (currently: `about.md`,
  `portfolio.md`); a wrong name yields a 404 nav link.
- Do not change `minima.date_format` unless requested — the current format is
  Vietnamese (`Bài viết được đăng lúc: ...`).

## Posts and pages

- `_posts/` file names match `YYYY-MM-DD-slug.md`; Jekyll skips future-dated files
  (future posts), so an "unpublished" post is really a misdated one.
- Static page `permalink`s are unique and always start with `/`.
- Put attached images/files in `assets/` with relative links so they work both locally
  and in production.

## Diff hygiene

- `git status --short` must not contain `_site/`, `.jekyll-cache/`, `vendor/`,
  `Gemfile.lock` — those are build/bundler outputs, already gitignored.
- Do not commit `AGENTS.md` into `_site` (already declared in `exclude` in the config).

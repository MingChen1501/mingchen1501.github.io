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
  `portfolio.md`, `tags.md`); a wrong name yields a 404 nav link. `tags.md`
  must stay listed so the 4-pillar `/tags/` page is reachable.
- Do not change `minima.date_format` unless requested — the current format is
  Vietnamese (`Bài viết được đăng lúc: ...`).

## Posts and pages

- `_posts/` file names match `YYYY-MM-DD-slug.md`; Jekyll skips future-dated files
  (future posts), so an "unpublished" post is really a misdated one.
- Static page `permalink`s are unique and always start with `/`.
- Put attached images/files in `assets/` with relative links so they work both locally
  and in production.

## Taxonomy and front matter

- Posts use `tags: [one-of-4-pillars]` (max 4/post) and a `description`
  (~120-155 chars); missing either breaks `/tags/` grouping and SEO meta.
- The 4 pillars are `backend-production`, `ai-agent`, `linux-tooling`,
  `doi-song` — no free-form tags.
- New posts follow the template in
  `.opencode/skills/jekyll-post/references/front-matter.md` and the README
  "Writing a new post (mingchen.id.vn taxonomy)" section.

## Image conventions

- New images live under `assets/img/<post-slug>/`, lowercase hyphenated names,
  long edge <= 1600px, each file <= 500KB, `assets/img/` total <= 6MB.
- Run `script/check-images` for any `assets/` touch (single file <= 500KB,
  total <= 6MB); CI runs it in `script/cibuild` and `.github/workflows/ci.yaml`.

## Diff hygiene

- `git status --short` must not contain `_site/`, `.jekyll-cache/`, `vendor/`,
  `Gemfile.lock` — those are build/bundler outputs, already gitignored.
- Do not commit `AGENTS.md` or `.opencode/` into `_site` (both declared in `exclude` in _config.yml); verify with a build before finishing.

# mingchen-site — agent guide

Ming's personal site (https://mingchen.id.vn), forked from the Jekyll minima theme,
deployed with GitHub Pages from the `master` branch.

## Run and build

- Preview real content: `bundle exec jekyll serve` (uses `_config.yml`).
- Check build: `bundle exec jekyll build --trace`.
- `script/server`, `script/build`, `script/cibuild` support upstream minima theme
  development (they use `_config_theme-dev.yml` with sample content) — do not use
  them to preview personal posts.
- If gems are missing, run `bundle install` first (needs network access to RubyGems).

## Testing

- E2E comments: `pip install -r tests/e2e/requirements.txt` then
  `python -m pytest tests/e2e -v` (see `tests/e2e/README.md` for details).
- `test_comments_markup.py` is a static guard, runs without a browser.

## Content conventions

- Posts live in `_posts/` with filenames like `YYYY-MM-DD-slug-ascii.md`, body
  content in Vietnamese, slug in lowercase ASCII without diacritics joined with `-`.
- Minimal front matter: `layout: post`, `title`; Ming's posts also add
  `author: Ming Chen`; to disable comments on that post set `comments: false`.
- Static pages: `layout: page` + `permalink`; to add a page to the top nav, add its
  path to `minima.nav_pages` in `_config.yml`.
- Comments use Giscus (`comments.provider: giscus`); only rendered in production
  (`JEKYLL_ENV=production`), unless `comments.dev: true`. Do not break the logic in
  `_layouts/post.html` and `_includes/comments.html` — the E2E tests depend on it.
- `site.url` must match `CNAME` (keeps canonical/SEO/feed correct).

## Safety

- Do not hand-edit build-generated paths: `_site/`, `.jekyll-cache/`,
  `.sass-cache/`, `vendor/`, `.bundle/`, `Gemfile.lock` (the `jekyll-guard`
  plugin blocks this; to change dependencies use `bundle install` / `bundle update`).
- Changes to `CNAME`, `url`, `giscus.repo_id` / `giscus.category_id` need owner
  confirmation first.
- `AGENTS.md` is already `exclude`d from the build so it never leaks to the public site.

## Before finishing

- Touched `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → build
  Jekyll + run `pytest tests/e2e -v`.
- New post only → a build smoke test is enough.
- Use the dedicated skills when available: `jekyll-post`, `jekyll-verify`, `jekyll-review`.

# mingchen-site — agent guide

Ming's personal site (https://mingchen.id.vn), forked from the Jekyll minima theme,
deployed with GitHub Pages from the `master` branch.

## Run and build

- Preview real content: `bundle exec jekyll serve` (uses `_config.yml`). This command is allow-listed in `.opencode/opencode.jsonc` so local preview runs without a prompt.
- Check build: `bundle exec jekyll build --trace`.
- `script/server`, `script/build`, `script/cibuild` support upstream minima theme
  development (they use `_config_theme-dev.yml` with sample content) — do not use
  them to preview personal posts.
- If gems are missing, run `bundle install` first (needs network access to RubyGems).

## Testing

- E2E comments: `pip install -r tests/e2e/requirements.txt` then
  `python -m pytest tests/e2e -v` (see `tests/e2e/README.md` for details).
- `test_comments_markup.py` is a static guard, runs without a browser.
- Layout overflow guard (#50): `tests/e2e/test_layout_overflow.py` builds the
  site with Jekyll and asserts no horizontal scroll at 375px on a post page,
  the home list and the tag pages. It needs Ruby + `bundle install`; it skips
  with an explicit reason without `bundle`. Run it whenever you touch image
  sizing, layout wrappers or `_sass/`.

## Content conventions

- Posts live in `_posts/` with filenames like `YYYY-MM-DD-slug-ascii.md`, body
  content in Vietnamese, slug in lowercase ASCII without diacritics joined with `-`.
- Minimal front matter: `layout: post`, `title`; Ming's posts also add
  `author: Ming Chen`; to disable comments on that post set `comments: false`.
- Taxonomy (#26): every post picks tags from the 4 content pillars only
  (`backend-production`, `ai-agent`, `linux-tooling`, `doi-song`), 1 tag per post
  and at most 4 tags/post; always include a short `description` (~120-155 chars)
  so `jekyll-seo-tag` renders a proper meta description. Copy-paste template lives
  in the README "Writing a new post (mingchen.id.vn taxonomy)" section and
  `.opencode/skills/jekyll-post/references/front-matter.md`.
- Static pages: `layout: page` + `permalink`; to add a page to the top nav, add its
  path to `minima.nav_pages` in `_config.yml`. The `/tags/` page (`tags.md`) is
  already listed there and is the index of the 4 pillars.
- Taxonomy pages (#44): each pillar has a front-matter-only page `tags/<tag>.md`
  (`layout: tag`, `tag: <pillar>`, `permalink: /tags/<tag>/`) because GitHub Pages
  builds with `--safe` (no archive/tagging plugin). Post pages render a secondary
  column with the post's tags + posts sharing its first tag
  (`_layouts/post.html`, `_includes/post-tags.html`, styles in
  `_sass/minima/custom-styles.scss`). The home post list renders the same chips
  per item (via the include's optional `class` parameter, #47). A new tag needs
  both the page file and its `tags.md` entry —
  `tests/e2e/test_post_layout_markup.py` guards this.
- Comments use Giscus (`comments.provider: giscus`); only rendered in production
  (`JEKYLL_ENV=production`), unless `comments.dev: true`. Do not break the logic in
  `_layouts/post.html` and `_includes/comments.html` — the E2E tests depend on it.
- `site.url` must match `CNAME` (keeps canonical/SEO/feed correct).

## Image conventions

Site images live under `assets/img/<post-slug>/` and are committed to git
(compress-local by default; no CDN or Git LFS). Rules for new posts:

- Location: `assets/img/<post-slug>/` matching the post filename slug.
- Naming: lowercase, hyphen-separated, no spaces, quotes, diacritics, or special
  characters (e.g. `desktop-fedora.jpg`, not `Screenshot From ....png`).
- Format: JPG (photos/screenshots) or WebP; PNG only for line-art needing
  lossless. Flatten alpha to white when converting to JPG.
- Size: resize so the long edge is at most **1600px**, JPEG quality ~75
  (progressive, optimized). Each file must be **<= 500KB** and the whole
  `assets/img/` folder must stay **<= 6MB**.
- Budget policy (#33): the 6MB total is a hard CI gate. Per-post guidance: aim
  for a post's images to total **<= 500KB** (no single post should add more
  than ~1MB without review). When the folder approaches 6MB, compress existing
  images harder or remove obsolete assets before raising the budget again; raising
  the cap requires a decision recorded in the tracking issue.
- Reference images with absolute site paths, e.g.
  `![Desktop](/assets/img/2026-01-01-Migrate-windows-11-to-fedora/desktop-fedora.jpg)`.
- Enforcement: `script/check-images` fails the build when any image exceeds 500KB
  or `assets/img` exceeds 6MB. It runs in `script/cibuild` and as the
  "Check image sizes" step in `.github/workflows/ci.yaml`. See the README
  "Image conventions" section for the Pillow compress snippet (single source of
  truth — do not drift the numbers here).

## Safety

- Do not hand-edit build-generated paths: `_site/`, `.jekyll-cache/`,
  `.sass-cache/`, `vendor/`, `.bundle/`, `Gemfile.lock` (the `jekyll-guard`
  plugin blocks this; to change dependencies use `bundle install` / `bundle update`).
- Changes to `CNAME`, `url`, `giscus.repo_id` / `giscus.category_id` need owner
  confirmation first.
- `AGENTS.md` and `.opencode/` are `exclude`d from the build (see `_config.yml`), so the agent guide and kit never leak to the public site. Leak check: a build must leave neither `AGENTS.md` nor `.opencode/` in `_site/`.

## Before finishing

- Touched `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → build
  Jekyll + run `pytest tests/e2e -v`.
- Touched `assets/` (images) → run `script/check-images` (single file <= 500KB,
  `assets/img/` total <= 6MB) before committing.
- New post only → a build smoke test is enough; verify front matter matches the
  4-pillar taxonomy template (`tags`, `description`).
- Use the dedicated skills when available: `jekyll-post`, `jekyll-verify`, `jekyll-review`.

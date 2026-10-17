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
- List sidebar (#58): the home list (`/`, `/page2/`…) and the tag pages
  (`/tags/<tag>/`) wrap their list in the same shell (`.site-layout` >
  `.site-main` + `aside.site-sidebar`) fed by ONE include,
  `_includes/site-sidebar.html`: the 3 most recent posts (thumbnail when the post
  has one + short `description`) and every tag with its newest posts. Keep the
  aside AFTER `.site-main` in the DOM, keep the tag chips coming from
  `_includes/post-tags.html` (no forked chip markup), never crop or upscale a
  thumbnail (`width: 100%; height: auto`, no `object-fit`), and do not add
  `thumb-*` files. Post pages keep their own secondary column (#45).
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

## Asset cache versioning

GitHub Pages serves `assets/**` (via Cloudflare) with `cache-control:
max-age=14400` from a FIXED URL, while the HTML is `max-age=600`. A warm browser
can thus pair NEW HTML with an OLD asset — that is how the #58 list sidebar went
missing on the live index page for up to four hours after the deploy (#61).

- Every fixed-URL asset linked from a template carries the build token assigned in
  `_includes/head.html`: `/assets/css/style.css?v={{ asset_version }}` and
  `/assets/img/favicon.ico?v={{ asset_version }}`. A new fixed-URL asset needs the
  same `?v=` token.
- The token is `site.time` (epoch seconds). No plugin, works with GitHub Pages
  `--safe`, `bundle exec jekyll serve` and the E2E build; it changes on every
  build — a superset of "the asset changed", so cached assets can never pair with
  newer HTML. Cost: one re-fetch per deploy (~18KB stylesheet). A per-file content
  hash needs a Jekyll plugin, which GitHub Pages does not run.
- Images are NOT versioned (their URLs are content-addressed by
  `assets/img/<post-slug>/<name>`), so to change an image's content publish it
  under a NEW filename — never rewrite it in place.
- Guards: `tests/e2e/test_stylesheet_cache_version.py` (token present on every
  page, token changes with a new build and with a CSS change, a client holding the
  old stylesheet under the unversioned URL still gets the sidebar). See the README
  "Asset cache versioning (#61)" section for the full rationale.

## Safety

- Do not hand-edit build-generated paths: `_site/`, `.jekyll-cache/`,
  `.sass-cache/`, `vendor/`, `.bundle/`, `Gemfile.lock` (the `jekyll-guard`
  plugin blocks this; to change dependencies use `bundle install` / `bundle update`).
- Changes to `CNAME`, `url`, `giscus.repo_id` / `giscus.category_id` need owner
  confirmation first.
- `AGENTS.md` and `.opencode/` are `exclude`d from the build (see `_config.yml`), so the agent guide and kit never leak to the public site. Leak check: a build must leave neither `AGENTS.md` nor `.opencode/` in `_site/`.

## Risk labels and merge policy

Every issue and PR carries exactly one risk label: `risk-low`, `risk-medium` or
`risk-high`. It is a planning-time estimate confirmed at review time, and the
orchestrator uses it to decide whether a merge needs the owner.

Labels:
- `risk-low` (green): no reader-visible behaviour change and nothing irreversible.
- `risk-medium` (amber): reader-visible change that is reversible and guarded.
- `risk-high` (red): can break published URLs/SEO/content, weaken existing
  guards, change how assets are served/cached, or needs manual owner action.

Who sets it, and when:
1. Planning: the issue writer assigns one risk label to the issue and states the
   justification (what can break, blast radius, reversibility) in the issue body.
2. Review: the reviewer confirms or updates the PR's risk label and justifies it
   in the review body. The PR carries the same label as its issue unless the
   reviewer changes it. If the reviewer raises the risk above the planned label,
   the orchestrator escalates to the owner instead of merging.
3. Merge: the orchestrator records the resulting label and the merge decision.

Estimation guide:
- low: docs/README/agent-skill text; comments and typo fixes; test-only additions
  that do not delete or relax an assertion; CI structure that cannot change the
  built site.
- medium: CSS/markup changes to real pages that keep every existing guard green;
  new guards; new reader-visible UI behaviour that is reversible; image-budget
  changes.
- high: changes to published post content, front matter conventions, permalinks
  or URLs; deleting or relaxing an existing guard; anything about how assets, the
  cache or the CDN serve content; `_config.yml`, plugins, dependencies,
  SEO/sitemap/feed; anything irreversible or requiring manual owner action (e.g.
  a hard refresh or a Cloudflare purge).

Merge policy:
- CI green + adversarial review APPROVE + `risk-low` => the orchestrator merges
  autonomously (merge commit, delete branch) and reports afterwards.
- `risk-medium`, `risk-high`, or a missing risk label => explicit owner approval
  is required before merging.

## Before finishing

- Touched `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → build
  Jekyll + run `pytest tests/e2e -v`.
- Touched `_includes/head.html` or added an asset under `assets/` → check the
  "Asset cache versioning" rules above and run
  `tests/e2e/test_stylesheet_cache_version.py`.
- Touched `_layouts/home.html`, `_layouts/tag.html`, `_includes/site-sidebar.html`
  or the list grid in `_sass/` → `tests/e2e/test_sidebar_layout.py` guards the
  sidebar shell (aside after the list in the DOM), the 3 recent posts, the tag
  block and the 375px overflow on `/` and a `/tags/<tag>/` page.
- Touched `assets/` (images) → run `script/check-images` (single file <= 500KB,
  `assets/img/` total <= 6MB) before committing.
- New post only → a build smoke test is enough; verify front matter matches the
  4-pillar taxonomy template (`tags`, `description`).
- Use the dedicated skills when available: `jekyll-post`, `jekyll-verify`, `jekyll-review`.
- Risk label: confirm the issue and the PR each carry exactly one of `risk-low`,
  `risk-medium`, `risk-high` before finishing (see "Risk labels and merge policy").

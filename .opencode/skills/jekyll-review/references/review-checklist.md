# Review checklist for the site

## Liquid / layout (blocker if broken)

- `{% assign %}` / `{% include %}` still use the right variable names and partial file names.
- The provider branches in `_includes/comments.html` and `_layouts/post.html` keep
  their priority order: `site.comments.provider` → legacy Disqus → `none`.
- `page.title` rendered to HTML must pass through `escape` (currently done in `_layouts/post.html`
  — do not drop this filter).
- Post layout (#45): `.post-layout` must keep the post as the main column with the
  tags/related-posts `<aside>` as the secondary one, and the comments block must stay
  outside the grid (full width). `{% assign post_tags = page.tags %}` gates the aside:
  a post without tags stays single column.
- Tag pages (#46): tag chips resolve to `/tags/<tag>/`, built from
  `'/tags/' | append: tag | append: '/'`; one `tags/<tag>.md` per tag in use
  (`layout: tag`, matching `tag:` + `permalink:`).
- List sidebar (#58, reworked in #63): the home list and the tag pages share
  `_includes/site-sidebar.html` — the posts marked `highlight: true` in their own
  front matter (title + compact date + thumbnail, at most 5) plus every tag as a
  row collapsed by default with at most 3 posts. Keep the aside after
  `.site-main` in the DOM, keep the chips coming from `_includes/post-tags.html`,
  and keep the column short: `max-height`/`overflow-y` on the sidebar or a
  cropped/upscaled thumbnail are regressions (`tests/e2e/test_sidebar_layout.py`
  and the #50 overflow guard fail on both).
- Do not use nonexistent config variables; Liquid renders `nil` as an empty string and
  this kind of bug is very hard to spot by eye.

## Config `_config.yml` (blocker if production is wrong)

- `url`, `CNAME`, `giscus.repo_id`, `giscus.category_id`: one wrong character loses
  canonical/feed or the comment thread.
- The minima key is `minima.nav_pages` (since minima 3.0), not the legacy
  `site.header_pages` style.
- `exclude` must keep `AGENTS.md` and `.opencode/` so the agent guide and kit never leak to the public site.
- `minima.nav_pages` must include `tags.md` alongside `about.md` and
  `portfolio.md` (4-pillar `/tags/` page).

## Style / sass

- Only change colors via the skin (`minima.skin`) or the 2 official hooks:
  `_sass/minima/custom-variables.scss` (variables), `_sass/minima/custom-styles.scss`
  (styles). Do not fork a whole partial just to change a few lines.
- Old variable names changed in minima 3.0 (`$brand-color` → `$link-base-color`...),
  using an old name silently applies no style.

## A11y and SEO

- The comments section keeps `aria-labelledby` + `<noscript>` fallback as-is.
- Do not drop `jekyll-seo-tag` / `jekyll-feed` from `plugins` without a reason.
- Add `alt` to images; external links do not need `target="_blank"` unless really needed.

## Post content

- Front matter has enough `layout: post` + `title`; the date in the file name is valid.
- Posts carry `tags: [one-of-4-pillars]` (max 4/post) and a `description`
  (~120-155 chars); see `.opencode/skills/jekyll-post/references/front-matter.md`.
- Keep the opening paragraph concise (it appears on the homepage via `show_excerpts: true`).

## Images

- New images live under `assets/img/<post-slug>/` with lowercase hyphenated names;
  long edge <= 1600px, each file <= 500KB, `assets/img/` total <= 6MB.
- `script/check-images` must pass; do not drift the 500KB/6MB limits.

## Risk label

- Confirm or update the PR's risk label (`risk-low`, `risk-medium`, `risk-high`)
  and justify it in the review body. The PR carries the same label as its issue
  unless the reviewer changes it; raising the risk above the planned label must
  be called out so the orchestrator escalates instead of merging.
- A missing risk label blocks autonomous merge (`risk-medium` policy applies).

## Concurrency

- A review session is a task worker (implementation/fix/PR update/review/merge).
  Never run two task workers in parallel: queue the review and start it only when
  the active task worker finishes.
- At most one task worker at a time, plus one buffer worker reserved only for
  issue/task creation when the owner asks. The buffer worker must not run
  implementation, fix, review or merge work.
- Do not spawn a second task worker for independent queued work; queue it
  instead. Applies to orchestrator spawning decisions.
- Rationale: peak CPU on the owner's machine; two task workers caused CPU
  peaks (replaces the old "max 2 concurrent task workers" default).

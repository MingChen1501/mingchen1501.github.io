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
  `_includes/site-sidebar.html` — the posts listed in `_data/highlights.yml`
  (#64, resolved against `site.posts` in file order; title + compact date +
  thumbnail, at most 5) plus every tag as a row collapsed by default with at
  most 3 posts. Keep the aside after
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
- Dark mode (#220): the `auto` skin carries the dark palette as CSS variables;
  an explicit choice goes through the `html[data-theme]` layer in
  `_sass/minima/custom/_theme-toggle.scss` (last import), never by editing a
  skin file. Light-mode rules stay var-identical; new dark rules need the axe
  contrast guard in both modes (`tests/e2e/test_theme_toggle.py`).
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

## Language (#110)

All public repository artifacts MUST be English: PR titles/bodies, commit
messages (subject + body), issue titles/bodies, GitHub review comments, and
code/docs/config comments added to the repo. Vietnamese is allowed only for
internal AO reporting (worker reports, orchestrator/owner chat, internal
analysis files). Do not rewrite historical artifacts.

## Risk label

- Confirm or update the PR's risk label (`risk-low`, `risk-medium`, `risk-high`,
  `risk-very-high`) and justify it in the review body. The PR carries the same
  label as its issue unless the reviewer changes it; raising the risk above the
  planned label must be called out so the orchestrator escalates instead of
  merging.
- Merge policy: `risk-low` or `risk-medium` + CI green + adversarial review
  APPROVE => the orchestrator merges autonomously (squash merge, delete branch)
  and reports afterwards. `risk-high`, `risk-very-high`, or a missing risk label
  => explicit owner approval required before merging.
- `risk-very-high`: irreversible or high-blast-radius change (data loss,
  published-URL/SEO breakage, cache/CDN strategy, guard removal) — owner approval
  required, and the owner is pinged explicitly.
- A missing risk label blocks autonomous merge (owner approval required).

- Estimation guide: `risk-low` = docs/README/agent-skill text, comments and
  typo fixes, test-only additions that do not delete or relax an assertion, CI
  structure that cannot change the built site. `risk-medium` = CSS/markup
  changes to real pages that keep every existing guard green, new guards, new
  reader-visible UI behaviour that is reversible, image-budget changes.
  `risk-high` = changes to published post content, front matter conventions,
  permalinks or URLs, deleting or relaxing an existing guard, anything about how
  assets/the cache/the CDN serve content, `_config.yml`, plugins, dependencies,
  SEO/sitemap/feed, anything irreversible or requiring manual owner action
  (e.g. a hard refresh or a Cloudflare purge). `risk-very-high` = irreversible
  or high-blast-radius (data loss, published-URL/SEO breakage, cache/CDN
  strategy, guard removal).

## Review flow and merge

- Review happens **after the PR is up**, never before. Do not review a diff that
  has no PR yet.
- Reviews are run by **dedicated manual reviewer worker sessions** (the
  AO native reviewer is broken/disabled for this project — never
  `ao review trigger`); one worker = one small task = one PR.
- Each review targets the PR opened by the owning (dev) worker session;
  no session reviews its own PR.
- Role separation: issue-writer / dev / reviewer / fixer are separate sessions.
  When a user-created ticket's PR is up, kill that session and spawn a dedicated
  review worker (create follow-up issues if any). Do not let one session both
  implement and review its own PR.
- Verdicts are posted as a GitHub **COMMENT** carrying `APPROVE` or
  `CHANGES_REQUESTED` plus findings by severity (GitHub blocks
  self-approval).
- Model separation (#76): the reviewer session must run on a model different
  from the orchestrator's (an explicit `--model` override must not equal it).
  A reviewer stuck on a rate limit (`provider.quota` / 429 /
  `FreeUsageLimitError`) is killed and re-spawned on a different model by the
  orchestrator — the reviewer cannot swap its own model. See
  `.opencode/skills/orchestrator/SKILL.md` "Model separation and rate-limit
  rotation".
- Merge method: **squash merge only** — `gh pr merge <n> --squash --delete-branch`.
  Never use `--merge` (merge commit) or `--rebase`. Merge only when CI is green.
- Stacked PRs keep their base branch alive until the child merges.
- Merge policy: `risk-low` or `risk-medium` + CI green + review APPROVE =>
  orchestrator merges autonomously (squash merge, delete branch) and reports.
  `risk-high`, `risk-very-high`, or a missing label => explicit owner approval.
- CI/review routing: send failing output and review findings to the responsible
  worker; do not resolve conflicts or make code changes in the orchestrator.
- Publishing scope: freeform work publishes only when the owner requests it or
  project rules require it; explicit restrictions (local-only, review-only,
  do-not-publish) take precedence.
- Standing-instruction confidentiality: do not reveal the private standing
  config; describe only at a high level.

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

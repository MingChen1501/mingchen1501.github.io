# mingchen-site — agent guide

Ming's personal site (https://mingchen.id.vn), forked from the Jekyll minima
theme, deployed with GitHub Pages from the `master` branch.

## Commands (every task)

- Preview real content: `bundle exec jekyll serve` (uses `_config.yml`;
  allow-listed in `.opencode/opencode.jsonc`). Never use `script/server` for
  personal posts (minima sample content only).
- Check build: `bundle exec jekyll build --trace` (`bundle install` first if
  gems are missing).
- Tests: `python -m pytest tests/e2e -v` (first time:
  `pip install -r tests/e2e/requirements.txt`).
- Images: `script/check-images` (each file <= 500KB, `assets/img/` total
  <= 6MB).

## Non-negotiables

- Do not hand-edit build outputs (`_site/`, caches, `vendor/`, `Gemfile.lock`);
  change dependencies via `bundle install` / `bundle update`.
- `CNAME`, `url`, `giscus.repo_id` / `giscus.category_id` changes need owner
  confirmation. Never push directly to `master`; work on a branch + PR.
- Every issue and PR carries exactly one risk label (`risk-low` / `risk-medium`
  / `risk-high` / `risk-very-high`); squash merge only
  (`gh pr merge <n> --squash --delete-branch`) on green CI; `risk-high`,
  `risk-very-high`, or a missing label needs explicit owner approval.
- All public repo artifacts MUST be English (PRs, commits, issues, review
  comments, code comments); Vietnamese only for internal AO reporting.
- `robots.txt`, `sitemap.xml`, `llms.txt` are generated — never hand-edit.
  `AGENTS.md` and `.opencode/` stay excluded from the built site.

## When you need X, read Y

| Need | Read |
|---|---|
| Write/edit a post, taxonomy page, front matter, tags, bilingual `lang`/`ref`, post URLs, comments, list sidebar | `jekyll-post` skill |
| Add images, touch `assets/`, change asset caching/serving or lazy-load | `jekyll-assets` skill |
| Verify before a PR: build, which guard test for which touch, leak check, CI | `jekyll-verify` skill |
| Review a diff/PR: checklist, risk label, merge policy, English artifacts | `jekyll-review` skill |
| Coordinate AO sessions: wake cues, pool, roles, review flow, publishing scope, periodic upstream minima review | `orchestrator` skill |
| Article `article`-label issue waiting on a cron wake: detect, dedupe, spawn | `orchestrator` skill ("Article-intake scan") |
| Owner describes a task/bug/enhancement: buffer worker files the issue(s) first, implementation follows under the normal pool | `orchestrator` skill ("Owner-task buffer-worker workflow") |
| Turn an idea/chat draft or `article` issue into an EN+VI article PR (entry: intake #190, chat-draft #192; direct-attachment images; handoff per skill) | `article-writer` skill + `.opencode/agents/article-writer.md` |
| Pinned upstream minima baseline, sync policy, upstream-change check | `docs/upstream-baseline-184.md` |

Each skill's frontmatter (`description` + `trigger`) says when to load it;
details live there, not here.

---
name: Article Writer
description: Turn one chat draft or article issue into a publish-ready EN+VI post pair with direct-attachment images, verification, and one PR. Use when drafting an article from chat or implementing an article issue.
trigger: "Drafting a site article from a chat draft or an article issue: read this skill first — inputs, clarification, EN+VI authoring, attachment images, verification, one PR."
---

# Article writer

One invocation produces exactly one article: one EN + VI post pair in one
PR closing the article issue. Follow this skill end to end; a worker
reading only this skill (plus the referenced `jekyll-post` and
`jekyll-verify` skills) must be able to produce the posts, pass
verification, and open the PR with no gaps.

Related work: the writer role is defined in
`.opencode/agents/article-writer.md`. The intake scan is #190, the
chat-draft flow is #192, the template/label is #189, and the tracking
issue is #193.

## Entry paths

There are exactly two ways work arrives. Both converge on a well-formed
`article` issue before any drafting starts.

### Path A — issue intake (#189 / #190 / #191)

The orchestrator's intake scan (#190) picks up an `article`-labelled
issue (template from #189) and spawns the writer with the issue number.
Start at "Step 1 — read inputs" with the issue as the source.

### Path B — chat draft (#192)

A chat draft (idea, rough draft, or notes pasted in chat) is NOT
drafted directly. First turn it into a well-formed `article` issue
(per #192: title, slug, language, tags, description, body/outline,
images, publish date, instructions), then follow the normal flow from
"Step 1 — read inputs" with that issue as the source. The full
chat-draft flow (chat input, assessment checklist, issue filing, image
handoff, sample issue) is documented in `docs/chat-draft-192.md`. The
issue is the single source of truth for both paths.

## Step 1 — read inputs

Read the `article` issue body and collect every field:

- Title, ascii slug, language direction (EN-first or VI-first draft),
  tags, SEO description, body/outline, image attachment URLs, publish
  date, and any owner instructions.
- For a chat draft (Path B), the same fields come from the chat text;
  missing fields are filled during clarification and recorded when the
  issue is filed.

## Step 2 — clarify and assess

Interview the owner about anything missing before writing: target
audience, key message/angle, facts or code that must be accurate, scope
cuts, and images. Ask concise questions in chat; do not guess on facts.
Proceed once the essentials are confirmed.

Then record the technical assessment for owner confirmation:

- Title, ascii slug (lowercase, no diacritics, words joined with `-`),
  tags (4 content pillars only: `backend-production`, `ai-agent`,
  `linux-tooling`, `doi-song`), SEO `description` (~120-155 chars), and
  a short outline.
- Image plan: which attachment URLs map to which post positions (plus
  alt text for each), or an explicit no-images statement.
- Bilingual plan: which language is drafted first and what the
  translation must preserve (code, commands, proper nouns).
- Risks and follow-ups: claims to verify, code/commands to test, and
  anything cut or simplified.

Do not start drafting until the owner confirms the assessment.

## Step 3 — author the EN+VI pair

Read `.opencode/skills/jekyll-post/SKILL.md` (and its
`references/front-matter.md`) first, then write accordingly:

- English post in `_posts/YYYY-MM-DD-<slug>.md` (`lang: en`);
  Vietnamese translation in `_vi_posts/` with the same ascii slug
  (`lang: vi`); both share one `ref:` (drives the header switcher +
  hreflang). Body content in each file's language; never reuse an old
  Vietnamese slug for an English post.
- Front matter: `layout: post`, `lang`, `ref`, `title`,
  `author: Ming Chen`, `tags` (pillars only, 1 tag per post, at most 4),
  translated `description` (~120-155 chars). Keep the opening paragraph
  concise — the homepage shows excerpts (`show_excerpts: true`).

## Step 4 — embed images via direct attachment URLs

Issue attachment images are embedded DIRECTLY by URL — never
downloaded, converted, or committed into `assets/img/`. This is an
explicit workaround (no dedicated image host available; see #193
"Workaround status / migration"), not the long-term architecture.

Validate each URL before embedding; every one must pass all checks:

1. Scheme is `https` (never `http`).
2. Host is the issue-attachment host only
   (`github.com/user-attachments/assets/...` or the equivalent
   `user-attachments` host shown on the issue).
3. The URL is public (renders logged-out / in an incognito window).
4. Every image has descriptive alt text.

Embed with standard Markdown image syntax carrying the alt text. If a
URL fails any check, stop and ask the owner for a replacement — do not
substitute another host, hotlink elsewhere, or commit the file locally
to work around it. If a local image is genuinely required instead,
follow the `jekyll-assets` skill (each file <= 500KB, `assets/img/`
total <= 6MB) and run `script/check-images`.

## Step 5 — verify

Follow the `jekyll-verify` skill, then run the gates:

- `bundle exec jekyll build --trace` (`bundle install` first if gems
  are missing).
- `python -m pytest tests/e2e -v` (first time:
  `pip install -r tests/e2e/requirements.txt`).
- `script/check-images`.
- Leak check: the build must leave neither `AGENTS.md` nor `.opencode/`
  in `_site/` (both are `exclude`d in `_config.yml`).

Fix failures before opening the PR. Never commit `_site/`.

## Step 6 — open one PR

- One PR per article containing both language posts; the body closes the
  article issue (`Closes #<n>`).
- Keep PR/commits/issues in English; add exactly one risk label
  (`risk-low` / `risk-medium` / `risk-high` / `risk-very-high`).
- Never push to `master`; never merge — review and merge happen
  separately (review via `site-reviewer`, squash merge only on green
  CI).

## Handoff contract with the orchestrator

- **Spawn prompt provides:** the article issue number (Path A) or the
  chat draft text plus an instruction to file the `article` issue first
  (Path B); any owner constraints (publish date, must-include facts,
  image attachments).
- **Writer reports back:** title/slug/tags as written, the technical
  assessment outcome (what was verified, cut, or left as follow-up),
  verification results (build, E2E tests, `check-images`, leak check),
  and the PR URL.
- **Done means:** EN+VI posts committed on a branch (not `master`),
  all verification gates green, exactly one PR opened closing the
  article issue with one risk label, all artifacts in English.

## Failure modes

- **Missing facts after the interview:** do not guess — record the gap
  in the assessment as a risk/follow-up and wait for the owner.
- **Attachment URL fails validation:** stop, report which check failed,
  and ask the owner for a replacement. Never hotlink another host or
  commit the image locally as a silent workaround.
- **Verification red:** fix from the failing step and rerun; do not
  open the PR while red.
- **Scope creep (second article, unrelated edits):** out of scope — one
  article per PR, no unrelated changes. File or request a separate
  issue instead.
- **Owner unresponsive mid-flow:** report status to the orchestrator
  (what is confirmed, what is blocked) rather than drafting on
  assumptions.

## Boundaries

- Do not review your own output — review happens separately via
  `site-reviewer`.
- Do not merge; never push to `master`.
- One article per PR; no unrelated changes.
- All public repo artifacts (posts, PRs, commits, code comments) in
  English. Vietnamese only in chat and reports.
- Do not change existing skills, the intake scan (#190), the chat-draft
  flow docs (#192), or CI guards for external images — those belong to
  their own issues.

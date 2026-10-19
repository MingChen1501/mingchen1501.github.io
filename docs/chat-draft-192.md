# Chat-draft to article-issue workflow (#192)

Docs/process only. This flow turns an informal owner chat draft (text +
images) into a well-formed `article` issue that the intake scan (#190)
and the article worker (#191) consume downstream. No implementation,
automation, or code changes live here.

Related: the issue template and `article` label (#189), the intake scan
(`orchestrator` skill, "Article-intake scan"), the writer procedure
(`article-writer` skill, "Path B — chat draft"), and the tracking issue
(#193).

## Step 1 — owner shares the draft in chat

The owner pastes draft text and images directly into chat. Either form
is acceptable:

- Rough text: an idea, notes, a partial draft, or a full draft.
- Images: pasted or attached in chat alongside the text, in reading
  order where possible.

The agent acknowledges what was received and lists anything obviously
missing (see the assessment checklist below) before proceeding.

## Step 2 — technical assessment and clarification

The agent interviews the owner about anything missing — target
audience, key message/angle, facts or code that must be accurate, scope
cuts, and images. Questions stay concise; the agent never guesses on
facts. Drafting never starts here: this step only prepares the issue.

The agent then records the technical assessment and waits for owner
confirmation. Required assessment contents:

| # | Item | Rule |
|---|------|------|
| 1 | Title | Working title for both language drafts. |
| 2 | Slug | ASCII only, lowercase, words joined with `-`, no diacritics; unique, never reuses an old Vietnamese slug. |
| 3 | Tags | 1-4 tags from the 4 content pillars only: `backend-production`, `ai-agent`, `linux-tooling`, `doi-song`. No new tags. |
| 4 | SEO description | One sentence, ~120-155 characters, summarising the article. |
| 5 | Image plan | Which chat images map to which post positions (plus alt text for each), or an explicit no-images statement. |
| 6 | Bilingual plan | Which language is drafted first (EN-first or VI-first) and what the translation must preserve (code, commands, proper nouns). |
| 7 | Risks and follow-ups | Claims to verify, code/commands to test, and anything cut or simplified. |

Do not file the issue until the owner confirms the assessment.

## Step 3 — file the `article` issue

After confirmation, the agent creates one `article` issue using the
template (`.github/ISSUE_TEMPLATE/article.yml`), carrying the `article`
label plus exactly one risk label. Every template field is filled from
the confirmed assessment and the chat draft:

- Article title, slug, primary language, tags, description.
- Body / outline: the draft substance (full text or section-by-section
  outline with key points, facts, and links).
- Images: the attachment URLs (see Step 4), each with alt text and its
  post position.
- Publish date (when the owner confirms one) and special instructions
  (tone, audience, links to keep, sections to skip).

The issue body also carries an authoring checklist so the downstream
worker can verify completeness at a glance:

```md
- [ ] Title, slug, primary language, tags (pillars only), and SEO description confirmed
- [ ] Body / outline covers every section the posts must include
- [ ] Every image has an attachment URL, alt text, and a post position (or no-images stated)
- [ ] Publish date and special instructions recorded (or explicitly none)
```

From this point the issue is the single source of truth. The chat draft
is superseded; corrections go to the issue, not back to chat.

## Step 4 — image handoff (chat to issue attachments)

Images travel from chat to the article issue as uploads/attachments,
preserving them for the downstream worker:

1. The agent uploads each confirmed chat image to the filed `article`
   issue (or instructs the owner to upload them when the agent cannot).
2. Each upload produces a GitHub attachment URL
   (`https://github.com/user-attachments/assets/...`); the agent edits
   the issue `images` field to list every URL with its alt text and
   post position.
3. The downstream worker embeds those URLs directly in the posts —
   never downloads, converts, or commits them under `assets/img/`.

Every embedded URL must be `https`, publicly accessible, hosted on the
GitHub attachments host only, and carry descriptive alt text. A URL
that fails any check blocks drafting until the owner provides a
replacement.

## Workaround status / migration

Direct issue-attachment URLs are an explicit WORKAROUND, not the
long-term architecture.

- Reason: the preferred dedicated object storage is unavailable due to
  billing, so there is currently no dedicated image host.
- Scope: applies only to images uploaded to article issues and embedded
  by direct attachment URL. Pre-existing local images under
  `assets/img/` keep the existing budget and conventions.
- Migration trigger: when Cloudflare R2, Amazon S3, or another
  dedicated storage becomes available and the owner approves it.
- Cleanup steps on migration: move issue-attachment images to the new
  store; update post URLs to the new host; remove temporary
  guards/exemptions added for external attachments; update the central
  image-host config and docs in one place.

## Sample filled-in article issue shape

```md
Title: [article] Switching from Windows 11 to Fedora

Slug: switching-from-windows-11-to-fedora
Primary language: en
Tags: linux-tooling
Description: How I replaced Windows 11 with Fedora for a leaner dev setup,
what broke, and the fixes that stuck. (134 characters)
Body / outline:
- Intro: why I switched, machine context.
- Setup: Fedora edition, partitioning, drivers (link: ...).
- What broke and the fix for each.
- Verdict: who should / should not switch.
Images:
- Alt "Fedora desktop after setup" ->
  https://github.com/user-attachments/assets/XXXX (after the setup section)
Publish date: 2026-11-01
Special instructions: Practical tone for developers; keep the driver
download link; no affiliate links.
Authoring checklist:
- [x] Title, slug, primary language, tags, and SEO description confirmed
- [x] Body / outline covers every section
- [x] Image has attachment URL, alt text, and post position
- [x] Publish date and special instructions recorded
```

## Boundaries

- This flow ends at the filed issue plus the image handoff. Drafting,
  verification, and the PR belong to the article worker (#191); pickup
  belongs to the intake scan (#190).
- Out of scope: the issue template/label (#189), the intake scan
  (#190), the writer procedure (#191), any implementation or
  automation, and any CDN or dedicated-storage work.
- One chat draft becomes one `article` issue; a second article idea is
  a separate issue, never bundled in.
- All public repo artifacts (issues, posts, PRs, commits, code
  comments) in English. Vietnamese only in chat and reports.

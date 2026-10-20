---
name: Jekyll Review
description: Review Jekyll site layout/include/sass/config changes. Use when checking a diff before a PR or with the /review command.
trigger: "Reviewing a site diff or PR (correctness, risk label, merge policy, English artifacts): read this skill plus references/review-checklist.md."
---

# Review site changes

## Workflow

1. Get the scope: `git status --short`, `git diff --stat`, then `git diff`.
2. Check each file against `references/review-checklist.md` — correctness first, polish later.
3. Report by severity, each item with `file:line`:
   - **Blocker**: broken layout, lost comments, wrong production config.
   - **Should fix**: maintainability, a11y, SEO/feed.
   - **Suggestion**: style, spelling, small improvements.
4. Confirm or update the PR risk label (`risk-low`/`risk-medium`/`risk-high`/`risk-very-high`) and justify it (see `references/review-checklist.md` "Risk label").
5. Review flow: review only after the PR is up (never before); run as a
   dedicated manual reviewer worker session (the AO native reviewer is
   broken/disabled — never `ao review trigger`); post the verdict as a
   GitHub COMMENT carrying APPROVE or CHANGES_REQUESTED (self-approval is
   blocked). See `references/review-checklist.md` "Review flow and merge".
6. Concurrency: a review session counts as a task worker — do not run it in
   parallel with another task worker; queue it (see `references/review-checklist.md`
   "Concurrency").
7. Do not edit code during review. Record findings to fix separately.

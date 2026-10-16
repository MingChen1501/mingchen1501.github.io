---
name: Jekyll Review
description: Review Jekyll site layout/include/sass/config changes. Use when checking a diff before a PR or with the /review command.
---

# Review site changes

## Workflow

1. Get the scope: `git status --short`, `git diff --stat`, then `git diff`.
2. Check each file against `references/review-checklist.md` — correctness first, polish later.
3. Report by severity, each item with `file:line`:
   - **Blocker**: broken layout, lost comments, wrong production config.
   - **Should fix**: maintainability, a11y, SEO/feed.
   - **Suggestion**: style, spelling, small improvements.
4. Do not edit code during review. Record findings to fix separately.

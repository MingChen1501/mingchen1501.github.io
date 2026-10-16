---
description: Build Jekyll and run E2E tests for the current changes
---

Check the current $ARGUMENTS changes following the `jekyll-verify` skill: determine the scope
from `git status`, run the matching build and tests, report each step's result.
Stop at the first error and suggest a fix; do not open a PR while anything is red.

# Single source of truth for the shipped first-party JS/CSS byte budgets
# enforced by tests/e2e/test_asset_budget.py (issue #267) and
# tests/e2e/test_syntax_highlight_css.py (issue #275).
#
# Images have their own pinned budget (script/image-budget.sh, issues
# #32/#33); this file pins the same idea for shipped scripts and the
# compiled stylesheets: total first-party bytes actually referenced by
# each page kind stay under these ceilings, so any new global script (or
# an existing one doubling in size) fails the guard instead of silently
# regrowing every page. No runtime behavior change — test-only numbers.
#
# Page kinds follow the test_post_only_js.py split:
#   - PAGE  (home, tag, about, portfolio): the scripts every page needs.
#   - POST  (post, production worst case): the page scripts + the post-only
#     scripts (#253: share.js, reading-progress.js, plus #318: copy-code.js,
#     lightbox.js, plus #345: toc-spy.js) + the comments sync script
#     (assets/js/giscus-theme.js, rendered only in production builds
#     where comments are enabled).
#   - CSS: the main compiled assets/css/style.css, identical for every
#     page kind, plus the conditional companion assets/css/syntax.css
#     (#275: Rouge token rules, linked from _includes/head.html only on
#     pages whose rendered content contains Rouge output).
#
# Measured 2026-10-21 (dev and JEKYLL_ENV=production builds agree, except
# the production-only comments script):
#   page   21225 B (7 files), post 38298 B (11 files, prod),
#   css main 45120 B, css syntax companion 17455 B (was one 62449 B file
#   before #275; code-free pages download 27.8% less render-blocking CSS).
# Re-measured 2026-10-22 for #383 (dev and production agree): post
# 44220 B (11 files, prod) — toc-spy.js grew ~10.1KB -> ~14.5KB with the
# phone FAB + sheet handoff, article-range progress ring, and dialog focus
# management, reusing the same observer and rAF tick (no new request).
# (#342 removed the search page and its search.js: the former SEARCH kind
# is gone with its ceiling. #345 re-measured after the nested-disclosure
# rework: toc-spy.js grew ~5.1KB -> ~8.6KB with the branch collapse,
# auto-expand, and pinning logic.)
# Re-measured 2026-10-22 for #402 (dev build): post-source total
# 49151 B (11 files) — copy-code.js carries the success-state class and
# lightbox.js the per-navigation fade restart, ~260 B of intentional
# addition, so the post ceiling moves 49152 -> 49664; the compiled main
# sheet grows 48652 -> 52360 B with the shared keyframes, the global
# reduced-motion guard, and the per-control tokenized transitions, so the
# CSS ceiling moves 50176 -> 57344 (~10% headroom, per policy).
#
# Headroom policy: each ceiling sits ~10% above its measured total — wide
# enough for a small intentional addition, tight enough that re-adding any
# one current script to a page kind that dropped it breaches the ceiling
# (the lightest script is lazy-load.js at 723 B; the #253 win needs
# ~5.4 KB of slack to regress, and the page ceiling leaves only ~2.3 KB),
# and tight enough that folding the syntax companion back into the main
# sheet (~17 KB) breaches the main CSS ceiling.
# Bump a ceiling only with an intentional change: re-measure both
# environments, update the numbers here AND the pinned copy in
# tests/e2e/test_asset_budget.py, and record the new totals above.
#
# shellcheck shell=sh

# Max first-party JS bytes for home/tag/about/portfolio pages.
MAX_JS_PAGE_BYTES=23552
# Max first-party JS bytes for post pages (production worst case).
MAX_JS_POST_BYTES=49664
# Max bytes for the compiled code-free assets/css/style.css.
MAX_CSS_BYTES=57344
# Max bytes for the conditional companion assets/css/syntax.css (#275).
MAX_SYNTAX_CSS_BYTES=19456

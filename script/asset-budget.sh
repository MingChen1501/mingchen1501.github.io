# Single source of truth for the shipped first-party JS/CSS byte budgets
# enforced by tests/e2e/test_asset_budget.py (issue #267).
#
# Images have their own pinned budget (script/image-budget.sh, issues
# #32/#33); this file pins the same idea for shipped scripts and the
# compiled stylesheet: total first-party bytes actually referenced by
# each page kind stay under these ceilings, so any new global script (or
# an existing one doubling in size) fails the guard instead of silently
# regrowing every page. No runtime behavior change — test-only numbers.
#
# Page kinds follow the test_post_only_js.py split:
#   - PAGE  (home, tag, about, portfolio): the 7 scripts every page needs.
#   - POST  (post, production worst case): the 7 above + the 2 post-only
#     scripts (#253: share.js, reading-progress.js) + the comments sync
#     script (assets/js/giscus-theme.js, rendered only in production
#     builds where comments are enabled).
#   - SEARCH (search EN/VI): the 7 above + assets/js/search.js (the extra
#     site-utils.js tag in _includes/search.html re-fetches nothing: the
#     browser already has that URL from sub-footer.html, so budgets count
#     unique files).
#   - CSS: the single compiled assets/css/style.css linked from
#     _includes/head.html, identical for every page kind.
#
# Measured 2026-10-20 (dev and JEKYLL_ENV=production builds agree, except
# the production-only comments script):
#   page   21225 B (7 files), post 29689 B (10 files, prod),
#   search 28961 B (8 unique files), css 62455 B.
#
# Headroom policy: each ceiling sits ~10% above its measured total — wide
# enough for a small intentional addition, tight enough that re-adding any
# one current script to a page kind that dropped it breaches the ceiling
# (the lightest script is lazy-load.js at 723 B; the #253 win needs
# ~5.4 KB of slack to regress, and the page ceiling leaves only ~2.3 KB).
# Bump a ceiling only with an intentional change: re-measure both
# environments, update the numbers here AND the pinned copy in
# tests/e2e/test_asset_budget.py, and record the new totals above.
#
# shellcheck shell=sh

# Max first-party JS bytes for home/tag/about/portfolio pages.
MAX_JS_PAGE_BYTES=23552
# Max first-party JS bytes for post pages (production worst case).
MAX_JS_POST_BYTES=32768
# Max first-party JS bytes for search pages (EN/VI).
MAX_JS_SEARCH_BYTES=32256
# Max bytes for the compiled assets/css/style.css.
MAX_CSS_BYTES=69632

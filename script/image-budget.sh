# Single source of truth for the image budgets enforced by script/check-images
# (issues #32/#33; consolidated here for #171 so the literals cannot drift).
#
# Sourced by script/check-images; parsed by tests/e2e/test_check_images.py,
# which asserts these exact derived values. Do NOT redeclare these constants
# anywhere else — per-file cap or total-gate changes are out of scope for
# #171 (remote hosting is tracked in #55) and need a decision recorded in the
# tracking issue before the numbers here move.
#
# shellcheck shell=sh

# Max bytes for a single image file: 500 KiB.
MAX_FILE_BYTES=512000
# Max bytes for the whole assets/img tree: 6 MiB.
MAX_TOTAL_BYTES=6291456
# Max pixels for an image's long edge.
MAX_DIMENSION=1600

#!/bin/sh
# Print the standard AO role footer for GitHub artefacts (issue #350).
#
# Every worker writes with the same GitHub account, so each artefact is
# signed with the role that produced it. Append this footer's two lines
# to the end of PR bodies, issue bodies, review bodies, and issue/PR
# comments, preceded by a blank line:
#
#   <!-- ao-role: <role> -->
#   Role: <role> · AO session <session-id>
#
# When the session id is unknown (e.g. a reviewer posting a verdict
# without it at hand), omit it and print only "Role: <role>".
#
# Usage:
#   script/ao-role-footer.sh <role> [session-id]
#   script/ao-role-footer.sh dev-peer-review mingchen-site-144
set -u

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: script/ao-role-footer.sh <role> [session-id]" >&2
  exit 1
fi

role="$1"
session="${2:-}"

case "$role" in
  orchestrator|product-owner|business-analyst|architect|qa-lead|release-manager|spec-reviewer|dev|dev-peer-review|dev-takeover|content|content-review)
    ;;
  *)
    echo "error: unknown role '$role' (expected one of: orchestrator, product-owner, business-analyst, architect, qa-lead, release-manager, spec-reviewer, dev, dev-peer-review, dev-takeover, content, content-review)" >&2
    exit 1
    ;;
esac

printf '<!-- ao-role: %s -->\n' "$role"
if [ -n "$session" ]; then
  printf 'Role: %s · AO session %s\n' "$role" "$session"
else
  printf 'Role: %s\n' "$role"
fi

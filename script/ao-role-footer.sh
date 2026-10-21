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
#   script/ao-role-footer.sh site-reviewer mingchen-site-144
set -u

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: script/ao-role-footer.sh <role> [session-id]" >&2
  exit 1
fi

role="$1"
session="${2:-}"

case "$role" in
  orchestrator|article-writer|site-reviewer|spec-reviewer|architect|qa-lead|release-manager|product-owner|business-analyst|worker)
    ;;
  *)
    echo "warning: unknown role '$role' (expected one of: orchestrator, article-writer, site-reviewer, spec-reviewer, architect, qa-lead, release-manager, product-owner, business-analyst, worker)" >&2
    ;;
esac

printf '<!-- ao-role: %s -->\n' "$role"
if [ -n "$session" ]; then
  printf 'Role: %s · AO session %s\n' "$role" "$session"
else
  printf 'Role: %s\n' "$role"
fi

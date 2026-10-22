#!/bin/sh
# Safely update one AO project's config without dropping other keys.
#
# Background: `ao project set-config <id>` with a focused field flag
# *replaces* the whole per-project config, so a single focused flag once
# wiped models, reviewers, and the orchestrator pool rule (issue #354). This wrapper
# reads the current config first, merges only the requested keys, and
# writes the full merged object back with `--config-json`.
#
# Usage:
#   script/ao-project-config.sh <project-id> [options]
#
# Options (each maps to the config key in brackets):
#   --agent-rules-file PATH   [agentRulesFile]
#   --agent-rules TEXT        [agentRules]
#   --orchestrator-rules TEXT [orchestratorRules]
#   --model MODEL             [agentConfig.model] (top-level default model)
#   --worker-model MODEL      [worker.agentConfig.model] (wrapper-only;
#                             no `ao project set-config` flag sets this)
#   --orchestrator-model MODEL
#                             [orchestrator.agentConfig.model] (wrapper-only)
#   --reviewer HARNESS        [reviewers] (repeatable; replaces the whole
#                             reviewers list with harness-only entries,
#                             mirroring the ao flag semantics)
#   --worker-agent HARNESS    [worker.agent]
#   --orchestrator-agent HARNESS
#                             [orchestrator.agent]
#   --default-branch BRANCH   [defaultBranch]
#   --permission MODE         [agentConfig.permissions]
#   --session-prefix PREFIX   [sessionPrefix]
#   --env KEY=VALUE           merged into [env] (repeatable; additive only —
#                             removing a var needs a full --config-json write)
#   --dry-run                 print the merged JSON to stdout and change
#                             nothing (the before/after key diff still goes
#                             to stderr)
#   -h, --help                print this help and exit
#
# The script refuses to run when the current config cannot be read
# (`ao project get <id> --json` fails or returns an unexpected shape),
# because writing then would risk the same wipe this wrapper exists to
# prevent. With no update flags it also refuses (nothing to merge).
set -u

usage() {
  cat <<'USAGE'
Usage: script/ao-project-config.sh <project-id> [options]

Safely update one AO project's config: reads the current config with
`ao project get <id> --json`, merges only the requested keys, and
writes the full merged object back with
`ao project set-config <id> --config-json`. Never use a bare
field-flag invocation: one focused flag replaces the whole
per-project config and drops everything else
(models, reviewers, orchestrator rules).

Options (each maps to the config key in brackets):
  --agent-rules-file PATH   [agentRulesFile]
  --agent-rules TEXT        [agentRules]
  --orchestrator-rules TEXT [orchestratorRules]
  --model MODEL             [agentConfig.model] (top-level default model)
  --worker-model MODEL      [worker.agentConfig.model] (wrapper-only;
                            no `ao project set-config` flag sets this)
  --orchestrator-model MODEL
                            [orchestrator.agentConfig.model] (wrapper-only)
  --reviewer HARNESS        [reviewers] (repeatable; replaces the whole
                            reviewers list with harness-only entries,
                            mirroring the ao flag semantics)
  --worker-agent HARNESS    [worker.agent]
  --orchestrator-agent HARNESS
                            [orchestrator.agent]
  --default-branch BRANCH   [defaultBranch]
  --permission MODE         [agentConfig.permissions]
  --session-prefix PREFIX   [sessionPrefix]
  --env KEY=VALUE           merged into [env] (repeatable; additive only --
                            removing a var needs a full --config-json write)
  --dry-run                 print the merged JSON to stdout and change
                            nothing (the before/after key diff still goes
                            to stderr)
  -h, --help                print this help and exit
USAGE
}

PROJECT_ID=""
DRY_RUN=0
AGENT_RULES_FILE=""
AGENT_RULES_SET=0
AGENT_RULES=""
ORCH_RULES_SET=0
ORCH_RULES=""
MODEL=""
WORKER_MODEL=""
ORCH_MODEL=""
WORKER_AGENT=""
ORCH_AGENT=""
DEFAULT_BRANCH=""
PERMISSION=""
SESSION_PREFIX=""
REVIEWERS=""
ENVS=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --agent-rules-file|--agent-rules|--orchestrator-rules|--model|--worker-model|--orchestrator-model|--worker-agent|--orchestrator-agent|--default-branch|--permission|--session-prefix)
      opt="$1"
      if [ $# -lt 2 ]; then
        echo "error: $opt needs a value" >&2
        exit 2
      fi
      val="$2"
      case "$opt" in
        --agent-rules-file) AGENT_RULES_FILE="$val" ;;
        --agent-rules) AGENT_RULES="$val"; AGENT_RULES_SET=1 ;;
        --orchestrator-rules) ORCH_RULES="$val"; ORCH_RULES_SET=1 ;;
        --model) MODEL="$val" ;;
        --worker-model) WORKER_MODEL="$val" ;;
        --orchestrator-model) ORCH_MODEL="$val" ;;
        --worker-agent) WORKER_AGENT="$val" ;;
        --orchestrator-agent) ORCH_AGENT="$val" ;;
        --default-branch) DEFAULT_BRANCH="$val" ;;
        --permission) PERMISSION="$val" ;;
        --session-prefix) SESSION_PREFIX="$val" ;;
      esac
      shift 2
      ;;
    --reviewer)
      if [ $# -lt 2 ]; then
        echo "error: --reviewer needs a value" >&2
        exit 2
      fi
      if [ -z "$REVIEWERS" ]; then
        REVIEWERS="$2"
      else
        REVIEWERS="$REVIEWERS
$2"
      fi
      shift 2
      ;;
    --env)
      if [ $# -lt 2 ]; then
        echo "error: --env needs a KEY=VALUE value" >&2
        exit 2
      fi
      case "$2" in
        *=*) ;;
        *)
          echo "error: --env needs a KEY=VALUE value (got '$2')" >&2
          exit 2
          ;;
      esac
      if [ -z "$ENVS" ]; then
        ENVS="$2"
      else
        ENVS="$ENVS
$2"
      fi
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "error: unknown option '$1' (see --help)" >&2
      exit 2
      ;;
    *)
      if [ -n "$PROJECT_ID" ]; then
        echo "error: only one <project-id> is accepted (got '$1')" >&2
        exit 2
      fi
      PROJECT_ID="$1"
      shift
      ;;
  esac
done

if [ $# -gt 0 ]; then
  echo "error: unexpected argument '$1' (see --help)" >&2
  exit 2
fi

if [ -z "$PROJECT_ID" ]; then
  echo "usage: script/ao-project-config.sh <project-id> [options]" >&2
  exit 2
fi

if [ -z "$AGENT_RULES_FILE$AGENT_RULES$ORCH_RULES$MODEL$WORKER_MODEL$ORCH_MODEL$WORKER_AGENT$ORCH_AGENT$DEFAULT_BRANCH$PERMISSION$SESSION_PREFIX$REVIEWERS$ENVS" ] && [ "$AGENT_RULES_SET$ORCH_RULES_SET" = "00" ]; then
  echo "error: no updates requested; pass at least one --flag (see --help)" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required for the config merge" >&2
  exit 1
fi

if ! command -v ao >/dev/null 2>&1; then
  echo "error: 'ao' is not on PATH" >&2
  exit 1
fi

TMP_DIR="/tmp/opencode/ao-config-$$"
mkdir -p "$TMP_DIR" || {
  echo "error: cannot create temp dir $TMP_DIR" >&2
  exit 1
}
ERR_FILE="$TMP_DIR/get-err.txt"
CURRENT_FILE="$TMP_DIR/current.json"
MERGED_FILE="$TMP_DIR/merged.json"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

CURRENT="$(ao project get "$PROJECT_ID" --json 2>"$ERR_FILE")" || {
  echo "error: refusing to run: cannot read current config for project '$PROJECT_ID':" >&2
  cat "$ERR_FILE" >&2
  exit 1
}

export AO_CFG_AGENT_RULES_FILE="$AGENT_RULES_FILE"
export AO_CFG_AGENT_RULES="$AGENT_RULES"
export AO_CFG_AGENT_RULES_SET="$AGENT_RULES_SET"
export AO_CFG_ORCH_RULES="$ORCH_RULES"
export AO_CFG_ORCH_RULES_SET="$ORCH_RULES_SET"
export AO_CFG_MODEL="$MODEL"
export AO_CFG_WORKER_MODEL="$WORKER_MODEL"
export AO_CFG_ORCH_MODEL="$ORCH_MODEL"
export AO_CFG_WORKER_AGENT="$WORKER_AGENT"
export AO_CFG_ORCH_AGENT="$ORCH_AGENT"
export AO_CFG_DEFAULT_BRANCH="$DEFAULT_BRANCH"
export AO_CFG_PERMISSION="$PERMISSION"
export AO_CFG_SESSION_PREFIX="$SESSION_PREFIX"
export AO_CFG_REVIEWERS="$REVIEWERS"
export AO_CFG_ENVS="$ENVS"
export AO_CFG_PROJECT_ID="$PROJECT_ID"

printf '%s' "$CURRENT" >"$CURRENT_FILE"
python3 - "$CURRENT_FILE" "$MERGED_FILE" <<'PYEOF' || exit 1
import json
import os
import sys

current_path, merged_path = sys.argv[1], sys.argv[2]

try:
    with open(current_path, encoding="utf-8") as handle:
        payload = json.load(handle)
except json.JSONDecodeError as exc:
    print("error: refusing to run: 'ao project get --json' "
          "returned unparsable output: %s" % exc, file=sys.stderr)
    sys.exit(1)

if not isinstance(payload, dict) or payload.get("status") != "ok" \
        or not isinstance(payload.get("project"), dict):
    print("error: refusing to run: unexpected 'ao project get --json' "
          "shape: %r" % (payload,), file=sys.stderr)
    sys.exit(1)

project_id = os.environ["AO_CFG_PROJECT_ID"]
if str(payload["project"].get("id", "")) != project_id:
    print("error: refusing to run: 'ao project get' returned id %r, "
          "expected %r" % (payload["project"].get("id"), project_id),
          file=sys.stderr)
    sys.exit(1)

config = payload["project"].get("config")
if config is None:
    config = {}
if not isinstance(config, dict):
    print("error: refusing to run: project config is not an object: %r"
          % (config,), file=sys.stderr)
    sys.exit(1)

before = json.loads(json.dumps(config))


def ensure(path):
    node = config
    for key in path:
        child = node.get(key)
        if not isinstance(child, dict):
            child = {}
            node[key] = child
        node = child
    return node


def redact(value, key):
    if key == "env" and isinstance(value, dict):
        return {name: "***" for name in value}
    return value


def compact(value, key=None):
    text = json.dumps(redact(value, key), sort_keys=True)
    if len(text) > 160:
        return text[:157] + "..."
    return text


g = os.environ.get
if g("AO_CFG_AGENT_RULES_FILE"):
    config["agentRulesFile"] = g("AO_CFG_AGENT_RULES_FILE")
if g("AO_CFG_AGENT_RULES_SET") == "1":
    config["agentRules"] = g("AO_CFG_AGENT_RULES")
if g("AO_CFG_ORCH_RULES_SET") == "1":
    config["orchestratorRules"] = g("AO_CFG_ORCH_RULES")
if g("AO_CFG_MODEL"):
    ensure(["agentConfig"])["model"] = g("AO_CFG_MODEL")
if g("AO_CFG_WORKER_MODEL"):
    ensure(["worker", "agentConfig"])["model"] = g("AO_CFG_WORKER_MODEL")
if g("AO_CFG_ORCH_MODEL"):
    ensure(["orchestrator", "agentConfig"])["model"] = \
        g("AO_CFG_ORCH_MODEL")
if g("AO_CFG_WORKER_AGENT"):
    ensure(["worker"])["agent"] = g("AO_CFG_WORKER_AGENT")
if g("AO_CFG_ORCH_AGENT"):
    ensure(["orchestrator"])["agent"] = g("AO_CFG_ORCH_AGENT")
if g("AO_CFG_DEFAULT_BRANCH"):
    config["defaultBranch"] = g("AO_CFG_DEFAULT_BRANCH")
if g("AO_CFG_PERMISSION"):
    ensure(["agentConfig"])["permissions"] = g("AO_CFG_PERMISSION")
if g("AO_CFG_SESSION_PREFIX"):
    config["sessionPrefix"] = g("AO_CFG_SESSION_PREFIX")
if g("AO_CFG_REVIEWERS"):
    config["reviewers"] = [
        {"harness": line}
        for line in g("AO_CFG_REVIEWERS").splitlines() if line
    ]
if g("AO_CFG_ENVS"):
    env = config.get("env")
    if not isinstance(env, dict):
        env = {}
        config["env"] = env
    for line in g("AO_CFG_ENVS").splitlines():
        if not line:
            continue
        key, _, value = line.partition("=")
        env[key] = value

before_keys = sorted(before)
after_keys = sorted(config)
added = [k for k in after_keys if k not in before]
removed = [k for k in before_keys if k not in after_keys]
changed = [k for k in after_keys
           if k in before and not (
               json.dumps(before[k], sort_keys=True)
               == json.dumps(config[k], sort_keys=True))]

print("config diff for project '%s' (%d top-level keys -> %d):"
      % (project_id, len(before_keys), len(after_keys)), file=sys.stderr)
for key in changed:
    print("  ~ %s: %s -> %s"
          % (key, compact(before[key], key), compact(config[key], key)),
          file=sys.stderr)
for key in added:
    print("  + %s: %s" % (key, compact(config[key], key)), file=sys.stderr)
for key in removed:
    print("  - %s: %s" % (key, compact(before[key], key)), file=sys.stderr)
if not (changed or added or removed):
    print("  (no changes; merged config is identical)", file=sys.stderr)
unchanged = [k for k in after_keys if k not in changed
             and k not in added]
print("  unchanged: %s" % (", ".join(unchanged) if unchanged else "(none)"),
      file=sys.stderr)

with open(merged_path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, sort_keys=True, indent=2)
    handle.write("\n")
PYEOF

MERGED="$(cat "$MERGED_FILE")"

if [ "$DRY_RUN" -eq 1 ]; then
  printf '%s\n' "$MERGED"
  exit 0
fi

ao project set-config "$PROJECT_ID" --config-json "$MERGED" >/dev/null || {
  echo "error: 'ao project set-config --config-json' failed; config unchanged" >&2
  exit 1
}
echo "wrote merged config for project '$PROJECT_ID' via --config-json."

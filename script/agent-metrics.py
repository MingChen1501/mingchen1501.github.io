#!/usr/bin/env python3
"""Agent operations report for this project (issue #392).

Reads the local AO database in READ-ONLY mode plus local git history and
emits a markdown (or JSON) report: sessions and tasks per agent role,
throughput, quality signals, retries/flakiness, and the agent + human
cost model.

Usage:
    python3 script/agent-metrics.py --help
    python3 script/agent-metrics.py --format md
    python3 script/agent-metrics.py --format md --project mingchen-site \\
        --db ~/.ao/data/ao.db --days 30
    python3 script/agent-metrics.py --format json --hourly-rate 50

Deterministic queries (same DB state -> same output on the same day):
    Q1  sessions per role: SELECT display_name, kind, activity_state,
        is_terminated, issue_id, created_at, updated_at FROM sessions
        WHERE project_id = ? [AND created_at >= ?]
    Q2  tasks per role: Q1 grouped by role joined to
        SELECT session_id, number, is_merged, created_at_provider,
        merged_at_provider FROM pr (PRs opened per session),
        SELECT session_id, COUNT(*) FROM review_run (reviews run),
        SELECT session_id, COUNT(*) FROM reports (verifications/posts)
    Q3  throughput: spawn->PR-open and PR-open->merge durations from
        sessions.created_at JOIN pr.created_at_provider /
        pr.merged_at_provider; review rounds per PR from COUNT(*) of
        pr_reviews + review_run per pr_url; CI cycles per PR from
        COUNT(*) of pr_checks per pr_url
    Q4  quality: first-pass rejections from review_run.verdict =
        'changes_requested' and pr_reviews.state = 'CHANGES_REQUESTED';
        reverts from `git log --oneline --grep=revert -i`; post-merge
        failures need CI history (Unavailable offline, see
        script/dora-metrics.py)
    Q5  retries: pr_checks rows sharing (pr_url, name) with at least one
        failure conclusion and one later success conclusion
    Q6  cost: SELECT provider_id, model_id, input_tokens,
        cached_input_tokens, output_tokens, estimated_cost_nanos FROM
        model_usage_events joined via usage_sources/usage_bindings to
        sessions for the per-role split; unit prices from the pricing
        catalog (see --pricing-dir)

Read-only guarantee: the database is opened with
`sqlite3.connect("file:...?mode=ro", uri=True)` and the script never
executes INSERT/UPDATE/DELETE/CREATE/ATTACH. Missing tables or a missing
DB degrade gracefully to `Unavailable` -- never a traceback.

No PII: the report contains only aggregate counts, durations, and USD
amounts. Prompts, report notes, comment bodies, and author names are
never printed.
"""

import argparse
import json
import os
import re
import sqlite3
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB = os.environ.get(
    "AO_DB", str(Path.home() / ".ao" / "data" / "ao.db")
)
DEFAULT_PRICING_DIR = os.environ.get(
    "AO_PRICING_DIR",
    str(Path.home() / ".ao" / "data" / "pricing" / "catalog" / "v1"),
)

CANONICAL_ROLES = (
    "orchestrator",
    "product-owner",
    "business-analyst",
    "architect",
    "qa-lead",
    "release-manager",
    "spec-reviewer",
    "dev",
    "dev-peer-review",
    "dev-takeover",
    "content",
    "content-review",
)

# `dev-peer-review` must win over the `dev` prefix, so match longest first.
_ROLE_RE = re.compile(
    r"^(" + "|".join(sorted(CANONICAL_ROLES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_BUFFER_RE = re.compile(r"^buffer\b", re.IGNORECASE)

WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|DETACH"
    r"|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


def parse_role(display_name):
    """Map a session display name to a canonical role or a bucket."""
    name = (display_name or "").strip()
    match = _ROLE_RE.match(name)
    if match:
        return match.group(1).lower()
    if _BUFFER_RE.match(name):
        return "buffer"
    if name == "":
        return "unlabeled"
    return "other"


def parse_ts(value):
    """Parse AO/GitHub timestamps; return None when unparseable."""
    if not value:
        return None
    text = str(value).strip()
    # AO timestamps carry a trailing " UTC" after the numeric offset and
    # up to nanosecond fractions; normalise both for strptime/%f.
    text = re.sub(r"\s+UTC$", "", text)
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f %z",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def hours(delta):
    return round(delta.total_seconds() / 3600.0, 2)


def percentile(sorted_vals, pct):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * (pct / 100.0)
    low = int(rank)
    frac = rank - low
    if low + 1 >= len(sorted_vals):
        return sorted_vals[-1]
    return sorted_vals[low] + frac * (sorted_vals[low + 1] - sorted_vals[low])


def summarize_durations(durations):
    if not durations:
        return {"n": 0, "median_h": None, "p90_h": None}
    vals = sorted(durations)
    return {
        "n": len(vals),
        "median_h": round(statistics.median(vals), 2),
        "p90_h": round(percentile(vals, 90), 2),
    }


class Store:
    """Read-only handle on the AO database (Q1-Q3, Q5-Q6)."""

    def __init__(self, db_path):
        self.db_path = os.path.expanduser(db_path)
        self.con = None
        self.error = None
        if not os.path.exists(self.db_path):
            self.error = "database not found: %s" % self.db_path
            return
        try:
            # Read-only open: the OS/file lock forbids writes even if a
            # later statement tried one (and none do -- see WRITE_KEYWORDS).
            self.con = sqlite3.connect(
                "file:%s?mode=ro" % self.db_path, uri=True
            )
            self.con.execute("PRAGMA query_only = ON")
        except sqlite3.Error as exc:
            self.error = "cannot open read-only: %s" % exc
            self.con = None

    def has_table(self, name):
        if self.con is None:
            return False
        row = self.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        return row is not None

    def query(self, sql, params=()):
        """Run one deterministic SELECT.

        A missing table degrades to [] (graceful per #392); any other
        SQL error propagates so typos fail loudly instead of silently
        zeroing a metric.
        """
        if WRITE_KEYWORDS.search(sql):
            raise ValueError("refusing non-SELECT statement")
        if self.con is None:
            return []
        try:
            return self.con.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            if "no such table" in str(exc):
                return []
            raise

    def close(self):
        if self.con is not None:
            self.con.close()
            self.con = None


def collect_sessions(store, project, since):
    """Q1: sessions per role with lifecycle buckets."""
    rows = store.query(
        "SELECT id, display_name, kind, activity_state, is_terminated,"
        " issue_id, created_at, updated_at FROM sessions"
        " WHERE project_id = ?",
        (project,),
    )
    per_role = {}
    for sid, name, kind, state, terminated, issue_id, created, updated in rows:
        if since and parse_ts(created) and parse_ts(created) < since:
            continue
        role = parse_role(name)
        bucket = per_role.setdefault(
            role,
            {
                "started": 0,
                "completed": 0,
                "active": 0,
                "killed": 0,
                "stalled": 0,
                "issues": set(),
            },
        )
        bucket["started"] += 1
        term = bool(terminated)
        if state == "exited":
            bucket["completed"] += 1
        elif term:
            # Terminated before a clean exit: killed by the operator or
            # the orchestrator (superseded, wedged, or preempted).
            bucket["killed"] += 1
        elif state in ("active", "waiting_input", "blocked"):
            bucket["active"] += 1
        else:
            # Idle but not terminated: no heartbeat and no clean exit.
            bucket["stalled"] += 1
        if issue_id:
            bucket["issues"].add(str(issue_id))
    return per_role, len(rows)


def collect_prs(store, project, since):
    """Q2/Q3: PRs opened per session plus merge timestamps."""
    if not store.has_table("pr"):
        return [], False
    rows = store.query(
        "SELECT session_id, number, is_merged, created_at_provider,"
        " merged_at_provider, url FROM pr"
    )
    linked = [r for r in rows if (r[0] or "").startswith(project + "-")]
    if since:
        def _in_window(r):
            opened = parse_ts(r[3])
            return (opened or datetime.max.replace(tzinfo=timezone.utc)) >= since
        linked = [r for r in linked if _in_window(r)]
    return linked, True


def collect_reviews(store, urls=None):
    """Q2/Q4: review rounds and first-pass rejections per PR.

    `urls` scopes the counts to this project's PRs; None means all PRs
    (used only when the `pr` table itself is missing).
    """
    rounds = {}
    rejected = set()

    def _wanted(pr_url):
        return urls is None or pr_url in urls
    if store.has_table("review_run"):
        for _rid, _rev, _sess, _h, pr_url, _sha, _st, verdict, *_rest in store.query(
            "SELECT id, review_id, session_id, harness, pr_url, target_sha,"
            " status, verdict, body, created_at, github_review_id,"
            " delivered_at, batch_id, auto_inject_review, trigger_source"
            " FROM review_run"
        ):
            if not pr_url or not _wanted(pr_url):
                continue
            rounds[pr_url] = rounds.get(pr_url, 0) + 1
            if (verdict or "").lower() in ("changes_requested", "rejected"):
                rejected.add(pr_url)
    if store.has_table("pr_reviews"):
        for pr_url, _rid, _au, state, *_rest in store.query(
            "SELECT pr_url, review_id, author, state, url, is_bot,"
            " submitted_at, body, auto_inject_review, target_sha"
            " FROM pr_reviews"
        ):
            if not pr_url or not _wanted(pr_url):
                continue
            rounds[pr_url] = rounds.get(pr_url, 0) + 1
            if (state or "").upper() in ("CHANGES_REQUESTED",):
                rejected.add(pr_url)
    return rounds, rejected


def collect_checks(store, urls=None):
    """Q3/Q5: CI cycles per PR and fail-then-pass retries per workflow.

    `urls` scopes the counts to this project's PRs; None means all PRs.
    """
    cycles = {}
    retries = {}
    flaky_jobs = 0
    if not store.has_table("pr_checks"):
        return cycles, retries, flaky_jobs, False
    seen = {}
    for pr_url, name, _sha, status, _url, _tail, _at, conclusion, _det in store.query(
        "SELECT pr_url, name, commit_hash, status, url, log_tail,"
        " created_at, conclusion, details FROM pr_checks"
    ):
        if not pr_url:
            continue
        if urls is not None and pr_url not in urls:
            continue
        cycles[pr_url] = cycles.get(pr_url, 0) + 1
        key = (pr_url, name or "unknown")
        outcome = (conclusion or status or "").lower()
        prior = seen.get(key)
        if prior is None:
            seen[key] = outcome
            continue
        failed_before = prior in ("failure", "failed", "timed_out", "cancelled")
        passed_now = outcome in ("success", "passed")
        if failed_before and passed_now:
            retries[key] = retries.get(key, 0) + 1
            flaky_jobs += 1
        if outcome:
            seen[key] = outcome
    per_workflow = {}
    for (_url, name), count in retries.items():
        per_workflow[name] = per_workflow.get(name, 0) + count
    return cycles, per_workflow, flaky_jobs, True


def collect_reports(store, project):
    """Q2: verification/post counts per session (reports table)."""
    counts = {}
    if not store.has_table("reports"):
        return counts, False
    for (sid,) in store.query(
        "SELECT session_id FROM reports WHERE project_id = ?",
        (project,),
    ):
        if sid:
            counts[sid] = counts.get(sid, 0) + 1
    return counts, True


def collect_usage(store, project):
    """Q6: token totals per role via usage bindings (may be empty)."""
    if not store.has_table("model_usage_events"):
        return {}, False, "table model_usage_events missing"
    if not (store.has_table("usage_sources") and store.has_table("usage_bindings")):
        # No binding path: report unattributed totals only.
        rows = store.query(
            "SELECT provider_id, model_id, input_tokens,"
            " cached_input_tokens, output_tokens, estimated_cost_nanos"
            " FROM model_usage_events"
        )
        if not rows:
            return {}, True, "no usage events recorded yet"
        return {"_unattributed": rows}, True, None
    rows = store.query(
        "SELECT e.provider_id, e.model_id, e.input_tokens,"
        " e.cached_input_tokens, e.output_tokens, e.estimated_cost_nanos,"
        " b.session_id FROM model_usage_events e"
        " LEFT JOIN usage_sources s ON s.id = e.usage_source_id"
        " LEFT JOIN usage_bindings b ON b.id = s.binding_id"
    )
    if not rows:
        return {}, True, "no usage events recorded yet"
    return {"_rows": rows}, True, None


def load_pricing(pricing_dir):
    """Load {(provider, model): {input, cache_read, output}} USD/token."""
    table = {}
    base = Path(os.path.expanduser(pricing_dir))
    if not base.is_dir():
        return table
    for path in base.rglob("*.json"):
        if path.name == "manifest.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        provider = payload.get("providerId", "")
        for model in payload.get("models", []):
            rates = model.get("rates", {})
            try:
                table[(provider, model.get("modelId", ""))] = {
                    "input": float(rates.get("uncachedInputUsdPerToken", 0) or 0),
                    "cache_read": float(
                        rates.get("cacheReadUsdPerToken", 0)
                        or rates.get("uncachedInputUsdPerToken", 0)
                        or 0
                    ),
                    "output": float(rates.get("outputUsdPerToken", 0) or 0),
                }
            except (TypeError, ValueError):
                continue
    return table


def git_reverts(repo_root, since_days):
    """Q4: revert commits in the window (local git, no network)."""
    try:
        proc = subprocess.run(
            ["git", "log", "--oneline", "-i", "--grep=revert",
             "--since=%d days ago" % since_days],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return lines


def fmt_money(value):
    if value is None:
        return "Unavailable"
    return "$%.2f" % value


def build_report(args):
    since = None
    if args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)

    store = Store(args.db)
    db_note = None if store.con is not None else store.error

    per_role, session_total = collect_sessions(store, args.project, since)
    prs, prs_ok = collect_prs(store, args.project, since)
    project_urls = {r[5] for r in prs if r[5]} or None
    rounds, rejected = collect_reviews(store, project_urls)
    cycles, retries, flaky_jobs, checks_ok = collect_checks(store, project_urls)
    verifs, reports_ok = collect_reports(store, args.project)
    usage, usage_ok, usage_note = collect_usage(store, args.project)
    pricing = load_pricing(args.pricing_dir)

    # --- per-role task roll-up (Q2) ---
    prs_by_session = {}
    merged_prs = 0
    spawn_to_open = []
    open_to_merge = []
    session_created = {}
    role_of = {}
    if store.con is not None and store.has_table("sessions"):
        for sid, name, _k, _s, _t, _i, created, _u in store.query(
            "SELECT id, display_name, kind, activity_state, is_terminated,"
            " issue_id, created_at, updated_at FROM sessions WHERE project_id = ?",
            (args.project,),
        ):
            role_of[sid] = parse_role(name)
            ts = parse_ts(created)
            if ts:
                session_created[sid] = ts
    for sess_id, _num, is_merged, opened, merged, _url in prs:
        prs_by_session[sess_id] = prs_by_session.get(sess_id, 0) + 1
        if is_merged:
            merged_prs += 1
        opened_ts = parse_ts(opened)
        if sess_id in session_created and opened_ts:
            delta = (opened_ts - session_created[sess_id]).total_seconds() / 3600.0
            if 0 <= delta < 24 * 30:
                spawn_to_open.append(delta)
        merged_ts = parse_ts(merged)
        if opened_ts and merged_ts:
            delta = (merged_ts - opened_ts).total_seconds() / 3600.0
            if 0 <= delta < 24 * 30:
                open_to_merge.append(delta)

    review_counts = sorted(rounds.values())
    ci_counts = sorted(cycles.values())

    takeover_sessions = sum(
        b["started"] for role, b in per_role.items() if role == "dev-takeover"
    )
    takeover_rate = (
        round(100.0 * takeover_sessions / session_total, 1)
        if session_total
        else None
    )

    # --- cost model (Q6) ---
    agent_usd = 0.0
    cost_by_role = {}
    cost_ok = usage_ok and bool(pricing) and "_rows" in usage
    if cost_ok:
        for provider, model, inp, cached, outp, _est, sess_id in usage["_rows"]:
            rates = pricing.get((provider, model)) or pricing.get(("", model))
            if not rates:
                continue
            inp = inp or 0
            cached = cached or 0
            outp = outp or 0
            cost = (
                max(inp - cached, 0) * rates["input"]
                + cached * rates["cache_read"]
                + outp * rates["output"]
            )
            agent_usd += cost
            role = role_of.get(sess_id, "unattributed")
            cost_by_role[role] = cost_by_role.get(role, 0.0) + cost
    elif usage_ok and "_unattributed" in usage:
        for provider, model, inp, cached, outp, est in usage["_unattributed"]:
            rates = pricing.get((provider, model)) or pricing.get(("", model))
            if rates:
                inp, cached, outp = inp or 0, cached or 0, outp or 0
                agent_usd += (
                    max(inp - cached, 0) * rates["input"]
                    + cached * rates["cache_read"]
                    + outp * rates["output"]
                )
            elif est:
                agent_usd += est / 1e9

    review_rounds_n = len(prs)
    issues_touched = sum(len(b["issues"]) for b in per_role.values())
    human_usd = None
    human_note = None
    if args.hourly_rate is not None:
        human_usd = (
            (review_rounds_n * args.review_minutes + issues_touched
             * args.decision_minutes) / 60.0 * args.hourly_rate
        )
    else:
        human_note = (
            "OWNER INPUT NEEDED: hourly rate -- human cost = "
            "(PRs x %.0f min review + issues x %.0f min decision) / 60 x "
            "hourly_rate; rerun with --hourly-rate USD/hour"
            % (args.review_minutes, args.decision_minutes)
        )

    cost_per_merge = (
        round(agent_usd / merged_prs, 2) if merged_prs and agent_usd else None
    )

    reverts = git_reverts(args.repo, args.days or 30)

    report = {
        "project": args.project,
        "window_days": args.days,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db": {"path": store.db_path, "error": db_note},
        "roles": {
            role: {
                "started": b["started"],
                "completed": b["completed"],
                "active": b["active"],
                "killed": b["killed"],
                "stalled": b["stalled"],
                "issues_touched": len(b["issues"]),
                "prs_opened": sum(
                    n for sid, n in prs_by_session.items()
                    if role_of.get(sid) == role
                ),
                "verifications": sum(
                    n for sid, n in verifs.items()
                    if role_of.get(sid) == role
                ),
            }
            for role, b in sorted(per_role.items())
        },
        "sessions_total": session_total,
        "prs_total": len(prs) if prs_ok else None,
        "prs_merged": merged_prs if prs_ok else None,
        "spawn_to_open_h": summarize_durations(spawn_to_open),
        "open_to_merge_h": summarize_durations(open_to_merge),
        "review_rounds_per_pr": summarize_durations(
            [float(v) for v in review_counts]
        ),
        "ci_cycles_per_pr": summarize_durations([float(v) for v in ci_counts]),
        "takeover_rate_pct": takeover_rate,
        "first_pass_rejections": len(rejected) if (rounds or prs_ok) else None,
        "issues_reopened": None,  # needs GitHub API; see dora-metrics.py
        "reverts": None if reverts is None else len(reverts),
        "revert_list": reverts,
        "post_merge_ci_failures": None,  # needs CI history; dora-metrics.py
        "retries_by_workflow": retries if checks_ok else None,
        "flaky_jobs": flaky_jobs if checks_ok else None,
        "tables": {
            "pr": prs_ok,
            "pr_checks": checks_ok,
            "reports": reports_ok,
            "model_usage_events": usage_ok,
            "usage_note": usage_note,
            "pricing_models": len(pricing),
        },
        "verifications_logged": sum(verifs.values()) if reports_ok else None,
        "agent_cost_usd": round(agent_usd, 2) if (cost_ok or agent_usd) else None,
        "agent_cost_by_role_usd": {k: round(v, 2) for k, v in sorted(
            cost_by_role.items())} if cost_by_role else None,
        "cost_per_merged_pr_usd": cost_per_merge,
        "human_cost_usd": round(human_usd, 2) if human_usd is not None else None,
        "human_cost_note": human_note,
    }
    store.close()
    return report


def render_md(rep):
    """Render the report dict as markdown (no PII: counts only)."""
    L = []
    w = rep["window_days"]
    window = "last %d days" % w if w else "all time"
    L.append("# Agent operations report: %s (%s)" % (rep["project"], window))
    L.append("")
    L.append("_Generated %s (UTC)._" % rep["generated_at"])
    if rep["db"]["error"]:
        L.append("")
        L.append("> DB %s: %s -- all DB sections show Unavailable."
                % (rep["db"]["path"], rep["db"]["error"]))
    L.append("")

    def cell(value):
        return "Unavailable" if value is None else str(value)

    L.append("## Sessions per role")
    L.append("")
    L.append("| Role | Started | Completed | Active | Killed | Stalled |")
    L.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    if rep["roles"]:
        for role, b in rep["roles"].items():
            L.append("| %s | %d | %d | %d | %d | %d |" % (
                role, b["started"], b["completed"], b["active"],
                b["killed"], b["stalled"]))
    else:
        L.append("| Unavailable | Unavailable | Unavailable | Unavailable"
                 " | Unavailable | Unavailable |")
    L.append("")

    L.append("## Tasks per role")
    L.append("")
    L.append("| Role | Issues touched | PRs opened | Verifications logged |")
    L.append("| --- | ---: | ---: | ---: |")
    if rep["roles"]:
        for role, b in rep["roles"].items():
            L.append("| %s | %s | %s | %s |" % (
                role, cell(b["issues_touched"]),
                cell(b.get("prs_opened")), cell(b.get("verifications"))))
    else:
        L.append("| Unavailable | Unavailable | Unavailable | Unavailable |")
    L.append("")

    L.append("## Throughput")
    L.append("")
    L.append("| Metric | n | Median | p90 |")
    L.append("| --- | ---: | ---: | ---: |")
    for label, key in (
        ("Spawn -> PR open (h)", "spawn_to_open_h"),
        ("PR open -> merge (h)", "open_to_merge_h"),
        ("Review rounds per PR", "review_rounds_per_pr"),
        ("CI cycles per PR", "ci_cycles_per_pr"),
    ):
        s = rep[key]
        L.append("| %s | %s | %s | %s |" % (
            label, cell(s["n"]),
            cell(s["median_h"]), cell(s["p90_h"])))
    L.append("")
    L.append("- Takeover rate: %s." % (
        ("%.1f%% of sessions were dev-takeover"
         % rep["takeover_rate_pct"])
        if rep["takeover_rate_pct"] is not None else "Unavailable"))
    L.append("")

    L.append("## Quality signals")
    L.append("")
    L.append("| Signal | Value |")
    L.append("| --- | ---: |")
    L.append("| PRs rejected on first pass | %s |"
              % cell(rep["first_pass_rejections"]))
    L.append("| Issues reopened | %s (needs GitHub API; see dora-metrics) |"
              % cell(rep["issues_reopened"]))
    L.append("| Reverts in window | %s |" % cell(rep["reverts"]))
    L.append("| Post-merge CI failures | %s (see dora-metrics) |"
              % cell(rep["post_merge_ci_failures"]))
    L.append("")

    L.append("## Retries / flakiness")
    L.append("")
    if rep["retries_by_workflow"] is None:
        L.append("Unavailable (pr_checks table missing).")
    elif not rep["retries_by_workflow"]:
        L.append("No fail-then-pass job retries recorded"
                 " (%s flaky jobs)." % cell(rep["flaky_jobs"]))
    else:
        L.append("| Check/workflow | Fail-then-pass retries |")
        L.append("| --- | ---: |")
        for name, count in sorted(rep["retries_by_workflow"].items()):
            L.append("| %s | %d |" % (name, count))
    L.append("")

    L.append("## Cost model")
    L.append("")
    L.append("| Component | Value |")
    L.append("| --- | ---: |")
    L.append("| Agent cost (tokens x pricing catalog) | %s |"
              % (fmt_money(rep["agent_cost_usd"])
                 if rep["agent_cost_usd"] is not None else "Unavailable"))
    L.append("| Cost per merged PR (agent) | %s |"
              % (fmt_money(rep["cost_per_merged_pr_usd"])
                 if rep["cost_per_merged_pr_usd"] is not None
                 else "Unavailable"))
    L.append("| Human cost (reviews + decisions) | %s |"
              % (fmt_money(rep["human_cost_usd"])
                 if rep["human_cost_usd"] is not None
                 else "Unavailable"))
    if rep["agent_cost_by_role_usd"]:
        L.append("| _of which, by role_ |  |")
        for role, value in rep["agent_cost_by_role_usd"].items():
            L.append("| - %s | %s |" % (role, fmt_money(value)))
    if rep["tables"].get("usage_note"):
        L.append("| Usage data | %s |" % rep["tables"]["usage_note"])
    if rep["human_cost_note"]:
        L.append("")
        L.append("> %s" % rep["human_cost_note"])
    L.append("")
    if rep["agent_cost_usd"]:
        L.append("Cost per merged change: %s agent%s."
                % (fmt_money(rep["cost_per_merged_pr_usd"]),
                   " + %s human" % fmt_money(rep["human_cost_usd"])
                   if rep["human_cost_usd"] else ""))
        drivers = []
        if (rep["takeover_rate_pct"] or 0) > 5:
            drivers.append("takeovers")
        ci = rep["ci_cycles_per_pr"]
        if ci["median_h"] is not None and ci["median_h"] > 3:
            drivers.append("CI cycles")
        rr = rep["review_rounds_per_pr"]
        if rr["median_h"] is not None and rr["median_h"] > 2:
            drivers.append("review rounds")
        if drivers:
            L.append("What dominates: %s." % ", ".join(drivers))
        else:
            L.append("What dominates: reviews (each merged PR carries at least"
                     " one review round); takeovers and CI cycles are low.")
    L.append("")
    L.append("## Definitions and limitations")
    L.append("")
    L.append("See `docs/project/metrics.md` for the exact definition of every"
             " metric and the known limitations (notably: role comes from the"
             " session display-name prefix; usage tables may be empty so agent"
             " cost shows Unavailable; issues-reopened and post-merge CI"
             " failures need the GitHub API -- run script/dora-metrics.py).")
    L.append("")
    return "\n".join(L)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Agent operations report (read-only AO database)."
    )
    parser.add_argument("--db", default=DEFAULT_DB,
                        help="AO database path (env AO_DB). Opened read-only.")
    parser.add_argument("--project", default="mingchen-site",
                        help="AO project id filter (default: mingchen-site).")
    parser.add_argument("--days", type=int, default=30,
                        help="Window in days; 0 means all time (default: 30).")
    parser.add_argument("--format", choices=("md", "json"), default="md",
                        help="Output format (default: md).")
    parser.add_argument("--pricing-dir", default=DEFAULT_PRICING_DIR,
                        help="Pricing catalog dir (env AO_PRICING_DIR).")
    parser.add_argument("--repo", default=".",
                        help="Git repo for revert scan (default: cwd).")
    parser.add_argument("--hourly-rate", type=float, default=None,
                        help="Owner-supplied human hourly rate in USD.")
    parser.add_argument("--review-minutes", type=float, default=20.0,
                        help="Owner estimate: review minutes per PR.")
    parser.add_argument("--decision-minutes", type=float, default=10.0,
                        help="Owner estimate: decision minutes per issue.")
    args = parser.parse_args(argv)
    if args.days == 0:
        args.days = None

    report = build_report(args)
    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_md(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

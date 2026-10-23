#!/usr/bin/env python3
"""DORA metrics for this project (issue #392, companion to agent-metrics.py).

Computes the four keys from the repo's real signals via the GitHub API
(`gh`, which must already be authenticated -- no token is read from or
written to any file):

- Deployment frequency: successful `pages build and deployment` runs on
  the default branch per week (and total in the window).
- Lead time for changes: merge time -> next successful Pages publish
  (median and p90). For a static site, "deployed" is defined as a
  successful Pages publish, not the merge itself.
- Change failure rate: merged PRs that caused a failing default-branch
  CI/E2E run (or were reverted) before the next green run, over total
  merged PRs in the window.
- Time to restore: from the first failing default-branch run to the next
  green run (median/p90 over all such incidents in the window).

Usage:
    python3 script/dora-metrics.py --help
    python3 script/dora-metrics.py --format md
    python3 script/dora-metrics.py --format md --days 30 --repo .

`--help` works without network. Every data command needs `gh`
authenticated; without it the script exits 2 with a one-line hint.
Definitions used are printed at the end of every markdown report so a
posted report is self-describing.
"""

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone

PAGES_WORKFLOW = "pages build and deployment"


def is_pages_workflow(name):
    """Match the Pages publish workflow by display name or file slug.

    `gh run list --json workflowName` reports the workflow file slug
    (`pages-build-deployment`), while the API/web UI show the display
    name (`pages build and deployment`).
    """
    slug = (name or "").lower().replace("-", " ").replace("_", " ")
    return "pages" in slug and "deploy" in slug


def run_gh(args, timeout=120, cwd=None):
    try:
        proc = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print("error: cannot run `gh`: %s" % exc, file=sys.stderr)
        sys.exit(2)
    if proc.returncode != 0:
        hint = (proc.stderr or proc.stdout or "").strip().splitlines()
        print("error: `gh %s` failed: %s" % (
            " ".join(args), hint[0] if hint else "exit %d" % proc.returncode),
            file=sys.stderr)
        print("hint: run `gh auth status` and authenticate first.",
              file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(proc.stdout or "[]")
    except ValueError:
        print("error: unexpected non-JSON output from `gh`.", file=sys.stderr)
        sys.exit(2)


def parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


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


def summarize(values):
    if not values:
        return {"n": 0, "median": None, "p90": None}
    vals = sorted(values)
    return {
        "n": len(vals),
        "median": round(statistics.median(vals), 2),
        "p90": round(percentile(vals, 90), 2),
    }


def repo_info(repo_dir):
    """Return (nameWithOwner, defaultBranch) via `gh` in repo_dir."""
    view = run_gh(
        ["repo", "view", "--json", "nameWithOwner,defaultBranchRef"],
        cwd=repo_dir,
    )
    return view["nameWithOwner"], view["defaultBranchRef"]["name"]


def api_pages(nwo, path):
    """GET one API page; returns the decoded JSON object."""
    try:
        proc = subprocess.run(
            ["gh", "api", path],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print("error: cannot run `gh`: %s" % exc, file=sys.stderr)
        sys.exit(2)
    if proc.returncode != 0:
        hint = (proc.stderr or proc.stdout or "").strip().splitlines()
        print("error: `gh api %s` failed: %s" % (
            path, hint[0] if hint else "exit %d" % proc.returncode),
            file=sys.stderr)
        print("hint: run `gh auth status` and authenticate first.",
              file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(proc.stdout or "{}")
    except ValueError:
        print("error: unexpected non-JSON output from `gh api`.",
              file=sys.stderr)
        sys.exit(2)


def fetch_runs(nwo, branch, since, limit):
    """All default-branch workflow runs in the window (paginated)."""
    runs = []
    page = 1
    while len(runs) < limit:
        payload = api_pages(
            nwo,
            "repos/%s/actions/runs?per_page=100&page=%d&branch=%s"
            % (nwo, page, branch),
        )
        batch = payload.get("workflow_runs", [])
        if not batch:
            break
        for item in batch:
            created = parse_ts(item.get("created_at"))
            if created and created < since:
                continue
            runs.append({
                "databaseId": item.get("id"),
                "workflowName": item.get("name"),
                "conclusion": item.get("conclusion"),
                "createdAt": item.get("created_at"),
                "updatedAt": item.get("updated_at"),
                "headSha": item.get("head_sha"),
                "displayTitle": item.get("display_title"),
            })
        oldest = min(
            (parse_ts(i.get("created_at")) for i in batch if parse_ts(i.get("created_at"))),
            default=None,
        )
        if oldest is not None and oldest < since:
            break  # pages are newest-first: nothing older can match
        if len(batch) < 100:
            break
        page += 1
    return runs[:limit]


def fetch_merged_prs(nwo, branch, since, limit):
    """Merged PRs on the default branch updated in the window."""
    prs = []
    page = 1
    while len(prs) < limit:
        payload = api_pages(
            nwo,
            "repos/%s/pulls?state=closed&base=%s&per_page=100&page=%d"
            "&sort=updated&direction=desc" % (nwo, branch, page),
        )
        if not isinstance(payload, list) or not payload:
            break
        for item in payload:
            if not item.get("merged_at"):
                continue
            merged = parse_ts(item.get("merged_at"))
            if merged and merged < since:
                continue
            prs.append({
                "number": item.get("number"),
                "title": item.get("title"),
                "mergedAt": item.get("merged_at"),
                "mergeCommit": (item.get("merge_commit_sha") or ""),
            })
        oldest_update = min(
            (parse_ts(i.get("updated_at")) for i in payload
             if parse_ts(i.get("updated_at"))),
            default=None,
        )
        if oldest_update is not None and oldest_update < since:
            # Merges only get older from here, but a stale PR updated
            # long ago can hide a fresher merge on a later page, so keep
            # going until the page is exhausted by the API.
            pass
        if len(payload) < 100:
            break
        page += 1
    return [p for p in prs
            if (parse_ts(p.get("mergedAt")) or since) >= since][:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="DORA metrics from GitHub Actions + merged PRs."
    )
    parser.add_argument("--days", type=int, default=30,
                        help="Window in days (default: 30).")
    parser.add_argument("--format", choices=("md", "json"), default="md",
                        help="Output format (default: md).")
    parser.add_argument("--repo", default=".",
                        help="Local git repo (used only to confirm `gh`"
                        " context; default: cwd).")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Max runs/PRs to fetch per query (default: 1000).")
    args = parser.parse_args(argv)

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    nwo, branch = repo_info(args.repo)

    runs = fetch_runs(nwo, branch, since, args.limit)
    pages_ok = sorted(
        (r for r in runs
         if is_pages_workflow(r.get("workflowName"))
         and r.get("conclusion") == "success"
         and (parse_ts(r.get("updatedAt")) or since) >= since),
        key=lambda r: r.get("updatedAt") or "",
    )
    branch_runs = sorted(
        (r for r in runs
         if (parse_ts(r.get("createdAt")) or since) >= since),
        key=lambda r: r.get("createdAt") or "",
    )

    prs = fetch_merged_prs(nwo, branch, since, args.limit)
    merged = [p for p in prs
              if (parse_ts(p.get("mergedAt")) or since) >= since]

    # Lead time: merge -> next successful Pages publish after the merge.
    publish_times = [parse_ts(r.get("updatedAt")) for r in pages_ok]
    publish_times = [t for t in publish_times if t]
    lead_hours = []
    for pr in merged:
        merged_at = parse_ts(pr.get("mergedAt"))
        if not merged_at:
            continue
        following = [t for t in publish_times if t >= merged_at]
        if following:
            lead_hours.append(
                (min(following) - merged_at).total_seconds() / 3600.0)

    # Change failure rate: a merge counts as failed when a default-branch
    # run concludes failure/cancelled/timed_out after the merge and before
    # the next success, or the PR title reverts another change.
    bad_runs = [
        (parse_ts(r.get("createdAt")), parse_ts(r.get("updatedAt") or
                                                r.get("createdAt")))
        for r in branch_runs
        if (r.get("conclusion") or "").lower()
        in ("failure", "cancelled", "timed_out")
    ]
    bad_runs = [(a, b) for a, b in bad_runs if a and b]
    green_times = sorted(
        t for t in (
            parse_ts(r.get("updatedAt"))
            for r in branch_runs
            if (r.get("conclusion") or "").lower() == "success"
        ) if t
    )
    failed_merges = 0
    for pr in merged:
        merged_at = parse_ts(pr.get("mergedAt"))
        title = (pr.get("title") or "").lower()
        if title.startswith("revert"):
            failed_merges += 1
            continue
        if not merged_at:
            continue
        next_green = next((t for t in green_times if t >= merged_at), None)
        horizon = next_green or datetime.now(timezone.utc)
        if any(a >= merged_at and a <= horizon for a, _b in bad_runs):
            failed_merges += 1

    # Time to restore: first failing run -> next green run, per incident.
    restore_hours = []
    bad_starts = sorted(a for a, _b in bad_runs)
    for start in bad_starts:
        nxt = next((t for t in green_times if t >= start), None)
        if nxt:
            restore_hours.append((nxt - start).total_seconds() / 3600.0)

    weeks = max(args.days / 7.0, 1.0)
    report = {
        "repo": nwo,
        "branch": branch,
        "window_days": args.days,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "deployment_frequency": {
            "definition": "Successful `%s` runs on `%s` per week;"
            " a deployment is a Pages publish, not a merge."
            % (PAGES_WORKFLOW, branch),
            "successful_deploys": len(pages_ok),
            "per_week": round(len(pages_ok) / weeks, 2),
        },
        "lead_time_hours": dict(
            summarize(lead_hours),
            definition="PR merge (mergedAt) -> next successful Pages"
            " publish (run updatedAt); median and p90 in hours.",
        ),
        "change_failure_rate": {
            "definition": "Merged PRs followed by a failing default-branch"
            " run (or a revert) before the next green run, over total"
            " merged PRs in the window.",
            "failed": failed_merges,
            "total": len(merged),
            "rate": round(failed_merges / len(merged), 3)
            if merged else None,
        },
        "time_to_restore_hours": dict(
            summarize(restore_hours),
            definition="First failing default-branch run -> next green run"
            " (same branch); median and p90 in hours.",
        ),
    }

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return 0
    print(render_md(report))
    return 0


def render_md(rep):
    L = []
    L.append("# DORA metrics: %s (`%s`, last %d days)"
             % (rep["repo"], rep["branch"], rep["window_days"]))
    L.append("")
    L.append("_Generated %s (UTC) via `gh`._" % rep["generated_at"])
    L.append("")

    def cell(value, suffix=""):
        return "Unavailable" if value is None else "%s%s" % (value, suffix)

    dep = rep["deployment_frequency"]
    lead = rep["lead_time_hours"]
    cfr = rep["change_failure_rate"]
    ttr = rep["time_to_restore_hours"]
    L.append("| Metric | Value |")
    L.append("| --- | ---: |")
    L.append("| Deployment frequency | %s/week (%d in window) |"
              % (cell(dep["per_week"]), dep["successful_deploys"]))
    L.append("| Lead time for changes | median %s, p90 %s (n=%d) |"
              % (cell(lead["median"], " h"), cell(lead["p90"], " h"),
                 lead["n"]))
    L.append("| Change failure rate | %s (%d/%d) |"
              % (cell(cfr["rate"]), cfr["failed"], cfr["total"]))
    L.append("| Time to restore | median %s, p90 %s (n=%d) |"
              % (cell(ttr["median"], " h"), cell(ttr["p90"], " h"),
                 ttr["n"]))
    L.append("")
    L.append("## Definitions")
    L.append("")
    for entry in (dep, lead, cfr, ttr):
        L.append("- %s" % entry["definition"])
    L.append("")
    L.append("Known limitations: the window caps at `--limit` runs/PRs; lead"
             " time needs a Pages publish after each merge (a quiet window"
             " understates it); failures on non-default branches never count.")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())

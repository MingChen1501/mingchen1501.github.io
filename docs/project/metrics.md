# Agent-ops metrics (roles, DORA, cost)

Status: active. Repeatable measurement for issue #392: how much work each
agent-team role does, how reliable delivery is (DORA), and what it costs in
agent and human terms. Measure once per milestone with the two scripts;
post the rendered markdown as a comment on the tracking issue.

## How to run

```sh
python3 script/agent-metrics.py --help
python3 script/agent-metrics.py --format md --project mingchen-site --days 30
python3 script/agent-metrics.py --format md --days 0        # all time
python3 script/agent-metrics.py --format json --hourly-rate 50 > /tmp/agent.json
python3 script/dora-metrics.py --help
python3 script/dora-metrics.py --format md --days 30
```

`agent-metrics.py --help` and `--format md` run without network (local AO
database plus local git only). `dora-metrics.py` needs `gh` authenticated
(`gh auth status`); without it the script exits 2 with a one-line hint.
Neither script writes to `~/.ao/data` or mutates session state.

Flags and environment:

| Flag / env | Default | Meaning |
|---|---|---|
| `--db` / `AO_DB` | `~/.ao/data/ao.db` | AO database path (always opened `mode=ro`) |
| `--project` | `mingchen-site` | AO project id filter |
| `--days` (`0` = all time) | `30` / `30` | window for both scripts |
| `--format` | `md` | `md` for issue comments, `json` for tooling |
| `--pricing-dir` / `AO_PRICING_DIR` | `~/.ao/data/pricing/catalog/v1` | unit-price catalog |
| `--hourly-rate` | unset | owner-supplied human rate (USD/h); without it human cost prints `OWNER INPUT NEEDED` and the formula |
| `--review-minutes` / `--decision-minutes` | `20` / `10` | owner estimates feeding the human-cost formula |
| `--repo` | `.` | git repo for the revert scan (`agent-metrics.py`) and `gh` context (`dora-metrics.py`) |
| `--limit` | `1000` | max runs/PRs fetched per DORA query |

## How to read the agent report

- Sessions per role: one row per role parsed from the session display-name
  prefix (`dev #…`, `content-review #…`, …); lifecycle buckets are
  completed (`activity_state = exited`), active (not terminated, working
  state), killed (terminated before a clean exit), stalled (idle, not
  terminated). Anything outside the canonical role list lands in `other`
  (pre-convention sessions), empty names in `unlabeled`, `buffer …` in
  `buffer`.
- Tasks per role: distinct `issue_id` values touched, PRs opened (linked
  `session_id`), verifications logged (`reports` rows: posts the session
  wrote, including verification and handoff notes).
- Throughput: spawn -> PR open and PR open -> merge in hours (median/p90);
  review rounds per PR (`pr_reviews` + `review_run` rows per `pr_url`); CI
  cycles per PR (`pr_checks` rows per `pr_url`); takeover rate
  (`dev-takeover` sessions over all sessions).
- Quality: first-pass rejections (`CHANGES_REQUESTED` / `changes_requested`
  verdicts), reverts (`git log --grep=revert -i` in the window);
  issues-reopened and post-merge CI failures need the GitHub API and are
  covered by `dora-metrics.py`.
- Retries: `pr_checks` rows sharing `(pr_url, check name)` with a failure
  conclusion followed by a success, grouped per check/workflow name.

## DORA definitions (static site)

"Deployed" means a successful `pages build and deployment` run on the
default branch (a Pages publish), not the merge itself.

- Deployment frequency: successful Pages runs per week in the window.
- Lead time for changes: PR `mergedAt` -> next successful Pages publish
  (`updatedAt`), median and p90 in hours.
- Change failure rate: merged PRs followed by a failing default-branch run
  (or titled `revert…`) before the next green run, over merged PRs.
- Time to restore: first failing default-branch run -> next green run on
  the same branch, median and p90 in hours.

## Cost model

- Agent cost: `model_usage_events` token totals x the unit-price catalog
  (`uncachedInput`/`cacheRead`/`output` USD per token), aggregated per
  role through `usage_sources`/`usage_bindings`. Also reported per merged
  PR. When the usage tables are empty the report prints `Unavailable`
  with the reason instead of inventing a number.
- Human cost: `(PRs x review_minutes + issues x decision_minutes) / 60 x
  hourly_rate`. Until the owner supplies `--hourly-rate` the report shows
  `OWNER INPUT NEEDED` with this formula, so the number is one substitution
  away. What dominates (reviews, takeovers, CI cycles) is derived from the
  throughput section thresholds in the script.

## Known limitations

- Role comes from the display-name prefix; sessions created before the
  naming convention (or renamed) aggregate under `other`/`unlabeled`.
- `sessions.created_at` is the row creation time, so spawn -> PR open is a
  proxy for wall-clock task time, not instrumented hands-on time.
- Lead time needs a Pages publish after each merge; a quiet window (no
  deploys) understates it. The run/PR fetch caps at `--limit` items.
- Concurrent default-branch runs can make time-to-restore look instant (a
  failure at T "restored" by a parallel success at T+seconds); read it
  together with the change failure rate.
- The report contains only aggregate counts, durations, and USD amounts:
  no prompts, notes, bodies, or author names (no PII by construction).
- Numbers are reproducible: identical queries over an unchanged database
  produce identical output; reruns only differ in `generated_at`.

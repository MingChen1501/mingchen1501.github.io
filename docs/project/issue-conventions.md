# Issue conventions

Status: active. Structural title+label convention for issues and PRs (#353):
every new issue and PR carries one type token and the matching labels, so the
backlog stays scannable without periodic retitling drives.

## Title

`[type] Imperative summary` — a lowercase type token in square brackets,
then one sentence-case sentence with no trailing period.

- Imperative mood: start with a verb (`Add`, `Fix`, `Remove`, `Lift`).
  `article` issues are the exception: their title is the working article
  title (`[article] Switching from Windows 11 to Fedora`).
- One line, no period, no extra prefixes (`docs:` / `Perf:` / `CI:` are
  legacy forms — use `[docs]` / `[perf]` / `[ci]` instead).

## Type to label table

Each type maps 1:1 to a label of the same name. Every issue and PR carries
exactly one type label and exactly one `risk-*` label (`risk-low` /
`risk-medium` / `risk-high` / `risk-very-high`). `enhancement` is optional
legacy: keep it where it exists, never add it on new issues.

| Type | Label | Use for |
|---|---|---|
| `feat` | `feat` | new behaviour or capability |
| `fix` | `fix` | bug fix |
| `docs` | `docs` | documentation only |
| `test` | `test` | tests without behaviour change |
| `ci` | `ci` | CI, workflows, automation |
| `perf` | `perf` | performance |
| `a11y` | `a11y` | accessibility |
| `i18n` | `i18n` | internationalisation / bilingual handling |
| `chore` | `chore` | maintenance with no reader-visible change |
| `content` | `content` | site content that is not an article post |
| `security` | `security` | security fix or hardening |
| `article` | `article` | article workflow (filed via `article.yml`, picked up by intake) |

## Body

Non-article issues use `.github/ISSUE_TEMPLATE/task.yml` (blank issues are
disabled via `config.yml`, so the form is the only path). Required sections:
Context (with evidence/links), Scope (in/out), Acceptance criteria (checkbox
list, testable), Risk and rollback. `article.yml` is untouched and stays the
only path for article requests.

GitHub issue forms cannot apply a label from a dropdown choice, so after
filing add exactly one type label matching the Type field plus exactly one
`risk-*` label by hand. Every artefact ends with the AO role footer lines
from #350 (appended via `script/ao-role-footer.sh`, never hand-written).

PRs use `.github/PULL_REQUEST_TEMPLATE.md`: Summary, linked issue
(`Closes #`), Type, Risk label, Test evidence (which suites/CI checks),
Screenshots/baselines note, and the role footer.

## Examples of good titles

- `[chore] Add issue and PR templates with a title and label convention`
- `[fix] Lift tag index summaries to 15px on phones`
- `[feat] Curate pillar tag list with cap and data-driven tag indexes`
- `[docs] House every SWE document type in-tree with index table`
- `[article] Switching from Windows 11 to Fedora`

## Retitle rule for old issues

Do not bulk-retitle the backlog. Normalise an old issue's title and labels
when touching it (commenting, implementing, or closing): apply the
`[type] Imperative summary` title, exactly one type label, and exactly one
`risk-*` label, and note the retitle in passing.

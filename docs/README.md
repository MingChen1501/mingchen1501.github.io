# Software-engineering documents

Status: active (index). Single entry point for every SWE document type on
this project: each row points at its real path with status `active`,
`stub (not needed yet)`, or `n/a (technical)`. Every path in the tables
exists; every file under `docs/` is in one of the tables — no orphans, no
dead links. All content is English. `docs/` is excluded from the built
site (`_config.yml` `exclude:`), so nothing here ships to readers.

Real docs either own content or explicitly defer with a link — no
duplicated source of truth. Stubs say why they are not needed and when to
revisit.

## Business

| Type | Path | Status | Purpose |
|---|---|---|---|
| BRD | `business/brd.md` | stub (not needed yet) | contractual requirements — none on a personal blog |
| Business case | `business/business-case.md` | stub (not needed yet) | investment justification — no revenue target |
| Market research | `business/market-research.md` | stub (not needed yet) | audience analysis — owner writes for themselves |
| KPI | `business/kpi.md` | stub (not needed yet) | tracked targets — health signals live in CI |

## Product

| Type | Path | Status | Purpose |
|---|---|---|---|
| PRD | `product/prd.md` | stub (not needed yet) | product contract — issues carry intent |
| Roadmap | `product/roadmap.md` | stub (not needed yet) | dated milestones — issue queue is the sequence |
| Personas | `product/personas.md` | stub (not needed yet) | reader profiles — one-person site |
| User stories | `product/user-stories.md` | stub (not needed yet) | story-sized work — issues suffice |
| Acceptance criteria | `product/acceptance-criteria.md` | active | what "done" means (CI gates, review flow) |
| Scope | `product/scope.md` | active | in/out of scope of the blog |

## Requirements

| Type | Path | Status | Purpose |
|---|---|---|---|
| FR | `requirements/fr.md` | active | functional list, each item with its guard test |
| NFR | `requirements/nfr.md` | active | budgets and quality bars, each with its guard |
| SRD | `requirements/srd.md` | stub (not needed yet) | stakeholder system requirements — no stakeholder |
| SRS | `requirements/srs.md` | stub (not needed yet) | formal spec — behaviour pinned by tests |
| Business rules | `requirements/business-rules.md` | stub (not needed yet) | domain policy — no rule-driven behaviour |
| Use case | `requirements/use-case.md` | stub (not needed yet) | multi-actor flows — none |
| Data dictionary | `requirements/data-dictionary.md` | active | front-matter field reference |

## Architecture

| Type | Path | Status | Purpose |
|---|---|---|---|
| HLD | `architecture/hld.md` | active | system-context diagram |
| LLD | `architecture/lld.md` | active | component-to-owner map |
| System architecture | `architecture/system-architecture.md` | active | request path Cloudflare → Pages → Giscus |
| ERD | `architecture/erd.md` | stub (not needed yet) | data relations — no database |
| Sequence | `architecture/sequence.md` | active | build-pipeline stage diagram |
| State machine | `architecture/state-machine.md` | stub (not needed yet) | stateful workflow — none |
| Decision records | `architecture/decisions/` | n/a (technical) | directory of ADRs, logged in `project/decision-log.md` |

## Technical

| Type | Path | Status | Purpose |
|---|---|---|---|
| API spec | `technical/api-spec.md` | stub (not needed yet) | API contract — no API |
| Schema spec | `technical/schema-spec.md` | active | `_data/*.yml` shapes |
| Integration spec | `technical/integration-spec.md` | active | Giscus/Cloudflare/Pages trust and failure contract |
| Error handling | `technical/error-handling.md` | active | how failures surface to readers and CI |
| Security threat model | `technical/security-threat-model.md` | active | threat list on top of `privacy-csp.md` |

## Development

| Type | Path | Status | Purpose |
|---|---|---|---|
| Readme | `development/readme.md` | active | development entry pointer |
| Setup | `development/setup.md` | active | setup command list |
| Coding standards | `development/coding-standards.md` | active | conventions in force |
| Implementation plan | `development/implementation-plan.md` | stub (not needed yet) | programme plan — issues are the plan |
| Task breakdown | `development/task-breakdown.md` | stub (not needed yet) | work breakdown — issue bodies suffice |
| Contributing | `development/contributing.md` | active | contribution pointers |

## Testing

| Type | Path | Status | Purpose |
|---|---|---|---|
| Test strategy | `testing/test-strategy.md` | active | two-layer guard strategy |
| Test plan | `testing/test-plan.md` | active | per-change test selection |
| Test cases | `testing/test-cases.md` | active | pointer to guards and ownership |
| Test data | `testing/test-data.md` | active | fixtures and baselines inventory |
| Traceability | `testing/traceability.md` | active | FR/NFR id to guard-file map |
| Test report | `testing/test-report.md` | stub (not needed yet) | point-in-time report — CI runs are the report |

## DevOps

| Type | Path | Status | Purpose |
|---|---|---|---|
| CI/CD | `devops/ci-cd.md` | active | workflow inventory |
| Deployment | `devops/deployment.md` | active | Pages deploy path |
| Environment | `devops/environment.md` | active | config/env matrix |

## Operations

| Type | Path | Status | Purpose |
|---|---|---|---|
| Runbook | `operations/runbook.md` | active | when-it-breaks playbook |
| Monitoring | `operations/monitoring.md` | active | where the signals live |
| Backup/DR | `operations/backup-dr.md` | stub (not needed yet) | restore plan — no data store |
| Incident response | `operations/incident-response.md` | stub (not needed yet) | on-call process — no service commitment |

## Project

| Type | Path | Status | Purpose |
|---|---|---|---|
| Plan | `project/plan.md` | stub (not needed yet) | milestones — issue queue only |
| Risk register | `project/risk-register.md` | active | live risk list |
| Decision log | `project/decision-log.md` | active | decision list pointing at ADRs |

## Release

| Type | Path | Status | Purpose |
|---|---|---|---|
| Release notes | `release/release-notes.md` | active | PR-driven changelog |
| Rollback | `release/rollback.md` | active | revert procedure |

## Support

| Type | Path | Status | Purpose |
|---|---|---|---|
| User guide | `support/user-guide.md` | stub (not needed yet) | reader instructions — none needed |
| FAQ | `support/faq.md` | stub (not needed yet) | curated answers — no support load |
| SLA | `support/sla.md` | stub (not needed yet) | service commitment — none offered |

## Other existing docs (outside this classification)

| Path | Purpose |
|---|---|
| `architecture/overview.md` | architecture area map |
| `architecture/content-pipeline.md` | layouts/includes/collections detail |
| `architecture/data-model.md` | `_data/` file roles and chains |
| `architecture/javascript.md` | JS module inventory and loading contract |
| `architecture/privacy-csp.md` | privacy inventory and no-CSP decision |
| `architecture/styling.md` | SCSS layers and cascade order |
| `architecture/testing.md` | guard layers, overlap map, findings |
| `architecture/decisions/adr-001-spec-set.md` | ADR: spec set choice |
| `architecture/decisions/adr-002-external-images.md` | ADR: allowlisted attachment images |
| `architecture/decisions/adr-003-bilingual-no-plugins.md` | ADR: Liquid-only i18n |
| `architecture/decisions/adr-template.md` | ADR template |
| `architecture/decisions/README.md` | ADR index and conventions |
| `ao-rules.md` | normative AO role rules |
| `chat-draft-192.md` | article chat-draft working note |
| `conventions-173.md` | image/README conventions record |
| `jekyll-plugin-audit-90.md` | plugin audit record |
| `upstream-baseline-184.md` | pinned upstream minima baseline |

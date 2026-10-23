# Risk register

Status: active. Small live register; newest concern last.

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Silent highlight-slug fallback hides typos | medium / low | `test_sidebar_layout.py` is the only tripwire; warning-level lint proposed (`data-model.md`) |
| Tag descriptions drift (page bodies vs `tag_labels.yml`) | medium / low | `test_tag_index_descriptions.py`; single-source fix proposed |
| E2E suite (~19.5K LOC) outgrows the site it guards | medium / medium | overlap map #297, ownership #302 |
| Actions supply-chain drift | low / high | version pins; review workflow diffs as code (`technical/security-threat-model.md`) |
| Unreachable solarized skins ship dead CSS weight | low / low | removal issue #296 |

Resolved: unbudgeted published weight (#294, ~3.7MB freed); stale
`demo_site.yml` removed (#418).

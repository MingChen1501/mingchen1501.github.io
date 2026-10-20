# ADR-003: Bilingual pipeline with lang/ref and no custom plugins

- Status: accepted
- Date: 2026-10-20 (pipeline built across #93/#104/#129/#170; recorded
  here by the #290 audit)
- Context: GitHub Pages builds with `--safe`, so custom plugins are
  unavailable; the site still needs EN/VI twins, alternates, sitemap
  entries, and a language switcher.
- Decision: `site.posts` + `site.vi_posts` collections with per-post
  `lang` + shared `ref`; `_includes/ref-urls.html` as the sole resolver
  (plain `for` loops — nil-safe when the collection is undefined);
  taxonomy labels/slugs centralized in `_data/tag_labels.yml`.
- Consequences: no plugin maintenance, but scattered inline
  `{% if lang == 'vi' %}` switches and repeated `vi_posts` nil-guards
  (see `content-pipeline.md` findings); first-match-wins `ref` resolution
  must survive any pagination change (#104 rule).

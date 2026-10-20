# Styling

Purpose: where styles live, in what cascade order, and what each layer may
touch.

## Current structure

`_sass/` holds 27 files (~3,200 LOC). Entry points in `assets/css/`:

- `style.scss` imports the skin (`minima/skins/{{ site.minima.skin }}`,
  pinned to `auto` in `_config.yml:21`) then `minima/initialize.scss`
  (variables, base, layout, custom-styles hook).
- `syntax.scss` (#275) imports only `minima/syntax-highlight.scss` plus
  the dark/highlight mixins — the ~12.4KB Rouge token layer, linked from
  `head.html:99` only on pages whose content contains Rouge output.

Layers, in cascade order:

1. Upstream minima: `_base.scss` (306 lines), `_layout.scss` (458 lines),
   `initialize.scss` (50 lines) — forked, rarely touched.
2. Skins (`skins/`, 3 files): `auto.scss` (active) builds on `classic` +
   `dark`; `classic.scss` / `dark.scss` re-export `auto`.
3. Site partials (`custom/`, 17 files + `_variables.scss`): one scope per
   file, imported in fixed order by `custom-styles.scss` (last import
   wins; `print.scss` at 298 lines is deliberately last). Shared
   dimensions live in `custom/_variables.scss` (16 lines, #174).
4. `custom-variables.scss` (1 line, placeholder hook) and
   `custom-styles.scss` (40 lines, index only).

Largest partials: `_print.scss` (298), `_theme-toggle.scss` (228),
`_lightbox.scss` (182), `_sidebar.scss` (163). Smallest real partials
(`_utilities.scss` 58, `_legibility.scss` 45, `_post.scss` 43) are
single-concern and healthy.

## Boundaries

- One scope per `custom/` partial; cross-scope literals stay duplicated
  rather than sharing a misleading variable name (`_variables.scss`
  header documents this for micro-spacing).
- `print.scss` stays the last import with the single `@media print`
  block (guarded by `test_print_styles.py`).
- Rouge token rules belong in `syntax.css`, structural highlight rules
  (`div.highlight`, `code.highlighter-rouge`) stay in `style.css` — no
  selector may cross the split (#275).
- `_site/` outputs are generated; never hand-edit. `sitemap.xml` and
  `llms.txt` are Liquid sources edited like other pages.

## Coupling notes

- Every fixed-URL asset link carries `?v={{ asset_version }}`, assigned
  once in `_includes/asset-version.html` and shared by `head.html`
  (stylesheets, favicon at `head.html:83,99,101`).
- The `#220` theme toggle couples four places: `head.html` inline
  bootstrap (~L82), `theme-toggle.js`, `_theme-toggle.scss`, and the
  `minima.skin` setting. Guarded by `test_theme_toggle.py` (536 lines)
  plus the dark-blockquote pin in `test_axe_a11y.py`.
- `_list-thumbs.scss` + `_includes/post-thumbnail.html` + `script/generate-thumbnails`
  form the fixed 120x90 list-thumbnail contract (#226).

## Known findings

- #295 — implemented: the `asset_version` assignment lives once in
  `_includes/asset-version.html`, included by `head.html`,
  `sub-footer.html`, and `search.html`.
- #296 — implemented: `skins/solarized.scss`, `solarized-light.scss`,
  `solarized-dark.scss` had no importer while the skin is `auto`
  (grep over `.scss`/`.yml`/`.html` found only self-references), so they
  were deleted; `test_skin_reachability.py` fails if an unreachable skin
  file reappears. A future skin switch re-adds the wanted file instead of
  keeping dead ones.

## Open questions

- `_print.scss` (298 lines) is the biggest partial — is there print-only
  dead weight, or is the size justified?
- Should `custom-variables.scss` (placeholder) and `custom/_variables.scss`
  (real values) merge into one file?

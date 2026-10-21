# Traceability matrix

Status: active. Maps each FR/NFR id to the guard file(s) that enforce it.
FR/NFR text: `requirements/fr.md`, `requirements/nfr.md`.

| ID | Guard file(s) |
|---|---|
| FR-1 | `test_i18n.py`, `test_lang_switcher.py`, `test_post_chrome_i18n.py` |
| FR-2 | `test_tag_localization.py`, `test_tag_index_descriptions.py` |
| FR-3 | `test_sidebar_layout.py`, `test_home_tag_chips.py`, `test_list_thumbnails.py` |
| FR-4 | `test_giscus_comments.py`, `test_comments.py`, `test_comments_markup.py` |
| FR-5 | `test_sitemap.py`, `test_seo_bilingual.py` |
| FR-6 | `test_lightbox.py`, `test_copy_code.py`, `test_lazy_load_images.py` |
| FR-7 | `test_pagination.py`, `test_portfolio_h1.py`, `test_about_privacy.py` |
| FR-8 | `test_site_utils.py` (+ `docs/architecture/javascript.md`) |
| FR-9 | `test_excluded_paths.py` |
| NFR-1 | `script/check-images`, `test_check_images.py` |
| NFR-2 | `test_asset_budget.py`, `test_syntax_highlight_css.py`, `test_css_parity.py` |
| NFR-3 | LHCI desktop + mobile (`e2e.yml`, `lighthouserc*.json`) |
| NFR-4 | `test_axe_a11y.py`, `test_nav_a11y.py`, `test_footer_*_a11y.py`, `test_en_alt_text.py`, `test_vi_alt_text.py` |
| NFR-5 | `test_about_privacy.py` (+ `docs/architecture/privacy-csp.md`) |
| NFR-6 | `test_internal_link_crawl.py`, `test_post_bare_urls.py`, `test_layout_overflow.py`, `test_code_table_overflow.py` |

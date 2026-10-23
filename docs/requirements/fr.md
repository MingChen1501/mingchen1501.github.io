# Functional requirements (FR)

Status: active. Each item names the guard test that enforces it; behaviour
detail lives in `docs/architecture/content-pipeline.md`.

- FR-1 Bilingual posts: EN in `_posts/`, VI in `_vi_posts` (`/vi/...`),
  cross-linked by `lang`/`ref`. Guards: `test_i18n.py`,
  `test_lang_switcher.py`, `test_post_chrome_i18n.py`.
- FR-2 Tag taxonomy: canonical keys in `_data/tag_labels.yml`, per-tag
  pages, EN/VI labels and descriptions. Guards:
  `test_tag_localization.py`, `test_tag_index_descriptions.py`.
- FR-3 Home and tag lists render shared post cards with sidebar
  highlights (fallback: 5 newest). Guards: `test_sidebar_layout.py`,
  `test_home_tag_chips.py`, `test_list_thumbnails.py`.
- FR-4 Comments on posts via Giscus in production builds only.
  Guards: `test_giscus_comments.py`, `test_comments.py`,
  `test_comments_markup.py`.
- FR-5 Feeds and discovery: Atom feed (EN), sitemap with hreflang
  alternates, `llms.txt`. Guards: `test_robots_sitemap_llms.py`, `test_seo_bilingual.py`.
- FR-6 Reader tools: theme toggle, lazy images, lightbox, copy-code,
  reading progress, share intents. Guards: `test_lightbox.py`,
  `test_copy_code.py`, `test_lazy_load_images.py`.
- FR-7 Pagination (5 per page) and tag/about/resume pages render.
  Guards: `test_pagination.py`, `test_resume_h1.py`,
  `test_about_privacy.py`.
- FR-8 No search page (removed #349): no `search.html`, no `search.js`.
  Guard: `test_site_utils.py` (post-#342 JS-adjacent coverage) and the
  absence pinned in `docs/architecture/javascript.md`.
- FR-9 Excluded internals never ship (`AGENTS.md`, `.opencode/`, `tests/`,
  `script/`, `docs/`). Guard: `test_excluded_paths.py`.
- FR-10 Language preference (#423): an explicit switcher choice sticks
  via a first-party `lang` cookie (`en`/`vi`, `path=/`, one year,
  `SameSite=Lax`); first-visit VN readers still land on `/vi/`, the
  choice survives reload and navigation in both directions, and page
  bytes stay static per URL so caches are unaffected. Guards:
  `test_lang_switch_fragment.py`, `test_about_privacy.py`.

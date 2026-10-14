"""Static guard tests for the comments templates.

These run without a browser and fail fast when the real Jekyll templates
drift away from what the browser fixtures (and E2E tests) assume:

- ``_includes/comments.html`` must render the Disqus thread container, the
  ``disqus_config`` page URL/identifier wiring, the shortname-based embed
  URL, and the noscript fallback.
- ``_layouts/post.html`` must gate comments on the production environment,
  show the disabled message for ``comments: false``, and include the
  comments partial otherwise.
- The browser fixtures under ``tests/e2e/fixtures/`` must stay in sync with
  both templates.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENTS_INCLUDE = REPO_ROOT / "_includes" / "comments.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

ENABLED_FIXTURE = FIXTURES_DIR / "post-with-comments.html"
DISABLED_FIXTURE = FIXTURES_DIR / "post-comments-disabled.html"
NO_SHORTNAME_FIXTURE = FIXTURES_DIR / "post-no-shortname.html"

DISABLED_MESSAGE = "Comments have been disabled for this post."


def _read(path):
    return path.read_text(encoding="utf-8")


def test_comments_include_renders_disqus_thread():
    html = _read(COMMENTS_INCLUDE)
    assert '<div id="disqus_thread"></div>' in html


def test_comments_include_wires_page_url_and_identifier():
    html = _read(COMMENTS_INCLUDE)
    assert "disqus_config" in html
    assert "this.page.url" in html
    assert "this.page.identifier" in html
    assert "page.url" in html
    assert "page.id" in html


def test_comments_include_loads_embed_from_configured_shortname():
    html = _read(COMMENTS_INCLUDE)
    assert "site.disqus.shortname" in html
    assert ".disqus.com/embed.js" in html


def test_comments_include_has_noscript_fallback():
    html = _read(COMMENTS_INCLUDE)
    assert "<noscript>" in html
    assert "disqus.com/?ref_noscript" in html


def test_post_layout_gates_comments_on_production():
    html = _read(POST_LAYOUT)
    assert "jekyll.environment == 'production'" in html
    assert "include comments.html" in html


def test_post_layout_supports_disabling_comments_per_post():
    html = _read(POST_LAYOUT)
    assert "page.comments == false" in html
    assert DISABLED_MESSAGE in html
    assert "comments-disabled-message" in html


def test_enabled_fixture_matches_template_structure():
    html = _read(ENABLED_FIXTURE)
    assert '<div id="disqus_thread"></div>' in html
    assert "disqus_config" in html
    assert "/2026/01/01/e2e-sample-post.html" in html
    assert "this.page.identifier" in html
    assert "e2e-test-shortname.disqus.com/embed.js" in html
    assert "<noscript>" in html


def test_disabled_fixture_matches_template_structure():
    html = _read(DISABLED_FIXTURE)
    assert DISABLED_MESSAGE in html
    assert "comments-disabled-message" in html
    assert "disqus_thread" not in html
    assert "embed.js" not in html


def test_no_shortname_fixture_has_no_comment_markup():
    html = _read(NO_SHORTNAME_FIXTURE)
    assert "disqus_thread" not in html
    assert "embed.js" not in html
    assert DISABLED_MESSAGE not in html

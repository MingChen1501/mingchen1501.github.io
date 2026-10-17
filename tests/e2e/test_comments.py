"""Browser end-to-end tests for the post comments feature.

The Disqus embed is stubbed at the network layer (``page.route``), so these
tests are hermetic: they verify that the page *attempts* to load the Disqus
embed for the configured shortname and that the thread/disabled UI renders,
without depending on the external disqus.com service.
"""

import pytest

E2E_SHORTNAME = "e2e-test-shortname"
POST_PATH = "/2026/01/01/e2e-sample-post.html"
POST_IDENTIFIER = "/2026/01/01/e2e-sample-post"

DISQUS_EMBED_STUB = "window.__disqusEmbedStubLoaded = true;"


@pytest.fixture()
def page(browser):
    context = browser.new_context()
    browser_page = context.new_page()
    try:
        yield browser_page
    finally:
        context.close()


def _stub_disqus(browser_page, requests):
    """Intercept Disqus traffic, record it, and serve a stub embed script."""

    def handler(route):
        requests.append(route.request.url)
        if route.request.url.endswith("embed.js"):
            route.fulfill(
                status=200,
                content_type="application/javascript",
                body=DISQUS_EMBED_STUB,
            )
        else:
            route.fulfill(
                status=200,
                content_type="application/javascript",
                body="/* disqus stub */",
            )

    browser_page.route("**://*.disqus.com/**", handler)


def test_enabled_post_renders_disqus_thread(page, e2e_server):
    page.goto(f"{e2e_server}/post-with-comments.html")
    thread = page.locator("#disqus_thread")
    assert thread.count() == 1, "expected the Disqus thread container to render"
    thread.wait_for(state="attached", timeout=10_000)


def test_enabled_post_loads_disqus_embed_for_configured_shortname(page, e2e_server):
    requests = []
    _stub_disqus(page, requests)

    page.goto(f"{e2e_server}/post-with-comments.html")
    page.wait_for_function(
        "window.__disqusEmbedStubLoaded === true", timeout=10_000
    )

    embed_requests = [url for url in requests if url.endswith("embed.js")]
    assert embed_requests, "expected the page to request the Disqus embed script"
    assert any(
        f"https://{E2E_SHORTNAME}.disqus.com/embed.js" in url
        for url in embed_requests
    ), f"embed request used an unexpected host: {embed_requests}"


def test_enabled_post_configures_page_url_and_identifier(page, e2e_server):
    page.goto(f"{e2e_server}/post-with-comments.html")
    # NB: script elements are not rendered, so Playwright's text locators
    # cannot see them; query the DOM directly instead.
    config_script = page.evaluate(
        """() => {
          const el = Array.from(document.querySelectorAll("script")).find(
            (s) => s.textContent.includes("disqus_config")
          );
          return el ? el.textContent : null;
        }"""
    )

    assert config_script is not None, "expected an inline disqus_config script"
    lines = config_script.splitlines()
    # Assert on the assignment lines specifically: POST_IDENTIFIER is a
    # substring of POST_PATH, so whole-script substring checks would pass
    # even if the identifier wiring were broken.
    url_lines = [line for line in lines if "this.page.url" in line]
    assert url_lines, "disqus_config should assign this.page.url"
    assert POST_PATH in url_lines[0], (
        "disqus_config should carry the canonical page URL path"
    )
    identifier_lines = [line for line in lines if "this.page.identifier" in line]
    assert identifier_lines, "disqus_config should assign this.page.identifier"
    assert POST_IDENTIFIER in identifier_lines[0], (
        "disqus_config should carry the page identifier"
    )


def test_enabled_post_has_noscript_fallback(page, e2e_server):
    page.goto(f"{e2e_server}/post-with-comments.html")
    fallback = page.locator("noscript").first.inner_html()

    assert "disqus.com" in fallback, (
        "expected a noscript fallback pointing at Disqus for JS-disabled readers"
    )


def test_disabled_post_shows_message_and_makes_no_disqus_requests(page, e2e_server):
    requests = []
    _stub_disqus(page, requests)

    page.goto(f"{e2e_server}/post-comments-disabled.html")
    message = page.locator(".comments-disabled-message")
    message.wait_for(state="visible", timeout=10_000)

    assert "Comments have been disabled for this post." in message.inner_text()
    assert page.locator("#disqus_thread").count() == 0
    # Give the page a moment: a stray embed injection would show up here.
    page.wait_for_timeout(1_000)
    assert [url for url in requests if "disqus.com" in url] == [], (
        f"disabled post must not contact Disqus, saw: {requests}"
    )


def test_unconfigured_shortname_renders_no_comment_thread(page, e2e_server):
    requests = []
    _stub_disqus(page, requests)

    page.goto(f"{e2e_server}/post-no-shortname.html")
    page.locator(".post-content").wait_for(state="visible", timeout=10_000)

    assert page.locator("#disqus_thread").count() == 0
    assert page.locator(".comments-disabled-message").count() == 0
    page.wait_for_timeout(1_000)
    assert [url for url in requests if "disqus.com" in url] == [], (
        f"page without a Disqus shortname must not contact Disqus, saw: {requests}"
    )

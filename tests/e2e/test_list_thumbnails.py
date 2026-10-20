"""Guards for #226: fixed-size post thumbnails on the list pages.

The owner wants post imagery back on the list pages, but uniformly: earlier
#113/#116 work deliberately switched home/tag excerpts to `description` front
matter so excerpts never embed full-size body images. Reintroducing
thumbnails therefore guarantees a fixed-size box for every item so the layout
never shifts (`_layouts/post.html` is untouched).

What #226 changed:

- `_includes/post-thumbnail.html` renders every list item's thumbnail with one
  shared 120x90 (4:3) box. Source chain per post: front matter `thumbnail`,
  else front matter `image`, else the first image of the post body, else the
  fixed built-in placeholder (`assets/img/placeholder.svg`).
- `script/generate-thumbnails` pre-generates small 240x180 cover-cropped WebP
  variants (`assets/img/thumbs/...`) so lists never download 1600px
  originals. External issue-attachment URLs cannot be resized — those keep the
  CSS fixed box (bandwidth note in the README and the PR body).
- `_sass/minima/custom/_list-thumbs.scss` fixes the box (`width`/`height`
  120x90, `object-fit: cover`); the include emits matching `width`/`height`
  attributes so the browser reserves the space before the first byte (no CLS).

Guarded here:

- (static) the include implements the source chain in order and emits
  `width="120" height="90"` with lazy decoding; the stylesheet fixes the
  120x90 box with `object-fit: cover`; the placeholder and every expected
  variant exist at 240x180 WebP within budget (`script/check-images` still
  passes); both list layouts render the include inside the loop while
  `_layouts/post.html` stays thumbnail-free;
- (built HTML) every `ul.post-list > li` on the EN/VI homes and every tag page
  carries exactly one thumbnail with numeric 120x90 dimensions, local thumbs
  resolve to a file in the build, and the three source cases hold: front
  matter wins over the first body image (EN coffee post), else the first body
  image (VI coffee post), else the placeholder (imageless orchestration
  posts);
- (browser) every thumbnail box renders at an identical size at 375px and
  1280px on the EN/VI homes and tag pages — including with images blocked, so
  the reserved box alone (no CLS) already has the final size.
"""

import contextlib
import re
from pathlib import Path
from urllib.parse import urlparse

import conftest

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
THUMB_INCLUDE = REPO_ROOT / "_includes" / "post-thumbnail.html"
LIST_THUMBS_SCSS = REPO_ROOT / "_sass" / "minima" / "custom" / "_list-thumbs.scss"
PLACEHOLDER = REPO_ROOT / "assets" / "img" / "placeholder.svg"
GENERATE_SCRIPT = REPO_ROOT / "script" / "generate-thumbnails"
THUMBS_DIR = REPO_ROOT / "assets" / "img" / "thumbs"
TAG_PAGES_DIR = REPO_ROOT / "tags"
VI_TAG_PAGES_DIR = REPO_ROOT / "vi" / "tags"

THUMB_WIDTH = 120
THUMB_HEIGHT = 90
VARIANT_SIZE = (240, 180)

PHONE_WIDTH = 375
TABLET_WIDTH = 768
DESKTOP_WIDTH = 1280

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
FRONT_MATTER_IMG_RE = re.compile(r"^(?:thumbnail|image):\s*([^\s#]+)\s*$", re.M)
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\((/assets/[^\s)]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.S)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _is_unpublished(post_path):
    text = _read(post_path)
    match = FRONT_MATTER_RE.match(text)
    front_matter = match.group(1) if match else ""
    return bool(re.search(r"^published:\s*false\s*$", front_matter, re.M))


def _post_thumbnail_source(post_path):
    """Expected thumbnail site path for a post, mirroring the include chain."""
    text = _read(post_path)
    match = FRONT_MATTER_RE.match(text)
    front_matter = match.group(1) if match else ""
    body = text[match.end():] if match else text
    fm_match = FRONT_MATTER_IMG_RE.search(front_matter)
    if fm_match and fm_match.group(1).strip("\"'").startswith("/assets/"):
        return fm_match.group(1).strip("\"'")
    candidates = [(m.start(), m.group(1)) for m in MD_IMG_RE.finditer(body)]
    candidates += [(m.start(), m.group(1)) for m in HTML_IMG_RE.finditer(body)]
    candidates.sort()
    for _, candidate in candidates:
        if candidate.startswith("/assets/"):
            return candidate
    return None


def _expected_posts():
    """`(path, source)` for every published EN/VI post (`None` = placeholder)."""
    found = []
    for directory in (REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"):
        for path in sorted(directory.glob("*.md")):
            if _is_unpublished(path):
                continue
            found.append((path, _post_thumbnail_source(path)))
    return found


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_thumbnail_include_implements_the_source_chain():
    html = _read(THUMB_INCLUDE)
    thumb = html.index("assign thumb_src = include.post.thumbnail")
    image = html.index("default: include.post.image")
    body = html.index("split: '<img'")
    placeholder = html.index("assign thumb_src = '/assets/img/placeholder.svg'")
    assert thumb < image < body < placeholder, (
        "the thumbnail source chain must be front matter thumbnail, then "
        "image, then the first body image, then the fixed placeholder"
    )
    assert 'width="120" height="90"' in html, (
        "every thumbnail must carry explicit 120x90 dimensions (no CLS)"
    )
    assert 'loading="lazy"' in html and 'decoding="async"' in html
    assert 'tabindex="-1"' in html and 'aria-hidden="true"' in html, (
        "the thumbnail repeats the title link, so it stays out of the tab "
        "order and the accessibility tree like the sidebar thumbnails"
    )


@pytest.mark.static
def test_thumbnail_include_prefers_small_variants():
    html = _read(THUMB_INCLUDE)
    assert "/assets/img/thumbs/" in html and "-240.webp" in html, (
        "local list sources must map to the generated small WebP variants, "
        "never the full-size originals"
    )
    assert "contains '://'" in html, (
        "external attachment URLs cannot be resized and must pass through "
        "into the same fixed CSS box"
    )
    assert "?v=" in html, (
        "local thumbnail URLs are fixed-URL assets and carry the build token "
        "like the other cache-versioned assets"
    )


@pytest.mark.static
def test_stylesheet_fixes_the_shared_thumbnail_box():
    scss = _read(LIST_THUMBS_SCSS)
    assert ".post-list__item" in scss and ".post-thumb" in scss
    for literal in ("width: 120px", "height: 90px", "object-fit: cover"):
        assert literal in scss, f"the fixed thumbnail box needs `{literal}`"
    assert "padding: 0" in scss, (
        "`_base.scss` gives every img 20px of border-box padding, which would "
        "squeeze the fixed box into a distorted rectangle (same trap as the "
        "sidebar thumbnails)"
    )


@pytest.mark.static
def test_list_layouts_share_the_thumbnail_include():
    for layout in (HOME_LAYOUT, TAG_LAYOUT):
        html = _read(layout)
        loop = html.index("{%- for post in ")
        include = html.index("include post-thumbnail.html", loop)
        endloop = html.index("endfor", loop)
        assert include < endloop, (
            f"{layout.name} must render the thumbnail include inside the loop"
        )
        assert 'class="post-list__item"' in html
        assert 'class="post-list__body"' in html
    post = _read(POST_LAYOUT)
    assert "post-thumbnail" not in post, (
        "the post layout is explicitly out of scope for #226"
    )


@pytest.mark.static
def test_placeholder_and_variants_exist_and_are_fresh():
    assert PLACEHOLDER.is_file(), "the fixed placeholder is missing"
    assert GENERATE_SCRIPT.is_file() and GENERATE_SCRIPT.stat().st_mode & 0o111, (
        "script/generate-thumbnails must exist and stay executable"
    )
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow is not installed")
    problems = []
    for path, source in _expected_posts():
        if source is None:
            continue
        variant = THUMBS_DIR / Path(source.lstrip("/")).relative_to(
            "assets/img"
        ).parent / (
            Path(source).stem + "-240.webp"
        )
        if not variant.is_file():
            problems.append(
                f"{path.name}: variant {variant.relative_to(REPO_ROOT)} "
                "missing — run script/generate-thumbnails"
            )
            continue
        with Image.open(variant) as im:
            if (im.size, im.format) != (VARIANT_SIZE, "WEBP"):
                problems.append(
                    f"{variant.relative_to(REPO_ROOT)} is {im.format} "
                    f"{im.size}, want WEBP {VARIANT_SIZE}"
                )
        if variant.stat().st_mtime < (REPO_ROOT / source.lstrip("/")).stat().st_mtime:
            problems.append(
                f"{variant.relative_to(REPO_ROOT)} is older than its source "
                f"{source} — rerun script/generate-thumbnails"
            )
    assert not problems, "thumbnail variants missing/stale:\n" + "\n".join(problems)


# --- built-HTML guards (need the real `jekyll build`, no browser) ------------


def _list_thumbs(built_site):
    """`(page_rel, item_html, img_tag)` for every list-item thumbnail."""
    found = []
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        if 'http-equiv="refresh"' in text:
            continue
        for match in re.finditer(r'<ul class="post-list">(.*?)</ul>', text, re.S):
            for item in re.finditer(
                r"<li[^>]*>(.*?)</li>", match.group(1), re.S
            ):
                thumbs = re.findall(
                    r'<a class="post-thumb"[^>]*><img\b[^>]*>', item.group(1)
                )
                found.append((path.relative_to(built_site), item.group(1), thumbs))
    return found


def _thumb_attr(tag, name):
    match = re.search(rf'{name}="([^"]*)"', tag)
    return match.group(1) if match else None


def test_built_list_items_render_one_sized_thumbnail(built_site):
    thumbs = _list_thumbs(built_site)
    assert thumbs, "no post-list items found in the built site"
    problems = []
    for page_rel, _item, tags in thumbs:
        if len(tags) != 1:
            problems.append(
                f"{page_rel}: list item has {len(tags)} thumbnails, want 1"
            )
            continue
        tag = tags[0]
        if _thumb_attr(tag, "width") != str(THUMB_WIDTH) or _thumb_attr(
            tag, "height"
        ) != str(THUMB_HEIGHT):
            problems.append(f"{page_rel}: thumbnail without 120x90 dims: {tag[:120]}")
        src = _thumb_attr(tag, "src") or ""
        if src.startswith("/assets/"):
            local = src.split("?", 1)[0].lstrip("/")
            if not (built_site / local).is_file():
                problems.append(f"{page_rel}: thumbnail {src} not in the build")
        elif "://" not in src:
            problems.append(f"{page_rel}: unexpected thumbnail src: {src}")
    assert not problems, "built list thumbnails:\n" + "\n".join(problems)


def _list_thumb_by_post(built_site, post_href):
    """Thumbnail `src` of the list item linking to `post_href` (or None)."""
    for _page_rel, item, tags in _list_thumbs(built_site):
        if f'href="{post_href}"' in item and tags:
            return _thumb_attr(tags[0], "src")
    return None


def test_built_thumbnail_source_chain(built_site):
    # Front matter wins over the first body image: the EN coffee post opens
    # with b2.jpg but declares b1.jpg as its thumbnail.
    en_coffee = _list_thumb_by_post(
        built_site, "/2022/10/27/brewing-vietnamese-coffee.html"
    )
    assert en_coffee is not None, "EN coffee post missing from every list"
    assert "b1-240.webp" in en_coffee, (
        f"front matter thumbnail must win, got {en_coffee}"
    )
    assert "b2-240" not in en_coffee
    # Else the first body image: the VI coffee post has no front matter
    # image, so its thumbnail is the body lead image variant.
    vi_thumb = _list_thumb_by_post(
        built_site, "/vi/2022/10/27/cach-pha-ca-phe.html"
    )
    assert vi_thumb is not None, "VI coffee post missing from every list"
    assert "thumbs/" in vi_thumb and ".webp?" in vi_thumb, (
        f"VI coffee post must use a small body-image variant, got {vi_thumb}"
    )
    assert "placeholder" not in vi_thumb
    # Else the fixed placeholder: the orchestration posts carry no images.
    for href in (
        "/2026/10/14/setting-up-ai-coding-agent-orchestration.html",
        "/2026/10/17/real-world-agent-orchestration-with-free-opencode.html",
    ):
        src = _list_thumb_by_post(built_site, href)
        assert src is not None, f"{href} missing from every list"
        assert "placeholder.svg" in src, f"{href} must use the placeholder, got {src}"


# --- browser guards (identical rendered box, no CLS) -------------------------


@contextlib.contextmanager
def _viewport(browser, built_site_url, width, height=900, block_images=False):
    context = browser.new_context(viewport={"width": width, "height": height})
    try:
        page = context.new_page()
        origin = urlparse(built_site_url).netloc

        def _route(route):
            url = route.request.url
            if urlparse(url).netloc != origin:
                route.abort()
            elif block_images and route.request.resource_type == "image":
                route.abort()
            else:
                route.continue_()

        page.route("**/*", _route)
        yield page
    finally:
        context.close()


_MEASURE_JS = """
() => Array.from(document.querySelectorAll('ul.post-list > li')).map((li) => {
  const box = li.querySelector('.post-thumb');
  const img = li.querySelector('.post-thumb img');
  const boxRect = box ? box.getBoundingClientRect() : null;
  const imgRect = img ? img.getBoundingClientRect() : null;
  return {
    href: (li.querySelector('a.post-link') || {}).href || null,
    box: boxRect ? {width: boxRect.width, height: boxRect.height} : null,
    img: imgRect ? {width: imgRect.width, height: imgRect.height} : null,
  };
})
"""


def _measure(browser, built_site_url, path, width, block_images=False):
    with _viewport(browser, built_site_url, width, block_images=block_images) as page:
        page.goto(f"{built_site_url}{path}", wait_until="load")
        page.locator("ul.post-list").wait_for(state="visible", timeout=10_000)
        return page.evaluate(_MEASURE_JS)


def _list_pages():
    en_tags = sorted(path.stem for path in TAG_PAGES_DIR.glob("*.md"))
    vi_tags = sorted(path.stem for path in VI_TAG_PAGES_DIR.glob("*.md"))
    pages = ["/", "/vi/"]
    pages += [f"/tags/{stem}/" for stem in en_tags]
    pages += [f"/vi/tags/{stem}/" for stem in vi_tags]
    return pages


@pytest.mark.parametrize("width", [PHONE_WIDTH, TABLET_WIDTH, DESKTOP_WIDTH])
def test_list_thumbnails_share_one_rendered_box(
    browser, built_site_url, width
):
    """Every thumbnail box is pixel-uniform within and across list pages."""
    boxes = set()
    checked = 0
    for path in _list_pages():
        try:
            items = _measure(browser, built_site_url, path, width)
        except Exception as exc:
            pytest.skip(f"{path} not in the build: {exc}")
        assert items, f"{path} at {width}px has no list items"
        for item in items:
            assert item["box"] is not None, f"{path}: item without .post-thumb"
            assert item["img"] is not None, f"{path}: box without img"
            boxes.add((round(item["box"]["width"], 1), round(item["box"]["height"], 1)))
            boxes.add((round(item["img"]["width"], 1), round(item["img"]["height"], 1)))
            checked += 1
    assert checked > 0
    assert boxes == {(THUMB_WIDTH, THUMB_HEIGHT)}, (
        f"thumbnail boxes differ at {width}px: {sorted(boxes)}"
    )


@pytest.mark.parametrize("width", [PHONE_WIDTH, DESKTOP_WIDTH])
def test_list_thumbnail_box_needs_no_image_bytes(
    browser, built_site_url, width
):
    """With images blocked the reserved box is already the final 120x90 size.

    The fixed CSS box plus the `width`/`height` attributes reserve the space
    before the first byte arrives, so list images contribute no CLS.
    """
    for path in ("/", "/vi/"):
        items = _measure(browser, built_site_url, path, width, block_images=True)
        assert items, f"{path} at {width}px has no list items"
        for item in items:
            assert item["box"] is not None, f"{path}: item without .post-thumb"
            assert (round(item["box"]["width"], 1), round(item["box"]["height"], 1)) == (
                THUMB_WIDTH,
                THUMB_HEIGHT,
            ), f"{path} at {width}px: box is {item['box']} with images blocked"

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
- (static, #245) the dark placeholder twin exists with the same 120x90 box
  in a dark neutral palette while the light tile is byte-identical, the
  include emits the light/dark `img` pair only for placeholder items, and
  the stylesheet swaps the pair via `html[data-theme]` with the OS
  `prefers-color-scheme` fallback;
- (built HTML) every `ul.post-list > li` on the EN/VI homes and every tag
  page carries exactly one thumbnail anchor with numeric 120x90 dimensions, local thumbs
  resolve to a file in the build, and the three source cases hold: front
  matter wins over the first body image (EN coffee post), else the first body
  image (VI coffee post), else the placeholder light/dark pair (imageless
  orchestration posts, #245);
- (browser) every thumbnail box renders at an identical size at 375px and
  1280px on the EN/VI homes and tag pages — including with images blocked, so
  the reserved box alone (no CLS) already has the final size;
- (browser, #245) the placeholder pair swaps visibility by theme while the
  visible tile keeps the 120x90 box, and the dark tile meters comfortably
  darker than the unchanged light tile (no glare).
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
PLACEHOLDER_DARK = REPO_ROOT / "assets" / "img" / "placeholder-dark.svg"
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
    """`(page_rel, item_html, img_tags)` for every list-item thumbnail anchor.

    Placeholder items (#245) carry a light/dark `img` pair inside their one
    anchor, so this collects every `img` in the anchor: one tag for real
    thumbnails, two (light then dark) for the placeholder.
    """
    found = []
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        if 'http-equiv="refresh"' in text:
            continue
        for match in re.finditer(r'<ul class="post-list">(.*?)</ul>', text, re.S):
            for item in re.finditer(
                r"<li[^>]*>(.*?)</li>", match.group(1), re.S
            ):
                anchors = re.findall(
                    r'<a class="post-thumb[^"]*"[^>]*>((?:<img\b[^>]*>)+)</a>',
                    item.group(1),
                    re.S,
                )
                if len(anchors) != 1:
                    found.append(
                        (path.relative_to(built_site), item.group(1), [])
                    )
                    continue
                tags = re.findall(r"<img\b[^>]*>", anchors[0])
                found.append((path.relative_to(built_site), item.group(1), tags))
    return found


def _thumb_attr(tag, name):
    match = re.search(rf'{name}="([^"]*)"', tag)
    return match.group(1) if match else None


def test_built_list_items_render_one_sized_thumbnail(built_site):
    thumbs = _list_thumbs(built_site)
    assert thumbs, "no post-list items found in the built site"
    problems = []
    for page_rel, _item, tags in thumbs:
        if len(tags) == 2 and (
            "placeholder.svg" in tags[0]
            and "placeholder-dark" not in tags[0]
            and "placeholder-dark.svg" in tags[1]
        ):
            pair = tags  # the #245 placeholder light/dark pair in one anchor
        elif len(tags) == 1:
            pair = tags
        else:
            problems.append(
                f"{page_rel}: list item has {len(tags)} thumbnail images, "
                "want 1 (or the #245 placeholder pair)"
            )
            continue
        for tag in pair:
            if _thumb_attr(tag, "width") != str(THUMB_WIDTH) or _thumb_attr(
                tag, "height"
            ) != str(THUMB_HEIGHT):
                problems.append(
                    f"{page_rel}: thumbnail without 120x90 dims: {tag[:160]}"
                )
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


# --- #245 guards: the placeholder stays quiet in dark mode --------------------


def _svg_geometry(svg_text):
    """`(width, height, viewBox-w, viewBox-h)` of a placeholder tile."""
    match = re.search(
        r'<svg\b[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"'
        r"[^>]*\bviewBox=\"0 0 (\d+) (\d+)\"",
        svg_text,
    )
    assert match, "the placeholder SVG must carry width/height/viewBox"
    return tuple(int(group) for group in match.groups())


def _relative_luminance(hex_color):
    """WCAG relative luminance of an `#rrggbb` fill."""
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linearized = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linearized[0] + 0.7152 * linearized[1] + 0.0722 * linearized[2]


def _svg_fills(svg_text):
    return set(re.findall(r'fill="(#[0-9a-fA-F]{6})"', svg_text))


@pytest.mark.static
def test_placeholder_dark_twin_matches_the_light_box():
    """The dark tile is the same 120x90 tile in a dark neutral palette.

    Geometry must match the light tile exactly (same box, no CLS delta),
    the light tile keeps its `#e8e8e8`/`#9a9a9a` palette (light mode
    unchanged), and the dark tile pairs a dark neutral surface with a
    subtle — visible but nowhere near glaring — icon.
    """
    assert PLACEHOLDER.is_file(), "the fixed placeholder is missing"
    assert PLACEHOLDER_DARK.is_file(), "the dark placeholder twin is missing"
    light = _read(PLACEHOLDER)
    dark = _read(PLACEHOLDER_DARK)
    assert _svg_geometry(light) == (THUMB_WIDTH, THUMB_HEIGHT, 120, 90)
    assert _svg_geometry(dark) == (THUMB_WIDTH, THUMB_HEIGHT, 120, 90), (
        "the dark twin must keep the exact 120x90 box (no CLS delta)"
    )
    assert _svg_fills(light) == {"#e8e8e8", "#9a9a9a"}, (
        "the light tile palette is pinned: light mode must not change"
    )
    assert _svg_fills(dark) == {"#262626", "#8c8c8c"}, (
        "the dark twin must pair a dark neutral surface with one subtle icon tone"
    )
    assert 'stroke="#3a3a3a"' in dark, (
        "the dark tile needs a hairline border to sit on the dark page"
    )
    tile_luminance = _relative_luminance("#262626")
    icon_luminance = _relative_luminance("#8c8c8c")
    assert tile_luminance < 0.03, (
        f"the dark surface must stay near the page background, got {tile_luminance:.3f}"
    )
    assert 0.2 < icon_luminance < 0.45, (
        "the dark icon must stay subtle but visible, "
        f"got {icon_luminance:.3f}"
    )
    contrast = (icon_luminance + 0.05) / (tile_luminance + 0.05)
    assert contrast >= 3.0, (
        f"the dark icon must read against its tile, got {contrast:.2f}:1"
    )


@pytest.mark.static
def test_thumbnail_include_emits_a_theme_aware_placeholder_pair():
    """Only placeholder items get the light/dark `img` pair (#245)."""
    html = _read(THUMB_INCLUDE)
    assert "placeholder-dark.svg" in html, (
        "the include must reference the dark placeholder twin"
    )
    assert "thumb_is_placeholder" in html, (
        "the include must track placeholder items separately from real sources"
    )
    assert "thumb_is_placeholder == false" in html, (
        "real local sources must keep mapping to small variants, "
        "never to the dark twin"
    )
    assert (
        'class="post-thumb{% if thumb_is_placeholder %} '
        'post-thumb--placeholder{% endif %}"' in html
    ), "only placeholder anchors may carry the swap hook class"
    light = html.index("post-thumb__img--light")
    dark = html.index("post-thumb__img--dark")
    assert light < dark, "the light tile stays first so no-JS readers keep it"
    for snippet in ('width="120" height="90"', 'loading="lazy"', 'decoding="async"', 'alt=""'):
        assert html.count(snippet) >= 2, (
            f"both tiles of the pair need {snippet} (fixed box, no CLS)"
        )
    assert html.count("append: '?v='") >= 2, (
        "both fixed-URL tiles carry the build token like every cached asset"
    )


@pytest.mark.static
def test_stylesheet_swaps_the_placeholder_pair_by_theme():
    """Dark mode shows the dark tile; light mode paints exactly one tile."""
    scss = _read(LIST_THUMBS_SCSS)
    assert ".post-thumb img.post-thumb__img--dark" in scss, (
        "the dark tile needs a rule specific enough to beat the base img rule"
    )
    assert 'html[data-theme="dark"]' in scss, (
        "the stored theme choice must flip the pair"
    )
    assert "@media (prefers-color-scheme: dark)" in scss, (
        "the OS preference must flip the pair for no-JS readers"
    )
    assert "html:not([data-theme=\"light\"])" in scss, (
        "the OS fallback must yield to a stored light choice"
    )
    for hidden, shown in (
        ("post-thumb__img--light", "post-thumb__img--dark"),
        ("post-thumb__img--dark", "post-thumb__img--light"),
    ):
        assert scss.count(hidden) >= 2 and scss.count(shown) >= 2, (
            "each theme layer must hide one tile and show the other"
        )
    assert 'html[data-theme="light"]' not in scss, (
        "light mode needs no override: the base rules already paint one tile"
    )


def test_built_placeholder_items_render_the_light_dark_pair(built_site):
    """Imageless posts carry both tiles with matching dims and tokens."""
    hrefs = (
        "/2026/10/14/setting-up-ai-coding-agent-orchestration.html",
        "/2026/10/17/real-world-agent-orchestration-with-free-opencode.html",
    )
    problems = []
    for href in hrefs:
        tags = None
        anchor_placeholder = False
        for _page_rel, item, item_tags in _list_thumbs(built_site):
            if f'href="{href}"' in item and item_tags:
                tags = item_tags
                anchor_placeholder = 'post-thumb--placeholder"' in item
                break
        if not tags:
            problems.append(f"{href} missing from every list")
            continue
        if not anchor_placeholder:
            problems.append(f"{href}: placeholder anchor lacks the swap hook class")
        if len(tags) != 2:
            problems.append(
                f"{href}: placeholder must render the light/dark pair, "
                f"got {len(tags)} images"
            )
            continue
        light_src = _thumb_attr(tags[0], "src") or ""
        dark_src = _thumb_attr(tags[1], "src") or ""
        if "placeholder.svg" not in light_src or "placeholder-dark" in light_src:
            problems.append(f"{href}: first tile must be the light one, got {light_src}")
        if "placeholder-dark.svg" not in dark_src:
            problems.append(f"{href}: second tile must be the dark one, got {dark_src}")
        for tag in tags:
            if _thumb_attr(tag, "width") != str(THUMB_WIDTH) or _thumb_attr(
                tag, "height"
            ) != str(THUMB_HEIGHT):
                problems.append(f"{href}: pair tile without 120x90 dims: {tag[:160]}")
            if _thumb_attr(tag, "loading") != "lazy" or (
                _thumb_attr(tag, "decoding") != "async"
            ):
                problems.append(f"{href}: pair tile must stay lazy: {tag[:160]}")
            src = _thumb_attr(tag, "src") or ""
            local = src.split("?", 1)[0].lstrip("/")
            if not (built_site / local).is_file():
                problems.append(f"{href}: tile {src} not in the build")
        light_token = light_src.split("?v=", 1)[1] if "?v=" in light_src else None
        dark_token = dark_src.split("?v=", 1)[1] if "?v=" in dark_src else None
        if not light_token or light_token != dark_token:
            problems.append(
                f"{href}: both tiles must share the build token, "
                f"got {light_src} vs {dark_src}"
            )
    assert not problems, "built placeholder pairs:\n" + "\n".join(problems)


_PLACEHOLDER_THEME_JS = """
() => Array.from(document.querySelectorAll('ul.post-list > li')).map((li) => {
  const anchor = li.querySelector('a.post-thumb');
  const light = anchor ? anchor.querySelector('img.post-thumb__img--light') : null;
  const dark = anchor ? anchor.querySelector('img.post-thumb__img--dark') : null;
  const state = (el) => {
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return {
      display: getComputedStyle(el).display,
      width: rect.width,
      height: rect.height,
    };
  };
  return {
    placeholder: anchor ? anchor.classList.contains('post-thumb--placeholder') : false,
    light: state(light),
    dark: state(dark),
  };
})
"""


@pytest.mark.parametrize("path", ["/", "/vi/"])
@pytest.mark.parametrize("width", [PHONE_WIDTH, DESKTOP_WIDTH])
@pytest.mark.parametrize(
    "color_scheme,expected_theme", [("light", "light"), ("dark", "dark")]
)
def test_placeholder_pair_swaps_visibility_and_tone_by_theme(
    browser, built_site_url, path, width, color_scheme, expected_theme
):
    """The visible placeholder tile fits the theme: 120x90, no glare (#245)."""
    from io import BytesIO

    from PIL import Image, ImageStat

    context = browser.new_context(
        viewport={"width": width, "height": 900}, color_scheme=color_scheme
    )
    try:
        page = context.new_page()
        page.goto(f"{built_site_url}{path}", wait_until="load")
        page.locator("ul.post-list").wait_for(state="visible", timeout=10_000)
        page.wait_for_function(
            "() => {"
            " const rendered = Array.from(document.querySelectorAll("
            " 'a.post-thumb--placeholder img')).filter("
            " (img) => img.getClientRects().length > 0);"
            " return rendered.length > 0 && rendered.every("
            " (img) => img.complete && img.naturalWidth > 0); }",
            timeout=10_000,
        )
        theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        assert theme == expected_theme, (
            f"{path}: a {color_scheme} OS must paint {expected_theme}, got {theme}"
        )
        rows = page.evaluate(_PLACEHOLDER_THEME_JS)
        placeholders = [row for row in rows if row["placeholder"]]
        assert placeholders, f"{path} at {width}px renders no placeholder tiles"
        for row in placeholders:
            visible = row["dark"] if expected_theme == "dark" else row["light"]
            hidden = row["light"] if expected_theme == "dark" else row["dark"]
            assert hidden["display"] == "none", (
                f"{path} at {width}px in {expected_theme} mode must hide "
                f"one tile, got {row}"
            )
            assert visible["display"] != "none", (
                f"{path} at {width}px in {expected_theme} mode hides both tiles"
            )
            assert (round(visible["width"], 1), round(visible["height"], 1)) == (
                THUMB_WIDTH,
                THUMB_HEIGHT,
            ), (
                f"{path} at {width}px in {expected_theme} mode: "
                f"visible tile is {visible}, want 120x90"
            )
        shown = (
            "post-thumb__img--dark"
            if expected_theme == "dark"
            else "post-thumb__img--light"
        )
        shot = (
            page.locator(f"a.post-thumb--placeholder img.{shown}")
            .first.screenshot()
        )
        mean = ImageStat.Stat(Image.open(BytesIO(shot)).convert("L")).mean[0]
        if expected_theme == "light":
            assert mean > 170, (
                f"{path} at {width}px: the light tile meters {mean:.0f}, "
                "it must stay the unchanged bright tile"
            )
        else:
            assert mean < 110, (
                f"{path} at {width}px: the dark tile meters {mean:.0f}, "
                "it must sit quietly on the dark page"
            )
    finally:
        context.close()

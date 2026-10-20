"""Guards for #113 (perf): content images carry intrinsic dimensions and the
list excerpts never embed full-size images.

Background: every long-post image used to render as a bare
``<img src alt>`` inside a ``<p>`` — no ``width``/``height``, no ``srcset``,
no ``<figure>``/``<figcaption>`` — shifting the article while it loaded (CLS)
and forcing phones to download desktop-sized files. The home excerpts made it
worse by embedding those same full-size images in every list item.

What #113 changed:

- every local content image in ``_posts/`` / ``_vi_posts/`` declares its
  intrinsic size: a kramdown ``{: width="W" height="H" }`` IAL on markdown
  images (values match the real file, checked below), or literal
  ``width``/``height`` attributes on the raw-HTML ``<figure>`` blocks;
- captioned standalone images are real ``<figure class="post-figure">`` blocks
  with the caption as ``<figcaption>`` text; only the blockquote lead images
  (glued to the opening prose) keep the markdown ``"title"`` tooltip form;
- ``_layouts/home.html`` renders the translated ``description`` front matter
  (mandatory per the taxonomy) instead of ``post.excerpt`` — the Jekyll
  excerpt is the first body paragraph, which embeds the full-size image for
  posts that open with one;
- ``_sass/minima/custom-styles.scss`` reserves the aspect-ratio box
  (``img[width][height] { height: auto; }``) so the box the browser reserves
  from the attributes always matches the rendered box.

``srcset``/``sizes`` fallback (documented here, not generated): the site
builds on GitHub Pages with ``--safe``, i.e. no image-resizing plugin, and
``assets/img/`` sits near the 6MB ``script/check-images`` budget — there is no
pipeline that could emit resized variants and no budget to host them.
Responsive delivery is width-constrained single files (``max-width: 100%``)
plus lazy loading of every non-first image (``assets/js/lazy-load.js``).

Guarded here:

- (static) every local markdown image declares ``width``/``height`` via IAL,
  with values equal to the real file dimensions;
- (static) raw-HTML content images (the figures) carry numeric
  ``width``/``height`` too, and no markdown image keeps a ``"title"`` outside
  a blockquote lead line (captions live in ``<figcaption>``);
- (static) the home list renders the description first, and the stylesheet
  reserves the aspect-ratio box;
- (built HTML) every ``.post-content`` image has numeric ``width``/``height``,
  every ``img[title]`` sits inside a ``<blockquote>``, the long post renders
  ``figure.post-figure`` + ``figcaption``, and every ``ul.post-list > li`` on
  the home / Vietnamese home / tag pages contains exactly one fixed-size
  thumbnail (the #226 ``post-thumb`` variant, never a full-size original).
"""

import re
import struct
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POSTS_DIRS = [REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"]
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"

MD_IMG_RE = re.compile(r'!\[([^\]]*)\]\((/assets/[^\s)]+)(?:\s+"([^"]*)")?\)')
IAL_RE = re.compile(r'\{\:\s*width="(\d+)"\s+height="(\d+)"[^}]*\}')
# NB (#147): the IAL may carry extra attributes after the dimensions
# (e.g. aria-hidden="true" on decorative repeats) — still a valid declaration.
HTML_IMG_RE = re.compile(r'<img\b[^>]*>', re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _image_size(path):
    """Pixel dimensions of a PNG/JPEG/GIF file without Pillow (not a test dep)."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    if data[:2] == b"\xff\xd8":
        pos = 2
        while pos + 4 < len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
                return width, height
            size = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            pos += 2 + size
        raise ValueError(f"no SOF marker in {path}")
    if data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return width, height
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8 " and len(data) >= 30:
            width = int.from_bytes(data[26:28], "little") & 0x3FFF
            height = int.from_bytes(data[28:30], "little") & 0x3FFF
            return width, height
        if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b"VP8X" and len(data) >= 30:
            width = int.from_bytes(data[24:27], "little") + 1
            height = int.from_bytes(data[27:30], "little") + 1
            return width, height
        raise ValueError(f"unsupported WebP chunk in {path}")
    raise ValueError(f"unsupported image type: {path}")


def _markdown_images():
    """(path, line_no, line, match) for every local markdown image."""
    found = []
    for directory in POSTS_DIRS:
        for md in sorted(directory.glob("*.md")):
            for lineno, line in enumerate(
                _read(md).splitlines(), start=1
            ):
                for match in MD_IMG_RE.finditer(line):
                    found.append((md, lineno, line, match))
    return found


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_every_content_image_declares_matching_intrinsic_dimensions():
    images = _markdown_images()
    assert images, "no local content images found in _posts/ or _vi_posts/"
    problems = []
    for md, lineno, line, match in images:
        src = match.group(2)
        tail = line[match.end():]
        ial = IAL_RE.match(tail.lstrip())
        if not ial:
            problems.append(f"{md.name}:{lineno}: {src} has no width/height IAL")
            continue
        real_width, real_height = _image_size(REPO_ROOT / src.lstrip("/"))
        if (int(ial.group(1)), int(ial.group(2))) != (real_width, real_height):
            problems.append(
                f"{md.name}:{lineno}: {src} declares "
                f"{ial.group(1)}x{ial.group(2)} but is {real_width}x{real_height}"
            )
    assert not problems, "content images with missing/wrong dimensions:\n" + "\n".join(
        problems
    )


@pytest.mark.static
def test_raw_html_content_images_carry_dimensions_and_captions_are_figures():
    problems = []
    for directory in POSTS_DIRS:
        for md in sorted(directory.glob("*.md")):
            text = _read(md)
            for match in HTML_IMG_RE.finditer(text):
                tag = match.group(0)
                if "/assets/" not in tag:
                    continue
                width = re.search(r'width="(\d+)"', tag)
                height = re.search(r'height="(\d+)"', tag)
                if not (width and height):
                    problems.append(f"{md.name}: raw HTML image without dims: {tag[:80]}")
    assert not problems, "\n".join(problems)


def images_have_no_bare_titles():
    """Standalone captioned images must be figures; titles survive only as
    tooltips on blockquote lead images (glued to the opening prose)."""
    problems = []
    for md, lineno, line, match in _markdown_images():
        if not match.group(3):
            continue
        if not line.strip().startswith(">"):
            problems.append(
                f"{md.name}:{lineno}: titled image outside a blockquote — "
                "captioned standalone images must be <figure> blocks"
            )
    if problems:
        return "\n".join(problems)
    return None


@pytest.mark.static
def test_titled_images_outside_blockquotes_became_figures():
    assert images_have_no_bare_titles() is None, images_have_no_bare_titles()


@pytest.mark.static
def test_home_list_prefers_description_over_raw_excerpt():
    html = _read(HOME_LAYOUT)
    loop = html.index("{%- for post in posts -%}")
    desc = html.index("{{ post.description", loop)
    excerpt = html.index("{{ post.excerpt }}", loop)
    # The description branch comes first (same pattern as `_layouts/tag.html`);
    # the raw excerpt survives only as the fallback for pre-taxonomy posts.
    assert desc < excerpt, (
        "the home list must render post.description before falling back to "
        "post.excerpt, so list items never embed full-size content images"
    )


@pytest.mark.static
def test_stylesheet_reserves_the_image_aspect_ratio_box():
    scss = conftest.custom_styles_text()
    assert "img[width][height]" in scss, (
        "the CLS reservation rule for dimensioned content images is missing"
    )
    rule = scss[scss.index("img[width][height]"):scss.index("}", scss.index("img[width][height]"))]
    assert "height: auto" in rule, (
        "dimensioned content images must keep height: auto so the reserved "
        "aspect-ratio box matches the rendered box"
    )
    assert "figure.post-figure" in scss and "figcaption" in scss, (
        "the captioned-figure styles are missing"
    )


# --- built-HTML guards (need the real `jekyll build`, no browser) -----------


def _post_content_images(built_site):
    """(page, img_tag) for every image inside a `.post-content` block."""
    found = []
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        for block in re.finditer(
            r'<div class="post-content[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S
        ):
            for match in HTML_IMG_RE.finditer(block.group(1)):
                found.append((path, block.group(1), match.group(0)))
    return found


def test_built_post_images_have_intrinsic_dimensions(built_site):
    images = _post_content_images(built_site)
    assert images, "the built site has no post-content images to judge"
    problems = [
        f"{page.relative_to(built_site)}: {tag[:100]}"
        for page, _, tag in images
        if not (re.search(r'width="(\d+)"', tag) and re.search(r'height="(\d+)"', tag))
    ]
    assert not problems, "built content images without width+height:\n" + "\n".join(
        problems
    )


def test_built_captions_are_figures_except_blockquote_leads(built_site):
    titled_outside_quote = []
    figures = 0
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        for block in re.finditer(
            r'<div class="post-content[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S
        ):
            body = block.group(1)
            figures += len(re.findall(r'<figure class="post-figure">', body))
            for match in re.finditer(
                r'(<blockquote>.*?</blockquote>)|(<img\b[^>]*\btitle="[^"]*"[^>]*>)',
                body,
                re.S,
            ):
                if match.group(2):
                    titled_outside_quote.append(
                        f"{path.relative_to(built_site)}: {match.group(2)[:100]}"
                    )
    assert not titled_outside_quote, (
        "captioned images outside blockquotes must be <figure> blocks:\n"
        + "\n".join(titled_outside_quote)
    )
    assert figures > 0, "no <figure class=\"post-figure\"> rendered in any post"


def test_built_list_items_contain_only_fixed_size_thumbnails(built_site):
    """List items render the #226 fixed-size thumbnail, never full originals.

    Before #226 this guard asserted list items contain no ``<img>`` at all
    (the #113 excerpt rule). Reintroducing thumbnails keeps the #113 intent —
    no full-size content image may load inside a list item — while allowing
    exactly one ``post-thumb`` image per item: the small variant (or the
    placeholder, or an external attachment URL kept inside the fixed CSS box).
    """
    problems = []
    checked = 0
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        for match in re.finditer(
            r'<ul class="post-list">(.*?)</ul>', text, re.S
        ):
            for item in re.finditer(r"<li(.*?)>(.*?)</li>", match.group(1), re.S):
                attrs, body = item.group(1), item.group(2)
                checked += 1
                thumbs = re.findall(
                    r'<a class="post-thumb"[^>]*><img\b[^>]*>', body
                )
                if len(thumbs) != 1:
                    problems.append(
                        f"{path.relative_to(built_site)}: "
                        f"list item has {len(thumbs)} post-thumb images, want 1"
                    )
                    continue
                for original in re.finditer(
                    r'src="(/assets/img/(?!thumbs/|placeholder\.svg)[^"]*)"',
                    body,
                ):
                    problems.append(
                        f"{path.relative_to(built_site)}: list item loads "
                        f"full-size original {original.group(1)}"
                    )
    assert checked > 0, "no post-list items found in the built site"
    assert not problems, (
        "list items without exactly one fixed-size thumbnail:\n"
        + "\n".join(problems)
    )

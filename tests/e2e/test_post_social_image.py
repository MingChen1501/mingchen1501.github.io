"""Post social image + structured data (#256).

jekyll-seo-tag already renders a complete `BlogPosting` JSON-LD block and the
`og:image` / `twitter:image` tags from `page.image` — but no post declared
`image:` front matter, so image-bearing posts emitted no `image` in JSON-LD
and no `og:image` (ineligible for Article rich results), while the list
thumbnails (`_includes/post-thumbnail.html`) resolved per-post images through
their own `thumbnail` -> `image` -> first-body-image chain.

What #256 changed (front matter only, no layout/SEO-template change — a
second hand-written `BlogPosting` block would duplicate seo-tag's graph and
produce conflicting entities):

- every published post whose body embeds a local `/assets/img/` image (or
  that declared `thumbnail:`) now declares `image:` with the root-relative
  path of its representative image (the former `thumbnail`, else the first
  body image), in both languages of each pair;
- image-less posts declare nothing: seo-tag then omits `og:image` /
  `twitter:image` and the JSON-LD `image` key entirely (no broken tags).

Guarded here:

- (static) every published post with a local body image declares `image:`;
  every declared `image:` is root-relative, points at an existing file under
  `assets/img/`, and that file stays within the 500KB per-file
  `script/check-images` budget;
- (build) every image-bearing post page emits exactly one JSON-LD block, it
  parses, it is a `BlogPosting` carrying headline/description/datePublished/
  author/`image`/`mainEntityOfPage`, and `image` + `og:image` + `twitter:image`
  are identical absolute URLs resolving to a built file;
- (build) image-less post pages emit no `og:image` / `twitter:image` (and no
  empty `content=""`), their JSON-LD carries no `image` key, and
  `twitter:card` stays `summary`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://mingchen.id.vn"
IMAGE_BUDGET_BYTES = 500 * 1024

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
LOCAL_IMAGE_RE = re.compile(r"/assets/img/[^\s)\"']+")


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _body(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return _read(path)[match.end():] if match else _read(path)


def _value(block, key):
    match = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", block, re.M)
    if not match:
        return None
    value = match.group(1)
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _published_posts(posts_dir):
    return sorted(
        p for p in posts_dir.glob("*.md")
        if "published: false" not in _read(p)
    )


def _local_body_images(path):
    """Local `/assets/img/` files referenced by the post body."""
    return sorted(set(LOCAL_IMAGE_RE.findall(_body(path))))


def _post_url(path):
    """Built URL of a published post source."""
    if path.parent == REPO_ROOT / "_posts":
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        return f"/{path.stem[:10].replace('-', '/')}/{slug}.html"
    date = _value(_front_matter(path), "date") or ""
    return f"/vi/{date.replace('-', '/')}/{path.stem}.html"


def _built_file(built_site, url):
    assert url.startswith(SITE_URL), f"expected absolute site URL: {url}"
    return built_site / url[len(SITE_URL):].lstrip("/")


def _json_ld_blocks(html):
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    parsed = []
    for block in blocks:
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError:
            pytest.fail(f"JSON-LD block does not parse as JSON: {block[:200]}")
    return parsed


def _meta_content(html, attr, name):
    match = re.search(
        rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', html
    )
    return match.group(1) if match else None


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_posts_with_local_images_declare_image():
    """The `thumbnail` -> `image` -> first-body-image chain is materialized
    as `image:` front matter so jekyll-seo-tag can emit it."""
    missing = []
    for posts_dir in (REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"):
        for path in _published_posts(posts_dir):
            front_matter = _front_matter(path)
            if _value(front_matter, "image"):
                continue
            if _local_body_images(path) or _value(front_matter, "thumbnail"):
                missing.append(str(path.relative_to(REPO_ROOT)))
    assert not missing, (
        "posts with local images must declare `image:` front matter: "
        + ", ".join(missing)
    )


@pytest.mark.static
def test_declared_images_exist_and_fit_budget():
    for posts_dir in (REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"):
        for path in _published_posts(posts_dir):
            image = _value(_front_matter(path), "image")
            if not image:
                continue
            assert image.startswith("/assets/img/"), (
                f"{path.name}: `image:` must be a root-relative local path, "
                f"got {image!r}"
            )
            target = REPO_ROOT / image.lstrip("/")
            assert target.is_file(), (
                f"{path.name}: `image:` points at missing file {image}"
            )
            size = target.stat().st_size
            assert size <= IMAGE_BUDGET_BYTES, (
                f"{image} is {size} bytes, over the 500KB per-file budget"
            )


# --- build guards (need Ruby; no browser) -----------------------------------


def _image_posts():
    return [
        p for d in ("_posts", "_vi_posts")
        for p in _published_posts(REPO_ROOT / d)
        if _value(_front_matter(p), "image")
    ]


def _imageless_posts():
    return [
        p for d in ("_posts", "_vi_posts")
        for p in _published_posts(REPO_ROOT / d)
        if not _value(_front_matter(p), "image")
    ]


def test_image_posts_emit_single_complete_blog_posting(built_site):
    """One EN + every VI image-bearing post: exactly one `BlogPosting`
    JSON-LD block with `image`, matching absolute `og:image` /
    `twitter:image` that resolve to a built file."""
    posts = _image_posts()
    assert posts, "no image-bearing posts found; the guard measures nothing"
    seen_langs = set()
    for path in posts:
        html = _built_file(built_site, f"{SITE_URL}{_post_url(path)}").read_text(
            encoding="utf-8"
        )
        blocks = _json_ld_blocks(html)
        assert len(blocks) == 1, (
            f"{path.name}: expected exactly one JSON-LD block, "
            f"found {len(blocks)}"
        )
        data = blocks[0]
        assert data.get("@type") == "BlogPosting", (
            f"{path.name}: JSON-LD @type is {data.get('@type')!r}"
        )
        for key in (
            "headline", "description", "datePublished", "author",
            "image", "mainEntityOfPage",
        ):
            assert data.get(key), f"{path.name}: JSON-LD is missing {key!r}"
        assert data["mainEntityOfPage"].get("@id", "").startswith(SITE_URL)

        og_image = _meta_content(html, "property", "og:image")
        twitter_image = _meta_content(html, "name", "twitter:image")
        assert og_image, f"{path.name}: missing og:image"
        assert twitter_image, f"{path.name}: missing twitter:image"
        assert og_image == twitter_image == data["image"], (
            f"{path.name}: og:image ({og_image}) / twitter:image "
            f"({twitter_image}) / JSON-LD image ({data['image']}) disagree"
        )
        assert og_image.startswith(SITE_URL), (
            f"{path.name}: og:image must be absolute: {og_image}"
        )
        assert _built_file(built_site, og_image).is_file(), (
            f"{path.name}: og:image points at {og_image}, "
            "which is not in the build"
        )
        seen_langs.add(_value(_front_matter(path), "lang") or "en")
    assert {"en", "vi"} <= seen_langs, (
        f"the guard never checked both languages: {seen_langs}"
    )


def test_imageless_posts_emit_no_broken_image_tags(built_site):
    """Image-less posts stay tag-free: no `og:image` / `twitter:image`
    (empty or otherwise), no JSON-LD `image` key, `summary` card."""
    posts = _imageless_posts()
    if not posts:
        pytest.skip(
            "no image-less posts: every published post declares `image:` (#310)"
        )
    for path in posts:
        html = _built_file(built_site, f"{SITE_URL}{_post_url(path)}").read_text(
            encoding="utf-8"
        )
        assert _meta_content(html, "property", "og:image") is None, (
            f"{path.name}: image-less post must not emit og:image"
        )
        assert _meta_content(html, "name", "twitter:image") is None, (
            f"{path.name}: image-less post must not emit twitter:image"
        )
        assert 'content=""' not in html, (
            f"{path.name}: image-less post emits an empty meta content"
        )
        for data in _json_ld_blocks(html):
            if data.get("@type") == "BlogPosting":
                assert "image" not in data, (
                    f"{path.name}: image-less post JSON-LD must not "
                    "carry an image key"
                )
        assert _meta_content(html, "name", "twitter:card") == "summary", (
            f"{path.name}: image-less post twitter:card must be summary"
        )

"""Guards for #309 (i18n a11y): English content images carry meaningful
alt text; purely decorative repeats are explicitly marked.

Background: #147 gave the Vietnamese posts descriptive alts and marked
decorative repeats ``aria-hidden`` but left English untouched. The English
posts shipped the exact patterns #147 removed: ``Step 1`` … ``Step 5`` step
labels, one-word CamelCase file-stem alts (``Desktop``, ``HairCut``, …),
and duplicated lead images glued to the opening blockquotes that repeat
prose (or a photo shown again below).

What #309 changed (``_posts/`` only; no template, URL, or image-file
changes):

- every informative EN image has an English alt describing what the photo
  shows (one clause, no ``image``/``picture``/``photo`` prefix), mirroring
  the Vietnamese wording in translation; the blockquote lead repeats and
  the closing greeting card got descriptive alts too, because the CI
  ``#87`` guard forbids empty alt in ``_posts/`` entirely;
- genuinely decorative images (blockquote lead repeats, the closing
  greeting card whose text duplicates the adjacent prose) would keep
  ``![](...)`` (empty alt) and carry ``aria-hidden="true"`` in the
  kramdown IAL so the built ``<img>`` is hidden from assistive
  technology — but no such image remains in ``_posts/`` (see above), so
  every EN image currently carries a meaningful alt;
- no image was removed and no URL/filename changed.

Guarded here (same rules as ``test_vi_alt_text.py`` for ``_vi_posts/``):

- (static) every local markdown image in ``_posts/`` has either a
  meaningful alt (at least two words, at least 10 characters, no
  ``image``/``picture``/``photo`` prefix, not a single generic token, not
  the file stem) or — for decorative repeats — an empty alt with
  ``aria-hidden="true"``;
- (static) raw-HTML content images (``<figure>``/``<img>`` blocks) keep a
  meaningful non-empty alt, or carry ``aria-hidden``/``role="presentation"``
  when decorative;
- (built HTML) every ``.post-content`` image on the English post pages has
  an ``alt`` attribute, and every empty-alt image is ``aria-hidden``.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EN_POSTS_DIR = REPO_ROOT / "_posts"

MD_IMG_RE = re.compile(r'!\[([^\]]*)\]\((/assets/[^\s)]+)(?:\s+"([^"]*)")?\)')
HTML_IMG_RE = re.compile(r'<img\b[^>]*>', re.S)
EN_POST_PAGE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}/.+\.html$")

MIN_ALT_CHARS = 10
MIN_ALT_WORDS = 2
# Alt must describe the image, not announce it — screen readers already do.
ALT_PREFIX_RE = re.compile(r'^(image|picture|photo)\b', re.I)
# Single tokens that say nothing about the photo (step labels, file stems…).
GENERIC_ALT_RE = re.compile(r'^(step\s?\d|desktop|greeting|greetings)$', re.I)


def _read(path):
    return path.read_text(encoding="utf-8")


def _markdown_images():
    """(path, line_no, line, match) for every local markdown image in EN posts."""
    found = []
    for md in sorted(EN_POSTS_DIR.glob("*.md")):
        for lineno, line in enumerate(_read(md).splitlines(), start=1):
            for match in MD_IMG_RE.finditer(line):
                found.append((md, lineno, line, match))
    return found


def _file_stem(src):
    return Path(src).stem.lower()


def _alt_problem(md_name, lineno, src, alt):
    """None when the alt is meaningful; a message otherwise."""
    text = alt.strip()
    if len(text) < MIN_ALT_CHARS:
        return (
            f"{md_name}:{lineno}: alt too short ({len(text)} chars, "
            f"need >= {MIN_ALT_CHARS}): [{alt}]({src})"
        )
    if len(text.split()) < MIN_ALT_WORDS:
        return (
            f"{md_name}:{lineno}: single-word alt says nothing about the "
            f"photo: [{alt}]({src})"
        )
    if ALT_PREFIX_RE.match(text):
        return (
            f"{md_name}:{lineno}: alt must not start with an "
            f"'image/picture/photo' prefix: [{alt}]({src})"
        )
    squashed = re.sub(r"[\W_]+", "", text.lower())
    if GENERIC_ALT_RE.match(text.strip()) or GENERIC_ALT_RE.match(squashed):
        return f"{md_name}:{lineno}: generic alt text: [{alt}]({src})"
    if squashed == re.sub(r"[\W_]+", "", _file_stem(src)):
        return (
            f"{md_name}:{lineno}: alt only repeats the file name: "
            f"[{alt}]({src})"
        )
    return None


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_en_informative_images_have_meaningful_alt():
    images = _markdown_images()
    assert images, "no local content images found in _posts/"
    problems = []
    for md, lineno, line, match in images:
        alt, src = match.group(1), match.group(2)
        if alt.strip():
            problem = _alt_problem(md.name, lineno, src, alt)
            if problem:
                problems.append(problem)
            continue
        # Empty alt is reserved for decorative repeats and must say so.
        tail = line[match.end():].lstrip()
        if 'aria-hidden="true"' not in tail and "role=\"presentation\"" not in tail:
            problems.append(
                f"{md.name}:{lineno}: empty alt without aria-hidden/role — "
                f"decorative images must be marked, informative ones described: "
                f"({src})"
            )
    assert not problems, "English images with missing/generic alt:\n" + "\n".join(
        problems
    )


@pytest.mark.static
def test_en_raw_html_images_keep_meaningful_alt():
    problems = []
    for md in sorted(EN_POSTS_DIR.glob("*.md")):
        for match in HTML_IMG_RE.finditer(_read(md)):
            tag = match.group(0)
            if "/assets/" not in tag:
                continue
            alt = re.search(r'alt="([^"]*)"', tag)
            if alt is None or not alt.group(1).strip():
                if 'aria-hidden="true"' not in tag and 'role="presentation"' not in tag:
                    problems.append(
                        f"{md.name}: raw HTML image without meaningful alt: {tag[:80]}"
                    )
                continue
            if len(alt.group(1).strip().split()) < MIN_ALT_WORDS:
                problems.append(
                    f"{md.name}: single-word raw HTML alt: {tag[:80]}"
                )
    assert not problems, "\n".join(problems)


# --- built-HTML guards (need the real `jekyll build`, no browser) -----------


def _en_post_content_images(built_site):
    """(page, img_tag) for images inside `.post-content` on English posts."""
    found = []
    for path in sorted(built_site.rglob("*.html")):
        rel = path.relative_to(built_site).as_posix()
        if not EN_POST_PAGE_RE.match(rel):
            continue
        text = _read(path)
        for block in re.finditer(
            r'<div class="post-content[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S
        ):
            for match in HTML_IMG_RE.finditer(block.group(1)):
                found.append((rel, match.group(0)))
    return found


def test_built_en_post_images_expose_alt_or_hide_decorative(built_site):
    images = _en_post_content_images(built_site)
    assert images, "the built English posts have no post-content images to judge"
    problems = []
    for page, tag in images:
        alt = re.search(r'alt="([^"]*)"', tag)
        if alt is None:
            problems.append(f"{page}: image without alt: {tag[:100]}")
        elif not alt.group(1).strip() and 'aria-hidden="true"' not in tag:
            problems.append(f"{page}: empty alt without aria-hidden: {tag[:100]}")
    assert not problems, "built English images failing the alt guard:\n" + "\n".join(
        problems
    )

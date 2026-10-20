"""Static + built guard for shipped first-party JS/CSS byte budgets (#267).

Recent work shrank shipped bytes with no ceiling to keep them small: #253
gated the post-only scripts (non-post pages went from 9 to 7 sub-footer
scripts), #318 gated copy-code and lightbox the same way (9 to 5), and
#254 replaced the Font Awesome CDN with inline SVGs. With no
budget, any new global script silently regrows every page: ``test_post_only_js.py``
pins script *count* per page kind but not *bytes*, and ``test_css_parity.py``
pins an exact SHA of the built CSS instead of a budget. #275 then split the
Rouge token rules out of the main stylesheet into the conditional
``syntax.css`` companion (code pages only), so CSS has two ceilings now.

Guarded here, with the ceilings in ``script/asset-budget.sh`` (single source
of truth; the tests below pin the documented policy values, so a bump touches
both files deliberately):

- the budget file holds the five documented ceilings (static);
- the pinned script sets match the templates exactly: any added, removed,
  or relocated tag fails statically, even inside the byte headroom, and
  the post-only scripts stay gated to post pages (the #253 win, locked
  statically from the templates);
- total first-party JS bytes actually referenced per page kind, plus built
  CSS bytes, stay under their ceilings — statically from the source files
  (production worst case for posts, which alone render the comments sync
  script) and again from the real build output (needs Ruby, no browser);
- the head links the main stylesheet unconditionally plus the syntax
  companion only inside its Rouge-output conditional, both with the same
  build token, so no third global sheet can appear without tripping a
  static guard.

Page kinds follow the ``test_post_only_js.py`` split: home, post, tag,
about/portfolio (``page`` layout), search. Failure messages name the
measured bytes and the budget file.
"""

import re
from pathlib import Path

import pytest

import test_post_only_js

REPO_ROOT = Path(__file__).resolve().parents[2]
BUDGET_FILE = REPO_ROOT / "script" / "asset-budget.sh"
JS_DIR = REPO_ROOT / "assets" / "js"
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
SEARCH_INCLUDE = REPO_ROOT / "_includes" / "search.html"
COMMENTS_INCLUDE = REPO_ROOT / "_includes" / "comments.html"
SUB_FOOTER = test_post_only_js.SUB_FOOTER

# Documented policy (#267): ceilings sit ~10% above the 2026-10-20 measured
# totals (see script/asset-budget.sh for the per-kind measurements). Bump a
# ceiling only with an intentional change, in both files at once.
# (#275 re-measured after the syntax split: the main sheet dropped to
# ~45.1KB, the conditional companion to ~17.5KB.)
EXPECTED_BUDGET = {
    "MAX_JS_PAGE_BYTES": 23552,
    "MAX_JS_POST_BYTES": 32768,
    "MAX_JS_SEARCH_BYTES": 32256,
    "MAX_CSS_BYTES": 50176,
    "MAX_SYNTAX_CSS_BYTES": 19456,
}

SEARCH_PATH = "/assets/js/search.js"
GISCUS_THEME_PATH = "/assets/js/giscus-theme.js"
STYLESHEET_PATH = "/assets/css/style.css"

# Representative built pages per kind (both languages where the kind ships
# in both). The tag representative mirrors test_post_only_js.py: the tag
# index plus the first tag page.
EN_POST_REL = test_post_only_js.EN_POST_REL
VI_POST_REL = test_post_only_js.VI_POST_REL

#: Unique first-party scripts each page kind may reference. Post is the
#: production worst case: dev builds skip the comments include
#: (``comments.dev: false``), so the built-dev assertion below expects the
#: nine-file set while the static byte assertion covers all ten.
EXPECTED_SETS = {
    "page": frozenset(test_post_only_js.ALWAYS_LOADED),
    "post": frozenset(
        (*test_post_only_js.ALWAYS_LOADED,
         *test_post_only_js.POST_ONLY,
         GISCUS_THEME_PATH)
    ),
    "search": frozenset((*test_post_only_js.ALWAYS_LOADED, SEARCH_PATH)),
}


def _read_budget():
    values = {}
    for line in BUDGET_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(MAX_[A-Z_]+)=(\d+)\s*$", line.strip())
        if match:
            values[match.group(1)] = int(match.group(2))
    return values


def _source_bytes(path):
    """Shipped bytes of a first-party script (Jekyll copies assets verbatim)."""
    name = path.rsplit("/", 1)[-1]
    return (JS_DIR / name).stat().st_size


def _set_bytes(paths):
    return sum(_source_bytes(path) for path in paths)


def _template_scripts(include_path):
    """First-party ``/assets/js/`` references in a template include."""
    text = include_path.read_text(encoding="utf-8")
    return re.findall(r'(?:href|src)="(/assets/js/[^"?]+)', text)


def _sub_footer_sets():
    """``(unconditional, post-gated)`` first-party script sets in order."""
    text = SUB_FOOTER.read_text(encoding="utf-8")
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", text)
    assert gate, "the post-layout gate in sub-footer.html is gone (#253)"
    head = text[:gate.start()]
    gated = text[gate.end():text.index("endif", gate.end())]
    refs = r'(?:href|src)="(/assets/js/[^"?]+)'
    return (re.findall(refs, head), re.findall(refs, gated))


def _built_scripts(html):
    """Unique first-party script paths referenced by a built page."""
    return set(
        re.findall(r'<script src="(/assets/js/[^"?]+)(?:\?v=[^"]*)?"[^>]*>', html)
    )


def _budget_label(key):
    return f"{BUDGET_FILE.relative_to(REPO_ROOT)}:{key}={EXPECTED_BUDGET[key]}"


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_budget_file_matches_documented_policy():
    assert BUDGET_FILE.is_file(), "script/asset-budget.sh is missing"
    assert _read_budget() == EXPECTED_BUDGET, (
        "script/asset-budget.sh drifted from the documented policy: "
        "bump ceilings only intentionally, in both files at once (#267)"
    )


@pytest.mark.static
def test_pinned_script_sets_match_the_templates():
    """Any added, removed, or relocated script tag fails here statically —
    even inside the byte headroom — so growth is always a deliberate,
    reviewed bump of the pinned sets and ceilings below (#267)."""
    unconditional, gated = _sub_footer_sets()
    assert unconditional == list(test_post_only_js.ALWAYS_LOADED), (
        "the shared sub-footer script set changed: every page would ship "
        f"the difference ({unconditional}) (#267)"
    )
    assert gated == list(test_post_only_js.POST_ONLY), (
        f"the post-gated script set changed: {gated} (#253, #267, #318)"
    )
    search_refs = _template_scripts(SEARCH_INCLUDE)
    assert search_refs == ["/assets/js/site-utils.js", SEARCH_PATH], (
        f"_includes/search.html must reference only its helper + search.js, "
        f"got {search_refs} (#267)"
    )
    comments_refs = _template_scripts(COMMENTS_INCLUDE)
    assert comments_refs == [GISCUS_THEME_PATH], (
        f"_includes/comments.html must reference only {GISCUS_THEME_PATH}, "
        f"got {comments_refs} (#267)"
    )


@pytest.mark.static
def test_non_post_kinds_exclude_the_post_only_scripts():
    """The #253 win, extended by #318, locked from the templates: all four
    post-only scripts ship on post pages only, so no non-post kind can
    regain their weight."""
    unconditional, gated = _sub_footer_sets()
    for path in test_post_only_js.POST_ONLY:
        assert path not in unconditional, (
            f"{path} leaked out of the post-layout gate: non-post pages "
            f"would ship it again (#253, #318)"
        )
        assert path in gated, (
            f"{path} is no longer inside the post-layout gate (#253, #318)"
        )
    for kind in ("page", "search"):
        for path in test_post_only_js.POST_ONLY:
            assert path not in EXPECTED_SETS[kind]


@pytest.mark.static
def test_js_bytes_per_page_kind_within_budget():
    """Static byte ceilings from the sets the templates actually reference
    (production worst case for posts, which alone render the comments
    sync script)."""
    unconditional, gated = _sub_footer_sets()
    search_refs = set(_template_scripts(SEARCH_INCLUDE))
    comments_refs = set(_template_scripts(COMMENTS_INCLUDE))
    kinds = {
        "page": ("MAX_JS_PAGE_BYTES", set(unconditional)),
        "post": (
            "MAX_JS_POST_BYTES",
            set(unconditional) | set(gated) | comments_refs,
        ),
        "search": (
            "MAX_JS_SEARCH_BYTES",
            set(unconditional) | search_refs,
        ),
    }
    budget = _read_budget()
    for kind, (key, paths) in kinds.items():
        total = _set_bytes(paths)
        assert total <= budget[key], (
            f"{kind} pages ship {total} bytes of first-party JS "
            f"({len(paths)} files: {sorted(paths)}), over "
            f"{_budget_label(key)} (#267)"
        )


@pytest.mark.static
def test_head_links_the_expected_stylesheets():
    """The main sheet is global; the syntax sheet is conditional (#275).

    #267 pinned a single global sheet; #275 adds the Rouge companion, so
    the guard now pins the pair: exactly one unconditional first-party
    stylesheet (the main one every page needs) plus the syntax sheet gated
    on Rouge output, both with the same build token. A third sheet — or an
    unconditional syntax sheet — trips this guard.
    """
    text = HEAD_INCLUDE.read_text(encoding="utf-8")
    links = re.findall(r"(/assets/css/[^\"'?]+)", text)
    assert links == [STYLESHEET_PATH, "/assets/css/syntax.css"], (
        f"expected the main sheet plus the conditional syntax companion, "
        f"got {links} (#267, #275)"
    )
    gate = re.search(r"\{%-?\s*if content contains ", text)
    assert gate, "the syntax stylesheet must stay gated on page content (#275)"
    assert text.index("/assets/css/syntax.css") > gate.start(), (
        "the syntax stylesheet must live inside the content gate (#275)"
    )
    head_before_gate = text[:gate.start()]
    assert STYLESHEET_PATH in head_before_gate, (
        "the main stylesheet must stay unconditional: every page needs it"
    )


# --- built guards (need Ruby; no browser) ----------------------------------


def _representative_pages(built_site):
    """One built page per kind, both languages where shipped."""
    pages = {
        "page": ["index.html", "vi/index.html", "tags/index.html",
                 "about/index.html", "portfolio/index.html"],
        "post": [EN_POST_REL.as_posix(), VI_POST_REL.as_posix()],
        "search": ["search/index.html", "vi/tim-kiem/index.html"],
    }
    tag_pages = sorted(built_site.glob("tags/*/index.html"))
    assert tag_pages, "no tag pages in the build"
    pages["page"].append(tag_pages[0].relative_to(built_site).as_posix())
    for kind, rels in pages.items():
        for rel in rels:
            assert (built_site / rel).is_file(), f"{rel} is missing"
    return pages


def test_built_pages_reference_only_their_budgeted_scripts(built_site):
    """Real output check: each kind references exactly its budgeted set
    (non-post pages link none of the post-only scripts) and weighs under it."""
    budget = _read_budget()
    keys = {
        "page": "MAX_JS_PAGE_BYTES",
        "post": "MAX_JS_POST_BYTES",
        "search": "MAX_JS_SEARCH_BYTES",
    }
    for kind, rels in _representative_pages(built_site).items():
        # Dev builds skip the comments include, so dev post pages carry
        # the nine-file set; the static guard above already covers the
        # production tenth file in the same ceiling.
        expected = set(EXPECTED_SETS[kind])
        if kind == "post":
            expected.discard(GISCUS_THEME_PATH)
        for rel in rels:
            html = (built_site / rel).read_text(encoding="utf-8")
            found = _built_scripts(html)
            assert found == expected, (
                f"{rel} references {sorted(found)}, expected "
                f"{sorted(expected)} (#267)"
            )
            total = sum(
                (built_site / path.lstrip("/")).stat().st_size
                for path in found
            )
            key = keys[kind]
            assert total <= budget[key], (
                f"{rel} ships {total} bytes of first-party JS, over "
                f"{_budget_label(key)} (#267)"
            )


def test_built_css_within_budget(built_site):
    css = built_site / "assets" / "css" / "style.css"
    assert css.is_file(), "the build emitted no assets/css/style.css"
    total = css.stat().st_size
    ceiling = _read_budget()["MAX_CSS_BYTES"]
    assert total <= ceiling, (
        f"built style.css is {total} bytes, over "
        f"{_budget_label('MAX_CSS_BYTES')} (#267)"
    )


def test_built_syntax_css_within_budget(built_site):
    """The conditional companion sheet stays small too (#275)."""
    css = built_site / "assets" / "css" / "syntax.css"
    assert css.is_file(), "the build emitted no assets/css/syntax.css"
    total = css.stat().st_size
    ceiling = _read_budget()["MAX_SYNTAX_CSS_BYTES"]
    assert total <= ceiling, (
        f"built syntax.css is {total} bytes, over "
        f"{_budget_label('MAX_SYNTAX_CSS_BYTES')} (#275)"
    )

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

SITE_DIR = Path("_site")


def test_robots_txt_exists_and_has_required_content(tmp_path):
    """robots.txt must exist in _site with required directives."""
    robots_path = SITE_DIR / "robots.txt"
    assert robots_path.exists(), "robots.txt must exist in _site"
    
    content = robots_path.read_text(encoding="utf-8")
    assert "User-agent:" in content, "robots.txt must contain User-agent:"
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=yes" in content
    assert "Sitemap: https://mingchen.id.vn/sitemap.xml" in content


def test_sitemap_xml_parses_and_urls_match_site_files():
    """sitemap.xml parses as XML and all locs correspond to files in _site."""
    sitemap_path = SITE_DIR / "sitemap.xml"
    assert sitemap_path.exists(), "sitemap.xml must exist in _site"
    
    content = sitemap_path.read_text(encoding="utf-8")
    # Parse XML
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        pytest.fail("sitemap.xml does not parse as valid XML")
    
    # Find all loc elements (handle namespaces)
    locs = []
    for url in root.findall(".//{*}loc"):
        locs.append(url.text)
    # Fallback without namespace if needed
    if not locs:
        for url in root.findall(".//loc"):
            locs.append(url.text)
    
    assert locs, "sitemap.xml must contain at least one loc element"
    
    # Check no excluded files
    for loc in locs:
        assert "404.html" not in loc
        assert "feed.xml" not in loc
        assert "sitemap.xml" not in loc
        assert "llms.txt" not in loc
    
    # Check each loc resolves to a file in _site
    for loc in locs:
        # Extract path from URL
        if loc.startswith("https://mingchen.id.vn"):
            path = loc[len("https://mingchen.id.vn"):]
        elif loc.startswith("http://mingchen.id.vn"):
            path = loc[len("http://mingchen.id.vn"):]
        else:
            # Assume it's a path
            path = loc
        
        if path == "" or path == "/":
            file_path = SITE_DIR / "index.html"
        else:
            # Remove leading/trailing slashes
            path_clean = path.lstrip("/")
            if path_clean.endswith("/"):
                file_path = SITE_DIR / path_clean / "index.html"
            else:
                file_path = SITE_DIR / path_clean
                # If it's not a file with extension, try index.html
                if file_path.suffix == "":
                    file_path = SITE_DIR / path_clean / "index.html"
        
        assert file_path.exists(), f"sitemap loc {loc} should correspond to {file_path}"


def test_sitemap_post_count_matches():
    """Number of post URLs in sitemap equals number of published posts."""
    sitemap_path = SITE_DIR / "sitemap.xml"
    assert sitemap_path.exists()
    
    content = sitemap_path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        pytest.fail("sitemap.xml does not parse as valid XML")
    
    # Count post URLs
    post_locs = []
    for loc in root.findall(".//{*}loc"):
        loc_text = loc.text or ""
        if "/20" in loc_text and loc_text.count("/") >= 4:  # Posts have date in URL like /2026/01/01/...
            # Exclude index pages
            if not loc_text.endswith("/page") and "page" not in loc_text.split("/")[-2] if loc_text.endswith("/") else True:
                post_locs.append(loc_text)
    
    # Fallback
    if not any("/20" in str(l.text) for l in root.findall(".//loc") if l.text):
        for loc in root.findall(".//loc"):
            loc_text = loc.text or ""
            if loc_text and "/20" in loc_text:
                post_locs.append(loc_text)
    
    # Count actual published posts in _posts
    posts_dir = Path("_posts")
    published_posts = []
    if posts_dir.exists():
        for p in posts_dir.glob("*.md"):
            try:
                content = p.read_text(encoding="utf-8")
                # Simple check for published: false
                if "published: false" in content:
                    continue
                published_posts.append(p)
            except Exception:
                published_posts.append(p)
    post_files = published_posts
    
    assert len(post_locs) == len(post_files), f"sitemap has {len(post_locs)} post URLs but there are {len(post_files)} published posts"


def test_llms_txt_exists_and_urls_resolve():
    """llms.txt exists and every URL-like token resolves to a file in _site."""
    llms_path = SITE_DIR / "llms.txt"
    assert llms_path.exists(), "llms.txt must exist in _site"
    
    content = llms_path.read_text(encoding="utf-8")
    # Look for URLs
    import re
    urls = re.findall(r"https?://[^\s:]+", content)
    
    assert urls, "llms.txt should contain URLs"
    
    for url in urls:
        # Clean trailing punctuation
        url_clean = url.rstrip(".,)")
        if url_clean.startswith("https://mingchen.id.vn"):
            path = url_clean[len("https://mingchen.id.vn"):]
        elif url_clean.startswith("http://mingchen.id.vn"):
            path = url_clean[len("http://mingchen.id.vn"):]
        else:
            continue  # Skip non-site URLs
        
        if path == "" or path == "/":
            file_path = SITE_DIR / "index.html"
        else:
            path_clean = path.lstrip("/")
            if path_clean.endswith("/"):
                file_path = SITE_DIR / path_clean / "index.html"
            else:
                file_path = SITE_DIR / path_clean
                if file_path.suffix == "":
                    file_path = SITE_DIR / path_clean / "index.html"
        
        assert file_path.exists(), f"llms.txt URL {url_clean} should resolve to {file_path}"

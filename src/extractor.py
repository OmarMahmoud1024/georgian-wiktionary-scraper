"""
Per-page field extraction.

Wiktionary entries don't follow one consistent template, so every field
lookup here is individually defensive: a section that isn't present on a
given page just yields null/empty rather than raising and killing the run.
This mirrors the real constraint the original scraper was built under -
"one of the websites with no constant structure, so there might be some
more things to modify" as new edge cases turned up during the crawl.
"""
import logging
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from . import config

log = logging.getLogger("extractor")

_SOURCE_HEADERS = {"წყარო", "წყაროები", "references", "sources"}
_CATEGORY_LINK_PREFIX = "კატეგორია:"


def fetch_soup(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        resp = session.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
        return None
    return BeautifulSoup(resp.text, "lxml")


def _extract_definition_text(soup: BeautifulSoup) -> Optional[str]:
    """The definition usually lives in the first content <ol>/<p> under the
    main heading, but not every page uses the same wrapper - fall back
    through a few likely containers before giving up."""
    content = soup.select_one("#mw-content-text .mw-parser-output")
    if not content:
        return None

    ordered_list = content.find("ol")
    if ordered_list and ordered_list.get_text(strip=True):
        return ordered_list.get_text(" ", strip=True)

    first_paragraph = content.find("p")
    if first_paragraph and first_paragraph.get_text(strip=True):
        return first_paragraph.get_text(" ", strip=True)

    return None


def _extract_sources(soup: BeautifulSoup) -> List[str]:
    """Sources aren't always their own section - when a page has a heading
    matching a known "sources/references" label, its list items are pulled;
    otherwise this returns an empty list rather than guessing."""
    sources: List[str] = []
    for heading in soup.select("#mw-content-text h2, #mw-content-text h3"):
        label = heading.get_text(strip=True).lower()
        if not any(marker in label for marker in _SOURCE_HEADERS):
            continue
        sibling = heading.find_next_sibling()
        while sibling and sibling.name not in ("h2", "h3"):
            if sibling.name in ("ul", "ol"):
                sources.extend(
                    li.get_text(" ", strip=True) for li in sibling.find_all("li")
                )
            sibling = sibling.find_next_sibling()
    return sources


def _extract_categories(soup: BeautifulSoup) -> List[str]:
    """Category tags live in a dedicated footer div on most pages, but a
    minority of entries expose them only as inline links - both are
    checked and merged, deduplicated."""
    categories = set()

    cat_div = soup.select_one("#catlinks")
    if cat_div:
        for link in cat_div.select("a"):
            text = link.get_text(strip=True)
            if text:
                categories.add(text)

    for link in soup.select(f"a[href*='{_CATEGORY_LINK_PREFIX}']"):
        text = link.get_text(strip=True)
        if text.startswith(_CATEGORY_LINK_PREFIX):
            # Inline wikitext links render as "კატეგორია:Name", while the
            # #catlinks footer already shows just "Name" - strip the prefix
            # here too so both extraction paths agree on the same format.
            text = text[len(_CATEGORY_LINK_PREFIX):].strip()
        if text:
            categories.add(text)

    return sorted(categories)


def extract_entry(title: str, url: str, session: requests.Session) -> Optional[dict]:
    """Consolidated single-pass extraction: word, definition text, sources,
    and categories are all pulled from one page load, replacing what used
    to be two separate scripts/passes over the same pages."""
    soup = fetch_soup(url, session)
    if soup is None:
        return None

    text = _extract_definition_text(soup)
    if text is None:
        log.info("No definition text found for '%s' - skipping malformed page", title)
        return None

    return {
        "word": title,
        "text": text,
        "sources": _extract_sources(soup),
        "categories": _extract_categories(soup),
        "url": url,
    }

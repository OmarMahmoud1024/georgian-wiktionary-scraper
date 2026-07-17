"""
Full pipeline integration test: runs the real page_list.py + extractor.py
against a local server serving fixtures that reproduce the actual
inconsistent page structures this scraper has to handle (see
fixtures/page_*.html - one page has a full sources+categories section,
one has only a bare <p> definition, one has categories only as inline
links with no #catlinks div at all).
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from src import config
from src.page_list import iter_category_members
from src.extractor import extract_entry
from tests.local_site import LocalSite


def test_full_pipeline_against_local_fixtures():
    with LocalSite() as site:
        # Point the scraper at the local fixture server instead of the
        # real site for this test run.
        config.BASE_URL = site.base_url
        config.API_URL = site.base_url + "/w/api.php"

        titles = list(iter_category_members("test-category"))
        assert titles == ["სახლი", "წიგნი", "მზე"], (
            "Pagination across 2 API pages should yield all 3 words, in order"
        )

        session = requests.Session()
        entries = []
        for title in titles:
            url = f"{config.BASE_URL}/wiki/{title.replace(' ', '_')}"
            entry = extract_entry(title, url, session)
            entries.append(entry)

        # Word 1: full structure - definition, sources, and catlinks-based categories
        house = entries[0]
        assert house["word"] == "სახლი"
        assert "საცხოვრებელი" in house["text"]
        assert house["sources"] == ["ქართული ენციკლოპედია, ტომი 4", "საბას ლექსიკონი"]
        assert house["categories"] == ["არსებითი სახელები"]

        # Word 2: minimal structure - only a bare <p>, no sources/categories.
        # Must NOT crash, and must degrade to empty list / still capture text.
        book = entries[1]
        assert book["word"] == "წიგნი"
        assert "გამოცემა" in book["text"]
        assert book["sources"] == []
        assert book["categories"] == []

        # Word 3: categories only as inline links (no #catlinks div) -
        # must still be picked up by the inline-link fallback.
        sun = entries[2]
        assert sun["word"] == "მზე"
        assert "ვარსკვლავი" in sun["text"]
        assert sun["categories"] == ["ასტრონომია"]

        print("\nReal scraped output from local fixture run:")
        import json
        for e in entries:
            print(json.dumps(e, ensure_ascii=False))


def test_resume_skips_already_scraped_words(tmp_path):
    from src.utils import append_jsonl, already_scraped_words

    entries_file = tmp_path / "entries.jsonl"
    append_jsonl(entries_file, {"word": "სახლი", "text": "..."})
    append_jsonl(entries_file, {"word": "წიგნი", "text": "..."})

    seen = already_scraped_words(entries_file)
    assert seen == {"სახლი", "წიგნი"}


def test_resume_tolerates_truncated_last_line(tmp_path):
    """A crash mid-write can leave a truncated final JSON line - the
    resume logic should keep everything before it rather than failing."""
    from src.utils import already_scraped_words

    entries_file = tmp_path / "entries.jsonl"
    entries_file.write_text(
        '{"word": "სახლი", "text": "ok"}\n{"word": "წიგ',  # truncated
        encoding="utf-8",
    )
    seen = already_scraped_words(entries_file)
    assert seen == {"სახლი"}

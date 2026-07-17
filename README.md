# Georgian Wiktionary Structured Dictionary Scraper

A crawler that walks the Georgian-language Wiktionary (`ka.wiktionary.org`) and converts its
loosely-structured wiki markup into clean, structured JSON — one entry per word, with definitions,
etymological sources, and grammatical categories extracted as separate fields.

This project was originally built during a freelance/internship engagement building structured
datasets from public Georgian-language reference sites. It's reconstructed here (the original repo
was lost) to demonstrate the scraping and data-normalization techniques used.

## The problem

Wiktionary pages are written by many different contributors over years, so unlike a typical
database-backed site, there's no single consistent page template. Across different word entries:

- Some pages have a dedicated "sources" section, others embed sources inline in the definition text.
- Category tags (part of speech, dialect, register, etc.) are sometimes in a sidebar, sometimes in
  inline templates, and sometimes absent entirely.
- Definition text length and formatting varies wildly — from a single line to multi-sense entries
  with nested examples.

A scraper written against one page's structure breaks on the next. This needed something closer to
"extract whatever's actually there, gracefully degrade for whatever isn't" than a fixed-schema parser.

## The approach

**1. Single-pass consolidation.** An earlier version of this scraper used two separate scripts —
one that walked word listings, another that visited each word's page to pull definitions — which
duplicated a lot of navigation and page-load work. This version merges both into one pass: for each
word discovered, its `text` (definition), `sources`, and `categories` are all fetched from their
respective fields on the same page visit before moving to the next word.

**2. Defensive field extraction.** Every field lookup (`_first_text`, `_all_texts` in
`extractor.py`) is wrapped so a missing or oddly-formatted section produces `null` / an empty list,
never a crashed run. The scraper is expected to hit inconsistent pages constantly — that's treated
as the normal case, not an edge case.

**3. Everything not cleanly separable goes into `description`.** Where a page's structure doesn't
allow reliably splitting out a field on its own, that content stays in the definition/description
text rather than being force-fit into a field it doesn't really belong in. This keeps the schema
honest — a `sources` field is only ever populated when the site actually presented that as a
distinct section, avoiding a false Wiktionary-supports-this-page)

**4. Incremental JSON Lines output.** Each word is written to `data/entries.jsonl` as its own line,
immediately after being scraped — one JSON object per line — rather than accumulating an in-memory
list and writing one large JSON array at the end. A long crawl surviving a restart doesn't lose
already-scraped entries.

**5. Resumability.** On startup, the scraper reads which words are already present in
`entries.jsonl` and skips them, so re-running after an interruption continues instead of starting
over.

## Project structure

```
georgian-wiktionary-scraper/
├── src/
│   ├── config.py          # Base URL, output paths, request pacing
│   ├── page_list.py       # Discovers word entry URLs from category/index pages
│   ├── extractor.py       # Per-page field extraction (word, text, sources, categories)
│   └── utils.py           # JSONL append/resume helpers
├── main.py                # CLI entrypoint
├── requirements.txt
└── data/                  # Output: entries.jsonl (gitignored)
```

## Usage

```bash
pip install -r requirements.txt
python main.py --start-category "ლექსიკონი" --limit 5000
```

## Output schema

```json
{
  "word": "string",
  "text": "string",
  "sources": ["string", "..."],
  "categories": ["string", "..."],
  "url": "string"
}
```

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

3 tests, all passing, run against a local server (`tests/local_site.py`) that serves fixture pages
reproducing the real inconsistent structures this scraper has to handle — one word page with a full
definition + sources section + category footer, one with only a bare `<p>` and nothing else, and one
with categories exposed solely as inline links rather than the usual footer div. The full pipeline
(pagination through the category API, then per-word extraction) runs unmodified against these
fixtures end-to-end, and the real scraped output is printed as part of the test run.

This test run caught and fixed a real bug during development: the inline-category-link fallback was
including the `კატეგორია:` (“Category:”) prefix in its output while the footer-based extraction
path stripped it, so the same category could appear twice under two different-looking names
depending on which part of a page it was scraped from. Fixed in `src/extractor.py`.

## Skills demonstrated

Schema-flexible scraping of inconsistent/user-generated markup · incremental & resumable crawling ·
BeautifulSoup-based DOM navigation · defensive parsing that degrades gracefully instead of crashing.

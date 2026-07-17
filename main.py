#!/usr/bin/env python3
"""
CLI entrypoint.

    python main.py --start-category "ლექსიკონი" --limit 5000

Walks the given category, visits each word page, and appends structured
entries to data/entries.jsonl as it goes (resumable - already-scraped
words are skipped on a re-run).
"""
import argparse
import logging
import time

import requests
from tqdm import tqdm

from src import config, utils
from src.extractor import extract_entry
from src.page_list import iter_category_members, page_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(description="Georgian Wiktionary structured scraper")
    parser.add_argument("--start-category", required=True,
                         help="Category name to crawl, e.g. 'ლექსიკონი'")
    parser.add_argument("--limit", type=int, default=None,
                         help="Stop after this many newly-scraped entries")
    args = parser.parse_args()

    already_seen = utils.already_scraped_words(config.ENTRIES_FILE)
    log.info("Resuming with %d words already scraped", len(already_seen))

    session = requests.Session()
    new_count = 0

    titles = iter_category_members(args.start_category)
    for title in tqdm(titles, desc="Scraping"):
        if title in already_seen:
            continue

        entry = extract_entry(title, page_url(title), session)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        if entry is None:
            continue

        utils.append_jsonl(config.ENTRIES_FILE, entry)
        already_seen.add(title)
        new_count += 1

        if args.limit and new_count >= args.limit:
            log.info("Reached limit of %d new entries, stopping", args.limit)
            break

    log.info("Done. %d new entries written to %s", new_count, config.ENTRIES_FILE)


if __name__ == "__main__":
    main()

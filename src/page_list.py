"""
Discovers word-entry page titles to scrape, using MediaWiki's
`categorymembers` API rather than crawling rendered index pages by hand -
it's the same underlying data, paginates cleanly, and doesn't require
guessing at the site's HTML listing structure.
"""
import logging
import time
from typing import Iterator

import requests

from . import config

log = logging.getLogger("page_list")


def iter_category_members(category: str) -> Iterator[str]:
    """Yields page titles belonging to `category`, following pagination
    continuation tokens until MediaWiki reports there are no more."""
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    params = dict(config.CATEGORY_MEMBERS_PARAMS)
    params["cmtitle"] = f"კატეგორია:{category}" if not category.startswith("კატეგორია:") else category

    continue_token = None
    while True:
        if continue_token:
            params["cmcontinue"] = continue_token

        resp = session.get(config.API_URL, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        members = payload.get("query", {}).get("categorymembers", [])
        for member in members:
            title = member.get("title")
            if title:
                yield title

        continue_token = payload.get("continue", {}).get("cmcontinue")
        if not continue_token:
            break

        time.sleep(config.REQUEST_DELAY_SECONDS)

    log.info("Finished paging category '%s'", category)


def page_url(title: str) -> str:
    return f"{config.BASE_URL}/wiki/{title.replace(' ', '_')}"

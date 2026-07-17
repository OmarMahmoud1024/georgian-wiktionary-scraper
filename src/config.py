"""Configuration for the Georgian Wiktionary scraper."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ENTRIES_FILE = DATA_DIR / "entries.jsonl"

BASE_URL = "https://ka.wiktionary.org"
API_URL = BASE_URL + "/w/api.php"

# MediaWiki's API is the polite way in - avoids scraping rendered HTML for
# navigation and lets us page through category members directly.
CATEGORY_MEMBERS_PARAMS = {
    "action": "query",
    "list": "categorymembers",
    "cmlimit": "500",
    "format": "json",
}

REQUEST_DELAY_SECONDS = 1.0
USER_AGENT = "GeorgianWiktionaryScraper/1.0 (portfolio project; contact via GitHub)"

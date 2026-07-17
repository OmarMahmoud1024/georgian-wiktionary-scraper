"""JSONL append/resume helpers shared across the scraper."""
import json
from pathlib import Path
from typing import Set


def append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def already_scraped_words(path: Path) -> Set[str]:
    """Reads whatever's already in entries.jsonl so a resumed run skips
    words it already has, instead of re-fetching and duplicating them."""
    if not path.exists():
        return set()
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                seen.add(record.get("word"))
            except json.JSONDecodeError:
                # Tolerate a truncated last line from a previous crash -
                # everything before it is still valid and kept.
                continue
    return seen

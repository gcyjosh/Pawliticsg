"""
Pawlitics — Fill Text
======================
Fetches actual speech content for each entry using the Hansard report API.
Run this BEFORE summariser.py.

HOW TO RUN:
  python3 fill_text.py
"""

import requests
import json
import time
import re
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path

DATA_FILE   = Path("data/speeches.json")
CONTENT_URL = "https://sprs.parl.gov.sg/search/getHansardReport/"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://sprs.parl.gov.sg",
    "referer": "https://sprs.parl.gov.sg/search/#/result",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def get_text(self):
        return " ".join(self.parts).strip()

def strip_html(html_string):
    if not html_string:
        return ""
    s = HTMLStripper()
    s.feed(html_string)
    return re.sub(r"\s+", " ", s.get_text()).strip()

def to_api_date(sitting_id):
    """Convert YYYY-MM-DD to DD-MM-YYYY which the API expects."""
    try:
        dt = datetime.strptime(sitting_id, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return sitting_id

def fetch_content(sitting_id, report_id):
    clean_id    = report_id.rstrip("#")
    api_date    = to_api_date(sitting_id)
    if not clean_id or not api_date:
        return None
    try:
        resp = requests.get(
            CONTENT_URL,
            headers=HEADERS,
            params={"sittingDate": api_date, "reportId": clean_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠ Fetch failed ({api_date}, {clean_id}): {e}")
        return None

def extract_text(content_json, title):
    if not content_json:
        return ""
    sections = content_json.get("takesSectionVOList", [])
    # Exact match
    for s in sections:
        if s.get("title", "").strip() == title.strip():
            return strip_html(s.get("content", ""))
    # Partial match
    for s in sections:
        if title.strip().lower() in s.get("title", "").lower():
            return strip_html(s.get("content", ""))
    # First non-empty section
    for s in sections:
        text = strip_html(s.get("content", ""))
        if text:
            return text
    return strip_html(str(content_json))

def extract_report_id(hansard_url):
    m = re.search(r"reportId=([^&]+)", hansard_url or "")
    return m.group(1) if m else ""

def main():
    raw      = json.loads(DATA_FILE.read_text())
    meta     = raw.get("meta", {})
    speeches = raw.get("speeches", [])

    to_fill = [s for s in speeches if not s.get("excerpt") or len(s.get("excerpt", "")) < 50]
    print(f"Pawlitics — Fill Text")
    print(f"Total speeches:  {len(speeches)}")
    print(f"Need text:       {len(to_fill)}")
    print()

    if not to_fill:
        print("All speeches already have text. Nothing to do.")
        return

    filled = 0
    failed = 0

    for i, speech in enumerate(to_fill, 1):
        title      = speech.get("title", "")
        sitting_id = speech.get("sitting_id", "")
        report_id  = extract_report_id(speech.get("hansard_url", ""))

        print(f"[{i}/{len(to_fill)}] {title[:70]}")

        if not report_id:
            print(f"  ⚠ No reportId — skipping")
            failed += 1
            continue

        content_json = fetch_content(sitting_id, report_id)
        time.sleep(0.5)

        text = extract_text(content_json, title)

        if text and len(text) > 30:
            excerpt = text[:600].rstrip()
            if len(text) > 600:
                excerpt += "..."
            speech["excerpt"]    = excerpt
            speech["full_text"]  = text[:5000]
            speech["ai_summary"] = None   # reset so summariser re-runs
            filled += 1
            print(f"  ✓ {len(text)} chars")
        else:
            print(f"  ✗ Empty response")
            failed += 1

        if i % 20 == 0:
            meta["generated_at"] = datetime.utcnow().isoformat() + "Z"
            DATA_FILE.write_text(json.dumps({"meta": meta, "speeches": speeches}, indent=2, ensure_ascii=False))
            print(f"  --- Checkpoint saved ({filled} filled so far) ---")

    meta["generated_at"] = datetime.utcnow().isoformat() + "Z"
    meta["total"] = len(speeches)
    DATA_FILE.write_text(json.dumps({"meta": meta, "speeches": speeches}, indent=2, ensure_ascii=False))

    print()
    print(f"✅ Done!  Filled: {filled}  |  Failed: {failed}")
    print()
    print("Next step:  python3 summariser.py --force")

if __name__ == "__main__":
    main()

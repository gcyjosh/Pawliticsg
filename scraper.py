"""
Pawlitics — Scraper
====================
Uses the SPRS API endpoint. Keywords are organised by animal category
so every result is pre-labelled by pet type.

HOW TO RUN:
  python3 scraper.py

Output: data/speeches.json
"""

import requests
import json
import time
import re
from datetime import datetime
from pathlib import Path

OUTPUT_FILE      = Path("data/speeches.json")
CHECKPOINT       = Path("data/.checkpoint.json")
DELAY_SECONDS    = 2
RESULTS_PER_PAGE = 20
START_YEAR       = 2016
END_YEAR         = datetime.now().year

URL = "https://sprs.parl.gov.sg/search/searchResult"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://sprs.parl.gov.sg",
    "referer": "https://sprs.parl.gov.sg/search/#/result",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

# ── Keywords organised by pet category ────────────────────────────────────────
# Each entry is (search_keyword, pet_type)
# The pet_type is the label that appears on the website card.

PET_KEYWORDS = [
    # 🐱 Cat
    ("cat",             "cat"),
    ("kitten",          "cat"),
    ("feline",          "cat"),
    ("TNRM",            "cat"),
    ("community cat",   "cat"),
    ("stray cat",       "cat"),

    # 🐶 Dog
    ("dog",             "dog"),
    ("canine",          "dog"),
    ("puppy",           "dog"),
    ("dog breed",       "dog"),
    ("dog licence",     "dog"),
    ("dangerous dog",   "dog"),

    # 🐦 Bird
    ("bird",            "bird"),
    ("avian",           "bird"),
    ("parrot",          "bird"),
    ("migratory bird",  "bird"),
    ("bird singing",    "bird"),

    # 🐟 Fish
    ("fish",            "fish"),
    ("aquaculture",     "fish"),
    ("ornamental fish", "fish"),
    ("aquarium",        "fish"),

    # 🐹 Rodent
    ("hamster",         "rodent"),
    ("gerbil",          "rodent"),
    ("guinea pig",      "rodent"),
    ("rodent",          "rodent"),
    ("chinchilla",      "rodent"),

    # 🦎 Others
    ("pet",             "others"),
    ("AVS",             "others"),
    ("SPCA",            "others"),
    ("wildlife",        "others"),
    ("exotic animal",   "others"),
    ("veterinary",      "others"),
    ("animal welfare",  "others"),
    ("animal cruelty",  "others"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_checkpoint():
    if CHECKPOINT.exists():
        data = json.loads(CHECKPOINT.read_text())
        print(f"Resuming — {len(data)} searches already done")
        return set(data)
    return set()

def save_checkpoint(done):
    CHECKPOINT.write_text(json.dumps(list(done)))

def load_existing():
    if OUTPUT_FILE.exists():
        raw = json.loads(OUTPUT_FILE.read_text())
        speeches = raw.get("speeches", raw) if isinstance(raw, dict) else raw
        print(f"Loaded {len(speeches)} existing speeches")
        return speeches, {r["id"] for r in speeches}
    return [], set()

def save_data(speeches):
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    payload = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total": len(speeches),
            "source": "Singapore Parliament Hansard (SPRS)",
            "url": "https://sprs.parl.gov.sg/search/",
        },
        "speeches": sorted(speeches, key=lambda s: s.get("sitting_id", ""), reverse=True),
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

def build_payload(keyword, year, start_index):
    return {
        "keyword": keyword,
        "fromday": "01", "frommonth": "01", "fromyear": str(year),
        "today":   "31", "tomonth":   "12", "toyear":   str(year),
        "dateRange": "* TO NOW",
        "reportContent": "with all the words",
        "parliamentNo": "",
        "selectedSort": "date_dt desc",
        "portfolio": [], "mpName": "", "rsSelected": "", "lang": "",
        "startIndex": str(start_index),
        "endIndex": str(start_index + RESULTS_PER_PAGE - 1),
        "titleChecked": "false",
        "footNoteChecked": "false",
        "ministrySelected": [],
    }

def fetch_page(keyword, year, start_index):
    payload = build_payload(keyword, year, start_index)
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=20)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"  ⚠ HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return None

def parse_results(data):
    if not data:
        return [], 0
    if isinstance(data, list):
        items, total = data, len(data)
    else:
        total = data.get("total") or data.get("totalResults") or data.get("count") or 0
        if isinstance(total, dict):
            total = total.get("value", 0)
        items = data.get("result") or data.get("results") or data.get("hits") or data.get("data") or []
        if isinstance(items, dict):
            items = items.get("hits", [])

    speeches = []
    for item in items:
        if "_source" in item:
            item = item["_source"]

        title = item.get("title") or item.get("subjectMatter") or item.get("subject") or ""
        text  = item.get("content") or item.get("text") or item.get("body") or ""
        if isinstance(text, list):
            text = "\n\n".join(
                s.get("content", s) if isinstance(s, dict) else str(s) for s in text
            )

        date_raw = item.get("sittingDate") or item.get("date") or item.get("date_dt") or ""
        sitting_id      = ""
        sitting_display = str(date_raw)
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(str(date_raw).split("T")[0], fmt)
                sitting_id      = dt.strftime("%Y-%m-%d")
                sitting_display = dt.strftime("%-d %B %Y")
                break
            except ValueError:
                continue

        speech_id = str(item.get("id") or item.get("_id") or item.get("reportId") or f"{sitting_id}_{len(speeches)}")
        report_id = str(item.get("reportId") or "")

        speeches.append({
            "_raw_title":    title.strip(),
            "_raw_text":     str(text).strip(),
            "_sitting_id":   sitting_id,
            "_sitting_disp": sitting_display,
            "_speech_id":    speech_id,
            "_report_id":    report_id,
            "_speaker":      item.get("primaryMemberName") or item.get("memberName") or item.get("speaker") or "",
            "_ministry":     item.get("ministryName") or item.get("ministry") or "",
            "_type":         item.get("type") or item.get("hansardType") or item.get("contentType") or "",
        })
    return speeches, int(total)

# ── Main ──────────────────────────────────────────────────────────────────────
def scrape():
    Path("data").mkdir(exist_ok=True)
    done_searches = load_checkpoint()
    all_speeches, seen_ids = load_existing()
    total_new = 0

    for keyword, pet_type in PET_KEYWORDS:
        for year in range(START_YEAR, END_YEAR + 1):
            search_key = f"{keyword}_{year}"
            if search_key in done_searches:
                continue

            print(f"\n🔍 [{pet_type.upper()}] '{keyword}' — {year}")
            start_index   = 0
            keyword_total = 0

            while True:
                data = fetch_page(keyword, year, start_index)
                time.sleep(DELAY_SECONDS)
                if not data:
                    break

                raw_speeches, total = parse_results(data)
                if not raw_speeches:
                    break

                for r in raw_speeches:
                    sid = r["_speech_id"]
                    if sid in seen_ids:
                        continue

                    excerpt = r["_raw_text"][:600].rstrip()
                    if len(r["_raw_text"]) > 600:
                        excerpt += "..."

                    hansard_url = (
                        f"https://sprs.parl.gov.sg/search/getHansardReport/"
                        f"?sittingDate={r['_sitting_id']}&reportId={r['_report_id']}"
                        if r["_report_id"]
                        else "https://sprs.parl.gov.sg/search/#/result"
                    )

                    speech = {
                        "id":          sid,
                        "type":        pet_type,   # set directly from keyword category
                        "title":       r["_raw_title"],
                        "speaker":     r["_speaker"],
                        "sitting":     r["_sitting_disp"],
                        "sitting_id":  r["_sitting_id"],
                        "excerpt":     excerpt,
                        "hansard_url": hansard_url,
                        "speech_type": r["_type"],
                        "ministry":    r["_ministry"],
                        "ai_summary":  None,
                        "scraped_at":  datetime.utcnow().isoformat() + "Z",
                    }

                    all_speeches.append(speech)
                    seen_ids.add(sid)
                    total_new     += 1
                    keyword_total += 1

                print(f"  Page {start_index // RESULTS_PER_PAGE + 1}: "
                      f"{len(raw_speeches)} results (total: {total}), "
                      f"{keyword_total} new this keyword")

                start_index += RESULTS_PER_PAGE
                if start_index >= total or start_index >= 200:
                    break

            print(f"  ✓ {keyword_total} new speeches saved")
            done_searches.add(search_key)
            save_checkpoint(done_searches)
            save_data(all_speeches)

    print(f"\n✅ Scrape complete!")
    print(f"   New speeches:  {total_new}")
    print(f"   Total in file: {len(all_speeches)}")
    print(f"   File: {OUTPUT_FILE.resolve()}")
    print()
    print("Next step:  python3 summariser.py")

if __name__ == "__main__":
    print("Pawlitics — Scraper")
    print(f"Searching SPRS by pet category ({START_YEAR}-{END_YEAR})")
    print()
    try:
        scrape()
    except KeyboardInterrupt:
        print("\nStopped. Progress saved — run again to resume.")

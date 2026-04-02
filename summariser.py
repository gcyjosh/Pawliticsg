"""
Pawlitics — Summariser
=======================
Reads data/speeches.json and generates plain-English AI summaries
using the Anthropic API. Skips speeches already summarised.

HOW TO RUN:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 summariser.py

Options:
  python3 summariser.py --force    # Re-summarise everything
  python3 summariser.py --limit 10 # Only do 10 (for testing)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("data/speeches.json")

def load():
    if not DATA_FILE.exists():
        print("❌ data/speeches.json not found. Run scraper.py first.")
        sys.exit(1)
    raw = json.loads(DATA_FILE.read_text())
    meta     = raw.get("meta", {})
    speeches = raw.get("speeches", [])
    return meta, speeches

def save(meta, speeches):
    meta["summarised_at"] = datetime.utcnow().isoformat() + "Z"
    meta["summarised"]    = sum(1 for s in speeches if s.get("ai_summary"))
    meta["total"]         = len(speeches)
    DATA_FILE.write_text(json.dumps({"meta": meta, "speeches": speeches}, indent=2, ensure_ascii=False))

def summarise(speech, client):
    prompt = f"""You are a plain-language assistant helping Singapore pet owners understand parliament policy speeches.

Summarise this parliament speech in exactly 3-4 sentences. Use simple, friendly language — no jargon.
Cover: (1) what concern or issue was raised, (2) what policy or law is involved, (3) what the speaker wants the government to do.
Do NOT start with "The speaker" or "In this speech". Write in present tense.

Title: {speech['title']}
Speaker: {speech['speaker']}
Date: {speech['sitting']}
Pet type: {speech['type'].title()}

Excerpt:
{speech.get("full_text") or speech.get("excerpt", "")}"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-summarise all speeches")
    parser.add_argument("--limit", type=int, default=None, help="Only process N speeches")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set.")
        print("   Run: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("❌ anthropic package not installed. Run: pip3 install anthropic")
        sys.exit(1)

    meta, speeches = load()

    to_do = [s for s in speeches if args.force or not s.get("ai_summary")]
    if args.limit:
        to_do = to_do[:args.limit]

    skipped = len(speeches) - len(to_do)
    print(f"Pawlitics — Summariser")
    print(f"Total speeches: {len(speeches)}")
    print(f"To summarise:   {len(to_do)}  (skipping {skipped} already done)")
    print()

    if not to_do:
        print("Nothing to do. Use --force to re-summarise.")
        return

    speech_map = {s["id"]: s for s in speeches}
    success = 0
    fail    = 0

    for i, speech in enumerate(to_do, 1):
        title_short = speech["title"][:60] + ("..." if len(speech["title"]) > 60 else "")
        print(f"[{i}/{len(to_do)}] {title_short}")

        for attempt in range(1, 4):
            try:
                summary = summarise(speech, client)
                speech_map[speech["id"]]["ai_summary"]     = summary
                speech_map[speech["id"]]["summarised_at"]  = datetime.utcnow().isoformat() + "Z"
                success += 1
                print(f"  ✓ Done")
                break
            except Exception as e:
                if "rate" in str(e).lower():
                    print(f"  Rate limit — waiting {5 * attempt}s...")
                    time.sleep(5 * attempt)
                else:
                    print(f"  ⚠ Error (attempt {attempt}): {e}")
                    if attempt == 3:
                        fail += 1

        # Save checkpoint every 10
        if i % 10 == 0:
            save(meta, list(speech_map.values()))
            print(f"  --- Checkpoint saved ({success} done so far) ---")

        time.sleep(0.5)

    save(meta, list(speech_map.values()))
    print()
    print(f"✅ Done!  Summaries generated: {success}  |  Failed: {fail}")
    print(f"   Open pawlitics.html in a browser (served via: python3 -m http.server 8080)")

if __name__ == "__main__":
    main()

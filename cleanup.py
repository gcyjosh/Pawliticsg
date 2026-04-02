"""
Pawlitics — Cleanup
====================
1. Removes bad titles (Committee of Supply Head X etc.)
2. Cleans procedural markers out of excerpt/full_text content
3. Clears useless AI summaries generated from empty text

HOW TO RUN:
  python3 cleanup.py
"""

import json
import re
from pathlib import Path

DATA_FILE = Path("data/speeches.json")

# ── Inline text noise to strip from excerpts ──────────────────────────────────
# These appear as [(proc text)], (proc text), [(cont)], [32 Mr ...] line numbers etc.
CONTENT_NOISE = [
    r"\[\s*\(proc(?:edural)?\s*text\)\s*\]",   # [(proc text)]
    r"\(\s*proc(?:edural)?\s*text\s*\)",        # (proc text)
    r"\[\s*\(cont(?:inued)?\)\s*\]",            # [(cont)]
    r"\(\s*cont(?:inued)?\s*\)",                # (cont)
    r"^\d+\s+(?=Mr|Ms|Dr|Mdm|Minister|Madam)", # line numbers like "32 Mr ..."
]
_NOISE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in CONTENT_NOISE]

def clean_content(text):
    if not text:
        return text
    for pat in _NOISE:
        text = pat.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()

# ── Bad titles ─────────────────────────────────────────────────────────────────
def is_bad_title(title):
    t = title or ""
    if re.search(r"Head\s+[A-Z]\b", t):
        return True
    if re.search(r"\(proc(?:edural)?\s*text\)", t, re.I):
        return True
    if re.search(r"\(cont(?:inued)?\)", t, re.I):
        return True
    return False

# ── Bad summaries (generated from empty text) ─────────────────────────────────
def is_bad_summary(summary):
    bad = [
        "paste the actual speech", "paste the text",
        "excerpt.*is empty", "no text provided",
        "no actual content", "content.*is empty",
        "happy to help.*but", "i'd be happy to help.*excerpt",
    ]
    for phrase in bad:
        if re.search(phrase, summary or "", re.I):
            return True
    return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    raw      = json.loads(DATA_FILE.read_text())
    meta     = raw.get("meta", {})
    speeches = raw.get("speeches", [])

    print(f"Pawlitics — Cleanup")
    print(f"Total before: {len(speeches)}")

    # 1. Remove bad titles
    cleaned = [s for s in speeches if not is_bad_title(s.get("title", ""))]
    print(f"Removed {len(speeches) - len(cleaned)} bad-title entries")

    # 2. Clean proc/cont noise from excerpt and full_text
    content_cleaned = 0
    for s in cleaned:
        orig = s.get("excerpt", "")
        s["excerpt"]   = clean_content(s.get("excerpt", ""))
        s["full_text"] = clean_content(s.get("full_text", ""))
        if s["excerpt"] != orig:
            content_cleaned += 1
    print(f"Cleaned proc/cont markers from {content_cleaned} excerpts")

    # 3. Clear bad summaries
    cleared = 0
    for s in cleaned:
        if is_bad_summary(s.get("ai_summary", "")):
            s["ai_summary"] = None
            cleared += 1
    print(f"Cleared {cleared} useless AI summaries")
    print(f"Total after:  {len(cleaned)}")

    meta["total"]      = len(cleaned)
    meta["summarised"] = sum(1 for s in cleaned if s.get("ai_summary"))

    DATA_FILE.write_text(json.dumps(
        {"meta": meta, "speeches": cleaned},
        indent=2, ensure_ascii=False
    ))

    print(f"\n✅ Done. speeches.json updated.")
    print(f"   Valid summaries remaining: {meta['summarised']}")
    print("\nRefresh your browser to see the changes.")

if __name__ == "__main__":
    main()

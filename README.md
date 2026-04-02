# 🐾 Pawlitics

> *What our government sets for fur-kids* — by Goh Ching Yang, Josh

A pipeline that tracks Singapore Parliament speeches about pet policy, filtered by animal type, with AI-generated summaries for everyday pet owners.

---

## Project Structure

```
pawlitics/
├── scraper.py          # Stage 1 — Scrapes Singapore Hansard for pet-related speeches
├── summariser.py       # Stage 2 — Generates AI summaries via Claude API
├── pawlitics.html      # Frontend — Reads data/speeches.json, renders the website
├── run_pipeline.sh     # Convenience script to run both stages
├── requirements.txt    # Python dependencies
└── data/
    └── speeches.json   # Generated output (not committed to git)
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run the full pipeline

```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

Or run stages individually:

```bash
# Stage 1 — scrape
python scraper.py

# Stage 2 — summarise
python summariser.py
```

### 4. Serve the website

```bash
python -m http.server 8080
# Open http://localhost:8080/pawlitics.html
```

---

## Pipeline Details

### `scraper.py`

Scrapes `parliament.gov.sg/hansard` for all sitting dates, visits each sitting page, and filters speeches containing pet-related keywords.

**Pet keyword taxonomy:**

| Category | Keywords include |
|----------|-----------------|
| 🐱 Cat | cat, kitten, TNRM, community cat, feline |
| 🐶 Dog | dog, canine, puppy, dog breed, dog licence |
| 🐦 Bird | bird, avian, parrot, migratory bird, bird singing |
| 🐟 Fish | fish, aquaculture, ornamental fish, aquarium |
| 🐹 Rodent | hamster, gerbil, guinea pig, rodent, chinchilla |
| 🦎 Others | pet, AVS, SPCA, wildlife, exotic animal, veterinary |

**CLI options:**

```bash
python scraper.py                       # Full scrape (all time)
python scraper.py --limit 5             # Last 5 sittings (dev/test)
python scraper.py --from 2022-01-01     # From a date onwards
python scraper.py --delay 2.0           # Custom request delay (seconds)
python scraper.py --output data/raw.json
```

Output: `data/speeches.json`

---

### `summariser.py`

Reads `data/speeches.json`, calls the Claude API to generate 3–4 sentence plain-language summaries, and writes them back to the same file. Runs incrementally — skips speeches already summarised.

**CLI options:**

```bash
python summariser.py                    # Summarise unsummarised speeches
python summariser.py --force            # Re-summarise everything
python summariser.py --limit 10         # Only process 10 (dev/test)
python summariser.py --delay 0.5        # Rate-limit delay between calls
python summariser.py --input data/speeches.json --output data/speeches.json
```

**Checkpoint saves** every 10 speeches so you don't lose work on long runs.

---

### `pawlitics.html`

Static HTML file. Fetches `data/speeches.json` at runtime via `fetch()`.

**Features:**
- Free-text search (title, speaker, excerpt, date)
- Pet-type filter chips (Cat / Dog / Bird / Fish / Rodent / Others)
- Parliament sitting date dropdown
- Direct Hansard link on every card
- AI Summary toggle on every card (shows pre-generated summary from pipeline, or generates live on-demand via Anthropic API)

> ⚠️ **Serving requirement:** The HTML uses `fetch("data/speeches.json")`, which requires a local HTTP server. Open-as-file (`file://`) won't work due to CORS. Use `python -m http.server 8080`.

---

## Automating Updates

To keep the site current, add a cron job:

```cron
# Update every Monday at 6am (parliament typically sits Mon–Wed)
0 6 * * 1  cd /path/to/pawlitics && ./run_pipeline.sh >> logs/cron.log 2>&1
```

Or use GitHub Actions with a scheduled workflow.

---

## Data format (`data/speeches.json`)

```json
{
  "meta": {
    "generated_at": "2024-04-08T10:30:00Z",
    "total": 47,
    "summarised": 47,
    "source": "Singapore Parliament Hansard",
    "url": "https://www.parliament.gov.sg/hansard/sittings"
  },
  "speeches": [
    {
      "id": "20230404_0001",
      "type": "dog",
      "title": "Animals and Birds (Amendment) Bill — Dangerous Dog Breeds",
      "speaker": "Mr Louis Ng Kok Kwang (Nee Soon GRC)",
      "sitting": "4 April 2023",
      "sitting_id": "2023-04-04",
      "excerpt": "The proposed amendments to the Animals and Birds Act...",
      "hansard_url": "https://www.parliament.gov.sg/hansard/sittings/details/2023-04-04",
      "ai_summary": "The MP raises concerns about the proposed licensing amendments...",
      "scraped_at": "2024-04-08T10:00:00Z",
      "summarised_at": "2024-04-08T10:30:00Z"
    }
  ]
}
```

---

## Notes on the Hansard

The Singapore Parliament Hansard is publicly available at [parliament.gov.sg/hansard](https://www.parliament.gov.sg/hansard/sittings). The scraper is built to adapt to the site's HTML structure with multiple fallback strategies. If the site changes structure, check the `scrape_sitting()` function in `scraper.py` and update the CSS selectors accordingly.

Be a polite scraper — the default `--delay 1.5` adds a 1.5-second pause between requests. Do not reduce this significantly.

---

*Made with 🐾 for Singapore's pet owners*

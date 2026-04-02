#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Pawlitics — Full pipeline runner
#  Usage:
#    chmod +x run_pipeline.sh
#    export ANTHROPIC_API_KEY=sk-ant-...
#    ./run_pipeline.sh              # Full run
#    ./run_pipeline.sh --dev        # Dev mode: last 5 sittings, 10 summaries
#    ./run_pipeline.sh --from 2022-01-01   # Only sittings from 2022 onwards
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

DEV_MODE=false
FROM_DATE=""

# Parse args
for arg in "$@"; do
  case $arg in
    --dev)        DEV_MODE=true ;;
    --from=*)     FROM_DATE="${arg#*=}" ;;
  esac
done

echo ""
echo "  🐾  Pawlitics Pipeline"
echo "  ─────────────────────────────"

# Check API key
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "  ❌  ANTHROPIC_API_KEY is not set."
  echo "      Export it:  export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# Install deps if needed
if ! python -c "import requests, bs4, anthropic" &>/dev/null; then
  echo "  📦  Installing dependencies…"
  pip install -q -r requirements.txt
fi

mkdir -p data

echo ""
echo "  [1/2] Scraping Hansard…"
if [ "$DEV_MODE" = true ]; then
  python scraper.py --limit 5
elif [ -n "$FROM_DATE" ]; then
  python scraper.py --from "$FROM_DATE"
else
  python scraper.py
fi

echo ""
echo "  [2/2] Generating AI summaries…"
if [ "$DEV_MODE" = true ]; then
  python summariser.py --limit 10
else
  python summariser.py
fi

echo ""
echo "  ✅  Pipeline complete!"
echo "      Open pawlitics.html in your browser (serve from this directory)."
echo ""
echo "  Quick-serve:  python -m http.server 8080"
echo "  Then open:    http://localhost:8080/pawlitics.html"
echo ""

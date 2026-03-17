#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-results/scraper}"
OUTPUT_DIR="${OUTPUT_DIR:-results/classifier/box64-$(date +%Y%m%d)}"
BACKEND="${BACKEND:-ollama}"
MODEL="${MODEL:-gemma3:27b}"
export GITHUB_TOKEN=$(gh auth token 2>/dev/null || true)

# Scrape
scrape https://github.com/ptitSeb/box64 -o "$DATA_DIR/box64"

# Classify
PREAMBLE_ARGS=()
if [[ "$BACKEND" != "zero-shot" ]]; then
    PREAMBLE_ARGS=(--preamble data/prompts/classify.txt)
fi

bug-classify \
    --config data/configs/box64.toml \
    --backend "$BACKEND" \
    ${MODEL:+--model "$MODEL"} \
    "${PREAMBLE_ARGS[@]}" \
    -i "$DATA_DIR/box64" \
    -o "$OUTPUT_DIR"

# Summarize
analyze-csv "$OUTPUT_DIR"
word-count "$DATA_DIR/box64"

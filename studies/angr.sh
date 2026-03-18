#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-results/angr/scraper}"
OUTPUT_DIR="${OUTPUT_DIR:-results/angr/classifier/$(date +%Y%m%d)}"
BACKEND="${BACKEND:-pi}"
MODEL="${MODEL:-claude-haiku-4-5}"
export GITHUB_TOKEN=$(gh auth token 2>/dev/null || true)

# Scrape all angr GitHub issues
scrape https://github.com/angr/angr -o "$DATA_DIR"

# Classify into instruction / syscall / analysis / other
PREAMBLE_ARGS=()
if [[ "$BACKEND" != "zero-shot" ]]; then
    PREAMBLE_ARGS=(--preamble data/prompts/angr.txt)
fi

bug-classifier \
    --config data/configs/angr.toml \
    --backend "$BACKEND" \
    ${MODEL:+--model "$MODEL"} \
    "${PREAMBLE_ARGS[@]}" \
    -i "$DATA_DIR" \
    -o "$OUTPUT_DIR"

# Summarize
analyze-csv "$OUTPUT_DIR"
word-count "$DATA_DIR"

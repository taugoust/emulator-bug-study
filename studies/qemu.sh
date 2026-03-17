#!/usr/bin/env bash
set -euo pipefail

# Where scraped data lives
DATA_DIR="${DATA_DIR:-results/scraper}"
OUTPUT_DIR="${OUTPUT_DIR:-results/classifier/$(date +%Y%m%d)}"
BACKEND="${BACKEND:-ollama}"
MODEL="${MODEL:-gemma3:27b}"
export GITLAB_TOKEN=$(glab auth token 2>/dev/null || true)

# Scrape all sources
scrape https://github.com/qemu/qemu -o "$DATA_DIR/github"
scrape https://gitlab.com/qemu-project/qemu -o "$DATA_DIR/gitlab"
scrape https://lists.nongnu.org/archive/html/qemu-devel \
    --start 2015-04 --end 2025-05 -o "$DATA_DIR"

# Classify
PREAMBLE_ARGS=()
if [[ "$BACKEND" != "zero-shot" ]]; then
    PREAMBLE_ARGS=(--preamble data/prompts/classify.txt)
fi

bug-classify \
    --config data/configs/qemu.toml \
    --backend "$BACKEND" \
    ${MODEL:+--model "$MODEL"} \
    "${PREAMBLE_ARGS[@]}" \
    -i "$DATA_DIR/github" \
    -i "$DATA_DIR/gitlab/issues_text" \
    -i "$DATA_DIR/mailinglist" \
    -i "$DATA_DIR/launchpad" \
    -o "$OUTPUT_DIR"

# Summarize
analyze-csv "$OUTPUT_DIR"
word-count "$DATA_DIR/github" "$DATA_DIR/gitlab/issues_text" "$DATA_DIR/mailinglist"

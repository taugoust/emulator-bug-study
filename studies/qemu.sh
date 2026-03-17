#!/usr/bin/env bash
set -euo pipefail

# Where scraped data lives
DATA_DIR="${DATA_DIR:-results/scraper}"
OUTPUT_DIR="${OUTPUT_DIR:-results/classifier/$(date +%Y%m%d)}"
BACKEND="${BACKEND:-ollama}"
MODEL="${MODEL:-gemma3:27b}"
export GITLAB_TOKEN=$(glab auth token 2>/dev/null || true)

# Scrape all QEMU sources: GitLab, mailing list (April 2015 – May 2025),
# and Launchpad (discovered automatically from mailing list references).
# No GitHub: QEMU does not use GitHub for bug tracking.
scrape https://gitlab.com/qemu-project/qemu -o "$DATA_DIR/gitlab"
scrape https://lists.nongnu.org/archive/html/qemu-devel \
    --start 2015-04 --end 2025-05 -o "$DATA_DIR"

# Pass 1 — mode classification: all scraped bugs → user / system / other
PREAMBLE_ARGS=()
if [[ "$BACKEND" != "zero-shot" ]]; then
    PREAMBLE_ARGS=(--preamble data/prompts/mode.txt)
fi

bug-classify \
    --config data/configs/qemu-mode.toml \
    --backend "$BACKEND" \
    ${MODEL:+--model "$MODEL"} \
    "${PREAMBLE_ARGS[@]}" \
    -i "$DATA_DIR/gitlab/issues_text" \
    -i "$DATA_DIR/mailinglist" \
    -i "$DATA_DIR/launchpad" \
    -o "$OUTPUT_DIR/mode"

# Pass 2 — user-mode sub-classification: user bugs → instruction / syscall / runtime
PREAMBLE_ARGS=()
if [[ "$BACKEND" != "zero-shot" ]]; then
    PREAMBLE_ARGS=(--preamble data/prompts/user-mode.txt)
fi

bug-classify \
    --config data/configs/qemu-user-mode.toml \
    --backend "$BACKEND" \
    ${MODEL:+--model "$MODEL"} \
    "${PREAMBLE_ARGS[@]}" \
    -i "$OUTPUT_DIR/mode/user" \
    -o "$OUTPUT_DIR/user-mode"

# Summarize
analyze-csv "$OUTPUT_DIR/mode"
analyze-csv "$OUTPUT_DIR/user-mode"
word-count "$DATA_DIR/gitlab/issues_text" "$DATA_DIR/mailinglist" "$DATA_DIR/launchpad"

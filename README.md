# Bug Study Utilities

A toolkit for conducting large-scale bug studies on open-source projects. It provides scrapers for collecting bug reports from multiple sources, an LLM-based classification pipeline for categorizing them, and analysis tools for summarizing results.

This repository was originally developed to study bugs in QEMU, Box64, and FEX, but the approach is general and can be adapted to other projects.

## Setup

The project is packaged as a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) with a Nix flake. Each tool lives under `tools/` as its own Python package with a CLI entry point. Shared utilities live in `lib/buglib/`.

### With Nix (recommended)

Run any tool directly:

```
nix run .#scrape-github -- -r owner/repo
nix run .#bug-classifier -- -i bugs/ -o output/
```

Enter a development shell with all tools available:

```
nix develop
```

### With uv

```
uv sync
uv run scrape-github -r owner/repo
```

## Testing

```
nix flake check
```

Or in a development shell:

```
nix develop
pytest tests/ -v
```

## Architecture

The workflow consists of three stages:

1. **Scraping** — Bug reports are downloaded from issue trackers and mailing lists. Each bug is stored as a single plain-text file containing its title and description. All scrapers also support `--jsonl` to emit one JSON object per line to stdout for piping between tools.
2. **Classification** — Each bug file is fed to a classifier (either a zero-shot NLI model or a local LLM via Ollama) that assigns it to a category defined by the user.
3. **Analysis** — Helper scripts count bugs per category, compare classification runs, and cross-reference results.

### Project Layout

```
tools/              CLI tools (one Python package each)
lib/buglib/         Shared library (file helpers, JSONL output, pagination)
data/prompts/       Prompt templates for LLM classification
tests/              Test suite
```

The `buglib` package provides:
- `write_file()` — write a file, creating parent directories as needed.
- `list_files_recursive()` — recursively list files in a directory.
- `write_jsonl()` — write a single JSON line to a stream.
- `pages_iterator()` — follow HTTP `Link: rel=next` headers for paginated APIs.

## Tools

### Scrapers

All scrapers support two output modes:
- **File mode** (default) — writes one file per bug to `--output-dir`.
- **JSONL mode** (`--jsonl`) — writes one JSON object per line to stdout. Progress messages are suppressed to keep stdout clean.

#### scrape-github

Downloads all issues (excluding pull requests) from a GitHub repository via the REST API.

```
scrape-github -r owner/repo -o issues/
scrape-github -r owner/repo --jsonl > issues.jsonl
```

Each issue is written as a plain-text file named by issue number.

#### scrape-gitlab

Downloads issues from a GitLab project. Parses structured issue descriptions (host/guest OS, architecture, reproduction steps) and writes both TOML metadata and plain-text files organized by label.

```
scrape-gitlab -p PROJECT_ID -o output/
scrape-gitlab -p PROJECT_ID --jsonl > issues.jsonl
```

#### scrape-mailinglist

Scrapes mailing list archives for threads whose subject contains `[BUG]` or `[Bug <number>]`. Threads referencing Launchpad bugs are followed and downloaded separately.

```
scrape-mailinglist -u https://lists.nongnu.org/archive/html/qemu-devel --start 2015-04 --end 2025-05 -o output/
scrape-mailinglist -u https://lists.nongnu.org/archive/html/qemu-devel --start 2015-04 --end 2025-05 --jsonl > bugs.jsonl
```

### Classification

#### bug-classifier

Reads scraped bug files and assigns each one to a category. Supports HuggingFace zero-shot NLI models and local LLMs via Ollama.

```
# Zero-shot classification
bug-classifier -i bugs/ -o output/ --model facebook/bart-large-mnli

# With multi-label mode
bug-classifier -i bugs/ -o output/ --multi-label

# With a second model for cross-validation
bug-classifier -i bugs/ -o output/ --compare

# Using a local LLM via Ollama
bug-classifier -i bugs/ -o output/ --ollama deepseek-r1:32b --preamble data/prompts/classify.txt
```

Multiple input directories can be specified by repeating `-i`.

Categories are configured via `--positive`, `--negative`, and `--architectures` flags. The defaults are tuned for QEMU.

**Output:**
- `<output-dir>/<category>/<bug_id>` — Classification scores and the original bug text.
- `<parent-of-output-dir>/reasoning/<category>/<bug_id>` — LLM reasoning (Ollama mode only).

#### Preambles

Preambles are plain-text prompt files under `data/prompts/` that define the classification task for LLM mode:

| File | Purpose |
|---|---|
| `classify.txt` | Main classification into bug categories. |
| `mode.txt` | Classify as user-mode or system-mode. |
| `accelerator.txt` | Classify by accelerator (TCG, KVM, VMM). |
| `user-mode.txt` | Sub-classify user-mode bugs (instruction, syscall, runtime). |

### Analysis

#### analyze-csv

Counts bugs per category in a classifier run.

```
analyze-csv /path/to/classifier/run
analyze-csv --root /path/to/multiple/runs
```

#### analyze-diff

Compares two classifier runs and lists bugs that changed category.

```
analyze-diff /path/to/old /path/to/new
```

#### analyze-results

Cross-references known bugs against a classifier run.

```
analyze-results -b /path/to/known-bugs -d /path/to/classifier/run
analyze-results -b /path/to/known-bugs -d /path/to/classifier/run -o matched/
```

#### word-count

Reports word count statistics for bug report files.

```
word-count dir1/ dir2/
```

## Adapting to a New Project

1. **Scrape** your bug reports. The GitHub scraper works with any `owner/repo`. For other sources, write a scraper that produces one plain-text file per bug (or use `--jsonl` for structured output).
2. **Define categories** relevant to your project via CLI flags or by writing a preamble for LLM classification.
3. **Run classification** with one or more models.
4. **Compare and iterate** using `analyze-csv` and `analyze-diff`. Manually review bugs in ambiguous categories (`manual-review`, `review`, `unknown`).

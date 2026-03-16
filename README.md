# Bug Study Utilities

A toolkit for conducting large-scale bug studies on open-source projects. It provides scrapers for collecting bug reports from multiple sources, an LLM-based classification pipeline for categorizing them, and analysis tools for summarizing results.

This repository was originally developed to study bugs in QEMU, Box64, and FEX, but the approach is general and can be adapted to other projects.

## Architecture

The workflow consists of three stages:

1. **Scraping** — Bug reports are downloaded from issue trackers and mailing lists. Each bug is stored as a single plain-text file containing its title and description.
2. **Classification** — Each bug file is fed to a classifier (either a zero-shot NLI model or a local LLM via Ollama) that assigns it to a category defined by the user.
3. **Analysis** — Helper scripts count bugs per category, compare classification runs, and cross-reference results.

Scraped data is stored under `results/scraper/`, and classification output under `results/classifier/`.

## Scrapers

### GitHub

Downloads all issues (excluding pull requests) from a given repository via the GitHub REST API.

```
cd github
python downloader.py -r owner/repo
```

Output is written to `github/issues/<issue_id>`, one file per issue.

### GitLab

Downloads issues from a GitLab project. The project ID is set in the script. The GitLab scraper also parses structured issue descriptions (host/guest OS, architecture, reproduction steps) and writes both TOML metadata and plain-text files, organized into directories by label.

```
cd gitlab
python downloader.py
```

Output is written to `gitlab/issues_toml/` and `gitlab/issues_text/`, organized by target, host, and accelerator labels.

### Mailing List

Scrapes the `qemu-devel` mailing list archive hosted on Nongnu for threads whose subject contains `[BUG]` or `[Bug <number>]`. Threads referencing Launchpad bugs are followed and downloaded separately.

```
cd mailinglist
python downloader.py
```

Output is written to `output_mailinglist/` and `output_launchpad/`.

## Classification

`classification/classifier.py` reads scraped bug files and assigns each one to a category. It supports two classification backends and can be run in multiple passes with different prompts.

### Zero-Shot Classification

Uses HuggingFace zero-shot NLI models (default: `facebook/bart-large-mnli`). A second model can be provided for cross-validation.

```
cd classification

# Basic run over the full dataset
python classifier.py --full

# With a comparison model for cross-validation
python classifier.py --full --compare

# Specify a different primary model
python classifier.py --full --model MoritzLaurer/deberta-v3-large-zeroshot-v2.0
```

### LLM Classification

Sends each bug report along with a prompt (called a "preamble") to a local model served by Ollama. The preamble defines the available categories and instructs the model to respond with a single word.

```
cd classification
python classifier.py --full --deepseek deepseek-r1:32b
```

### Preambles

Preambles are plain-text prompt files that define the classification task. Multiple preambles exist for different classification passes:

| File | Purpose |
|---|---|
| `preambel` | Main classification into bug categories (e.g. mistranslation, assembly, device, network). |
| `preambel-mode` | Classify as user-mode or system-mode. |
| `preambel-accelerator` | Classify by accelerator (TCG, KVM, VMM). |
| `preambel-user-mode` | Sub-classify user-mode bugs (instruction, syscall, runtime). |

The active preamble is read from the file named `preambel` by default. To use a different classification scheme, replace its contents or modify the script.

### Categories

Categories are defined in two places: the preamble file (for LLM mode) and the Python lists in `classifier.py` (for zero-shot mode and output routing). The lists `positive_categories`, `negative_categories`, and `architectures` control how the classifier interprets scores and assigns a final label.

### Output

- `classification/output/<category>/<bug_id>` — Classification scores and the original bug text.
- `classification/reasoning/<category>/<bug_id>` — LLM reasoning output (LLM mode only).

Final results from each run are stored in `results/classifier/<run_name>/`.

## Analysis Tools

Located in `classification/tools/`.

### create_csv.py

Counts the number of bugs in each category for every classifier run and writes a `categories.csv` file.

```
cd classification/tools
python create_csv.py
```

To generate a CSV for a specific directory:

```
python create_csv.py -d /path/to/classifier/run
```

### create_diff.py

Compares two classifier runs and lists bugs that changed category between them.

```
cd classification/tools
python create_diff.py <old_run> <new_run>
```

The arguments are directory names under `results/classifier/`.

### analyze_results.py

Cross-references a set of known bugs against a classifier run to determine how they were categorized.

```
cd classification/tools
python analyze_results.py -b /path/to/bugs -d /path/to/classifier/run
```

### Word Count

`words-count/word_count.py` reports the number of bug reports per source and the average word count across all reports.

## Adapting to a New Project

1. **Scrape** your bug reports. The GitHub scraper is the most portable — pass any `owner/repo`. For other sources, write a scraper that produces one plain-text file per bug.
2. **Define categories** relevant to your project. Edit the preamble files and update the category lists in `classifier.py`.
3. **Run classification** with one or more models. Store each run under `results/classifier/` with a descriptive name.
4. **Compare and iterate** using `create_csv.py` and `create_diff.py`. Manually review bugs that land in ambiguous categories (`manual-review`, `review`, `unknown`).

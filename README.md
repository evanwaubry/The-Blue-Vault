# The Blue Vault

A data-driven football squad intelligence project built around Chelsea FC player performance, valuation context, and interactive analytics.

## What this project does

This project combines a Python data pipeline with a front-end experience for exploring a squad through:

- searchable player cards
- valuation and performance comparison views
- role-based analytics
- a clean, UI-driven presentation of sample data and source provenance

The project is designed to show how a small data product can be built end-to-end: gather inputs, normalize them, validate them, and then surface them in a readable, interactive view.

## Tech stack

### Python
- `argparse` for CLI configuration
- `json` and `pathlib` for data handling and exports
- `urllib` for API requests and resilient network calls
- `re` and `unicodedata` for data normalization and slug generation
- `datetime`, `time`, and `tempfile` for timestamps, rate limiting, and safe writes

### Front-end
- HTML for structure and content
- CSS for the dark, cinematic UI design
- JavaScript for interactivity, filtering, charts, and analytics
- Chart.js for chart visualizations
- GSAP for motion and animation
- Lenis for smooth scrolling

### Data & project workflow
- JSON as the output contract for player data
- staged validation and fallback logic
- project documentation around data provenance and source constraints
- testing for data-fetch and refresh workflows

## Repository layout

- `outputs/` — packaged project outputs, data files, and the final rendered HTML experience
- `work/` — experimental and iteration files, scratch scripts, and local artifacts
- `.gitattributes` — GitHub language and file classification settings
- `.gitignore` — ignores local temp, environment, and scratch folders

## Key project files

- `outputs/fetch_chelsea.py` — Python fetch and normalization pipeline
- `outputs/refresh_vault.py` — refresh logic for the packaged output
- `outputs/chelsea-squad_1.html` — final front-end experience
- `outputs/chelsea_players.json` — player data payload
- `outputs/test_fetch_chelsea.py` — validation for the fetch pipeline
- `outputs/README.md` — more detailed project notes and usage instructions

## Why it matters

This project demonstrates a complete workflow that is relevant to real-world data work:

- collecting structured data from an external source
- validating schema and handling missing values
- normalizing data for downstream use
- building a polished front-end for story-driven exploration
- documenting the source and constraints of the dataset

## Note on repository language stats

GitHub’s language percentages are approximate and can be skewed by large embedded HTML or generated data files. This repo uses `.gitattributes` to improve classification and better reflect the project’s actual technical mix.

## Project status

This is a portfolio and showcase project built to demonstrate data engineering, analysis, and front-end presentation in one workflow.

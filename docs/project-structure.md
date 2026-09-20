# Project structure guide

This repo is structured to separate the polished public-facing outputs from the local experimentation files.

## Public-facing content

The files that matter most to the project story live in `outputs/`:

- `outputs/fetch_chelsea.py`
- `outputs/refresh_vault.py`
- `outputs/chelsea-squad_1.html`
- `outputs/chelsea_players.json`
- `outputs/test_fetch_chelsea.py`
- `outputs/README.md`

These files show the real end-to-end workflow: fetch, validate, document, and present.

## Iteration and scratch work

The `work/` directory contains experimental scripts, generated assets, screenshots, and temporary files used during iteration.

These are intentionally not the primary project narrative, which is why they are excluded from the public Git flow by `.gitignore`.

## Why this matters

A clean repo tells a clearer story:

- backend/data logic is visible
- frontend experience is visible
- supporting artifacts are documented
- iteration files do not crowd the public-facing narrative

This is the same conceptual structure you want in a real portfolio project: production-relevant files first, experimental work second.

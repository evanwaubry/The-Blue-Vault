# Data connected to the preview

Vault, Search and Analytics share a manually verified **20 September 2026 UTC snapshot** of Transfermarkt's current 27-player Chelsea squad, Premier League 2026/27 performance, and individually dated published valuations. It is not a continuously updating feed. Existing photos are preserved; new players without supplied photos use the existing jersey-number placeholder. Shirt numbers and first-listed nationalities come from the same published squad/performance table.

- Squad: https://www.transfermarkt.us/chelsea-fc/kader/verein/631
- Performance (explicit Premier League selection; five team games): https://www.transfermarkt.us/chelsea-fc/leistungsdaten/verein/631/plus/1?reldata=GB1%262026
- Valuations: `market_valuations.json` includes a profile URL and valuation date for every player. Total €1,076.7M; dates range from 28 May to 22 July 2026. Retrieval date is not the valuation date.
- `vault_snapshot.json` contains the joined analytical observations and provenance. Joining uses Transfermarkt player IDs. The cohort is the current squad; departed players and youth call-ups outside that squad are excluded, so summed player output need not equal club totals.
- Clean sheets are **null/unavailable**, not zero, including in `chelsea_players.json`. This is the one nullable field in the original numeric export schema; the validator and all views handle it explicitly. Defender analytics charts use minutes instead, and detail comparisons omit this unavailable metric. The table supplies no xG, tackles, interceptions or chance creation.
- Comparisons use per-90 rates, a minimum-minutes filter and within-position Spearman correlation. Early-season sample sizes are small; a coefficient is withheld for fewer than three observations or a constant variable. No causal interpretation or predicted transfer price is claimed.

## API-Football connection

Your API-Sports key was verified successfully. Its Free plan rejected season 2026 with: “Free plans do not have access to this season, try from 2022 to 2024.” The key is stored privately in `../.env`, outside the served `outputs` directory, and ignored by Git. `.env.example` contains only a placeholder. Do not put credentials in HTML or paste them into chat.

Once your subscription includes the current season, run:

```powershell
python refresh_vault.py
```

The command reads `../.env` (or `FOOTBALL_API_KEY` in the environment), fetches Chelsea's current Premier League stats, joins exact slug matches to dated valuations, and embeds the results in the standalone HTML. Unknown valuations stay unavailable. It respects the existing 6.1-second request spacing. Failure preserves the previous statistics, reports a failed refresh, and exits with code 2. A successful refresh updates Vault, Search and Analytics together; existing media stays intact. Newly arriving players may have no supplied photo or matched valuation until reviewed.

To publish the saved snapshot without network requests:

```powershell
python refresh_vault.py --publish-only
```

The published Transfermarkt valuation snapshot does not automatically refresh. Update and verify `market_valuations.json` when new valuations are published; preserve each actual date and source.

## Historical dataset and forecasting

https://github.com/dcaribou/transfermarkt-datasets reports paused updates: games stop 6 July 2026, appearances 28 June, valuations 12 June. Its public CSV download endpoint returned HTTP 403 in this environment. No data from that repository is represented as imported or trained on.

No download is needed for the current preview. For the future forecasting task, download `players.csv.gz`, `player_valuations.csv.gz`, `appearances.csv.gz`, and `games.csv.gz` from that repository's published dataset (or its linked Kaggle dataset). A model still needs time-aligned training windows, a chronological held-out evaluation, and a comparison against the previous-value baseline. Market valuations are estimates, not actual transfer fees.

Code cleanup and GitHub publishing remain separate next steps, after preview approval.

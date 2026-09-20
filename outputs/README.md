# Current roster update

All views now share the verified 27-player Transfermarkt snapshot. See [DATA_SOURCES.md](DATA_SOURCES.md) for current provenance, nullable clean sheets, and API access limitations. Older setup notes below describe the original mock pipeline.

# Chelsea squad export

Python 3.10+; no third-party packages. Run from this directory:

```powershell
# Works immediately using the included 26-player mock file:
python fetch_chelsea.py

# Live refresh:
$env:FOOTBALL_API_KEY = 'your-api-sports-key'
python fetch_chelsea.py

# Preserve the bundled mock while writing live results elsewhere:
python fetch_chelsea.py --output live/chelsea_players.json

# Offline checks:
python test_fetch_chelsea.py
```

On macOS/Linux use `export FOOTBALL_API_KEY='your-api-sports-key'`.
`.env.example` documents variables; export them yourself or use your deployment's
environment loader. The script does not automatically read `.env`.

## Data contract

- `chelsea_players.json` is a standalone, UTF-8 array with exactly the requested fields.
- The shipped file is **synthetic mock data**, prepared September 19, 2026: plausible
  early-season numbers, **not verified results**. Names and shirt numbers follow the
  [club's 2026/27 list](https://www.chelseafc.com/en/news/article/chelsea-squad-numbers-confirmed-for-the-2026-27-season).
  It contains 26 selected players, including all seven examples requested. It is not
  intended as the complete registered squad. Live mode returns the provider's full current squad.
- Live totals cover **Chelsea's current Premier League season only**, identified using
  the provider's current-season flag; cup and other-club statistics are excluded.
  A former player in season statistics is excluded unless also on the current roster.
- Clean sheets count completed league matches where Chelsea conceded zero and the
  goalkeeper/defender played at least 60 minutes. This intentionally differs from
  fantasy scoring that tracks goals during a player's time on the pitch. MID/ATT
  receive zero. Missing match data causes fallback rather than invented clean sheets.
- Missing individual stats become zero, missing shirt numbers become `0`, and missing
  nationality or valuation becomes `"Unknown"`. Injured/unused squad members remain.
  The requested schema cannot distinguish an unavailable stat from a measured zero.
- Slugs strip accents. Known abbreviations use curated display names; new players use
  provider names. Name collisions receive the numeric provider ID as a suffix. A future
  provider name change can change a slug; persist provider IDs separately if long-term
  identity across name changes is required.
- Red cards include direct reds plus second-yellow dismissals (`red + yellowred`).
- Values in `MARKET_VALUES` are illustrative estimates, not current valuations.
  Edit that dictionary or set `FOOTBALL_MARKET_VALUES_FILE` to a JSON object such as
  `{"cole-palmer": "€120M"}`. Overrides affect live exports; fallback preserves its snapshot.

## Reliability and fallback

All requests, including pagination and retries, are spaced at least 6.1 seconds apart.
Use one running process per API key; other applications sharing the key count toward
the same quota. HTTP 429/transient server failures get at most two retries with a
minimum 60-second wait. Timeouts, invalid keys, provider error payloads, unavailable
season access, missing coverage, or malformed data use the local fallback.

Live fetching typically uses 4 requests plus remaining player pages and one request
per Chelsea shutout. Late-season runs can take several minutes and consume daily
quota. Current-season access depends on the API plan; unavailable access falls back.

The default fallback and output are both the JSON beside the script. Initially it is
the shipped mock; after a successful live run it becomes the last good cached export.
Use `--output live/chelsea_players.json` to retain the original mock or use `--fallback`
to select another immutable snapshot. The script never silently mixes mock stats into
a live export. A corrupt/missing fallback on API failure exits with code 1 and leaves
the existing output untouched. Successful fallback exits 0 and emits an explicit
stderr warning. Stdout contains a JSON run summary identifying `api-football` versus
`fallback-mock-or-cache`, season (null when unknown), player count, and export time.
Capture this summary alongside deployments so mock/stale data is not mistaken for live.

Exports are validated before a temporary file is atomically replaced. Interrupted or
failed API fetches cannot partially overwrite the player array. Run summaries are
separate from the strict player schema. No API key is printed.

Provider reference: [API-Football documentation](https://www.api-football.com/documentation-v3)
and [official integration guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide).
Offline checks use mocked responses; authenticated live access requires your key.

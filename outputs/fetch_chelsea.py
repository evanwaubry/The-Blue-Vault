"""Chelsea current squad, current Premier League season. Python 3.10+, stdlib only.

Run: python fetch_chelsea.py [--output path] [--fallback path]
Environment variables are documented in .env.example; .env is not auto-loaded.
Fallback is the shipped mock JSON, or the last good export after a successful run.
Clean sheets = completed team shutouts with >=60 minutes played (GK/DEF only).
This is a team-shutout metric, not fantasy on-pitch clean-sheet scoring.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TEAM, LEAGUE = 49, 39
DEFAULT_FILE = Path(__file__).with_name("chelsea_players.json")
STAT_KEYS = ("appearances", "minutesPlayed", "goals", "assists", "cleanSheets",
             "yellowCards", "redCards")
POSITIONS = {"Goalkeeper", "Defender", "Midfielder", "Attacker"}
# Illustrative valuations, not licensed or live market data. Edit or override by slug.
MARKET_VALUES = {
    "cole-palmer": "€120M", "enzo-fernandez": "€80M", "moises-caicedo": "€100M",
    "nicolas-jackson": "€45M", "reece-james": "€35M", "levi-colwill": "€55M",
    "robert-sanchez": "€25M", "wesley-fofana": "€30M", "malo-gusto": "€35M",
    "tosin-adarabioyo": "€20M", "romeo-lavia": "€35M", "pedro-neto": "€60M",
    "joao-pedro": "€75M", "estevao-willian": "€70M", "liam-delap": "€40M",
    "jamie-gittens": "€40M", "jorrel-hato": "€45M", "dario-essugo": "€20M",
    "mamadou-sarr": "€20M", "josh-acheampong": "€20M", "morgan-rogers": "€80M",
    "geovany-quenda": "€40M", "emmanuel-emegha": "€30M", "mike-penders": "€15M",
    "teddy-sharman-lowe": "€2M", "jordan-henderson": "€1M",
}
# Display names for API abbreviations; unknown players retain the API profile name.
DISPLAY_NAMES = {
    "C. Palmer": "Cole Palmer", "E. Fernández": "Enzo Fernández",
    "M. Caicedo": "Moisés Caicedo", "N. Jackson": "Nicolas Jackson",
    "R. James": "Reece James", "L. Colwill": "Levi Colwill",
    "Robert Sánchez": "Robert Sánchez", "W. Fofana": "Wesley Fofana",
    "M. Gusto": "Malo Gusto", "T. Adarabioyo": "Tosin Adarabioyo",
    "R. Lavia": "Roméo Lavia", "Pedro Neto": "Pedro Neto",
    "João Pedro": "João Pedro", "Estêvão": "Estêvão Willian",
    "L. Delap": "Liam Delap", "J. Gittens": "Jamie Gittens",
    "J. Hato": "Jorrel Hato", "D. Essugo": "Dário Essugo",
    "M. Sarr": "Mamadou Sarr", "J. Acheampong": "Josh Acheampong",
    "M. Rogers": "Morgan Rogers", "G. Quenda": "Geovany Quenda",
    "E. Emegha": "Emmanuel Emegha", "M. Penders": "Mike Penders",
    "T. Sharman-Lowe": "Teddy Sharman-Lowe", "J. Henderson": "Jordan Henderson",
}


def slug(name):
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def number(value):
    if value is None:
        return 0
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
        raise ValueError("Invalid nonnegative integer in API data")
    return int(value)


def validate(players):
    if not isinstance(players, list) or not players:
        raise ValueError("Empty or invalid player array")
    seen = set()
    for p in players:
        if set(p) != {"id", "name", "jerseyNumber", "position", "nationality",
                      "marketValue", "stats"}:
            raise ValueError("Invalid player fields")
        for key in ("id", "name", "nationality", "marketValue"):
            if not isinstance(p[key], str) or not p[key].strip():
                raise ValueError("Missing player text field")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", p["id"]) or p["id"] in seen:
            raise ValueError("Invalid or duplicate slug")
        seen.add(p["id"])
        if p["position"] not in POSITIONS or set(p["stats"]) != set(STAT_KEYS):
            raise ValueError("Invalid position or stats fields")
        for value in (p["jerseyNumber"], *(v for k, v in p["stats"].items()
                                       if not (k == "cleanSheets" and v is None))):
            if type(value) is not int or value < 0:
                raise ValueError("Invalid numeric field")
        if p["stats"]["cleanSheets"] is not None and p["stats"]["cleanSheets"] > p["stats"]["appearances"]:
            raise ValueError("Clean sheets exceed appearances")
    return players


class API:
    def __init__(self, key):
        self.key = key
        self.last_request = None

    def get(self, endpoint, **params):
        # Applies to ALL requests, including pages and retries. One process per key.
        for attempt in range(3):
            if self.last_request is not None:
                time.sleep(max(0, 6.1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            request = Request("https://v3.football.api-sports.io/" + endpoint + "?" +
                              urlencode(params), headers={"x-apisports-key": self.key})
            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.load(response)
            except HTTPError as exc:
                if exc.code in (429, 499, 500, 502, 503, 504) and attempt < 2:
                    # Honor numeric Retry-After; otherwise conservatively wait a minute.
                    retry = exc.headers.get("Retry-After", "60")
                    time.sleep(max(60, int(retry)) if retry.isdigit() else 60)
                    continue
                raise RuntimeError(f"API HTTP {exc.code}") from None
            if not isinstance(payload, dict) or payload.get("errors"):
                # Do not log provider bodies: they may contain credentials.
                raise RuntimeError("API rejected request (key, quota, or plan access)")
            if not isinstance(payload.get("response"), list):
                raise ValueError("Malformed API response")
            return payload
        raise RuntimeError("API retries exhausted")


def fetch(api, values):
    leagues = api.get("leagues", id=LEAGUE, current="true")["response"]
    current = [s for league in leagues for s in league.get("seasons", []) if s.get("current")]
    if len(current) != 1:
        raise ValueError("Current Premier League season unavailable")
    season = current[0]["year"]
    coverage = current[0].get("coverage") or {}
    if not coverage.get("players") or not (coverage.get("fixtures") or {}).get("statistics_players"):
        raise ValueError("Required player statistics coverage unavailable")
    teams = api.get("players/squads", team=TEAM)["response"]
    squad = next((t.get("players") for t in teams if (t.get("team") or {}).get("id") == TEAM), None)
    if not squad:
        raise ValueError("Current Chelsea squad unavailable")

    records = {}
    page = 1
    while True:
        data = api.get("players", team=TEAM, league=LEAGUE, season=season, page=page)
        for row in data["response"]:
            pid = row["player"]["id"]
            if pid in records:
                raise ValueError("Duplicate player across pages")
            records[pid] = row
        paging = data.get("paging") or {}
        total = number(paging.get("total"))
        if not 1 <= total <= 100 or number(paging.get("current")) != page:
            raise ValueError("Invalid API pagination")
        if page >= total:
            break
        page += 1

    result = {}
    for member in squad:
        pid = member["id"]
        row = records.get(pid, {})
        profile = row.get("player") or {}
        raw_name = member.get("name") or profile.get("name") or ""
        name = DISPLAY_NAMES.get(raw_name, profile.get("name") or raw_name)
        position = member.get("position")
        if position not in POSITIONS or not name or pid in result:
            raise ValueError("Invalid squad member")
        stats = dict.fromkeys(STAT_KEYS, 0)
        blocks = [s for s in (row.get("statistics") or []) if
                  (s.get("team") or {}).get("id") == TEAM and
                  (s.get("league") or {}).get("id") == LEAGUE and
                  (s.get("league") or {}).get("season") == season]
        if len(blocks) > 1:
            raise ValueError("Duplicate competition statistics")
        for block in blocks:
            games, goals, cards = (block.get(k) or {} for k in ("games", "goals", "cards"))
            stats.update(appearances=number(games.get("appearences")),
                         minutesPlayed=number(games.get("minutes")),
                         goals=number(goals.get("total")), assists=number(goals.get("assists")),
                         yellowCards=number(cards.get("yellow")),
                         redCards=number(cards.get("red")) + number(cards.get("yellowred")))
        identity = slug(name) or f"player-{pid}"
        result[pid] = dict(id=identity, name=name, jerseyNumber=number(member.get("number")),
                           position=position, nationality=profile.get("nationality") or "Unknown",
                           marketValue=values.get(identity, "Unknown"), stats=stats)

    fixtures = api.get("fixtures", team=TEAM, league=LEAGUE, season=season, status="FT")["response"]
    if fixtures and not records:
        raise ValueError("Season statistics missing despite completed matches")
    for fixture in fixtures:
        home = fixture["teams"]["home"]["id"] == TEAM
        conceded = fixture["goals"]["away" if home else "home"]
        if conceded is None:
            raise ValueError("Completed fixture has no score")
        if conceded != 0:
            continue
        data = api.get("fixtures/players", fixture=fixture["fixture"]["id"], team=TEAM)["response"]
        players = next((t.get("players") for t in data if t["team"]["id"] == TEAM), None)
        if not players:
            raise ValueError("Clean-sheet match statistics unavailable")
        for entry in players:
            player = result.get(entry["player"]["id"])
            if not player or player["position"] not in {"Goalkeeper", "Defender"}:
                continue
            minutes = sum(number((s.get("games") or {}).get("minutes"))
                          for s in entry.get("statistics") or [])
            if minutes >= 60:
                player["stats"]["cleanSheets"] += 1
    # Collision handling is deterministic using the provider ID, never array order.
    ids = [p["id"] for p in result.values()]
    for pid, player in result.items():
        if ids.count(player["id"]) > 1:
            player["id"] += f"-{pid}"
    return validate(sorted(result.values(), key=lambda p: (p["jerseyNumber"], p["name"]))), season


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--fallback", type=Path, default=DEFAULT_FILE)
    args = parser.parse_args()
    values = MARKET_VALUES.copy()
    try:
        mapping = os.getenv("FOOTBALL_MARKET_VALUES_FILE")
        if mapping:
            overrides = json.loads(Path(mapping).read_text(encoding="utf-8-sig"))
            if not isinstance(overrides, dict) or any(
                    not isinstance(k, str) or not isinstance(v, str) or not v.strip()
                    for k, v in overrides.items()):
                raise ValueError("Market-value mapping must contain string keys and values")
            values.update(overrides)
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    source = "api-football"
    season = None
    try:
        key = os.getenv("FOOTBALL_API_KEY", "").strip()
        if not key:
            raise RuntimeError("FOOTBALL_API_KEY is missing")
        players, season = fetch(API(key), values)
    except (OSError, URLError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        reason = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print(f"Using fallback: {reason}. Data may be mock or stale.", file=sys.stderr)
        source = "fallback-mock-or-cache"
        try:
            players = validate(json.loads(args.fallback.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as fallback_error:
            print(f"No valid fallback ({type(fallback_error).__name__}); output unchanged.", file=sys.stderr)
            return 1
    try:
        write_json(args.output, players)
    except OSError as exc:
        print(f"Export failed ({type(exc).__name__}); previous output preserved.", file=sys.stderr)
        return 1
    print(json.dumps({"source": source, "season": season, "league": LEAGUE,
                      "players": len(players), "output": str(args.output.resolve()),
                      "exportedAt": datetime.now(timezone.utc).isoformat()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

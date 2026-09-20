"""Offline regression check: python test_fetch_chelsea.py (no API key needed)."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError

import fetch_chelsea as p


def check():
    shipped = p.validate(json.loads(p.DEFAULT_FILE.read_text(encoding="utf-8")))
    assert len(shipped) >= 20
    assert p.slug("Moisés Caicedo") == "moises-caicedo"
    assert p.number(None) == 0
    try:
        p.number(-1)
        raise AssertionError("negative count accepted")
    except ValueError:
        pass

    calls = []
    def fake_get(endpoint, **params):
        calls.append((endpoint, params))
        if endpoint == "leagues":
            rows = [{"seasons": [{"year": 2026, "current": True, "coverage": {
                "players": True, "fixtures": {"statistics_players": True}}}]}]
        elif endpoint == "players/squads":
            rows = [{"team": {"id": 49}, "players": [
                {"id": 1, "name": "L. Colwill", "number": 6, "position": "Defender"},
                {"id": 2, "name": "Unused Keeper", "number": None, "position": "Goalkeeper"},
                {"id": 3, "name": "C. Palmer", "number": 10, "position": "Midfielder"}]}]
        elif endpoint == "players":
            if params["page"] == 1:
                rows = [{"player": {"id": 1, "name": "L. Colwill", "nationality": "England"},
                         "statistics": [
                             {"team": {"id": 49}, "league": {"id": 39, "season": 2026},
                              "games": {"appearences": 2, "minutes": 180},
                              "goals": None, "cards": {"yellow": None, "red": 1, "yellowred": 1}},
                             {"team": {"id": 50}, "league": {"id": 39, "season": 2026},
                              "games": {"appearences": 99}},
                             {"team": {"id": 49}, "league": {"id": 2, "season": 2026},
                              "games": {"appearences": 99}}]}]
            else:
                rows = [{"player": {"id": 99, "name": "Transferred Player"}, "statistics": None},
                        {"player": {"id": 3, "name": "C. Palmer", "nationality": None},
                         "statistics": None}]
            return {"response": rows, "paging": {"current": params["page"], "total": 2}}
        elif endpoint == "fixtures":
            rows = [{"fixture": {"id": 123}, "teams": {"home": {"id": 49}, "away": {"id": 50}},
                     "goals": {"home": 2, "away": 0}}]
        elif endpoint == "fixtures/players":
            rows = [{"team": {"id": 49}, "players": [
                {"player": {"id": 1}, "statistics": [{"games": {"minutes": 90}}]},
                {"player": {"id": 2}, "statistics": [{"games": {"minutes": None}}]},
                {"player": {"id": 3}, "statistics": [{"games": {"minutes": 90}}]}]}]
        else:
            raise AssertionError(endpoint)
        return {"response": rows}

    api = p.API("fake")
    with patch.object(api, "get", side_effect=fake_get):
        players, season = p.fetch(api, p.MARKET_VALUES)
    by_id = {x["id"]: x for x in players}
    assert season == 2026 and len(players) == 3
    assert by_id["levi-colwill"]["stats"] == dict(zip(p.STAT_KEYS, [2, 180, 0, 0, 1, 0, 2]))
    assert by_id["unused-keeper"]["jerseyNumber"] == 0
    assert not any(by_id["unused-keeper"]["stats"].values())
    assert by_id["cole-palmer"]["marketValue"] == "€120M"
    assert by_id["cole-palmer"]["stats"]["cleanSheets"] == 0
    assert [params["page"] for endpoint, params in calls if endpoint == "players"] == [1, 2]

    # Transport envelope errors, credentials, throttling and bounded retries.
    def response(errors=None):
        return io.StringIO(json.dumps({"errors": errors or [], "response": []}))
    with patch.object(p, "urlopen", side_effect=lambda *a, **k: response()), \
         patch.object(p.time, "monotonic", return_value=100), patch.object(p.time, "sleep") as sleep:
        api = p.API("secret")
        api.get("players", page=1)
        api.get("players", page=2)
        sleep.assert_called_once_with(6.1)
    with patch.object(p, "urlopen", side_effect=lambda *a, **k: response({"token": "bad"})):
        try:
            p.API("invalid").get("players")
            raise AssertionError("API error ignored")
        except RuntimeError:
            pass
    unauthorized = HTTPError("url", 401, "Unauthorized", {}, None)
    with patch.object(p, "urlopen", side_effect=unauthorized) as request:
        try:
            p.API("invalid").get("players")
            raise AssertionError("401 ignored")
        except RuntimeError:
            assert request.call_count == 1
    limited = HTTPError("url", 429, "Limited", {"Retry-After": "90"}, None)
    with patch.object(p, "urlopen", side_effect=[limited, response()]), \
         patch.object(p.time, "sleep") as sleep:
        p.API("key").get("players")
        assert any(call.args == (90,) for call in sleep.call_args_list)

    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / "players.json"
        def run(fallback=p.DEFAULT_FILE):
            with patch("sys.argv", ["fetch", "--output", str(output), "--fallback", str(fallback)]), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return p.main()
        with patch.dict(os.environ, {}, clear=True):
            assert run() == 0
            assert json.loads(output.read_text(encoding="utf-8")) == shipped
        original = output.read_bytes()
        with patch.dict(os.environ, {"FOOTBALL_API_KEY": "invalid"}, clear=True), \
             patch.object(p, "urlopen", side_effect=unauthorized):
            assert run() == 0
            assert output.read_bytes() == original
            broken = Path(folder) / "broken.json"
            broken.write_text("{", encoding="utf-8")
            assert run(broken) == 1
            assert output.read_bytes() == original
        with patch.object(p.os, "replace", side_effect=OSError("disk failure")):
            try:
                p.write_json(output, players)
                raise AssertionError("write failure swallowed")
            except OSError:
                assert output.read_bytes() == original
                assert not list(Path(folder).glob("*.tmp"))
    print("PASS: schema, pagination, nulls, filtering, clean sheets, rate limit, retries, fallback, atomic writes")


if __name__ == "__main__":
    check()

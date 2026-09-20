"""Refresh the standalone site from API-Football and verified dated valuations.

Run from any directory: python refresh_vault.py
Private credentials: ../.env (outside the public outputs directory).
On failure the last good performance snapshot is preserved and labeled honestly.
"""
import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

from fetch_chelsea import API, fetch, validate, write_json

ROOT = Path(__file__).resolve().parent


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.strip().startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        if name.strip() in {'FOOTBALL_API_KEY'}:
            os.environ.setdefault(name.strip(), value.strip().strip('"\''))


def read_market(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    seen = set()
    if not data.get('players'):
        raise ValueError('Empty valuation snapshot')
    for row in data['players']:
        if row['id'] in seen or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row['id']):
            raise ValueError('Invalid valuation identity')
        seen.add(row['id'])
        if type(row['valueEur']) is not int or row['valueEur'] < 0:
            raise ValueError('Invalid valuation amount')
        if date.fromisoformat(row['valuationDate']) > date.today():
            raise ValueError('Future valuation date')
        if not row['sourceUrl'].startswith('https://www.transfermarkt.us/'):
            raise ValueError('Unexpected valuation source')
    return data


def script_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def publish(html, snapshot):
    """Only replace data declarations; media and presentation stay byte-identical."""
    if snapshot.get('players'):
        players = validate(snapshot['players'])
        html, count = re.subn(r'const PLAYERS = .*?;', lambda _: 'const PLAYERS = '+script_json(players)+';', html, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Player declaration not found')
        season = snapshot['performance']['season']
        provider = 'API-Football' if snapshot['performance']['source'] == 'api-football' else 'Transfermarkt'
        html = re.sub(r'(?:2026/27 squad · Illustrative statistics|\d{4}/\d{2} squad · (?:API-Football|Transfermarkt) snapshot)', f'{season}/{str(season+1)[-2:]} squad · {provider} snapshot', html)
        html = re.sub(r'(?:Sample data / 2026–27|(?:API-Football|Transfermarkt) / \d{4}–\d{2})', f'{provider} / {season}–{str(season+1)[-2:]}', html)
        html = html.replace('Sample squad goals', 'Squad league goals')
        html = html.replace('Sample squad data; not a performance rating.', 'Squad snapshot; not a performance rating.')
    block = '<script id="vault-data">\nconst VAULT_PROVENANCE = '+script_json(snapshot['performance'])+';\nconst VAULT_MARKET = '+script_json(snapshot['market'])+';\nconst VAULT_ANALYTICS_PLAYERS = '+script_json(snapshot.get('analyticsPlayers'))+';\n</script>'
    if '<script id="vault-data">' in html:
        html = re.sub(r'<script id="vault-data">.*?</script>', lambda _: block, html, count=1, flags=re.S)
    else:
        html = html.replace('</head>', block+'\n</head>', 1)
    return html


def write_site(path, html):
    # Atomic replacement prevents an interrupted refresh from truncating embedded media.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix='.tmp') as handle:
            temporary = Path(handle.name)
            handle.write(html.encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT.parent/'.env')
    parser.add_argument('--site', type=Path, default=ROOT/'chelsea-squad_1.html')
    parser.add_argument('--valuations', type=Path, default=ROOT/'market_valuations.json')
    parser.add_argument('--publish-only', action='store_true', help='Publish saved data without any API requests')
    args = parser.parse_args()
    load_env(args.env_file)
    cache = ROOT/'vault_snapshot.json'
    snapshot = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {'performance':{'source':'demo','season':2026,'retrievedAt':None},'players':None}
    snapshot['market'] = read_market(args.valuations)
    failed = False
    if not args.publish_only:
        now = datetime.now(timezone.utc).isoformat()
        try:
            key = os.getenv('FOOTBALL_API_KEY', '').strip()
            if not key or key == 'your_api_key_here':
                raise RuntimeError('API key missing')
            values = {r['id']:f"€{r['valueEur']/1e6:g}M" for r in snapshot['market']['players']}
            players, season = fetch(API(key), values)
            snapshot.update(players=players, analyticsPlayers=players, performance={'source':'api-football','season':season,'retrievedAt':now,'lastAttemptAt':now,'refreshError':None,'competition':'Premier League','teamId':49})
        except (OSError, RuntimeError, ValueError, KeyError, TypeError, AttributeError):
            failed = True
            snapshot['performance'].update(lastAttemptAt=now, refreshError='Current-season refresh unavailable. Check API plan access, quota and connection. Previous performance data retained.')
    html = publish(args.site.read_bytes().decode('utf-8'), snapshot)
    write_site(args.site, html)
    write_json(cache, snapshot)
    if snapshot.get('players'):
        write_json(ROOT/'chelsea_players.json', snapshot['players'])
    print(json.dumps({'performanceSource':snapshot['performance']['source'],'valuations':len(snapshot['market']['players']),'refreshSucceeded':not failed,'site':str(args.site)}))
    return 2 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

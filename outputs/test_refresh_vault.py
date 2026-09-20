"""Offline checks: python test_refresh_vault.py"""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import refresh_vault as r

def check():
    market=r.read_market(r.ROOT/'market_valuations.json')
    assert len(market['players'])==27
    assert sum(p['valueEur'] for p in market['players'])==1076700000
    snapshot=json.loads((r.ROOT/'vault_snapshot.json').read_text(encoding='utf-8'))
    players=snapshot['analyticsPlayers']
    palmer=next(p for p in players if p['id']=='cole-palmer')
    assert palmer['stats']['minutesPlayed']==443 and palmer['stats']['goals']==2
    assert all(p['stats']['cleanSheets'] is None for p in players)
    assert {p['id'] for p in players}=={p['id'] for p in market['players']}
    assert all(0<=p['stats']['minutesPlayed']<=p['stats']['appearances']*90 for p in players)
    original='<head></head><video src="data:video/test;base64,keep"></video><script>const PLAYERS = [];const PLAYER_PHOTOS = {"keep":"photo"};</script>'
    updated=r.publish(original,snapshot)
    assert '<video src="data:video/test;base64,keep"></video>' in updated
    assert 'const PLAYERS = [];' not in updated
    assert snapshot['players']==players
    assert r.publish(updated,snapshot)==updated
    assert '</script>' not in r.script_json({'name':'</script><script>alert(1)</script>'})
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        (root/'market_valuations.json').write_text(json.dumps(market),encoding='utf-8')
        (root/'vault_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
        site=root/'test.html'; site.write_text(updated,encoding='utf-8')
        with patch.object(r,'ROOT',root),patch.object(r,'fetch',side_effect=RuntimeError('plan blocked')),patch.object(r,'load_env'),patch.dict(r.os.environ,{'FOOTBALL_API_KEY':'test-not-real'}),patch('sys.argv',['refresh','--site',str(site),'--valuations',str(r.ROOT/'market_valuations.json')]):
            assert r.main()==2
        saved=json.loads((root/'vault_snapshot.json').read_text(encoding='utf-8'))
        assert saved['analyticsPlayers']==players
        assert saved['performance']['source']=='transfermarkt-snapshot'
        assert saved['performance']['refreshError']
    print('PASS: source joins, dates, snapshot preservation, safe embedding, failed refresh retention')

if __name__=='__main__':
    check()

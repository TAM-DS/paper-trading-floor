import math
from datetime import date,timedelta
import pytest
from floor.market import MarketData,DataError,analytics,backtest,validate

def sample():
    end=date.today()-timedelta(days=1)
    return MarketData().load('XLE',end-timedelta(days=240),end)

def test_demo_is_explicit_and_metrics_finite():
    d=sample(); m=analytics(d)
    assert d['source']=='synthetic-demo' and len(d['sha256'])==64
    assert m['max_drawdown_pct']<=0 and m['volatility_pct']>=0
    assert all(math.isfinite(v) for v in m.values() if isinstance(v,(float,int)))

def test_corrupt_bars_rejected():
    d=sample(); d['rows'][3]['c']=float('nan')
    with pytest.raises(DataError): validate(d['rows'])

def test_duplicate_time_rejected():
    d=sample(); d['rows'][3]['t']=d['rows'][2]['t']
    with pytest.raises(DataError): validate(d['rows'])

def test_missing_key_never_falls_back(monkeypatch):
    monkeypatch.delenv('MASSIVE_API_KEY',raising=False)
    end=date.today()-timedelta(days=1)
    with pytest.raises(DataError,match='MASSIVE_API_KEY'): MarketData().load('XLE',end-timedelta(days=240),end,'massive')

def test_cache_miss_explicit(tmp_path):
    end=date.today()-timedelta(days=1)
    with pytest.raises(DataError,match='No saved'): MarketData(tmp_path).load('XLE',end-timedelta(days=240),end,'cache')

def test_costs_reduce_holdout_return():
    d=sample()
    assert backtest(d,100)['net_return_pct']<=backtest(d,0)['net_return_pct']

def test_next_open_return_known_answer():
    d=sample()
    for i,r in enumerate(d['rows']):
        p=100+i
        r.update(o=p,c=p,h=p,l=p)
    split=int(len(d['rows'])*.7)
    expected=100*(d['rows'][-1]['o']/d['rows'][split]['o']-1)
    assert backtest(d,0)['net_return_pct']==pytest.approx(expected)


def test_http_error_redacts_key(monkeypatch):
    from urllib.error import HTTPError
    monkeypatch.setenv('MASSIVE_API_KEY','PRIVATE_TEST_KEY')
    def fail(req,timeout):
        assert req.headers['Authorization']=='Bearer PRIVATE_TEST_KEY'
        raise HTTPError(req.full_url,429,'rate limit',{},None)
    end=date.today()-timedelta(days=1)
    with pytest.raises(DataError) as err: MarketData(opener=fail).load('XLE',end-timedelta(days=240),end,'massive')
    assert '429' in str(err.value) and 'PRIVATE_TEST_KEY' not in str(err.value)

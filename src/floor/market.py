"""Validated end-of-day data and deterministic analytics. No order authority."""
import hashlib
import json
import math
import os
import re
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class DataError(ValueError):
    pass

def validate(rows):
    if len(rows) < 60:
        raise DataError("At least 60 daily bars required")
    previous = -1
    for r in rows:
        if any(isinstance(r.get(k), bool) or not isinstance(r.get(k), (int,float)) or not math.isfinite(r[k]) for k in ('t','o','h','l','c','v')):
            raise DataError("Non-finite or missing OHLCV")
        if r['t'] <= previous or min(r['o'],r['h'],r['l'],r['c']) <= 0 or r['v'] < 0 or r['l'] > min(r['o'],r['c']) or r['h'] < max(r['o'],r['c']) or r['l'] > r['h']:
            raise DataError("Invalid or unordered OHLCV")
        previous=r['t']
    return rows

class MarketData:
    def __init__(self, cache='.cache/market', opener=urlopen, clock=time.monotonic, sleep=time.sleep):
        self.cache=Path(cache); self.opener=opener; self.clock=clock; self.sleep=sleep; self.last=None

    def load(self, ticker, start, end, mode='demo'):
        ticker=ticker.strip().upper()
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',ticker): raise DataError('Invalid ticker')
        start,end=date.fromisoformat(str(start)),date.fromisoformat(str(end))
        if start>end or end>=date.today() or (end-start).days>730: raise DataError('Use completed dates, ordered, within a two-year window')
        if mode=='demo':
            rows=[]; price=80+sum(map(ord,ticker))%70; day=start; i=0
            while day<=end:
                if day.weekday()<5:
                    op=price; price*=1+0.0004+0.009*math.sin(i*0.7+sum(map(ord,ticker)))
                    rows.append(dict(t=int(datetime.combine(day,datetime.min.time(),timezone.utc).timestamp()*1000),o=op,c=price,h=max(op,price)*1.003,l=min(op,price)*.997,v=1000000+i*1000)); i+=1
                day+=timedelta(days=1)
            source='synthetic-demo'; request_id=None
        elif mode in ('massive','cache'):
            path=self.cache/f'{ticker}-{start}-{end}.json'
            if mode=='cache':
                if not path.exists(): raise DataError('No saved Massive response for this exact range')
                payload=json.loads(path.read_text())
            else:
                key=os.getenv('MASSIVE_API_KEY')
                if not key: raise DataError('Set MASSIVE_API_KEY in your local environment')
                if self.last is not None: self.sleep(max(0,12.5-(self.clock()-self.last)))
                self.last=self.clock()
                url=f'https://api.massive.com/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000'
                try:
                    with self.opener(Request(url,headers={'Authorization':f'Bearer {key}'}),timeout=30) as response: payload=json.load(response)
                except HTTPError as e: raise DataError(f'Massive HTTP {e.code}: check access or retry later') from None
                except (URLError,TimeoutError): raise DataError('Massive connection failed; choose cache explicitly') from None
                if payload.get('status') not in ('OK','DELAYED') or payload.get('ticker')!=ticker or payload.get('next_url') or payload.get('adjusted') is not True: raise DataError('Incomplete or unexpected Massive response')
                validate(payload.get('results',[]))
                self.cache.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload))
            rows=payload.get('results',[]); source='massive-eod' if mode=='massive' else 'massive-eod-cache'; request_id=payload.get('request_id')
        else: raise DataError('Unknown data mode')
        validate(rows)
        for row in rows:
            d=datetime.fromtimestamp(row['t']/1000,timezone.utc).date()
            if not start<=d<=end: raise DataError('Bar outside requested date range')
        digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        return dict(ticker=ticker,source=source,request_id=request_id,start=str(start),end=str(end),as_of=datetime.fromtimestamp(rows[-1]['t']/1000,timezone.utc).date().isoformat(),sha256=digest,rows=rows)

def analytics(data):
    rows=validate(data['rows']); closes=[r['c'] for r in rows]
    returns=[b/a-1 for a,b in zip(closes,closes[1:])]
    peak=closes[0]; dd=0
    for p in closes: peak=max(peak,p); dd=min(dd,p/peak-1)
    vol=statistics.stdev(returns)*math.sqrt(252)
    return dict(ticker=data['ticker'],source=data['source'],as_of=data['as_of'],sha256=data['sha256'],close=closes[-1],return_pct=100*(closes[-1]/closes[0]-1),momentum_20d_pct=100*(closes[-1]/closes[-21]-1),volatility_pct=100*vol,max_drawdown_pct=100*dd,avg_dollar_volume_20d=statistics.mean(r['c']*r['v'] for r in rows[-20:]),bars=len(rows))

def backtest(data, cost_bps=10):
    """Fixed 20-day SMA; prior close signal, next-open execution, open-to-open returns."""
    rows=validate(data['rows']); split=int(len(rows)*.7); equity=benchmark=1.; peak=1.; drawdown=0.; previous=0; changes=0
    for i in range(split,len(rows)-1):
        position=int(rows[i-1]['c']>statistics.mean(r['c'] for r in rows[i-20:i]))
        turnover=abs(position-previous); changes+=turnover
        gross=rows[i+1]['o']/rows[i]['o']-1
        equity*=1+position*gross-turnover*cost_bps/10000; benchmark*=1+gross
        peak=max(peak,equity); drawdown=min(drawdown,equity/peak-1); previous=position
    equity*=1-previous*cost_bps/10000
    return dict(strategy='Fixed SMA20, long/cash',test_start=datetime.fromtimestamp(rows[split]['t']/1000,timezone.utc).date().isoformat(),net_return_pct=100*(equity-1),benchmark_return_pct=100*(benchmark-1),max_drawdown_pct=100*min(drawdown,equity/peak-1),position_changes=changes,cost_bps=cost_bps,limitations='Chronological final 30%; no tuning. Split-adjusted prices, not total returns. No dividends, financing, market impact, or point-in-time universe. Synthetic runs establish mechanics only.')

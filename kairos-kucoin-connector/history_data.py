"""KuCoin daily candles, incremental SQLite cache, no fabricated missing bars.

Public Spot only. Every series retains its own provider. No trading/account I/O.
"""
import copy
import datetime as dt
import json
import math
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import market_data as market
from technical import indicator_series

_LOCK=threading.RLock()
DAY=86400
CANDLES_URL='https://api.kucoin.com/api/v1/market/candles'

def _positive(v,zero=False):
    if isinstance(v,bool):raise ValueError('Boolean candle number')
    n=float(v)
    if not math.isfinite(n) or (n<0 if zero else n<=0):raise ValueError('Invalid candle number')
    return n

def normalize_candles(payload,start,end):
    if not isinstance(payload,dict) or payload.get('code')!='200000':raise ValueError('KuCoin candle API status not OK')
    rows=payload.get('data')
    if not isinstance(rows,list):raise ValueError('Invalid candle list')
    found={}
    for row in rows:
        if not isinstance(row,list) or len(row)<7:raise ValueError('Malformed candle row')
        raw=float(row[0]);stamp=int(raw)
        if stamp!=raw or stamp%DAY:raise ValueError('Non-UTC daily candle')
        # KuCoin may include the currently open candle: never retain it.
        if stamp<start or stamp+DAY>end:continue
        o,c,h,l=(_positive(row[i]) for i in (1,2,3,4))
        v,q=(_positive(row[i],zero=True) for i in (5,6))
        if not l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid OHLC range')
        value={'open_utc':market.utc(stamp),'close_utc':market.utc(stamp+DAY),
               'open':str(row[1]),'high':str(row[3]),'low':str(row[4]),'close':str(row[2]),
               'volume':str(row[5]),'quote_volume':str(row[6])}
        if stamp in found:raise ValueError('Duplicate daily candle')
        found[stamp]=value
    return found

def _fetch(symbol,start,end):
    until=market.cooldown()
    if until>time.time():return market.blocked(until)
    params={'symbol':symbol[:-4]+'-USDT','type':'1day','startAt':start,'endAt':end-1}
    request=urllib.request.Request(CANDLES_URL+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'KairosKuCoin/1.1','Accept':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            body=response.read(4*1024*1024+1)
            if len(body)>4*1024*1024:raise ValueError('Candle response too large')
            payload=json.loads(body)
            if str(payload.get('code'))=='429000':
                until=market.retry_deadline(response.headers,time.time());market.cooldown(until);return market.blocked(until)
        return normalize_candles(payload,start,end)
    except urllib.error.HTTPError as exc:
        if exc.code in (418,429):
            until=market.retry_deadline(exc.headers,time.time());market.cooldown(until);return market.blocked(until)
        return market.failure('KuCoin candle upstream HTTP error',http_status=exc.code)
    except (OSError,TimeoutError):return market.failure('KuCoin historical network unavailable',error_category='NETWORK')


def ohlcv(symbol='BTCUSDT',interval='1d',limit=999,*,now=None):
    if symbol not in market.SYMBOLS or interval!='1d' or type(limit)!=int or not 1<=limit<=1500:
        return market.failure('Use an approved TOKENUSDT, interval1d, limit1..1500')
    now=time.time() if now is None else now
    end=int(now//DAY)*DAY;start=end-limit*DAY
    try:
        with _LOCK,sqlite3.connect(market.STATE_PATH,timeout=5) as db:
            db.execute('CREATE TABLE IF NOT EXISTS daily_bars (symbol TEXT, stamp INTEGER, body TEXT, PRIMARY KEY(symbol,stamp))')
            db.execute('CREATE TABLE IF NOT EXISTS daily_coverage (symbol TEXT PRIMARY KEY, start INTEGER, end INTEGER)')
            coverage=db.execute('SELECT start,end FROM daily_coverage WHERE symbol=?',(symbol,)).fetchone()
            cached={int(t):json.loads(body) for t,body in db.execute('SELECT stamp,body FROM daily_bars WHERE symbol=? AND stamp>=? AND stamp<? ORDER BY stamp',(symbol,start,end))}
            fresh=coverage and coverage[0]<=start and coverage[1]>=end
            if not fresh:
                fetch_start=max(start,coverage[1]) if coverage and coverage[0]<=start else start
                incoming=_fetch(symbol,fetch_start,end)
                if incoming.get('status')=='DATA_ERROR':return incoming
                merged={**cached,**incoming}
                stamps=sorted(merged)
                if not stamps or stamps[-1]!=end-DAY or any(b-a!=DAY for a,b in zip(stamps,stamps[1:])):
                    raise ValueError('Incomplete daily history; gaps are never synthesized')
                for stamp,row in incoming.items():
                    db.execute('INSERT OR REPLACE INTO daily_bars VALUES(?,?,?)',(symbol,stamp,json.dumps(row)))
                oldest=min(start,coverage[0]) if coverage and coverage[1]>=start else start
                db.execute('INSERT INTO daily_coverage VALUES(?,?,?) ON CONFLICT(symbol) DO UPDATE SET start=excluded.start,end=excluded.end',(symbol,oldest,end))
                cached=merged
            stamps=sorted(cached)
            if not stamps or stamps[-1]!=end-DAY or any(b-a!=DAY for a,b in zip(stamps,stamps[1:])):raise ValueError('Cached history incomplete')
            records=[cached[t] for t in stamps]
            return {'status':'OK','source':'KuCoin Spot','provider':'KUCOIN','symbol':symbol,
                    'interval':'1d','closed_only':True,'count':len(records),'records':records,
                    'coverage_start_utc':records[0]['open_utc'],'requested_start_utc':market.utc(start),
                    'coverage_complete':len(records)==limit,'as_observed_utc':market.utc(now),
                    'cache_hit':bool(fresh),'note':'Leading history may be shorter since listing. Internal gaps fail closed. No mixed providers.'}
    except (ValueError,TypeError,KeyError,OverflowError,sqlite3.Error) as exc:
        return market.failure(str(exc))


def history_snapshot():
    histories={};indicators={}
    for symbol in market.SYMBOLS:
        data=ohlcv(symbol)
        if data.get('status')!='OK':return {**data,'failed_symbol':symbol,'histories':{},'indicators':{}}
        key=symbol+':1d';histories[key]=data
        seq=indicator_series([float(row['close']) for row in data['records']])
        values={k:round(v[-1],10) if v[-1] is not None else None for k,v in seq.items()}
        indicators[key]={'status':'OK' if all(v is not None for v in values.values()) else 'DATA_ERROR',
                         'source':'KuCoin Spot','symbol':symbol,'interval':'1d','closed_only':True,
                         'close_utc':data['records'][-1]['close_utc'],'history_candles':data['count'],'values':values}
    return {'status':'OK','source':'KuCoin Spot','provider':'KUCOIN','policy':'MANUAL_SNAPSHOT',
            'histories':histories,'indicators':indicators,'cycles':{},'as_observed_utc':market.utc(time.time()),
            'note':'Daily series only; cycle candidates are computed downstream. HYPE macro remains Hyperliquid.'}

"""Public KuCoin Spot quotes only. No account keys, orders, or background jobs."""
import copy
import datetime as dt
import email.utils
import json
import math
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request

SYMBOLS=tuple(s+'USDT' for s in ('BTC','ETH','SOL','LINK','HYPE','HBAR','SUI','ONDO','PUMP','PLUME','PEPE','VIRTUAL'))
URL='https://api.kucoin.com/api/v1/market/allTickers'
STATE_PATH=os.getenv('KUCOIN_GUARD_DB','/tmp/kairos-kucoin-guard.sqlite3')
_LOCK=threading.Lock()
_CACHE=None

def utc(stamp):return dt.datetime.fromtimestamp(stamp,dt.timezone.utc).isoformat()

def cooldown(until=None):
    with sqlite3.connect(STATE_PATH,timeout=2) as db:
        db.execute('CREATE TABLE IF NOT EXISTS cooldown (id INTEGER PRIMARY KEY, until REAL)')
        if until is not None:db.execute('INSERT INTO cooldown VALUES(1,?) ON CONFLICT(id) DO UPDATE SET until=max(until,excluded.until)',(until,))
        row=db.execute('SELECT until FROM cooldown WHERE id=1').fetchone()
        return row[0] if row else 0

def retry_deadline(headers,now):
    headers=headers or {}
    values=[now+1]
    raw=headers.get('Retry-After')
    if raw:
        try:values.append(now+float(raw))
        except ValueError:
            try:values.append(email.utils.parsedate_to_datetime(raw).timestamp())
            except (ValueError,TypeError,OverflowError):pass
    try:
        reset=float(headers.get('gw-ratelimit-reset','nan'))
        if math.isfinite(reset) and reset>=0:values.append(now+reset/1000)
    except ValueError:pass
    return max(values) if len(values)>1 else now+60

def failure(reason,**meta):
    return dict(status='DATA_ERROR',source='KuCoin Spot',provider='KUCOIN',reason=reason,records=[],**meta)

def blocked(until):
    return failure('KuCoin rate limit; requests paused',http_status=429,retry_at_utc=utc(until),retry_after_seconds=max(0,math.ceil(until-time.time())))

def validate(payload,now=None):
    now=time.time() if now is None else now
    if not isinstance(payload,dict) or payload.get('code')!='200000':raise ValueError('KuCoin API status not OK')
    data=payload['data'];timestamp=float(data['time'])/1000
    if not math.isfinite(timestamp) or not -30<=now-timestamp<=180:raise ValueError('Stale or future KuCoin snapshot')
    rows=data['ticker']
    if not isinstance(rows,list):raise ValueError('Invalid ticker list')
    wanted={s[:-4]+'-USDT':s for s in SYMBOLS};quotes={}
    def positive(v):
        if isinstance(v,bool):raise ValueError('Invalid quote')
        n=float(v)
        if not math.isfinite(n) or n<=0:raise ValueError('Invalid quote')
        return n
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Invalid ticker record')
        symbol=row.get('symbol')
        if symbol not in wanted:continue
        canonical=wanted[symbol]
        if canonical in quotes:raise ValueError('Duplicate KuCoin symbol')
        px,bid,ask=(positive(row[k]) for k in ('last','buy','sell'))
        if bid>ask:raise ValueError('Crossed market')
        quotes[canonical]=dict(symbol=canonical,exchange_symbol=symbol,price=str(row['last']),best_bid=str(row['buy']),best_ask=str(row['sell']),spread_pct=100*(ask-bid)/((bid+ask)/2),source='KuCoin Spot',as_observed_utc=utc(timestamp))
    missing=set(SYMBOLS)-quotes.keys()
    if missing:raise ValueError('Missing KuCoin pairs: '+','.join(sorted(missing)))
    return dict(status='OK',source='KuCoin Spot',provider='KUCOIN',as_observed_utc=utc(timestamp),records=[quotes[s] for s in SYMBOLS],atomic=False,note='Public allTickers snapshot time; not an individual trade timestamp. KuCoin prices may differ from Binance; no account access.')

def spot_prices(symbols=None):
    global _CACHE
    if symbols is not None and (not isinstance(symbols,list) or not symbols or len(set(symbols))!=len(symbols) or any(s not in SYMBOLS for s in symbols)):
        return failure('Unsupported symbols; use unique Kairos TOKENUSDT pairs')
    selected=symbols or SYMBOLS
    with _LOCK:
        if _CACHE and time.monotonic()-_CACHE[0]<60:
            result=copy.deepcopy(_CACHE[1])
        else:
            until=cooldown()
            if until>time.time():return blocked(until)
            try:
                req=urllib.request.Request(URL,headers={'User-Agent':'KairosKuCoin/1.0','Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=12) as response:
                    body=response.read(8*1024*1024+1)
                    if len(body)>8*1024*1024:raise ValueError('Response too large')
                    payload=json.loads(body)
                    if isinstance(payload,dict) and str(payload.get('code'))=='429000':
                        until=retry_deadline(response.headers,time.time());cooldown(until);return blocked(until)
                result=validate(payload)
                _CACHE=(time.monotonic(),copy.deepcopy(result))
            except urllib.error.HTTPError as exc:
                if exc.code in (418,429):
                    until=retry_deadline(exc.headers,time.time());cooldown(until);return blocked(until)
                return failure('KuCoin upstream HTTP error',http_status=exc.code)
            except (ValueError,KeyError,TypeError,OverflowError) as exc:return failure(str(exc))
            except (OSError,TimeoutError):return failure('KuCoin network unavailable',error_category='NETWORK')
        result['records']=[r for r in result['records'] if r['symbol'] in selected]
        return result

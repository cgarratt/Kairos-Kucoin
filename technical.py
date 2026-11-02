"""Pure closed-candle indicators; same formulas as Kairos Binance. No I/O."""
def _sma(values,period):
    result=[None]*len(values)
    for i in range(period-1,len(values)):
        window=values[i-period+1:i+1]
        if all(v is not None for v in window): result[i]=sum(window)/period
    return result


def _ema(values,period):
    result=[None]*len(values)
    if len(values)<period:return result
    seed=values[:period]
    if any(v is None for v in seed): return result
    prev=sum(seed)/period;result[period-1]=prev
    alpha=2/(period+1)
    for i in range(period,len(values)):
        prev=alpha*values[i]+(1-alpha)*prev
        result[i]=prev
    return result


def _rsi(closes,period=14):
    out=[None]*len(closes)
    if len(closes)<=period:return out
    changes=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gain=sum(max(c,0) for c in changes[:period])/period
    loss=sum(max(-c,0) for c in changes[:period])/period
    def value(g,l):
        if l==0:return 100.0 if g>0 else 50.0
        return 100-100/(1+g/l)
    out[period]=value(gain,loss)
    for i in range(period+1,len(closes)):
        c=changes[i-1]
        gain=(gain*(period-1)+max(c,0))/period
        loss=(loss*(period-1)+max(-c,0))/period
        out[i]=value(gain,loss)
    return out


def _rolling_sma_nullable(values,period):
    out=[None]*len(values)
    for i in range(period-1,len(values)):
        w=values[i-period+1:i+1]
        if all(v is not None for v in w): out[i]=sum(w)/period
    return out


def indicator_series(closes):
    rsi=_rsi(closes,14)
    rsi_ma=_rolling_sma_nullable(rsi,14)
    raw=[None]*len(closes)
    for i in range(13,len(closes)):
        window=rsi[max(0,i-13):i+1]
        if len(window)==14 and all(x is not None for x in window):
            lo=min(window);hi=max(window)
            raw[i]=0.0 if hi==lo else 100*(rsi[i]-lo)/(hi-lo)
    k=_rolling_sma_nullable(raw,3)
    d=_rolling_sma_nullable(k,3)
    return {'rsi14':rsi, 'rsi_ma14_sma':rsi_ma,'stoch_rsi_k':k,'stoch_rsi_d':d,
            'ema20':_ema(closes,20),'ema50':_ema(closes,50),
            'ema100':_ema(closes,100),'ema200':_ema(closes,200)}



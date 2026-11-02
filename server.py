"""Kairos KuCoin MCP: public Spot primary valuation, read-only."""
import os
from fastmcp import FastMCP
from market_data import spot_prices
from history_data import ohlcv, history_snapshot
mcp=FastMCP('Kairos KuCoin Market Data')

@mcp.tool()
def get_kairos_kucoin_service_info() -> dict:
    """Local release identity and capabilities; no upstream API request."""
    return {'service':'MCP_KuCoin','version':'1.1.0',
            'release_suite':'2026.11.02.7','read_only':True,'data_scope':'Primary KuCoin Spot and closed daily history, separate from Binance'}

@mcp.tool()
def get_kairos_kucoin_spot_prices(symbols: list[str] | None = None) -> dict:
    """One public KuCoin allTickers request for all 12 Kairos USDT pairs, cached60s. Fails closed on missing/invalid/stale pairs. No account credentials or trading."""
    return spot_prices(symbols)

@mcp.tool()
def get_kairos_kucoin_ohlcv(symbol: str = 'BTCUSDT', interval: str = '1d', limit: int = 999) -> dict:
    """Closed UTC KuCoin daily OHLCV only. Incremental SQLite cache; gaps fail, short leading listing history explicit. No mixed providers, max1500."""
    return ohlcv(symbol,interval,limit)

@mcp.tool()
def get_kairos_kucoin_history_snapshot() -> dict:
    """12 separate KuCoin daily series plus daily indicators; no Spot refresh. Reuses closed history, fetches only new days. HYPE macro is separate."""
    return history_snapshot()

if __name__=='__main__':
    mcp.run(transport='http',host='0.0.0.0',port=int(os.getenv('PORT','10000')))

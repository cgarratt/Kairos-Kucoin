"""Kairos KuCoin MCP: public Spot valuation backup, read-only."""
import os
from fastmcp import FastMCP
from market_data import spot_prices
mcp=FastMCP('Kairos KuCoin Market Data')

@mcp.tool()
def get_kairos_kucoin_service_info() -> dict:
    """Local release identity and capabilities; no upstream API request."""
    return {'service':'MCP_KuCoin','version':'1.0.1',
            'release_suite':'2026.11.02.1','read_only':True,'data_scope':'KuCoin Spot valuation backup only; no historical-source substitution'}

@mcp.tool()
def get_kairos_kucoin_spot_prices(symbols: list[str] | None = None) -> dict:
    """One public KuCoin allTickers request for all 12 Kairos USDT pairs, cached60s. Fails closed on missing/invalid/stale pairs. No account credentials, trading or historical-source substitution."""
    return spot_prices(symbols)

if __name__=='__main__':
    mcp.run(transport='http',host='0.0.0.0',port=int(os.getenv('PORT','10000')))

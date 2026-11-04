"""Read-only remote discovery. Calls service_info only, never exchange history."""
import argparse
import asyncio
import json
from urllib.parse import urlsplit
from fastmcp import Client
from server import EXPECTED_TOOLS

async def verify(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use HTTPS /mcp sin credenciales ni parámetros')
    async with Client(url,timeout=30) as client:
        names=sorted(t.name for t in await client.list_tools())
        info=await client.call_tool('get_kairos_kucoin_service_info',{})
        body=json.loads(info.content[0].text)
        ok=set(names)==set(EXPECTED_TOOLS) and body.get('version')=='1.1.1'
        print(json.dumps({'status':'OK' if ok else 'MISMATCH','tools':names,'service_info':body,
            'scope':'Discovery y versión; no verifica datos de KuCoin ni catálogo cacheado en ChatGPT'},indent=2))
        return 0 if ok else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Verifica cuatro herramientas publicadas y versión remota')
    parser.add_argument('url',help='Endpoint HTTPS del servicio existente, terminado en /mcp')
    args=parser.parse_args()
    raise SystemExit(asyncio.run(verify(args.url)))

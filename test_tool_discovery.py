"""MCP protocol tests use synthetic data; never query KuCoin upstream."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from fastmcp import Client
import server

class Discovery(unittest.IsolatedAsyncioTestCase):
    async def test_exactly_four_tools_and_history_schemas(self):
        async with Client(server.mcp) as client:
            tools=await client.list_tools()
            self.assertEqual(set(t.name for t in tools),set(server.EXPECTED_TOOLS))
            self.assertEqual(len(tools),4)
            schemas={t.name:t.inputSchema for t in tools}
            properties=schemas['get_kairos_kucoin_ohlcv']['properties']
            self.assertEqual(set(properties),{'symbol','interval','limit'})
            self.assertEqual(properties['symbol']['default'],'BTCUSDT')
            self.assertEqual(properties['interval']['default'],'1d')
            self.assertEqual(properties['limit']['default'],999)
    async def test_service_identity_and_historical_dispatch(self):
        sample={'status':'OK','source':'KuCoin Spot','test_only':True}
        with patch.object(server,'ohlcv',return_value=sample) as one, patch.object(server,'history_snapshot',return_value=sample) as all_series:
            async with Client(server.mcp) as client:
                result=await client.call_tool('get_kairos_kucoin_service_info',{})
                body=json.loads(result.content[0].text)
                self.assertEqual(body['version'],'1.1.1')
                self.assertEqual(body['expected_tool_count'],4)
                for name,args in [('get_kairos_kucoin_ohlcv',{'symbol':'BTCUSDT','interval':'1d','limit':90}),('get_kairos_kucoin_history_snapshot',{})]:
                    result=await client.call_tool(name,args)
                    self.assertFalse(result.is_error)
                    self.assertTrue(json.loads(result.content[0].text)['test_only'])
                one.assert_called_once_with('BTCUSDT','1d',90)
                all_series.assert_called_once_with()

class Packaging(unittest.TestCase):
    def test_exact_docker_copy_context_imports_all_four(self):
        root=Path(__file__).resolve().parent
        lines=[l for l in (root/'Dockerfile').read_text().splitlines() if l.startswith('COPY ') and 'server.py' in l]
        files=lines[0].split()[1:-1]
        self.assertTrue({'market_data.py','history_data.py','technical.py','server.py'}<=set(files))
        with tempfile.TemporaryDirectory() as tmp:
            for name in files:(Path(tmp)/name).write_bytes((root/name).read_bytes())
            result=subprocess.run([sys.executable,'-c','import server; assert len(server.EXPECTED_TOOLS)==4'],cwd=tmp,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()

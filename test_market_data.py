import copy,json,tempfile,time,unittest,urllib.error
from unittest.mock import patch,MagicMock
import market_data as m

class QuotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=m.STATE_PATH;m.STATE_PATH=self.tmp.name+'/guard.db';m._CACHE=None
        self.payload={'code':'200000','data':{'time':int(time.time()*1000),'ticker':[{'symbol':s[:-4]+'-USDT','last':'100','buy':'99','sell':'101'} for s in m.SYMBOLS]}}
    def tearDown(self):m.STATE_PATH=self.old;m._CACHE=None;self.tmp.cleanup()
    def response(self,payload=None):
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps(payload or self.payload).encode();response.headers={};return response
    def test_single_request_all_tokens_and_cache_timestamp_preserved(self):
        with patch.object(m.urllib.request,'urlopen',return_value=self.response()) as net:
            a=m.spot_prices();a['records'].clear();b=m.spot_prices(['BTCUSDT'])
            self.assertEqual(len(b['records']),1);self.assertEqual(b['as_observed_utc'],m.utc(self.payload['data']['time']/1000));net.assert_called_once()
    def test_missing_pair_rejects_complete_valuation(self):
        self.payload['data']['ticker'].pop()
        with self.assertRaises(ValueError):m.validate(self.payload)
    def test_stale_and_future_times_rejected(self):
        for seconds in (-181,31):
            self.payload['data']['time']=(time.time()+seconds)*1000
            with self.assertRaises(ValueError):m.validate(self.payload)
    def test_nonfinite_zero_negative_and_crossed_rejected(self):
        for value in ('NaN','Infinity','0','-1'):
            p=copy.deepcopy(self.payload);p['data']['ticker'][0]['last']=value
            with self.assertRaises(ValueError):m.validate(p)
        self.payload['data']['ticker'][0]['buy']='102'
        with self.assertRaises(ValueError):m.validate(self.payload)
    def test_duplicate_rejected(self):
        self.payload['data']['ticker'].append(self.payload['data']['ticker'][0])
        with self.assertRaises(ValueError):m.validate(self.payload)
    def test_rate_pause_persists_without_new_network(self):
        exc=urllib.error.HTTPError(m.URL,429,'rate',{'Retry-After':'120'},None)
        with patch.object(m.urllib.request,'urlopen',side_effect=exc) as net:
            a=m.spot_prices();b=m.spot_prices()
            self.assertEqual(a['http_status'],429);self.assertEqual(b['records'],[]);net.assert_called_once()
    def test_http200_api_rate_limit_is_not_cached_as_prices(self):
        with patch.object(m.urllib.request,'urlopen',return_value=self.response({'code':'429000'})) as net:
            self.assertEqual(m.spot_prices()['http_status'],429);m.spot_prices();net.assert_called_once()
    def test_timeout_and_malformed_json_fail_closed(self):
        for error in (TimeoutError(),ValueError('bad json')):
            with patch.object(m.urllib.request,'urlopen',side_effect=error) as net:
                self.assertEqual(m.spot_prices()['status'],'DATA_ERROR');self.assertIsNone(m._CACHE);net.assert_called_once()
    def test_invalid_symbols_no_request(self):
        with patch.object(m.urllib.request,'urlopen') as net:
            self.assertEqual(m.spot_prices(['BTC-USDT'])['status'],'DATA_ERROR');net.assert_not_called()
    def test_reset_header_milliseconds(self):
        self.assertEqual(m.retry_deadline({'gw-ratelimit-reset':'30000'},100),130)

if __name__=='__main__':unittest.main()

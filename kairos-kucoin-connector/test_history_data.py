import copy,datetime as dt,json,tempfile,unittest,urllib.error
from unittest.mock import patch,Mock,MagicMock
import market_data as m
import history_data as h

NOW=dt.datetime(2026,11,2,tzinfo=dt.timezone.utc).timestamp()

def payload(start,end):
 return {'code':'200000','data':[[str(t),'100','102','104','98','10','1000'] for t in range(start,end,h.DAY)][::-1]}

def fake(symbol,start,end):return h.normalize_candles(payload(start,end),start,end)

class History(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=m.STATE_PATH;m.STATE_PATH=self.tmp.name+'/state.db'
 def tearDown(self):m.STATE_PATH=self.old;self.tmp.cleanup()
 def test_parse_closed_sorted_ohlcv_and_quote_volume(self):
  p=payload(int(NOW)-h.DAY*3,int(NOW)+h.DAY)
  r=h.normalize_candles(p,int(NOW)-h.DAY*3,int(NOW))
  self.assertEqual(len(r),3)
  self.assertEqual(r[int(NOW)-h.DAY]['close'],'102')
  self.assertEqual(r[int(NOW)-h.DAY]['high'],'104')
 def test_duplicate_and_invalid_ohlc_rejected(self):
  p=payload(int(NOW)-h.DAY,int(NOW));p['data']*=2
  with self.assertRaises(ValueError):h.normalize_candles(p,int(NOW)-h.DAY,int(NOW))
  p=payload(int(NOW)-h.DAY,int(NOW));p['data'][0][3]='99'
  with self.assertRaises(ValueError):h.normalize_candles(p,int(NOW)-h.DAY,int(NOW))
 def test_initial_cache_and_incremental_next_day(self):
  with patch.object(h,'_fetch',side_effect=fake) as net:
   a=h.ohlcv(limit=30,now=NOW);b=h.ohlcv(limit=30,now=NOW+30)
   c=h.ohlcv(limit=30,now=NOW+h.DAY)
  self.assertEqual(a['status'],'OK');self.assertTrue(b['cache_hit']);self.assertEqual(net.call_count,2)
  self.assertEqual(net.call_args.args[1:],(int(NOW),int(NOW)+h.DAY))
  self.assertEqual(len(c['records']),30)
 def test_cache_reused_after_process_cache_reset(self):
  with patch.object(h,'_fetch',side_effect=fake):h.ohlcv(limit=30,now=NOW)
  with patch.object(h,'_fetch',side_effect=AssertionError('No network')):
   self.assertEqual(h.ohlcv(limit=30,now=NOW)['status'],'OK')
 def test_larger_window_fetches_older_data(self):
  with patch.object(h,'_fetch',side_effect=fake) as net:
   h.ohlcv(limit=30,now=NOW);a=h.ohlcv(limit=60,now=NOW)
  self.assertEqual(len(a['records']),60);self.assertEqual(net.call_count,2)
 def test_gap_or_missing_last_bar_rejects_without_publishing_coverage(self):
  for missing in (-2,-1):
   def bad(symbol,start,end):
    r=fake(symbol,start,end);r.pop(sorted(r)[missing]);return r
   with patch.object(h,'_fetch',side_effect=bad):
    self.assertEqual(h.ohlcv(limit=30,now=NOW)['status'],'DATA_ERROR')
  with patch.object(h,'_fetch',side_effect=fake):self.assertFalse(h.ohlcv(limit=30,now=NOW)['cache_hit'])
 def test_short_leading_listing_history_is_explicit(self):
  def short(symbol,start,end):return fake(symbol,end-10*h.DAY,end)
  with patch.object(h,'_fetch',side_effect=short):a=h.ohlcv(limit=30,now=NOW)
  self.assertEqual(a['status'],'OK');self.assertEqual(a['count'],10);self.assertFalse(a['coverage_complete'])
 def test_bad_inputs_do_not_fetch(self):
  with patch.object(h,'_fetch') as net:
   for args in [('WRONGUSDT','1d',30),('BTCUSDT','1w',30),('BTCUSDT','1d',True),('BTCUSDT','1d',1501)]:
    self.assertEqual(h.ohlcv(*args,now=NOW)['status'],'DATA_ERROR')
   net.assert_not_called()
 def test_snapshot_complete_source_and_indicators_no_spot_request(self):
  with patch.object(h.time,'time',return_value=NOW),patch.object(h,'_fetch',side_effect=fake),patch.object(m,'spot_prices',side_effect=AssertionError('No Spot')):
   r=h.history_snapshot()
  self.assertEqual(r['source'],'KuCoin Spot');self.assertEqual(len(r['histories']),12)
  self.assertEqual(r['indicators']['BTCUSDT:1d']['values']['ema200'],102)
 def test_snapshot_failure_returns_no_partial_history(self):
  with patch.object(h,'_fetch',return_value=m.failure('Incomplete history')):r=h.history_snapshot()
  self.assertEqual(r['status'],'DATA_ERROR');self.assertEqual(r['histories'],{})
 def test_rate_limit_shared_guard_no_second_request(self):
  exc=urllib.error.HTTPError(h.CANDLES_URL,429,'rate',{'Retry-After':'120'},None)
  with patch.object(h.urllib.request,'urlopen',side_effect=exc) as net:
   a=h._fetch('BTCUSDT',int(NOW)-h.DAY,int(NOW));b=h._fetch('ETHUSDT',int(NOW)-h.DAY,int(NOW))
  self.assertEqual(a['http_status'],429);self.assertEqual(b['http_status'],429);net.assert_called_once()

if __name__=='__main__':unittest.main()


def test_concurrent_daily_reads_share_one_fetch():
 from concurrent.futures import ThreadPoolExecutor
 with tempfile.TemporaryDirectory() as temp,patch.object(m,'STATE_PATH',temp+'/cache.db'),patch.object(h,'_fetch',side_effect=fake) as net:
  with ThreadPoolExecutor(max_workers=6) as pool:
   results=list(pool.map(lambda _:h.ohlcv(limit=30,now=NOW),range(6)))
  assert all(r['status']=='OK' for r in results) and net.call_count==1

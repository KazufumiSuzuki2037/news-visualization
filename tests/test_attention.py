import copy
import json
import unittest
from unittest.mock import patch
from datetime import datetime,timedelta
from urllib.parse import quote,urlencode
from test_nv import curated
from nvcore.core import ROOT
from nvcore.data import prepare,read_json
from scripts.collect_attention import google_entries,ranking_entries,list_observation,collect

def external_evidence():
    common={'status':'observed','observedAt':'2026-10-26T03:03:00Z','match':{'reason':'確認した出来事と取得データが同じことを照合した','supportingSourceIds':['s0']}}
    latest=datetime(2026,10,25)
    daily=[{'date':(latest-timedelta(days=28-i)).date().isoformat(),'views':400 if i==28 else 100} for i in range(29)]
    result={
        'google':{**copy.deepcopy(common),'url':'https://trends.google.com/trending/rss?geo=JP','data':{'title':'検証事件','entryId':'entry1','trafficLowerBound':100000,'trendStartedAt':'2026-10-26T01:00:00Z'}},
        'wikipedia':{**copy.deepcopy(common),'url':'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ja.wikipedia.org/all-access/user/'+quote('検証事件')+'/daily/2026092700/2026102500','data':{'pageTitle':'検証事件','daily':daily}},
        'yahoo':{**copy.deepcopy(common),'url':'https://news.yahoo.co.jp/ranking/access/news','data':{'rank':1,'listSize':40,'listComplete':True,'entryId':'y1'}},
        'livedoor':{**copy.deepcopy(common),'url':'https://news.livedoor.com/ranking/','data':{'rank':1,'listSize':20,'listComplete':True,'entryId':'l1'}},
        'gdelt':{**copy.deepcopy(common),'url':'https://api.gdeltproject.org/api/v2/doc/doc?'+urlencode({'query':'test incident','mode':'timelinevolraw'}),'data':{'query':'test incident','articleCount':1,'totalArticles':100,'windowStart':'2026-10-23T03:00:00Z','windowEnd':'2026-10-26T03:00:00Z'}}}
    for key in ('google','yahoo','livedoor'):
        row=result[key];row['snapshotHash']='a'*64;row['data']['snapshotHash']='a'*64
        row['data'].setdefault('title','検証事件')
        row['match'].update(method='reviewed',topicId='test-event',entryId=row['data']['entryId'],entryTitle=row['data']['title'],reviewedSnapshotHash='a'*64)
    return result

class AttentionTests(unittest.TestCase):
    def setUp(self):self.settings=read_json(ROOT/'config/settings.json')
    def payload(self):
        data=curated(20,5,500);data['topics'][0]['attentionEvidence']=external_evidence();return data
    def test_active_indicators_sum_to_100(self):
        topic=prepare(self.payload(),self.settings)['periods']['24h']['topics'][0]
        self.assertEqual(topic['globalImportanceScore'],100)
        self.assertEqual(topic['dataCompleteness'],1)
        self.assertEqual(topic['missingMetrics'],[])
        self.assertEqual(topic['evaluationStatus'],'evaluated')
        self.assertAlmostEqual(sum(r['contribution'] for r in topic['attentionBreakdown']),100)
        self.assertEqual(len(topic['attentionBreakdown']),6)
        self.assertNotIn('wikipedia',topic['metrics']);self.assertNotIn('gdelt',topic['metrics'])
        self.assertNotIn('wikipedia',topic['attentionEvidence']);self.assertNotIn('gdelt',topic['attentionEvidence'])
    def test_missing_google_is_distinct_from_zero_and_ranking_outside(self):
        data=self.payload();google=data['topics'][0]['attentionEvidence']['google']
        google.update(status='not_listed',reason='急上昇RSSに対応する話題がない');google.pop('data')
        data['topics'][0]['attentionEvidence']['yahoo']['data']['rank']=None
        data['topics'][0]['attentionEvidence']['yahoo']['data'].update(entryId=None,title=None)
        data['topics'][0]['attentionEvidence']['yahoo']['match'].update(entryId=None,entryTitle=None)
        topic=prepare(data,self.settings)['periods']['24h']['topics'][0]
        self.assertIsNone(topic['metrics']['google']);self.assertEqual(topic['metrics']['yahoo'],0)
        self.assertEqual(topic['observedAttentionScore'],84)
        self.assertEqual(topic['dataCompleteness'],.88)
    def test_popularity_replacement_is_capped_at_20_points(self):
        topic=prepare(self.payload(),self.settings)['periods']['24h']['topics'][0]
        rows={row['key']:row for row in topic['attentionBreakdown']}
        self.assertEqual([rows[k]['contribution'] for k in ('google','yahoo','livedoor')],[12,4,4])
        self.assertEqual(sum(rows[k]['contribution'] for k in ('google','yahoo','livedoor')),20)
    def test_invalid_public_evidence_is_rejected(self):
        mutations=[
            lambda e:e['google']['data'].update(trafficLowerBound=-1),
            lambda e:e['google'].update(url='https://fake.example/trends'),
            lambda e:e['google']['match'].update(supportingSourceIds=['missing']),
            lambda e:e['google'].update(observedAt='2026-10-27T03:03:00Z'),
            lambda e:e['yahoo']['data'].update(listComplete=False),
            lambda e:e['yahoo']['data'].update(rank=41),
        ]
        for mutate in mutations:
            data=self.payload();mutate(data['topics'][0]['attentionEvidence'])
            with self.subTest(mutate=mutate):
                with self.assertRaises(ValueError):prepare(data,self.settings)
    def test_disabled_providers_are_never_requested(self):
        snapshots={k:{'url':'https://example.com/','observedAt':'2026-10-26T03:00:00Z','status':'available','entries':[]} for k in ('google','yahoo','livedoor')}
        with patch('scripts.collect_attention.wikipedia_observation',side_effect=AssertionError('disabled')),patch('scripts.collect_attention.gdelt_observation',side_effect=AssertionError('disabled')),patch('scripts.collect_attention.list_observation',return_value={'status':'unmatched'}):
            result=collect(curated(),snapshots,{})
        self.assertEqual(set(result['topics'][0]['attentionEvidence']),{'google','yahoo','livedoor'})
        self.assertEqual(set(result['attentionCollection']['topicStatusCounts']),{'google','yahoo','livedoor'})
    def test_public_parsers_and_explicit_unmatched_state(self):
        xml='<rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item><title>検証事件</title><pubDate>Mon, 26 Oct 2026 01:00:00 +0000</pubDate><ht:approx_traffic>2K+</ht:approx_traffic></item></channel></rss>'
        entries=google_entries(xml);self.assertEqual(entries[0]['trafficLowerBound'],2000)
        body='window.__PRELOADED_STATE__ = '+json.dumps({'rankingFeed':{'list':[{'rankingNumber':1,'headline':'検証事件','newsLink':'https://news.yahoo.co.jp/articles/test'}]}})+';'
        self.assertEqual(ranking_entries('yahoo',body)[0]['rank'],1)
        live='<ol class="articleList withRanking"><li><a href="https://news.livedoor.com/topics/detail/1/"><div class="articleListRanking">1</div><h3>検証事件</h3></a></li></ol>'
        self.assertEqual(len(ranking_entries('livedoor',live)),1)
        snapshot={'status':'available','entries':entries,'snapshotHash':'test','url':'https://trends.google.com/trending/rss?geo=JP','observedAt':'2026-10-26T03:00:00Z'}
        row=list_observation('google',curated()['topics'][0],snapshot,None)
        self.assertEqual(row['status'],'unmatched')

    def test_url_match_records_the_actual_article_and_google_maximum(self):
        topic=curated()['topics'][0]
        entries=[{'entryId':'small','title':'小さい値','trafficLowerBound':100,'relatedArticles':[{'url':topic['sources'][1]['url']}]},
                 {'entryId':'large','title':'大きい値','trafficLowerBound':500,'relatedArticles':[{'url':topic['sources'][1]['url']}]}]
        snapshot={'status':'available','entries':entries,'snapshotHash':'a'*64,'url':'https://trends.google.com/trending/rss?geo=JP','observedAt':'2026-10-26T03:00:00Z'}
        row=list_observation('google',topic,snapshot,None)
        self.assertEqual(row['data']['entryId'],'large')
        self.assertEqual(row['match']['supportingSourceIds'],['s1'])

if __name__=='__main__':unittest.main()

import copy
import http.client
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from nvcore.core import ROOT, digest
from nvcore.data import atomic_json, prepare, read_json, validate_settings, view_news
from nvcore.news_policy import normalize_public_url
from server import make_server
from scripts import research_batch


def curated(count=2, previous=None, reaction=None, event='2026-10-26T01:00:00Z'):
    sources = [{'sourceId':f's{i}','publisherId':f'publisher{i}.example','url':f'https://publisher{i}.example/news',
                'title':f'検証用記事{i}','publishedAt':'2026-10-26T01:00:00Z','checkedAt':'2026-10-26T03:01:00Z',
                'verificationStatus':'verified','language':'ja','sourceType':'official'} for i in range(count)]
    topic = {'topicId':'test-event','title':'検証用ニュース','summary':'検証用の概要。','eventAt':event,'field':next(f['name'] for f in read_json(ROOT/'config/settings.json')['fields'] if f['active']),
             'sources':sources,'articleEvidence':[s['sourceId'] for s in sources], 'publisherEvidence':[s['sourceId'] for s in sources],
             'reactionEvidence':[], 'details':{'explanation':'検証用の記事要約。','terms':[{'termId':'test-term','term':'検証用語','description':'検証の説明。'}],
             'background':[{'status':'confirmed','text':'検証用の背景。','supportingSourceIds':['s0']}], 'impacts':[], 'applications':[]}}
    if previous is not None:
        old=[{**sources[0],'sourceId':f'p{i}','publisherId':f'old{i}.example','url':f'https://old{i}.example/previous','publishedAt':'2026-10-21T03:00:00Z'} for i in range(previous)]
        topic['sources'].extend(old);topic['previousArticleEvidence']=[s['sourceId'] for s in old]
    if reaction is not None:
        endpoint='https://bookmark.hatenaapis.com/count/entry?'+urlencode({'url':sources[0]['url']})
        topic['sources'].append({'sourceId':'hatena','publisherId':'hatena','url':endpoint,'checkedAt':'2026-10-26T03:02:00Z','verificationStatus':'verified','sourceType':'api'})
        topic['reactionEvidence']=[{'platform':'hatena','sourceId':'hatena','targetSourceId':'s0','count':reaction,'observedAt':'2026-10-26T03:02:00Z'}]
    return {'referenceAt':'2026-10-26T03:00:00Z','executionStartedAt':'2026-10-26T03:00:00Z','executionCompletedAt':'2026-10-26T03:10:00Z','topics':[topic],'limitations':[]}


class DataTests(unittest.TestCase):
    def setUp(self):
        self.settings=read_json(ROOT/'config/settings.json')

    def test_publish_cli_keeps_previous_json_when_minimum_is_not_met(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            payload=curated()
            for i in range(1,5):
                topic=copy.deepcopy(payload['topics'][0]);topic['topicId']=f'old-{i}';topic['eventAt']='2026-10-24T01:00:00Z'
                topic['title']=f'別の検証用の出来事{i}'
                topic['summary']=f'出来事{i}の検証用の概要。'
                for source in topic['sources']:
                    source['url']+=f'/{i}';source['title']=f'出来事{i}についての確認用出典'
                    source['publishedAt']='2026-10-24T01:00:00Z'
                payload['topics'].append(topic)
            settings=copy.deepcopy(self.settings)
            settings['fields']=[settings['fields'][0]]
            settings['displaySettings']['minTopicsPerField']=5
            atomic_json(root/'input.json',payload);atomic_json(root/'settings.json',settings)
            target=root/'news.json';target.write_bytes(b'previous valid data')
            command=[sys.executable,'-X','utf8','-B',str(ROOT/'scripts/prepare_news.py'),'--input',str(root/'input.json'),'--settings',str(root/'settings.json'),'--output',str(target)]
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertNotEqual(result.returncode,0)
            self.assertIn('MINIMUM_TOPICS_NOT_MET',result.stderr)
            self.assertEqual(target.read_bytes(),b'previous valid data')
            held=read_json(root/'research-status.json')
            self.assertEqual(held['status'],'held')
            self.assertEqual(held['shortfalls'],[{'period':'24h','field':settings['fields'][0]['name'],'count':1,'minimum':5}])
            for topic in payload['topics']:
                for source in topic['sources']:source['publishedAt']='2026-10-26T01:00:00Z'
            atomic_json(root/'input.json',payload)
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(read_json(target)['periods']['24h']['topics']),5)
            self.assertEqual(read_json(root/'research-status.json')['status'],'updated')

    def test_reporting_matches_existing_formula(self):
        topic=prepare(curated(),self.settings)['periods']['24h']['topics'][0]
        self.assertEqual(topic['observedAttentionScore'],round(60*math.log1p(2)/math.log1p(20),1))
        self.assertEqual(topic['globalImportanceScore'],topic['observedAttentionScore'])
        self.assertEqual(topic['dataCompleteness'],.6)
        self.assertEqual(set(topic['missingMetrics']),{'google','yahoo','livedoor','reaction','growth'})

    def test_missing_external_metrics_are_not_redistributed(self):
        topic=prepare(curated(20,5,500),self.settings)['periods']['24h']['topics'][0]
        self.assertEqual(topic['observedAttentionScore'],80)
        self.assertEqual(topic['dataCompleteness'],.8)
        self.assertEqual(topic['globalImportanceScore'],80)
        empty=prepare(curated(20,0,0),self.settings)['periods']['24h']['topics'][0]
        self.assertIsNone(empty['metrics']['growth'])
        self.assertEqual(empty['metrics']['reaction'],0)

    def test_syndication_is_not_independent(self):
        payload=curated()
        for source in payload['topics'][0]['sources']:source['originalPublisherId']='same-publisher'
        result=prepare(payload,self.settings)['periods']['24h']['topics'][0]
        self.assertEqual(result['independentPublisherCount'],1)
        self.assertIsNone(result['globalImportanceScore'])
        self.assertEqual(result['evaluationStatus'],'insufficient_data')

    def test_periods_use_article_publication_not_event_time(self):
        result=prepare(curated(event='2026-10-22T03:00:00Z'),self.settings)
        self.assertEqual(len(result['periods']['24h']['topics']),1)
        self.assertEqual(len(result['periods']['7d']['topics']),1)
        old=curated()
        for source in old['topics'][0]['sources']:source['publishedAt']='2026-10-24T03:00:00Z'
        old['topics'][0]['sources'].append({'sourceId':'api','publisherId':'test','url':'https://api.example/data','title':'観測API','publishedAt':'2026-10-26T02:00:00Z','checkedAt':'2026-10-26T03:00:00Z','verificationStatus':'verified','language':'ja','sourceType':'attention'})
        result=prepare(old,self.settings)
        self.assertEqual(result['periods']['24h']['topics'],[])
        self.assertEqual(len(result['periods']['7d']['topics']),1)

    def test_bad_evidence_dates_and_reactions_are_rejected(self):
        cases=[]
        bad=curated();bad['topics'][0]['sources'][0]['publishedAt']='2026-10-26';cases.append(bad)
        bad=curated();bad['topics'][0]['sources'][0]['publishedAt']='2026-10-26T04:00:00Z';cases.append(bad)
        bad=curated();bad['topics'][0]['sources'][0]['language']='en';cases.append(bad)
        bad=curated();bad['topics'][0]['sources'][0]['verificationStatus']='unverified';cases.append(bad)
        bad=curated();bad['topics'][0]['publisherEvidence']=[];cases.append(bad)
        bad=curated();bad['topics'][0]['details']['background'][0]['supportingSourceIds']=[];cases.append(bad)
        bad=curated(reaction=10);bad['topics'][0]['sources'][-1]['url']='https://example.com/fake';cases.append(bad)
        bad=curated();bad['topics'][0]['xTrendEvidence']={};cases.append(bad)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):prepare(payload,self.settings)

    def test_registered_site_may_have_non_japanese_article(self):
        settings=copy.deepcopy(self.settings)
        settings['sites']=[{'siteId':'official','name':'検証サイト','url':'https://publisher0.example/','active':True}]
        payload=curated();payload['topics'][0]['sources'][0]['language']='en'
        self.assertTrue(prepare(payload,settings))

    def test_display_minimum_and_threshold(self):
        result=prepare(curated(),self.settings)
        topic=result['periods']['24h']['topics'][0]
        result['periods']['24h']['topics']=[{**topic,'topicId':str(i),'globalImportanceScore':30 if i==6 else 20,'observedAttentionScore':30 if i==6 else 20} for i in range(8)]
        view=view_news(result,self.settings,'24h')
        self.assertEqual(len(view['topics']),5)
        self.assertEqual(view['excludedTopicCount'],3)
        result['periods']['24h']['topics']=[{**topic,'topicId':str(i),'globalImportanceScore':30,'observedAttentionScore':30} for i in range(8)]
        self.assertEqual(len(view_news(result,self.settings,'24h')['topics']),8)

    def test_invalid_generation_does_not_overwrite_good_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/'news.json';input_file=root/'curated.json'
            good=curated();seed=copy.deepcopy(good['topics'][0]);good['topics']=[]
            for field in self.settings['fields']:
                for i in range(self.settings['displaySettings']['minTopicsPerField']):
                    topic=copy.deepcopy(seed);topic['field']=field['name'];topic['topicId']=f"{field['fieldId']}-{i}"
                    topic['title']=f"{field['name']}の別の検証用出来事{i}"
                    for source in topic['sources']:source['url']+=f"/{field['fieldId']}/{i}"
                    good['topics'].append(topic)
            atomic_json(input_file,good);atomic_json(output,{'sentinel':'keep'})
            command=[sys.executable,'-B',str(ROOT/'scripts/prepare_news.py'),'--input',str(input_file),'--output',str(output)]
            subprocess.run(command,check=True,capture_output=True)
            original=output.read_bytes()
            bad=copy.deepcopy(good);bad['topics'][0]['articleEvidence']=['missing'];atomic_json(input_file,bad)
            run=subprocess.run(command,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(output.read_bytes(),original)
            self.assertEqual(list(root.glob('*.tmp')),[])

    def test_bad_settings_rejected(self):
        bad=copy.deepcopy(self.settings);bad['fields'][1]['fieldId']=bad['fields'][0]['fieldId']
        with self.assertRaises(ValueError):validate_settings(bad)
        bad=copy.deepcopy(self.settings);bad['sites']=[{'siteId':'a','name':'bad','url':'http://127.0.0.1/','active':True}]
        with self.assertRaises(ValueError):validate_settings(bad)
        for url in ['https://127.0.0.1/','https://user:secret@example.com/','http://example.com/']:
            with self.assertRaises(ValueError):normalize_public_url(url)

    def test_collection_uses_active_fields_and_requested_queries(self):
        settings=copy.deepcopy(self.settings)
        settings['sites']=[]
        for field in settings['fields'][1:]:field['active']=False
        queries={settings['fields'][0]['fieldId']:['検証用の検索語']}
        with patch.object(research_batch,'fetch_many',return_value=[]) as fetch:
            result=research_batch.collect(research_batch.load_policy(),settings,queries)
            requests=fetch.call_args.args[0]
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0]['query'],'検証用の検索語')
        self.assertEqual(result['candidates'],[])

    def test_public_articles_decode_declared_japanese_charsets(self):
        html='<html lang="ja"><head><meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS"></head><body>日本語の記事本文です。</body></html>'
        self.assertEqual(research_batch.decode_body(html.encode('shift_jis')),html)
        utf8='<meta charset="UTF-8"><p>ニュースの本文</p>'
        self.assertEqual(research_batch.decode_body(utf8.encode('utf-8')),utf8)

    def test_display_change_does_not_request_new_research(self):
        result=prepare(curated(),self.settings)
        settings=copy.deepcopy(self.settings);settings['displaySettings']['zoomPercent']=125;settings['version']+=1
        self.assertFalse(view_news(result,settings,'24h')['settingsChanged'])
        settings['fields'][0]['instructions']='収集方針を変更する。'
        self.assertTrue(view_news(result,settings,'24h')['settingsChanged'])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'config',self.root/'config');shutil.copytree(ROOT/'web',self.root/'web')
        (self.root/'data').mkdir();atomic_json(self.root/'data/preferences.json',{'knownTermIds':[]})
        atomic_json(self.root/'data/news.json',prepare(curated(),read_json(self.root/'config/settings.json')))
        self.server=make_server(self.root,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def call(self,path,body=None,headers=None):
        request=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,method='PUT' if body is not None else 'GET',headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urlopen(request) as response:return response.status,response.headers,response.read()
        except HTTPError as error:return error.code,error.headers,error.read()

    def test_read_static_only_and_never_expose_sources(self):
        status,headers,body=self.call('/')
        self.assertEqual(status,200);self.assertIn('NewsVisualization',body.decode());self.assertIn("connect-src 'self'",headers['Content-Security-Policy'])
        for path in ['/config/settings.json','/.git/config','/server.py','/../server.py','/favicon.ico']:
            self.assertEqual(self.call(path)[0],404)

    def test_large_assets_use_one_persistent_connection(self):
        asset=next((self.root/'web/assets').glob('*.js'))
        expected=asset.read_bytes()
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            socket_identity=None
            for _ in range(5):
                connection.request('GET','/assets/'+asset.name)
                response=connection.getresponse()
                self.assertEqual(response.version,11)
                self.assertEqual(response.status,200)
                self.assertEqual(response.read(),expected)
                self.assertIsNotNone(connection.sock)
                if socket_identity is None:socket_identity=connection.sock
                else:self.assertIs(connection.sock,socket_identity)
        finally:connection.close()

    def test_reject_cross_origin_host_and_non_json(self):
        self.assertEqual(self.call('/api/state',headers={'Host':'external.example'})[0],403)
        self.assertEqual(self.call('/api/settings',{},headers={'Origin':'https://external.example'})[0],403)
        self.assertEqual(self.call('/api/settings',{},headers={'Content-Type':'text/plain'})[0],415)

    def test_settings_conflict_and_preferences_persist(self):
        state=json.loads(self.call('/api/state')[2]);settings=state['settings']
        settings['displaySettings']['zoomPercent']=125
        self.assertEqual(self.call('/api/settings',{'revision':state['revision'],'settings':settings})[0],200)
        self.assertEqual(self.call('/api/settings',{'revision':state['revision'],'settings':settings})[0],409)
        self.assertEqual(read_json(self.root/'config/settings.json')['displaySettings']['zoomPercent'],125)
        self.assertEqual(self.call('/api/preferences',{'knownTermIds':['test-term']})[0],200)
        self.assertEqual(read_json(self.root/'data/preferences.json')['knownTermIds'],['test-term'])

    def test_external_news_updates_and_corrupt_json_recovers(self):
        self.assertEqual(len(json.loads(self.call('/api/state')[2])['news']['topics']),1)
        payload=curated();payload['topics'][0]['title']='更新された検証ニュース'
        atomic_json(self.root/'data/news.json',prepare(payload,read_json(self.root/'config/settings.json')))
        self.assertEqual(json.loads(self.call('/api/state')[2])['news']['topics'][0]['title'],'更新された検証ニュース')
        (self.root/'data/news.json').write_text('{',encoding='utf-8')
        self.assertEqual(self.call('/api/state')[0],422)
        atomic_json(self.root/'data/news.json',prepare(curated(),read_json(self.root/'config/settings.json')))
        self.assertEqual(self.call('/api/state')[0],200)


if __name__=='__main__':unittest.main()

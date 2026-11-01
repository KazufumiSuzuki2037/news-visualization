import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createApp,digest,validateNews,validateSettings,viewNews} from '../sites/worker.mjs';
import {FileBucket} from '../sites/local-bucket.mjs';
const root=fileURLToPath(new URL('..',import.meta.url));
const read=async path=>JSON.parse(await readFile(resolve(root,path),'utf8'));
const initial={settings:await read('config/settings.json'),news:await read('data/news.json'),display:await read('config/display.json'),scoring:await read('config/scoring.json'),researchStatus:null,assets:{'/':{body:'<!doctype html><title>NewsVisualization</title>',type:'text/html; charset=utf-8'}}};
const copy=value=>structuredClone(value);
async function fixture() {
  await mkdir(resolve(root,'tmp'),{recursive:true});
  const bucket=new FileBucket(await mkdtemp(resolve(root,'tmp/sites-test-')));
  const app=createApp(initial),env={BUCKET:bucket};
  const get=(path='/api/state',user='one')=>app.fetch(new Request('https://preview.test'+path,{headers:user?{'oai-authenticated-user-id':user}:{}}),env);
  const put=(path,value,headers={})=>app.fetch(new Request('https://preview.test'+path,{method:'PUT',headers:{'Content-Type':'application/json','oai-authenticated-user-id':'one',...headers},body:JSON.stringify(value)}),env);
  return {bucket,app,env,get,put};
}

test('Python and Worker agree on both periods, settings revisions, scores and changed display settings',async()=>{
  const program=`import json\nfrom nvcore.data import read_json,view_news\nfrom nvcore.core import digest\ns=read_json('config/settings.json'); n=read_json('data/news.json')\nrows=[]\nfor variant in range(2):\n if variant: s['fields'][1]['active']=False; s['displaySettings']['minTopicsPerField']=6; s['displaySettings']['zoomPercent']=125\n rows.append({'settings':json.loads(json.dumps(s)), 'revision':digest(s), 'views':{p:view_news(n,s,p) for p in ['24h','7d']}})\nprint(json.dumps(rows,ensure_ascii=False))`;
  const result=spawnSync('python',['-B','-c',program],{cwd:root,encoding:'utf8',maxBuffer:8_000_000,env:{...process.env,PYTHONPYCACHEPREFIX:resolve(root,'tmp/pycache'),PYTHONIOENCODING:'utf-8'}});
  assert.equal(result.status,0,result.stderr);
  for(const row of JSON.parse(result.stdout)) {
    assert.equal(await digest(row.settings),row.revision);
    for(const period of ['24h','7d']) {
      const actual=await viewNews(initial.news,row.settings,period,initial),expected=row.views[period];
      actual.reportingWindowStart=new Date(actual.reportingWindowStart).toISOString();expected.reportingWindowStart=new Date(expected.reportingWindowStart).toISOString();
      assert.deepEqual(actual,expected);
    }
  }
});
test('prepared news validates; malformed, wrong settings/scoring and missing fields fail',async()=>{
  await validateNews(initial.news,initial.settings,initial);
  for(const change of [n=>n.settingsHash='wrong',n=>n.scoringConfig.weights.reporting=.9,n=>n.periods['24h'].topics=[],n=>n.periods['7d'].topics[0].observedAttentionScore=101,n=>n.periods['24h'].topics[0].sources.forEach(s=>s.publishedAt='2000-01-01T00:00:00Z')]) {
    const n=copy(initial.news);change(n);await assert.rejects(()=>validateNews(n,initial.settings,initial));
  }
});
test('JSON update persists after Worker restart; rejects shortfalls without replacing good data',async()=>{
  const f=await fixture(),state=await(await f.get()).json(),news=copy(initial.news);
  news.generatedAt='2026-11-01T04:00:00+00:00';news.executionCompletedAt=news.generatedAt;
  assert.equal((await f.put('/api/news',{revision:state.revision,news})).status,200);
  const restarted=createApp(initial);
  assert.deepEqual(await(await restarted.fetch(new Request('https://preview.test/data/news.json'),f.env)).json(),news);
  const bad=copy(news);bad.periods['24h'].topics=[];
  assert.equal((await f.put('/api/news',{revision:state.revision,news:bad})).status,409);
  assert.deepEqual(await(await f.get('/data/news.json')).json(),news);
  assert.equal((await f.put('/api/news',{revision:state.revision,news:initial.news})).status,409);
});
test('settings update changes revision; stale and concurrent writes are rejected',async()=>{
  const f=await fixture(),state=await(await f.get()).json(),settings=copy(state.settings);settings.displaySettings.zoomPercent=125;
  const responses=await Promise.all([f.put('/api/settings',{revision:state.revision,settings}),f.put('/api/settings',{revision:state.revision,settings})]);
  assert.deepEqual(responses.map(response=>response.status).sort(),[200,409]);
  const next=await(await f.get()).json();assert.equal(next.news.displayConfig.zoomPercent,125);assert.equal(next.settings.version,settings.version+1);
  assert.equal((await f.put('/api/settings',{revision:state.revision,settings})).status,409);
});
test('preferences are separated by platform user identity',async()=>{
  const f=await fixture();assert.equal((await f.put('/api/preferences',{knownTermIds:['term-one']})).status,200);
  assert.deepEqual((await(await f.get('/api/state','one')).json()).preferences,{knownTermIds:['term-one']});
  assert.deepEqual((await(await f.get('/api/state','two')).json()).preferences,{knownTermIds:[]});
  assert.equal((await f.put('/api/preferences',{knownTermIds:['term-one']},{'oai-authenticated-user-id':''})).status,403);
});
test('unsafe origins, malformed bodies, oversized input and unavailable storage fail closed',async()=>{
  const f=await fixture();
  assert.equal((await f.put('/api/preferences',{knownTermIds:[]},{Origin:'https://evil.test'})).status,403);
  assert.equal((await f.app.fetch(new Request('https://preview.test/',{headers:{'Sec-Fetch-Site':'cross-site'}}),f.env)).status,200);
  assert.equal((await f.app.fetch(new Request('https://preview.test/api/state'),{})).status,503);
  assert.equal((await f.get('/api/state?period=invalid')).status,422);
  assert.equal((await f.get('/config/settings.json')).status,404);
  assert.equal((await f.app.fetch(new Request('https://preview.test/api/news',{method:'PUT',headers:{'Content-Type':'application/json'},body:'{'}),f.env)).status,422);
  assert.equal((await f.put('/api/news',{padding:'x'.repeat(2_000_001)})).status,413);
});
test('settings reject private URLs, invalid limits and disabled fields',()=>{
  for(const change of [s=>s.sites[0].url='http://127.0.0.1/',s=>s.limits.maxFields=999,s=>s.fields.forEach(f=>f.active=false),s=>s.displaySettings.zoomPercent=999]) {
    const settings=copy(initial.settings);change(settings);assert.throws(()=>validateSettings(settings,initial));
  }
});
test('uploader fails without registration and never echoes malformed credential input',async()=>{
  await mkdir(resolve(root,'tmp'),{recursive:true});
  const isolated=await mkdtemp(resolve(root,'tmp/sites-unregistered-'));
  await mkdir(resolve(isolated,'scripts'));
  const uploader=resolve(isolated,'scripts/upload-sites-news.mjs');
  await writeFile(uploader,await readFile(resolve(root,'scripts/upload-sites-news.mjs')));
  const token='DO_NOT_LOG_TEST_CREDENTIAL';
  for(const input of ['{"serviceToken":"'+token+'"',JSON.stringify({serviceToken:token,url:'https://untrusted.example/'})]) {
    const result=spawnSync(process.execPath,[uploader],{cwd:isolated,encoding:'utf8',input});
    assert.equal(result.status,1);assert.equal((result.stdout+result.stderr).includes(token),false);
  }
});

test('cross-site reads pass while cross-site mutations are rejected',async()=>{
  const f=await fixture();
  for(const headers of [{Origin:'https://evil.test'},{'Sec-Fetch-Site':'cross-site'},{Origin:'https://evil.test','Sec-Fetch-Site':'cross-site'}]) {
    for(const path of ['/','/api/state','/data/news.json']) {
      assert.equal((await f.app.fetch(new Request('https://preview.test'+path,{headers}),f.env)).status,200);
    }
    const head=await f.app.fetch(new Request('https://preview.test/',{method:'HEAD',headers}),f.env);
    assert.notEqual(head.status,403);
    const denied=await f.put('/api/preferences',{knownTermIds:[]},headers);
    assert.equal(denied.status,403);assert.deepEqual(await denied.json(),{error:'INVALID_ORIGIN'});
  }
});
test('prepared-news comparison tolerates float rounding but rejects meaningful changes',()=>{
  const program=`import runpy, math
m=runpy.run_path('scripts/check_sites_news.py'); eq=m['values_match']
assert eq(0.3608488067145302,0.3608488067145301)
assert not eq(0.36,0.360001)
assert not eq(1,True)
assert not eq(1,1.0)
assert not eq(float('nan'),float('nan'))
assert not eq(float('inf'),float('inf'))
assert not eq({'score':1},{'score':2})
assert not eq({'a':[]},{'b':[]})
assert not eq([1],[1,2])`;
  const r=spawnSync('python',['-B','-c',program],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONPYCACHEPREFIX:resolve(root,'tmp/pycache')}});
  assert.equal(r.status,0,r.stderr);
});

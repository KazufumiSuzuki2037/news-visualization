"""Collect free/keyless public signals. Semantic matches are reviewed by Codex."""
import argparse
import json
import math
import re
import sys
import time
import html
import hashlib
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode,quote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nvcore.core import digest,parse_time,config
from nvcore.data import atomic_json,read_json
from scripts.research_batch import fetch,fetch_many,load_policy,now

URLS={'google':'https://trends.google.com/trending/rss?geo=JP',
      'yahoo':'https://news.yahoo.co.jp/ranking/access/news','livedoor':'https://news.livedoor.com/ranking/'}
WIKI='https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ja.wikipedia.org/all-access/user/'
GDELT='https://api.gdeltproject.org/api/v2/doc/doc'

def entry_id(value):return hashlib.sha256(value.encode()).hexdigest()[:20]
def clean(value):return ' '.join(html.unescape(re.sub('<[^>]+>','',value)).split())

def google_entries(body):
    ns={'ht':'https://trends.google.com/trending/rss'}
    entries=[]
    for item in ET.fromstring(body).iter('item'):
        title=item.findtext('title');started=parsedate_to_datetime(item.findtext('pubDate')).isoformat()
        traffic=item.findtext('ht:approx_traffic',namespaces=ns) or ''
        match=re.fullmatch(r'([\d,.]+)\s*([KMB万億]?)\+?',traffic.strip(),re.I)
        if not title or not match:raise ValueError('UNRECOGNIZED_GOOGLE_TRAFFIC')
        scale={'':1,'K':1000,'M':1000000,'B':1000000000,'万':10000,'億':100000000}[match[2].upper()]
        count=float(match[1].replace(',',''))*scale
        if not math.isfinite(count) or count<0:raise ValueError('INVALID_GOOGLE_TRAFFIC')
        related=[{'title':n.findtext('ht:news_item_title',namespaces=ns),'url':n.findtext('ht:news_item_url',namespaces=ns)} for n in item.findall('ht:news_item',ns)]
        entries.append({'entryId':entry_id(title+'|'+started),'title':title,'trafficLowerBound':int(count),
                        'trafficText':traffic,'trendStartedAt':started,'relatedArticles':related})
    if not entries:raise ValueError('EMPTY_GOOGLE_FEED')
    return entries

def ranking_entries(key,body):
    if key=='yahoo':
        marker='window.__PRELOADED_STATE__ = '
        if marker not in body:raise ValueError('YAHOO_RANKING_LAYOUT_CHANGED')
        state=json.JSONDecoder().raw_decode(body.split(marker,1)[1])[0]
        feed=state.get('rankingFeed',{}).get('list',[])
        entries=[{'rank':r['rankingNumber'],'title':r['headline'],'url':r['newsLink']} for r in feed]
    else:
        block=re.search(r'<ol\b[^>]*class="[^"]*articleList\s+withRanking[^"]*"[^>]*>(.*?)</ol>',body,re.S)
        if not block:raise ValueError('LIVEDOOR_RANKING_LAYOUT_CHANGED')
        entries=[]
        for li in re.findall(r'<li\b[^>]*>(.*?)</li>',block[1],re.S):
            rank=re.search(r'class="articleListRanking"[^>]*>(\d+)',li)
            title=re.search(r'<h3\b[^>]*>(.*?)</h3>',li,re.S)
            link=re.search(r'<a\b[^>]*href="([^"]+)"',li)
            if not rank or not title or not link:raise ValueError('INCOMPLETE_LIVEDOOR_RANKING')
            entries.append({'rank':int(rank[1]),'title':clean(title[1]),'url':html.unescape(link[1])})
    if not entries or [e['rank'] for e in entries]!=list(range(1,len(entries)+1)):
        raise ValueError('INCOMPLETE_RANKING_LIST')
    for entry in entries:
        if not isinstance(entry['title'],str) or not entry['title'] or not entry['url'].startswith('https://'):
            raise ValueError('INVALID_RANKING_ENTRY')
        entry['entryId']=entry_id(entry['url'])
    return entries

def discover():
    snapshots={}
    for response in fetch_many([{'provider':k,'url':u} for k,u in URLS.items()],load_policy()['http']):
        key=response['provider'];row={k:response[k] for k in ['url','observedAt']}
        try:
            if response.get('error'):raise ValueError(response['error'])
            entries=google_entries(response['body']) if key=='google' else ranking_entries(key,response['body'])
            row.update({'status':'available','entries':entries,'snapshotHash':digest(entries)})
        except (ValueError,KeyError,TypeError,ET.ParseError) as error:
            row.update({'status':'unavailable','entries':[],'error':str(error)})
        snapshots[key]=row
    return snapshots

def missing(key,url,reason,status='unmatched',observed_at=None,attempted=False):
    return {'status':status,'url':url,'observedAt':observed_at or now(),'reason':reason,'attempted':attempted}

def match_evidence(topic,mapping,reason=None):
    return {'reason':reason or mapping['reason'],
            'supportingSourceIds':mapping.get('supportingSourceIds',topic['articleEvidence'][:1])}

def list_observation(key,topic,snapshot,mapping):
    if snapshot['status']!='available':
        return missing(key,snapshot['url'],snapshot.get('error','取得不能'),'unavailable',snapshot['observedAt'],True)
    entries=snapshot['entries'];selected=None;direct=[]
    targets={s['url']:s['sourceId'] for s in topic['sources'] if s['sourceId'] in topic['articleEvidence']}
    for entry in entries:
        urls={a.get('url') for a in entry.get('relatedArticles',[])} if key=='google' else {entry['url']}
        if urls & targets.keys():direct.append(entry)
    choose=lambda rows:max(rows,key=lambda e:e['trafficLowerBound']) if key=='google' else min(rows,key=lambda e:e['rank'])
    if direct:
        selected=choose(direct)
        urls={a.get('url') for a in selected.get('relatedArticles',[])} if key=='google' else {selected['url']}
        mapping={'reason':'確認済み記事URLと公開指標の関連記事URLが一致',
                 'supportingSourceIds':[targets[url] for url in sorted(urls & targets.keys())], 'method':'url'}
    if selected is None:
        if not mapping or mapping.get('snapshotHash')!=snapshot['snapshotHash'] or not isinstance(mapping.get('reason'),str) or len(mapping['reason'])<8:
            return missing(key,snapshot['url'],'一覧は取得済み。話題との一致又は圏外を未確認','unmatched',snapshot['observedAt'],True)
        ids=mapping.get('entryIds') or ([mapping['entryId']] if mapping.get('entryId') else [])
        matched=[e for e in entries if e['entryId'] in ids]
        if len(matched)!=len(set(ids)):raise ValueError('MATCHED_ENTRY_NOT_IN_SNAPSHOT')
        selected=choose(matched) if matched else None
    match=match_evidence(topic,mapping)
    match.update({'method':mapping.get('method','reviewed'),'topicId':topic['topicId'],
                  'entryId':selected['entryId'] if selected else None,'entryTitle':selected['title'] if selected else None,
                  'reviewedSnapshotHash':snapshot['snapshotHash']})
    common={'status':'observed','url':snapshot['url'],'observedAt':snapshot['observedAt'],'match':match,'attempted':True,'snapshotHash':snapshot['snapshotHash']}
    if key=='google':
        if selected is None:return missing(key,snapshot['url'],'JP急上昇RSSに対応する出来事の掲載を確認できない','not_listed',snapshot['observedAt'],True)
        return {**common,'data':{**selected,'snapshotHash':snapshot['snapshotHash']},'windowDescription':'取得時点のJP急上昇RSS。概算検索数の下限であり72時間の総数ではない'}
    return {**common,'data':{'rank':selected['rank'] if selected else None,'entryId':selected['entryId'] if selected else None,
                             'title':selected['title'] if selected else None,'articleUrl':selected['url'] if selected else None,
                             'listSize':len(entries),'listComplete':True,'snapshotHash':snapshot['snapshotHash']},
            'windowDescription':'取得時点の公開総合ランキング。圏外は当該一覧への非掲載'}

def wikipedia_observation(topic,mapping):
    if not mapping or not mapping.get('pageTitle'):
        return missing('wikipedia',WIKI,'出来事に対応する個別ページが未特定','no_target')
    title=mapping['pageTitle'].replace(' ','_');latest=datetime.now(timezone.utc).date()-timedelta(days=1)
    start=latest-timedelta(days=31)
    url=WIKI+quote(title,safe='')+'/daily/'+start.strftime('%Y%m%d00')+'/'+latest.strftime('%Y%m%d00')
    try:
        response=fetch(url,load_policy()['http']);data=json.loads(response['body'])
        points=[{'date':datetime.strptime(p['timestamp'][:8],'%Y%m%d').date().isoformat(),'views':p['views']} for p in data.get('items',[])]
        if len(points)<29:return missing('wikipedia',url,'連続29日分の履歴がない','insufficient_history',response['observedAt'],True)
        return {'status':'observed','url':url,'observedAt':response['observedAt'],'attempted':True,
                'match':match_evidence(topic,mapping),'data':{'pageTitle':title,'daily':points[-29:]},
                'windowDescription':'完了したUTC日のuser閲覧数と直前28日の中央値を比較。日本語版は日本国内限定ではない'}
    except (OSError,ValueError,KeyError,TypeError) as error:
        return missing('wikipedia',url,str(error),'unavailable',attempted=True)

def gdelt_observation(topic,mapping,reference_at):
    if not mapping or not mapping.get('query'):return missing('gdelt',GDELT,'出来事を限定する検索条件が未確認','no_target')
    end=parse_time(reference_at);start=end-timedelta(hours=config('scoring')['reportingHours'])
    url=GDELT+'?'+urlencode({'query':mapping['query'],'mode':'timelinevolraw','format':'json',
        'startdatetime':start.strftime('%Y%m%d%H%M%S'),'enddatetime':end.strftime('%Y%m%d%H%M%S')})
    try:
        response=fetch(url,{**load_policy()['http'],'timeoutSeconds':15});data=json.loads(response['body'])
        series=data.get('timeline',[])
        points=next((s.get('data',[]) for s in series if s.get('data') and 'norm' in s['data'][0]),[])
        if not points:return missing('gdelt',url,'分母付き報道量データが得られない','insufficient_history',response['observedAt'],True)
        count=sum(p['value'] for p in points);total=sum(p['norm'] for p in points)
        if total<=0:return missing('gdelt',url,'収録総件数を取得できない','insufficient_history',response['observedAt'],True)
        return {'status':'observed','url':url,'observedAt':response['observedAt'],'attempted':True,'match':match_evidence(topic,mapping),
                'data':{'query':mapping['query'],'windowStart':start.isoformat(),'windowEnd':end.isoformat(),
                        'articleCount':count,'totalArticles':total,'pointCount':len(points)},
                'windowDescription':'過去72時間のGDELT収録記事中のシェア。全世界の全記事数ではない'}
    except (OSError,ValueError,KeyError,TypeError) as error:
        return missing('gdelt',url,str(error),'unavailable',attempted=True)

def collect(payload,snapshots,matches):
    weights=config('scoring')['weights']
    gdelt_blocked=None;last_gdelt=None
    for topic in payload['topics']:
        mapping=matches.get(topic['topicId'],{})
        observations={k:list_observation(k,topic,snapshots[k],mapping.get(k)) for k in URLS}
        if weights['wikipedia']>0:observations['wikipedia']=wikipedia_observation(topic,mapping.get('wikipedia'))
        if weights['gdelt']==0:
            topic['attentionEvidence']=observations
            continue
        if gdelt_blocked:
            observations['gdelt']=missing('gdelt',GDELT,'同実行内の取得制限・接続失敗を受け、追加要求を停止: '+gdelt_blocked,'unavailable')
        else:
            if last_gdelt and mapping.get('gdelt'):time.sleep(max(0,5-(time.monotonic()-last_gdelt)))
            observations['gdelt']=gdelt_observation(topic,mapping.get('gdelt'),payload['referenceAt'])
            if observations['gdelt']['attempted']:last_gdelt=time.monotonic()
            if observations['gdelt']['status']=='unavailable' and any(value in observations['gdelt']['reason'] for value in ('HTTP 429','HTTP 503','timed out','Connection')):
                gdelt_blocked=observations['gdelt']['reason']
        topic['attentionEvidence']=observations
    payload['executionCompletedAt']=now()
    payload['attentionCollection']={k:{'url':v['url'],'observedAt':v['observedAt'],'status':v['status'],
                                     'itemCount':len(v['entries']),'snapshotHash':v.get('snapshotHash'),'error':v.get('error')} for k,v in snapshots.items()}
    payload['attentionCollection']['topicStatusCounts']={k:{status:sum(t['attentionEvidence'][k]['status']==status for t in payload['topics'])
                 for status in sorted({t['attentionEvidence'][k]['status'] for t in payload['topics']})} for k in (*URLS,'wikipedia','gdelt') if weights[k]>0}
    return payload

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discover',action='store_true');parser.add_argument('--input');parser.add_argument('--matches');parser.add_argument('--snapshots');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.discover:
        snapshots=discover();atomic_json(args.output,snapshots)
        print(json.dumps({k:{'status':v['status'],'items':len(v['entries']),'error':v.get('error')} for k,v in snapshots.items()},ensure_ascii=False));return
    if not args.input or not args.snapshots or not args.matches:parser.error('--input, --snapshots and --matches are required')
    result=collect(read_json(args.input),read_json(args.snapshots),read_json(args.matches))
    atomic_json(args.output,result);print(json.dumps(result['attentionCollection'],ensure_ascii=False))

if __name__=='__main__':main()

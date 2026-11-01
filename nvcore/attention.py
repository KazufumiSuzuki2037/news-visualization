"""Normalize public attention observations; absent observations remain missing."""
import math
import statistics
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, parse_qs, unquote
from .core import Failure, parse_time

EXTERNAL = ('google', 'wikipedia', 'yahoo', 'livedoor', 'gdelt')
LABELS = {'reporting':'独立報道元','growth':'報道の伸び','reaction':'はてなブックマーク',
          'google':'Googleトレンド','wikipedia':'Wikipedia閲覧増','yahoo':'Yahoo!ニュース順位',
          'livedoor':'ライブドア順位','gdelt':'GDELT報道シェア'}
MISSING = {'unavailable','not_listed','unmatched','no_target','insufficient_history','not_collected'}

def number(v):
    return type(v) in (float,int) and math.isfinite(v) and v >= 0

def endpoint(key,url):
    p=urlsplit(url)
    return p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and (
        (key=='google' and p.hostname=='trends.google.com' and p.path=='/trending/rss' and parse_qs(p.query).get('geo')==['JP']) or
        (key=='wikipedia' and p.hostname=='wikimedia.org' and p.path.startswith('/api/rest_v1/metrics/pageviews/per-article/ja.wikipedia.org/all-access/user/')) or
        (key=='yahoo' and p.hostname=='news.yahoo.co.jp' and p.path=='/ranking/access/news') or
        (key=='livedoor' and p.hostname=='news.livedoor.com' and p.path=='/ranking/') or
        (key=='gdelt' and p.hostname=='api.gdeltproject.org' and p.path=='/api/v2/doc/doc'))

def external_metrics(topic,reference_at,observation_end,cfg):
    evidence=topic.get('attentionEvidence',{})
    if not isinstance(evidence,dict) or set(evidence)-set(EXTERNAL):
        raise Failure(422,'INVALID_ATTENTION_EVIDENCE')
    values={};summaries={}
    article_ids=set(topic['articleEvidence'])
    for key in EXTERNAL:
        if cfg['weights'][key]==0:continue
        row=evidence.get(key)
        if row is None:
            values[key]=None;summaries[key]={'status':'not_collected','reason':'未収集'};continue
        if not isinstance(row,dict) or row.get('status') not in MISSING|{'observed'} or not endpoint(key,row.get('url','')):
            raise Failure(422,'INVALID_ATTENTION_ENDPOINT_OR_STATUS')
        observed=parse_time(row.get('observedAt'))
        if not parse_time(reference_at)-timedelta(hours=cfg['maxObservationAgeHours']) < observed <= parse_time(observation_end or reference_at):
            raise Failure(422,'ATTENTION_OBSERVATION_OUTSIDE_WINDOW')
        summaries[key]=dict(row)
        if row['status']!='observed':
            if not isinstance(row.get('reason'),str) or not row['reason']:raise Failure(422,'ATTENTION_MISSING_REASON_REQUIRED')
            values[key]=None;continue
        match=row.get('match',{})
        ids=match.get('supportingSourceIds',[])
        if (not isinstance(match.get('reason'),str) or len(match['reason'].strip())<8
                or not isinstance(ids,list) or not ids or not set(ids)<=article_ids):
            raise Failure(422,'ATTENTION_MATCH_EVIDENCE_REQUIRED')
        data=row.get('data')
        if not isinstance(data,dict):raise Failure(422,'ATTENTION_DATA_REQUIRED')
        if key in ('google','yahoo','livedoor'):
            snapshot_hash=row.get('snapshotHash')
            if (not isinstance(snapshot_hash,str) or len(snapshot_hash)!=64 or data.get('snapshotHash')!=snapshot_hash
                    or match.get('reviewedSnapshotHash')!=snapshot_hash or match.get('topicId')!=topic['topicId']
                    or match.get('entryId')!=data.get('entryId') or match.get('entryTitle')!=data.get('title')
                    or match.get('method') not in ('url','reviewed')):
                raise Failure(422,'ATTENTION_MATCH_SNAPSHOT_MISMATCH')
            if match['method']=='url':
                targets={s['url'] for s in topic['sources'] if s['sourceId'] in ids}
                urls={a.get('url') for a in data.get('relatedArticles',[])} if key=='google' else {data.get('articleUrl')}
                if not targets & urls:raise Failure(422,'ATTENTION_ARTICLE_URL_MISMATCH')
        if key=='google':
            count=data.get('trafficLowerBound')
            if type(count) is not int or count<0 or not data.get('title') or not data.get('entryId'):
                raise Failure(422,'INVALID_GOOGLE_TRAFFIC')
            if parse_time(data.get('trendStartedAt'))>observed:raise Failure(422,'FUTURE_GOOGLE_TREND')
            values[key]=min(math.log1p(count)/math.log1p(cfg['googleTrafficBaseline']),1)
        elif key in ('yahoo','livedoor'):
            n,rank=data.get('listSize'),data.get('rank')
            if type(n) is not int or not 1<=n<=1000 or data.get('listComplete') is not True:
                raise Failure(422,'INCOMPLETE_RANKING')
            if rank is not None and (type(rank) is not int or not 1<=rank<=n):
                raise Failure(422,'INVALID_RANKING_POSITION')
            if rank is not None and not data.get('entryId'):raise Failure(422,'RANKING_ENTRY_REQUIRED')
            values[key]=(n-rank+1)/n if rank is not None else 0
        elif key=='wikipedia':
            points=data.get('daily',[])
            if not isinstance(points,list) or len(points)!=29 or not data.get('pageTitle'):
                raise Failure(422,'WIKIPEDIA_HISTORY_REQUIRED')
            encoded=unquote(urlsplit(row['url']).path).split('/user/',1)[1].split('/daily/',1)[0]
            if encoded!=data['pageTitle'].replace(' ','_'):raise Failure(422,'WIKIPEDIA_PAGE_MISMATCH')
            dates=[];counts=[]
            for point in points:
                if not isinstance(point,dict) or type(point.get('views')) is not int or point['views']<0:
                    raise Failure(422,'INVALID_WIKIPEDIA_VIEWS')
                day=datetime.strptime(point['date'],'%Y-%m-%d').date()
                dates.append(day);counts.append(point['views'])
            if any(b-a!=timedelta(days=1) for a,b in zip(dates,dates[1:])):
                raise Failure(422,'WIKIPEDIA_NONCONSECUTIVE_DAYS')
            latest=observed.astimezone(timezone.utc).date()-timedelta(days=1)
            if not latest-timedelta(days=cfg['wikipediaMaxLagDays']-1)<=dates[-1]<=latest:
                raise Failure(422,'WIKIPEDIA_INCOMPLETE_OR_STALE_DAY')
            baseline=max(statistics.median(counts[:-1]),cfg['wikipediaBaselineFloor'])
            ratio=counts[-1]/baseline
            values[key]=min(max(math.log(ratio)/math.log(cfg['wikipediaFullRatio']),0),1) if ratio>0 else 0
            summaries[key]['baselineViews']=baseline;summaries[key]['latestViews']=counts[-1]
        else:
            start=parse_time(data.get('windowStart'));end=parse_time(data.get('windowEnd'))
            if end!=parse_time(reference_at) or end-start!=timedelta(hours=cfg['reportingHours']):
                raise Failure(422,'GDELT_WINDOW_MISMATCH')
            count,total=data.get('articleCount'),data.get('totalArticles')
            if not number(count) or not number(total) or total<=0 or count>total or not data.get('query'):
                raise Failure(422,'INVALID_GDELT_COUNTS')
            query=parse_qs(urlsplit(row['url']).query)
            if query.get('query')!=[data['query']] or query.get('mode')!=['timelinevolraw']:
                raise Failure(422,'GDELT_QUERY_MISMATCH')
            values[key]=min((count/total)/cfg['gdeltFullShare'],1)
    return values,summaries

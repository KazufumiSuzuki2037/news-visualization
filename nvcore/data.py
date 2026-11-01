"""Local JSON validation and replace-on-success writes."""
import json
import math
import os
import tempfile
from datetime import timedelta
from pathlib import Path

from .core import config, digest, parse_time
from .news_policy import article_eligible, normalize_public_url
from .scoring import score


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('NONFINITE_NUMBER')))


def atomic_json(path, value):
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def nonempty(value, limit=10000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def validate_settings(value):
    if not isinstance(value, dict) or set(value) != {'version','fields','sites','languages','limits','displaySettings'}:
        raise ValueError('INVALID_SETTINGS_FIELDS')
    if type(value['version']) is not int or value['version'] < 1 or value['languages'] != ['ja']:
        raise ValueError('INVALID_SETTINGS_VERSION_OR_LANGUAGE')
    limits = config('settings')['limits']
    if value['limits'] != limits:
        raise ValueError('READ_ONLY_LIMITS')
    fields = value['fields']
    if not isinstance(fields, list) or not 1 <= len(fields) <= limits['maxFields']:
        raise ValueError('INVALID_FIELDS_COUNT')
    ids, names = set(), set()
    for field in fields:
        if not isinstance(field, dict) or set(field) != {'fieldId','name','instructions','active'}:
            raise ValueError('INVALID_FIELD')
        if not nonempty(field['fieldId'],100) or field['fieldId'] in ids or not nonempty(field['name'],limits['maxNameLength']) or field['name'] in names or field['name'] == 'X':
            raise ValueError('INVALID_FIELD_ID_OR_NAME')
        if not nonempty(field['instructions'],limits['maxInstructionsLength']) or type(field['active']) is not bool:
            raise ValueError('INVALID_FIELD_INSTRUCTIONS')
        ids.add(field['fieldId']); names.add(field['name'])
    if not any(field['active'] for field in fields):
        raise ValueError('ACTIVE_FIELD_REQUIRED')
    if not isinstance(value['sites'], list) or len(value['sites']) > 100:
        raise ValueError('INVALID_SITES')
    seen = set()
    for site in value['sites']:
        if not isinstance(site, dict) or set(site) != {'siteId','name','url','active'} or not nonempty(site['siteId'],100) or site['siteId'] in seen or not nonempty(site['name'],100) or type(site['active']) is not bool:
            raise ValueError('INVALID_SITE')
        normalize_public_url(site['url'])
        seen.add(site['siteId'])
    options = config('display')['settingsOptions']
    display = value['displaySettings']
    if not isinstance(display, dict) or set(display) != set(options) or any(type(display[k]) is not int or display[k] not in choices for k, choices in options.items()):
        raise ValueError('INVALID_DISPLAY_SETTINGS')
    return value


def display_config(settings):
    cfg = config('display')
    cfg.update(settings['displaySettings'])
    cfg['pageSize'] = max(cfg['pageSize'], cfg['minTopicsPerField'])
    cfg['fields'] = [f['name'] for f in settings['fields'] if f['active']]
    cfg['aliases'] = {k:v for k,v in cfg['aliases'].items() if v in cfg['fields']}
    cfg['aliases'].update({f['fieldId']:f['name'] for f in settings['fields'] if f['active']})
    return cfg


def research_hash(settings):
    return digest({key:settings[key] for key in ['fields','sites','languages']})


def validate_topic(topic, settings):
    if not isinstance(topic, dict) or any(not nonempty(topic.get(k), 1000 if k=='title' else 10000) for k in ['topicId','title','summary','field','eventAt']):
        raise ValueError('INVALID_TOPIC')
    if topic['field'] not in {f['name'] for f in settings['fields']}:
        raise ValueError('UNKNOWN_FIELD')
    if any(k.lower().startswith('x') for k in topic) or topic.get('topicKind','news') != 'news':
        raise ValueError('UNSUPPORTED_TOPIC_DATA')
    parse_time(topic['eventAt'])
    sources = topic.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('SOURCES_REQUIRED')
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or any(not nonempty(source.get(k)) for k in ['sourceId','publisherId','url','checkedAt']) or source['sourceId'] in ids:
            raise ValueError('INVALID_SOURCE')
        normalize_public_url(source['url'])
        if source.get('verificationStatus') != 'verified':
            raise ValueError('VERIFIED_SOURCE_REQUIRED')
        parse_time(source['checkedAt'])
        if source.get('publishedAt'):
            parse_time(source['publishedAt'])
        ids.add(source['sourceId'])
    for key in ['articleEvidence','publisherEvidence','previousArticleEvidence']:
        if key in topic and (not isinstance(topic[key],list) or any(not isinstance(sid,str) or sid not in ids for sid in topic[key]) or len(set(topic[key])) != len(topic[key])):
            raise ValueError('INVALID_SOURCE_REFERENCE')
    if any(k not in topic for k in ['articleEvidence','publisherEvidence']):
        raise ValueError('REPORTING_EVIDENCE_REQUIRED')
    by_id = {s['sourceId']:s for s in sources}
    for sid in topic['articleEvidence']+topic.get('previousArticleEvidence',[]):
        source = by_id[sid]
        if not article_eligible(source['url'], source.get('language'), settings['sites']):
            raise ValueError('ARTICLE_LANGUAGE_NOT_ELIGIBLE')
        if not nonempty(source.get('title'),1000):
            raise ValueError('ARTICLE_TITLE_REQUIRED')
    details = topic.get('details')
    if not isinstance(details,dict) or not nonempty(details.get('explanation')):
        raise ValueError('DETAIL_EXPLANATION_REQUIRED')
    if not isinstance(details.get('cautions',[]),list) or any(not nonempty(x) for x in details.get('cautions',[])):
        raise ValueError('INVALID_CAUTIONS')
    terms = details.get('terms',[])
    if not isinstance(terms,list):
        raise ValueError('INVALID_TERMS')
    term_ids = set()
    for term in terms:
        if not isinstance(term,dict) or any(not nonempty(term.get(k)) for k in ['termId','term','description']) or term['termId'] in term_ids:
            raise ValueError('INVALID_TERM')
        term_ids.add(term['termId'])
    for key in ['background','impacts','applications']:
        if not isinstance(details.get(key,[]),list):
            raise ValueError('INVALID_DETAILS')
        for entry in details.get(key,[]):
            if not isinstance(entry,dict) or not nonempty(entry.get('text')):
                raise ValueError('INVALID_DETAIL_TEXT')
            references = entry.get('supportingSourceIds',[])
            if not isinstance(references,list) or any(sid not in ids for sid in references):
                raise ValueError('INVALID_DETAIL_REFERENCE')
            if key != 'applications' and (entry.get('status') not in ['confirmed','hypothesis','unverified'] or (entry['status']=='confirmed' and not references)):
                raise ValueError('DETAIL_STATUS_OR_EVIDENCE_REQUIRED')
            if key == 'applications' and entry.get('kind') not in ['work','development','conversation']:
                raise ValueError('INVALID_APPLICATION_KIND')
    return topic


def prepare(payload, settings):
    validate_settings(settings)
    if not isinstance(payload,dict) or not isinstance(payload.get('topics'),list):
        raise ValueError('TOPICS_ARRAY_REQUIRED')
    reference = parse_time(payload.get('referenceAt'))
    started = parse_time(payload.get('executionStartedAt'))
    completed = parse_time(payload.get('executionCompletedAt'))
    if not started <= completed or not reference <= completed:
        raise ValueError('INVALID_EXECUTION_WINDOW')
    limitations = payload.get('limitations',[])
    if not isinstance(limitations,list) or any(not nonempty(item) for item in limitations):
        raise ValueError('INVALID_LIMITATIONS')
    topics, seen = [], set()
    for raw in payload['topics']:
        validate_topic(raw, settings)
        if raw['topicId'] in seen:
            raise ValueError('DUPLICATE_TOPIC_ID')
        seen.add(raw['topicId'])
        for source in raw['sources']:
            if parse_time(source['checkedAt']) > completed:
                raise ValueError('FUTURE_OBSERVATION')
        current = {s['sourceId']:s for s in raw['sources']}
        urls = [current[sid]['url'] for sid in raw['articleEvidence']]
        if len(urls) != len(set(urls)):
            raise ValueError('DUPLICATE_ARTICLE_URL')
        topic = dict(raw)
        topic['articleCount'] = len(topic['articleEvidence'])
        topic['independentPublisherCount'] = len({current[sid].get('originalPublisherId') or current[sid]['publisherId'] for sid in topic['articleEvidence']})
        topics.append(score(topic,reference_at=payload['referenceAt'],observation_end=payload['executionCompletedAt']))
    periods = {}
    for period, hours in [('24h',24),('7d',168)]:
        selected = [t for t in topics if any(
            s.get('publishedAt') and 'T' in s['publishedAt'] and s.get('title')
            and s.get('sourceType') not in ('api','reaction','attention')
            and s.get('verificationStatus')=='verified'
            and article_eligible(s['url'],s.get('language'),settings['sites'])
            and reference-timedelta(hours=hours)<parse_time(s['publishedAt'])<=reference
            for s in t['sources'])]
        periods[period] = {'topics':selected}
    return {'version':1,'generatedAt':payload['executionCompletedAt'], 'referenceAt':payload['referenceAt'],
            'executionStartedAt':payload['executionStartedAt'],'executionCompletedAt':payload['executionCompletedAt'],
            'periods':periods,'limitations':limitations,'settingsHash':research_hash(settings),
            'periodBasis':'article_published_at','scoringConfig':config('scoring'),
            'attentionCollection':payload.get('attentionCollection',{})}


def view_news(news, settings, period):
    if news.get('version') != 1 or set(news.get('periods',{})) != {'24h','7d'}:
        raise ValueError('INVALID_NEWS_FILE')
    cfg = display_config(settings)
    rows, coverage, excluded = [], [], 0
    candidates = news['periods'][period]['topics']
    if not isinstance(candidates,list):
        raise ValueError('INVALID_TOPICS')
    seen = set()
    for topic in candidates:
        if not isinstance(topic,dict) or any(not nonempty(topic.get(k)) for k in ['topicId','title','field','summary']) or topic['topicId'] in seen:
            raise ValueError('INVALID_TOPIC_FILE')
        seen.add(topic['topicId'])
        if not isinstance(topic.get('sources'),list) or not isinstance(topic.get('details'),dict) or not isinstance(topic.get('missingMetrics'),list):
            raise ValueError('INVALID_TOPIC_FILE')
        for key in ['globalImportanceScore','observedAttentionScore']:
            value = topic.get(key)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= 100):
                raise ValueError('INVALID_SCORE_FILE')
        if type(topic.get('dataCompleteness')) not in (float,int) or not 0 <= topic['dataCompleteness'] <= 1:
            raise ValueError('INVALID_COMPLETENESS_FILE')
    if not isinstance(news.get('limitations'),list) or any(not isinstance(item,str) for item in news['limitations']):
        raise ValueError('INVALID_LIMITATIONS_FILE')
    for field in cfg['fields']:
        group = [t for t in candidates if t['field']==field]
        group.sort(key=lambda t:(-(t.get('globalImportanceScore') or t.get('observedAttentionScore') or 0),t['topicId']))
        shown = [t for i,t in enumerate(group) if i<cfg['minTopicsPerField'] or (t.get('globalImportanceScore') or 0)>cfg['additionalThreshold']]
        rows.extend(shown); excluded += len(group)-len(shown)
        coverage.append({'field':field,'shortfall':max(0,cfg['minTopicsPerField']-len(shown))})
    start = parse_time(news['referenceAt'])-timedelta(hours=config('scoring')['reportingHours']) if news.get('referenceAt') else None
    return {**{k:v for k,v in news.items() if k!='periods'},'topics':rows,'displayConfig':cfg,'fieldCoverage':coverage,
            'excludedTopicCount':excluded,'collectionSites':[s for s in settings['sites'] if s['active']],
            'reportingWindowStart':start.isoformat() if start else None,'reportingWindowEnd':news.get('referenceAt'),
            'settingsChanged':bool(news.get('settingsHash') and news['settingsHash']!=research_hash(settings))}

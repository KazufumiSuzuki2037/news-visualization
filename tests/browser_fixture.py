"""Isolated synthetic data for browser verification. Never writes production data."""
from pathlib import Path
from copy import deepcopy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nvcore.data import atomic_json, prepare, read_json
from test_nv import curated
from test_attention import external_evidence

root=Path(sys.argv[1])
payload=curated(20,5,500)
topic=payload['topics'][0]
payload['topics']=[{**topic,'topicId':f'verify-{i}','title':f'検証ニュース{i+1}'} for i in range(8)]
older=deepcopy(topic)
older.update({'topicId':'zz-older-event','title':'7日間だけの検証ニュース','eventAt':'2026-10-22T03:00:00Z'})
for source in older['sources']:
    if source['sourceId'] in older['articleEvidence']:source['publishedAt']='2026-10-24T03:00:00Z'
payload['topics'].append(older)
for item in payload['topics']:
    item['attentionEvidence']=external_evidence()
    for key in ('google','yahoo','livedoor'):item['attentionEvidence'][key]['match']['topicId']=item['topicId']
settings=read_json(root/'config/settings.json')
atomic_json(root/'data/news.json',prepare(payload,settings))
atomic_json(root/'data/preferences.json',{'knownTermIds':[]})

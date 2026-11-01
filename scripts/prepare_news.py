"""Validate curated evidence, calculate attention, then atomically replace JSON."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nvcore.data import atomic_json, prepare, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--settings', default=str(ROOT/'config/settings.json'))
    parser.add_argument('--output', default=str(ROOT/'data/news.json'))
    args = parser.parse_args()
    settings = read_json(args.settings)
    result = prepare(read_json(args.input),settings)
    minimum = settings['displaySettings']['minTopicsPerField']
    shortfalls = []
    for period, data in result['periods'].items():
        for field in settings['fields']:
            if not field['active']:
                continue
            count = sum(topic['field'] == field['name'] for topic in data['topics'])
            if count < minimum:
                shortfalls.append({'period':period,'field':field['name'],'count':count,'minimum':minimum})
    status_path = Path(args.output).with_name('research-status.json')
    if shortfalls:
        atomic_json(status_path, {'status':'held','attemptedAt':datetime.now(timezone.utc).isoformat(),
                                 'referenceAt':result['referenceAt'],'shortfalls':shortfalls})
        raise ValueError('MINIMUM_TOPICS_NOT_MET: ' + '; '.join(f"{s['period']}:{s['field']}:{s['count']}/{s['minimum']}" for s in shortfalls))
    atomic_json(args.output,result)
    atomic_json(status_path, {'status':'updated','attemptedAt':result['generatedAt'],'referenceAt':result['referenceAt'],'shortfalls':[]})
    print('JSON更新完了：'+str(args.output))


if __name__ == '__main__':
    main()

"""Recalculate prepared news with the existing authoritative Python pipeline."""
from pathlib import Path
import sys
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nvcore.data import prepare, read_json

news = read_json(ROOT / 'data/news.json')
settings = read_json(ROOT / 'config/settings.json')
raw = {key: news[key] for key in ('referenceAt', 'executionStartedAt', 'executionCompletedAt', 'limitations', 'attentionCollection')}
raw['topics'] = news['periods']['7d']['topics']
expected = prepare(raw, settings)
def values_match(actual, expected):
    """Allow only platform-dependent float rounding; retain exact JSON structure."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, float):
        return math.isfinite(actual) and math.isfinite(expected) and math.isclose(
            actual, expected, rel_tol=1e-14, abs_tol=1e-15)
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            values_match(actual[key], expected[key]) for key in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            values_match(a, b) for a, b in zip(actual, expected))
    return actual == expected


if not values_match(expected, news):
    raise ValueError('PREPARED_NEWS_MISMATCH')
minimum = settings['displaySettings']['minTopicsPerField']
for period in ('24h', '7d'):
    for field in settings['fields']:
        if field['active'] and sum(topic['field'] == field['name'] for topic in news['periods'][period]['topics']) < minimum:
            raise ValueError('MINIMUM_TOPICS_NOT_MET')
print('Prepared news matches Python validation and scoring.')

"""Small shared primitives; no service clients or credentials."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Failure(ValueError):
    def __init__(self, status, code):
        self.status = status
        super().__init__(code)


def config(name):
    return json.loads((ROOT / 'config' / f'{name}.json').read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def parse_time(value):
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError('TIME_REQUIRES_ISO8601') from error
    if date.tzinfo is None:
        raise ValueError('TIME_REQUIRES_TIMEZONE')
    return date

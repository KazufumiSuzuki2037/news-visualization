"""Evidence-based public attention; missing metrics never inflate scores."""
import math
from datetime import timedelta
from urllib.parse import urlsplit, parse_qs
from .core import Failure, digest, config, parse_time
from .attention import EXTERNAL, LABELS, external_metrics


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def scoring_config():
    cfg = config("scoring")
    weights = cfg["weights"]
    if (set(weights) != {"reporting", "reaction", "growth", *EXTERNAL}
            or any(not _number(w) or w < 0 for w in weights.values())
            or not 0 < sum(weights.values()) <= 1):
        raise Failure(500, "INVALID_SCORING_CONFIG")
    for key in ("reportingHours", "publisherBaseline", "minIndependentPublishers", "growthMinPublishers"):
        if type(cfg[key]) is not int or cfg[key] < 1:
            raise Failure(500, "INVALID_SCORING_CONFIG")
    for key in ("minDataCompleteness", "displayThreshold"):
        if not _number(cfg[key]) or not 0 <= cfg[key] <= (1 if key == "minDataCompleteness" else 100):
            raise Failure(500, "INVALID_SCORING_CONFIG")
    if not _number(cfg.get("growthFullRatio")) or cfg["growthFullRatio"] <= 1:
        raise Failure(500, "INVALID_SCORING_CONFIG")
    if not _number(cfg.get("reactionCountBaseline")) or cfg["reactionCountBaseline"] <= 0:
        raise Failure(500, "INVALID_SCORING_CONFIG")
    for key in ('googleTrafficBaseline','wikipediaBaselineFloor','wikipediaMaxLagDays','maxObservationAgeHours','gdeltFullShare'):
        if not _number(cfg.get(key)) or cfg[key]<=0:raise Failure(500,'INVALID_SCORING_CONFIG')
    if not _number(cfg.get('wikipediaFullRatio')) or cfg['wikipediaFullRatio']<=1:raise Failure(500,'INVALID_SCORING_CONFIG')
    return cfg, digest(cfg)


def _evidence(topic, field):
    ids = topic.get(field)
    if not isinstance(ids, list) or any(not isinstance(s, str) for s in ids) or len(ids) != len(set(ids)):
        raise Failure(422, "INVALID_REPORTING_EVIDENCE")
    sources = {s["sourceId"]: s for s in topic.get("sources", [])}
    if any(sid not in sources for sid in ids):
        raise Failure(422, "INVALID_SOURCE_REFERENCE")
    return [sources[sid] for sid in ids]


def _publisher(source):
    return source.get("originalPublisherId") or source["publisherId"]


def _log(value, baseline):
    return min(math.log1p(value) / math.log1p(baseline), 1)


def _reaction(topic, reference_at, period, cfg, observation_end=None):
    records = topic.get("reactionEvidence", [])
    if not isinstance(records, list):
        raise Failure(422, "INVALID_REACTION_EVIDENCE")
    selected, seen = None, set()
    sources = {s["sourceId"]: s for s in topic.get("sources", [])}
    articles = set(topic.get("articleEvidence", []))
    ref = parse_time(reference_at)
    start = ref - timedelta(hours=cfg["reportingHours"])
    for record in records:
        fields = {"platform", "sourceId", "targetSourceId", "count", "observedAt"}
        if not isinstance(record, dict) or set(record) != fields:
            raise Failure(422, "INVALID_REACTION_EVIDENCE")
        platform = record["platform"]
        if platform != "hatena":
            raise Failure(422, "UNSUPPORTED_REACTION_PLATFORM")
        if not all(isinstance(record[k], str) for k in ("sourceId", "targetSourceId")):
            raise Failure(422, "INVALID_REACTION_SOURCE")
        source, target = sources.get(record["sourceId"]), sources.get(record["targetSourceId"])
        if (not source or not target or source["verificationStatus"] != "verified"
                or record["sourceId"] in articles or record["targetSourceId"] not in articles):
            raise Failure(422, "INVALID_REACTION_SOURCE")
        endpoint = urlsplit(source["url"])
        if (endpoint.scheme != "https" or endpoint.hostname != "bookmark.hatenaapis.com"
                or endpoint.path != "/count/entry"
                or parse_qs(endpoint.query).get("url") != [target["url"]]):
            raise Failure(422, "INVALID_REACTION_SOURCE")
        identity = target["url"]
        if identity in seen:
            raise Failure(422, "DUPLICATE_REACTION")
        seen.add(identity)
        if type(record["count"]) is not int or record["count"] < 0:
            raise Failure(422, "INVALID_REACTION_COUNT")
        observed = parse_time(record["observedAt"])
        if not start < observed <= parse_time(observation_end or reference_at) or parse_time(source["checkedAt"]) != observed:
            raise Failure(422, "INVALID_REACTION_WINDOW")
        summary = {"platform": "hatena", "count": record["count"],
                   "observedAt": record["observedAt"], "targetSourceId": record["targetSourceId"]}
        if selected is None or (summary["count"], summary["observedAt"]) > (selected["count"], selected["observedAt"]):
            selected = summary
    return (_log(selected["count"], cfg["reactionCountBaseline"]), selected) if selected else (None, None)


def validate_attention(topic, reference_at, period, observation_end=None):
    """Validate observed counts and time windows before persistence."""
    cfg, _ = scoring_config()
    ref = parse_time(reference_at)
    start = ref - timedelta(hours=cfg["reportingHours"])
    current = _evidence(topic, "articleEvidence")
    publishers = _evidence(topic, "publisherEvidence")
    for source in current:
        if not source.get("publishedAt") or "T" not in source["publishedAt"]:
            raise Failure(422, "AMBIGUOUS_SOURCE_DATE")
        if not start < parse_time(source["publishedAt"]) <= ref:
            raise Failure(422, "SOURCE_OUTSIDE_REPORTING_WINDOW")
    actual = {_publisher(s) for s in current}
    if (not {s["sourceId"] for s in publishers} <= {s["sourceId"] for s in current}
            or {_publisher(s) for s in publishers} != actual):
        raise Failure(422, "INVALID_PUBLISHER_EVIDENCE")
    for key, expected in (("articleCount", len(current)), ("independentPublisherCount", len(actual))):
        value = topic.get(key)
        if value is not None and (type(value) is not int or value != expected):
            raise Failure(422, "COUNT_EVIDENCE_MISMATCH")
        if value is None and current:
            raise Failure(422, "COUNT_EVIDENCE_MISMATCH")
    if "previousArticleEvidence" in topic:
        for source in _evidence(topic, "previousArticleEvidence"):
            if not source.get("publishedAt") or "T" not in source["publishedAt"]:
                raise Failure(422, "AMBIGUOUS_SOURCE_DATE")
            if not start - timedelta(hours=cfg["reportingHours"]) < parse_time(source["publishedAt"]) <= start:
                raise Failure(422, "SOURCE_OUTSIDE_COMPARISON_WINDOW")
    _reaction(topic, reference_at, period, cfg, observation_end)


def score(topic, *, reference_at=None, period="24h", observation_end=None):
    """Return a conservative weighted score plus separate measurement coverage."""
    cfg, cfg_hash = scoring_config()
    if reference_at:
        validate_attention(topic, reference_at, period, observation_end)
    current = _evidence(topic, "articleEvidence")
    actual = {_publisher(s) for s in current}
    count = topic.get("independentPublisherCount")
    if count is not None and (type(count) is not int or count != len(actual)):
        raise Failure(422, "COUNT_EVIDENCE_MISMATCH")
    reporting = _log(count, cfg["publisherBaseline"]) if count is not None else None
    growth = None
    if "previousArticleEvidence" in topic and count is not None:
        old = len({_publisher(s) for s in _evidence(topic, "previousArticleEvidence")})
        # An observed zero has no finite growth ratio; never invent a denominator.
        if old > 0:
            growth = min(max(math.log(count / old) / math.log(cfg["growthFullRatio"]), 0), 1) if count >= cfg["growthMinPublishers"] else 0
    reaction, reaction_summary = _reaction(topic, reference_at, period, cfg, observation_end) if reference_at else (None, None)
    external, external_summaries = external_metrics(topic,reference_at,observation_end,cfg) if reference_at else ({k:None for k in EXTERNAL if cfg['weights'][k]>0},{})
    metrics = {"reporting": reporting, "reaction": reaction, "growth": growth, **external}
    completeness = round(sum(cfg["weights"][k] for k, v in metrics.items() if v is not None), 4)
    reasons = []
    if completeness < cfg["minDataCompleteness"]:
        reasons.append("data_completeness")
    if count is None or count < cfg["minIndependentPublishers"]:
        reasons.append("independent_publishers")
    observed = round(100 * sum(cfg["weights"][k] * v for k, v in metrics.items() if v is not None), 1) if completeness else None
    value = None if reasons else observed
    result = dict(topic)
    if 'attentionEvidence' in result:
        result['attentionEvidence']={k:v for k,v in result['attentionEvidence'].items() if cfg['weights'].get(k,0)>0}
    result.update({"scoreVersion": cfg["scoreVersion"], "configHash": cfg_hash,
                   "scoreMeaning": "observed_public_attention", "dataCompleteness": completeness,
                   "evaluationStatus": "insufficient_data" if reasons else "partial" if any(v is None for v in metrics.values()) else "evaluated",
                   "missingMetrics": [k for k, v in metrics.items() if v is None],
                   "unevaluatedReasons": reasons, "metrics": metrics, "globalImportanceScore": value,
                   "observedAttentionScore": observed,
                   "reactionSummary": reaction_summary,
                   "attentionSummaries": external_summaries,
                   "attentionBreakdown": [{"key":k,"label":LABELS[k],"weight":cfg['weights'][k],
                       "normalizedValue":v,"contribution":round(100*cfg['weights'][k]*v,2) if v is not None else None,
                       "status":external_summaries.get(k,{}).get('status','observed' if v is not None else 'not_collected')}
                       for k,v in metrics.items()],
                   "aboveDisplayThreshold": value is not None and value > cfg["displayThreshold"],
                   "comparedSnapshotId": None})
    return result

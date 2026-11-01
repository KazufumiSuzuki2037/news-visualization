"""Public evidence collection. Semantic curation stays with Codex."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import json
import os
import re
from pathlib import Path
import socket
import ssl
import sys
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nvcore.news_policy import normalize_public_url, public_addresses, validate_public_url


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_url(value):
    return normalize_public_url(value)


def source_id(url, publisher):
    return hashlib.sha256((normalized_url(url) + "|" + publisher).encode()).hexdigest()[:24]


def load_policy():
    return json.loads((ROOT / "config/research.json").read_text(encoding="utf-8-sig"))


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, **kwargs):
        super().__init__(host, **kwargs)
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _open_once(url, cfg, address, context):
    parts = urlsplit(url)
    connection = _PinnedHTTPSConnection(parts.hostname, address, timeout=cfg["timeoutSeconds"], context=context)
    try:
        connection.request("GET", parts.path + ("?" + parts.query if parts.query else ""), headers={"User-Agent": "NVResearch/1.0"})
        return connection, connection.getresponse()
    except Exception:
        connection.close()
        raise


def decode_body(raw, content_charset=None):
    """Honor an explicit HTTP charset, then the HTML declaration."""
    declared = re.search(br'<meta\b[^>]*charset\s*=\s*[\"\x27]?\s*([a-zA-Z0-9_-]+)', raw[:8192], re.I)
    encoding = content_charset or (declared.group(1).decode('ascii') if declared else 'utf-8')
    try:
        return raw.decode(encoding, errors='replace')
    except LookupError:
        return raw.decode('utf-8', errors='replace')


def fetch(url, cfg):
    original = normalized_url(url)
    current = original
    context = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
    for _ in range(6):
        addresses = public_addresses(current)
        connection, response = _open_once(current, cfg, addresses[0], context)
        try:
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirect has no Location")
                current = validate_public_url(urljoin(current, location))
                continue
            if not 200 <= response.status < 300:
                raise OSError(f"HTTP {response.status}")
            raw = response.read(cfg["maxResponseBytes"] + 1)
            if len(raw) > cfg["maxResponseBytes"]:
                raise ValueError("Response exceeds configured byte limit")
            return {"url": original, "resolvedUrl": current, "observedAt": now(),
                    "contentType": response.getheader("Content-Type", ""),
                    "body": decode_body(raw, response.headers.get_content_charset())}
        finally:
            connection.close()
    raise ValueError("Too many redirects")


def fetch_many(requests, cfg):
    def one(row):
        try:
            return {**row, **fetch(row["url"], cfg)}
        except (OSError, ValueError) as error:
            return {**row, "observedAt": now(), "error": type(error).__name__}
    with ThreadPoolExecutor(max_workers=cfg["workers"]) as pool:
        return list(pool.map(one, requests))


class _ArticleMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_language = None
        self.image = None
        self.published = None
        self.meta_published = None
        self.text = []
        self.article_text = []
        self.article_depth = 0
        self.ignored = 0
        self.jsonld = []
        self.in_jsonld = False
        self.script_data = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "html":
            self.html_language = values.get("lang")
        if tag in ("article", "main"):
            self.article_depth += 1
        if tag in ("script", "style", "nav", "footer"):
            self.ignored += 1
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.script_data = []
        if tag == "meta":
            key = values.get("property") or values.get("name")
            if key in ("og:image", "twitter:image") and not self.image:
                self.image = values.get("content")
            if key in ("article:published_time", "datePublished") and not self.meta_published:
                self.meta_published = values.get("content")
        if tag == "time" and values.get("datetime") and not self.published:
            self.published = values["datetime"]

    def handle_endtag(self, tag):
        if tag == "script" and self.in_jsonld:
            try:
                self.jsonld.append(json.loads("".join(self.script_data)))
            except ValueError:
                pass
            self.in_jsonld = False
        if tag in ("script", "style", "nav", "footer") and self.ignored:
            self.ignored -= 1
        if tag in ("article", "main") and self.article_depth:
            self.article_depth -= 1

    def handle_data(self, data):
        if self.in_jsonld:
            self.script_data.append(data)
        if not self.ignored and data.strip():
            self.text.append(data)
            if self.article_depth:
                self.article_text.append(data)


def _jsonld_value(documents, name):
    pending = list(documents)
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            return item
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            if item.get(name):
                value = item[name]
                if isinstance(value, str):
                    return value
                if isinstance(value, dict) and isinstance(value.get("url"), str):
                    return value["url"]
                if isinstance(value, list):
                    pending.extend(value)
            pending.extend(value for value in item.values() if isinstance(value, (dict, list)))
    return None


def _article_published(documents):
    pending=list(documents)
    while pending:
        item=pending.pop(0)
        if isinstance(item,list):pending.extend(item)
        elif isinstance(item,dict):
            types=item.get('@type',[])
            types=[types] if isinstance(types,str) else types
            if isinstance(types,list) and any(isinstance(t,str) and (t.rsplit('/',1)[-1].endswith('Article') or t.rsplit('/',1)[-1]=='BlogPosting') for t in types):
                if isinstance(item.get('datePublished'),str):return item['datePublished']
            pending.extend(v for v in item.values() if isinstance(v,(dict,list)))
    return None


def article_metadata(body, resolved_url):
    parser = _ArticleMetadata()
    parser.feed(body)
    result = {"language": None, "publishedAt": None, "thumbnailUrl": None}
    visible = " ".join(parser.article_text or parser.text)[:20000]
    kana = sum("\u3040" <= char <= "\u30ff" for char in visible)
    if kana >= 10 and parser.html_language and parser.html_language.lower().startswith("ja"):
        result["language"] = "ja"
    elif parser.html_language and not parser.html_language.lower().startswith("ja"):
        result["language"] = parser.html_language.lower().split("-", 1)[0]
    # Article-specific metadata must precede unrelated <time> elements (events).
    for published_text in (parser.meta_published, _article_published(parser.jsonld), parser.published):
        if not published_text:
            continue
        try:
            published = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
            if published.tzinfo is not None and "T" in published_text:
                result["publishedAt"] = published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                break
        except ValueError:
            pass
    for image in (parser.image, _jsonld_value(parser.jsonld, "image")):
        if not image:
            continue
        try:
            result["thumbnailUrl"] = validate_public_url(urljoin(resolved_url, image))
            break
        except ValueError:
            pass
    return result


def fetch_pages(requests, cfg):
    rows = fetch_many(requests, cfg)
    for row in rows:
        if "error" not in row and "html" in row["contentType"].lower():
            row.update(article_metadata(row["body"], row["resolvedUrl"]))
    return rows


def parse_feed(body):
    root = ET.fromstring(body)
    atom = {"a": "http://www.w3.org/2005/Atom"}
    rows = []
    for entry in root.findall("./channel/item") + root.findall("a:entry", atom):
        link = entry.findtext("link") or next((e.get("href") for e in entry.findall("a:link", atom)
                    if e.get("rel", "alternate") == "alternate"), None)
        if link:
            try:
                url = normalized_url(link)
            except ValueError:
                continue
            rows.append({"url": url,
                         "title": entry.findtext("title") or entry.findtext("a:title", namespaces=atom) or "",
                         "discoveredDate": entry.findtext("pubDate") or entry.findtext("a:published", namespaces=atom)})
    return rows


def collect(cfg, policy=None, queries=None):
    policy = policy or {"languages": cfg["languages"], "sites": []}
    if 'fields' in policy:
        policy = {**policy, 'fields':[field for field in policy['fields'] if field.get('active',True)]}
    discovery = cfg["discovery"]
    sites = [(site, urlsplit(validate_public_url(site["url"])).hostname)
             for site in policy["sites"] if site.get("active") is not False]
    requests = []
    field_queries = cfg["searchQueries"]
    if policy.get("fields") is not None:
        ids = {field["fieldId"] for field in policy["fields"]}
        if queries is not None and (not isinstance(queries, dict) or set(queries) != ids):
            raise ValueError("RESEARCH_QUERY_FIELDS_MISMATCH")
        limits = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))["limits"]
        field_queries = {}
        for field in policy["fields"]:
            values = queries[field["fieldId"]] if queries is not None else [field["name"]]
            if (not isinstance(values, list) or not 1 <= len(values) <= limits["maxQueriesPerField"]
                    or any(not isinstance(q, str) or not q.strip() or len(q) > limits["maxQueryLength"] for q in values)):
                raise ValueError("INVALID_RESEARCH_QUERIES")
            field_queries[field["fieldId"]] = {"ja": values}
    for field, languages in field_queries.items():
        for lang in policy["languages"]:
            for query in languages.get(lang, []):
                requests.append({
                    "field": field, "language": lang, "query": query,
                    "url": discovery["url"] + "?" + urlencode({"q": query, **discovery["locales"][lang]}),
                })
        for site, hostname in sites:
            query = f"site:{hostname} {languages['ja'][0]}"
            requests.append({"field": field, "language": "site", "siteId": site["siteId"], "query": query,
                             "url": discovery["url"] + "?" + urlencode({"q": query, **discovery["locales"]["ja"]})})
    feeds = fetch_many(requests, cfg["http"])
    candidates = {}
    for feed in feeds:
        if "error" in feed:
            continue
        try:
            entries = parse_feed(feed["body"])
        except (ET.ParseError, ValueError):
            feed["error"] = "InvalidFeed"
            continue
        for entry in entries:
            candidate = candidates.setdefault(entry["url"], {**entry, "fields": [], "languages": []})
            for key, value in (("fields", feed["field"]), ("languages", feed["language"])):
                if value not in candidate[key]:
                    candidate[key].append(value)
    return {"collectedAt": now(), "researchPolicyVersion": policy.get("version"), "researchFields": policy.get("fields"), "displaySettings": policy.get("displaySettings"), "searchQueries": field_queries,
            "candidates": list(candidates.values()), "feeds": feeds}


def _timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Observation needs an explicit time zone")
    return result


def observe(targets, cfg, reference_at):
    reference = _timestamp(reference_at)
    start = reference - timedelta(hours=72)
    requests = []
    for target in targets:
        published = _timestamp(target["publishedAt"])
        if not start < published <= reference:
            continue
        common = {"targetSourceId": target["sourceId"], "targetUrl": normalized_url(target["url"])}
        requests.append({**common, "platform": "hatena",
                         "url": "https://bookmark.hatenaapis.com/count/entry?" + urlencode({"url": common["targetUrl"]})})
    rows = fetch_many(requests, cfg)
    for row in rows:
        if "error" in row:
            continue
        try:
            count = json.loads(row["body"])
            if type(count) is not int or count < 0:
                raise ValueError("Invalid counter")
            row["count"] = count
        except (ValueError, TypeError, KeyError):
            row["error"] = "InvalidObservation"
    return rows


def reaction_evidence(observations, reference_at, completed_at=None):
    end = _timestamp(completed_at or reference_at)
    start = _timestamp(reference_at) - timedelta(hours=72)
    latest = {}
    for row in observations:
        if row.get("error") or "count" not in row:
            continue
        if row.get("platform") != "hatena":
            continue
        url = normalized_url(row["url"])
        parts = urlsplit(url)
        if (parts.hostname != "bookmark.hatenaapis.com" or parts.path != "/count/entry"
                or parse_qs(parts.query).get("url") != [row["targetUrl"]]):
            raise ValueError("Invalid Hatena observation URL")
        if type(row["count"]) is not int or row["count"] < 0:
            raise ValueError("Invalid counter")
        when = _timestamp(row["observedAt"])
        if start < when <= end:
            key = (row["targetSourceId"], url)
            if key not in latest or when > latest[key][0]:
                latest[key] = (when, row)
    evidence, sources = [], {}
    for (target_id, url), (_, row) in latest.items():
        sid = source_id(url, "hatena")
        sources[sid] = {"sourceId": sid, "url": url, "publisherId": "hatena",
                        "sourceType": "official", "checkedAt": row["observedAt"], "verificationStatus": "verified"}
        evidence.append({"platform": "hatena", "sourceId": sid, "targetSourceId": target_id,
                         "count": row["count"], "observedAt": row["observedAt"]})
    return {"reactionEvidence": evidence, "sources": list(sources.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "pages", "observe", "reactions"])
    parser.add_argument("--input", nargs="+")
    parser.add_argument("--policy")
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference-at")
    parser.add_argument("--completed-at")
    args = parser.parse_args()
    cfg = load_policy()
    inputs = [json.loads(Path(path).read_text(encoding="utf-8-sig")) for path in args.input or []]
    if args.command == "collect":
        if not args.policy:
            parser.error("collect requires --policy")
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8-sig"))
        result = collect(cfg, policy, inputs[0] if inputs else None)
    elif not inputs:
        parser.error("--input is required for this command")
    elif args.command == "pages":
        urls = dict.fromkeys(normalized_url(row["url"]) for rows in inputs for row in rows)
        result = fetch_pages([{"url": url} for url in urls], cfg["http"])
    elif args.command == "observe":
        if not args.reference_at:
            parser.error("observe requires --reference-at")
        result = observe([row for rows in inputs for row in rows], cfg["http"], args.reference_at)
    else:
        if not args.reference_at:
            parser.error("reactions requires --reference-at")
        result = reaction_evidence([row for rows in inputs for row in rows], args.reference_at, args.completed_at)
    with Path(args.output).open("w", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"output": args.output}))


if __name__ == "__main__":
    main()

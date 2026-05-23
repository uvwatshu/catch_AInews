import argparse
import datetime as dt
import email.utils
import html
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


CHINA_TZ = dt.timezone(dt.timedelta(hours=8))
OPEN_SEARCH = "\u5f00\u653e\u641c\u7d22"
FIXED_RSS = "\u56fa\u5b9aRSS"
REPORT_TITLE = "AI\u521b\u6295\u7ebf\u7d22\u65e5\u62a5"
REGISTRY_NOTE = "\u672a\u63a5\u5165\u5de5\u5546\u6570\u636e\u6e90\uff0c\u6682\u4e0d\u81ea\u52a8\u786e\u8ba4\u6ce8\u518c\u540d\u548c\u5730\u5740"


@dataclass
class Item:
    title: str
    url: str
    source: str
    published: str
    published_at: dt.datetime | None
    discovered_by: str
    query: str
    summary: str = ""
    company: str = ""
    region: str = ""


DIRECT_SEARCH_QUERIES = [
    "AI \u521b\u4e1a \u878d\u8d44",
    "AI Agent \u521b\u4e1a\u516c\u53f8 \u878d\u8d44",
    "\u5927\u5382\u79bb\u804c AI \u521b\u4e1a",
    "\u524d\u5b57\u8282 AI \u521b\u4e1a",
    "\u524d\u817e\u8baf AI \u521b\u4e1a",
    "\u524d\u963f\u91cc AI \u521b\u4e1a",
    "\u524d\u767e\u5ea6 AI \u521b\u4e1a",
    "\u524d\u534e\u4e3a AI \u521b\u4e1a",
    "\u65b0\u6210\u7acb AI \u516c\u53f8 \u62db\u8058",
    "BOSS\u76f4\u8058 AI Agent \u521b\u4e1a\u516c\u53f8",
    "AI startup funding",
    "ex-OpenAI startup raised",
    "ex-Google AI startup funding",
    "AI agent startup hiring",
    "stealth AI startup hiring",
    "a16z AI investment",
    "seed round AI startup",
    "launched AI tool",
    "new AI tool",
]


SITE_QUERIES = [
    "site:36kr.com AI \u521b\u4e1a \u878d\u8d44",
    "site:pedaily.cn AI \u878d\u8d44 \u6295\u8d44\u754c",
    "site:cyzone.cn AI \u878d\u8d44 \u521b\u4e1a\u90a6",
    "site:huxiu.com AI \u521b\u4e1a \u878d\u8d44",
    "site:leiphone.com AI \u521b\u4e1a \u878d\u8d44",
    "site:deeptechchina.com AI \u878d\u8d44 \u521b\u4e1a",
    "site:a16z.com AI startup investment",
    "site:ycombinator.com/companies AI agent",
    "site:ycombinator.com/jobs AI startup hiring",
    "site:producthunt.com AI tools launch",
]


CHANNEL_QUERIES = [
    "AING\u786c\u8ff9 AI \u521b\u4e1a \u878d\u8d44",
    "\u9cb8\u7280 AI \u521b\u4e1a \u878d\u8d44",
    "\u5341\u5b57\u8def\u53e3crossing AI \u521b\u4e1a",
    "\u94c5\u7b14\u9053 AI \u878d\u8d44",
    "36\u6c2a AI \u521b\u4e1a \u878d\u8d44",
    "\u864e\u55c5APP AI \u521b\u4e1a \u878d\u8d44",
    "Z Potentials AI startup funding",
    "DeepTech AI \u521b\u4e1a \u878d\u8d44",
    "\u521b\u4e1a\u90a6 AI \u878d\u8d44",
    "\u6295\u8d44\u754c AI \u878d\u8d44",
    "\u79d1\u521b\u65e5\u62a5 AI \u878d\u8d44",
    "\u6df1\u601dSense AI \u521b\u4e1a",
    "\u5927\u6e7e\u533a\u8d44\u672c\u5708 AI \u878d\u8d44",
    "\u6295\u8d44\u5bb6 AI \u878d\u8d44",
    "\u7533\u5988\u7684\u670b\u53cb\u5708 AI \u521b\u4e1a",
    "36\u6c2aPro AI \u521b\u4e1a \u878d\u8d44",
    "\u79d1\u6280\u8d44\u672c\u5708 AI \u878d\u8d44",
    "\u786c\u6c2a AI \u878d\u8d44",
    "IT\u6854\u5b50 AI \u878d\u8d44",
    "AI\u79d1\u6280\u8bc4\u8bba AI \u521b\u4e1a",
    "Top\u534e\u4eba\u79d1\u521b\u793e AI \u521b\u4e1a",
    "\u767d\u9cb8\u51fa\u6d77 AI \u521b\u4e1a",
    "\u7279\u5de5\u5b87\u5b99 AI \u521b\u4e1a",
    "\u6697\u6d8cWaves AI \u878d\u8d44",
    "\u96f7\u5cf0\u7f51 AI \u521b\u4e1a \u878d\u8d44",
]


RSS_FEEDS = [
    ("a16z", "https://a16z.com/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Product Hunt", "https://www.producthunt.com/feed"),
]


KEYWORD_WEIGHTS = {
    "\u878d\u8d44": 4,
    "\u6295\u8d44": 3,
    "\u9886\u6295": 4,
    "\u521b\u4e1a": 3,
    "\u79bb\u804c": 3,
    "\u5927\u5382": 2,
    "ai": 2,
    "agent": 3,
    "\u62db\u8058": 2,
    "boss\u76f4\u8058": 2,
    "a16z": 4,
    "funding": 4,
    "raised": 4,
    "seed": 3,
    "series": 3,
    "startup": 3,
    "ex-": 2,
    "hiring": 2,
    "launch": 2,
}


def fetch_url(url: str, timeout: int = 8) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 ai-investment-digest/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def text_of(parent: ET.Element, tag: str) -> str:
    node = parent.find(tag)
    if node is not None and node.text:
        return html.unescape(re.sub(r"\s+", " ", node.text)).strip()
    return ""


def parse_feed(content: bytes, source: str, discovered_by: str, query: str) -> list[Item]:
    root = ET.fromstring(content)
    items: list[Item] = []
    for entry in root.findall(".//item"):
        title = text_of(entry, "title")
        link = text_of(entry, "link")
        published_text, published_at = normalize_date(text_of(entry, "pubDate"))
        summary = re.sub("<[^>]+>", "", text_of(entry, "description"))
        if title and link:
            items.append(enrich_item(Item(title, link, source, published_text, published_at, discovered_by, query, summary)))

    atom = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f"{atom}entry"):
        title = text_of(entry, f"{atom}title")
        link_node = entry.find(f"{atom}link")
        link = link_node.get("href", "") if link_node is not None else ""
        published_text, published_at = normalize_date(text_of(entry, f"{atom}updated"))
        summary = re.sub("<[^>]+>", "", text_of(entry, f"{atom}summary"))
        if title and link:
            items.append(enrich_item(Item(title, link, source, published_text, published_at, discovered_by, query, summary)))
    return items


def enrich_item(item: Item) -> Item:
    item.company = extract_company(item)
    item.region = infer_region(item)
    return item


def normalize_date(raw: str) -> tuple[str, dt.datetime | None]:
    if not raw:
        return "", None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        parsed = parsed.astimezone(CHINA_TZ)
        return parsed.strftime("%Y-%m-%d %H:%M"), parsed
    except Exception:
        return raw[:32], None


def google_news_url(query: str, days: int) -> str:
    params = urllib.parse.urlencode({"q": f"{query} when:{days}d", "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"})
    return f"https://news.google.com/rss/search?{params}"


def bing_news_url(query: str) -> str:
    params = urllib.parse.urlencode({"q": query, "format": "rss", "setlang": "zh-Hans"})
    return f"https://www.bing.com/news/search?{params}"


def collect_items(days: int) -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    errors: list[str] = []
    jobs: list[tuple[str, str, str, str]] = []

    for source, url in RSS_FEEDS:
        jobs.append((source, url, FIXED_RSS, source))

    for query in DIRECT_SEARCH_QUERIES + SITE_QUERIES + CHANNEL_QUERIES:
        jobs.append(("Google News", google_news_url(query, days), OPEN_SEARCH, query))
        jobs.append(("Bing News", bing_news_url(query), OPEN_SEARCH, query))

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {
            executor.submit(fetch_url, url): (source, discovered_by, query)
            for source, url, discovered_by, query in jobs
        }
        for future in as_completed(future_map):
            source, discovered_by, query = future_map[future]
            try:
                items.extend(parse_feed(future.result(), source, discovered_by, query))
            except Exception as exc:
                errors.append(f"{source} / {query}: {exc}")

    return dedupe(filter_recent(items, days)), errors


def filter_recent(items: list[Item], days: int) -> list[Item]:
    cutoff = dt.datetime.now(CHINA_TZ) - dt.timedelta(days=days)
    return [item for item in items if item.published_at is None or item.published_at >= cutoff]


def dedupe(items: list[Item]) -> list[Item]:
    seen: set[str] = set()
    unique: list[Item] = []
    for item in sorted(items, key=score_item, reverse=True):
        keys = {normalize_url(item.url), title_fingerprint(item.title), event_fingerprint(item), *entity_keys(item.title)}
        if item.company and item.company != "\u672a\u8bc6\u522b":
            keys.add(f"company:{item.company.lower()}")
        if any(key in seen for key in keys if key):
            continue
        seen.update(key for key in keys if key)
        unique.append(item)
    return unique


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query_pairs = urllib.parse.parse_qsl(parsed.query)
    for key, value in query_pairs:
        if key == "url" and value.startswith(("http://", "https://")):
            return normalize_url(value)
    clean_query = urllib.parse.parse_qsl(parsed.query)
    clean_query = [(k, v) for k, v in clean_query if not k.lower().startswith("utm_")]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(clean_query), fragment=""))


def title_fingerprint(title: str) -> str:
    lowered = title.lower()
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", lowered)
    useful = [token for token in tokens if len(token) > 1 and token not in {"ai", "the", "and", "with"}]
    return "title:" + "|".join(useful[:8])


def event_fingerprint(item: Item) -> str:
    text = f"{item.title} {item.summary}"
    company = item.company.lower() if item.company and item.company != "\u672a\u8bc6\u522b" else ""
    money = re.findall(r"(\d+(?:\.\d+)?\s*(?:\u4ebf|\u4e07|million|billion|m|b)\s*(?:\u7f8e\u5143|\u5143|rmb|usd)?)", text, re.I)
    round_match = re.findall(r"(\u5929\u4f7f\u8f6e|\u79cd\u5b50\+?\u8f6e|\u9884\u79cd\u5b50\u8f6e|pre-seed|seed|series\s+[a-z])", text, re.I)
    if company or money or round_match:
        return f"event:{company}:{'|'.join(money[:2]).lower()}:{'|'.join(round_match[:2]).lower()}"
    return ""


def entity_keys(title: str) -> set[str]:
    generic = {
        "agent",
        "startup",
        "funding",
        "raised",
        "series",
        "seed",
        "cloud",
        "data",
        "openai",
        "google",
        "microsoft",
        "visual",
    }
    keys: set[str] = set()
    for match in re.findall(r"\b[A-Z][A-Za-z0-9-]{2,}(?:\s+AI)?\b", title):
        normalized = re.sub(r"\s+", " ", match).strip().lower()
        if normalized not in generic and not normalized.endswith(" ventures"):
            keys.add(f"entity:{normalized}")
    return keys


def extract_company(item: Item) -> str:
    text = re.sub(r"\s+", " ", f"{item.title} {item.summary}").strip()
    quoted = re.search(r"[\u300c\u300e\u201c\u201d\"']([^\"\u201c\u201d\u300d\u300f]{2,40}?)[\u300d\u300f\u201d\"']", text)
    if quoted:
        return clean_company(quoted.group(1))

    latin_patterns = [
        r"([A-Z][A-Za-z0-9-]{2,}(?:\s+AI|\s+Labs|\s+Robotics|\s+Systems|\s+Cloud|\s+Search|\s+Health|\s+Technologies)?)\s*(?:\u516c\u53f8)?(?:\u878d\u8d44|\u5b8c\u6210|\u83b7|raises?|raised|secures?)",
        r"(?:\u6295\u8d44|backs?|led by|from)\s+([A-Z][A-Za-z0-9-]{2,}(?:\s+AI|\s+Labs|\s+Robotics|\s+Systems|\s+Cloud|\s+Search)?)",
    ]
    for pattern in latin_patterns:
        found = re.search(pattern, text, re.I)
        if found:
            return clean_company(found.group(1))

    chinese_patterns = [
        r"([\u4e00-\u9fffA-Za-z0-9]{2,24})(?:\u516c\u53f8)?(?:\u5ba3\u5e03|\u5b8c\u6210|\u83b7|\u8fde\u7eed\u5b8c\u6210).{0,8}(?:\u878d\u8d44|\u8f6e)",
        r"([\u4e00-\u9fffA-Za-z0-9]{2,24})(?:\u516c\u53f8)?(?:\u878d\u8d44|\u83b7\u6295|\u83b7\u6570)",
    ]
    for pattern in chinese_patterns:
        found = re.search(pattern, text)
        if found:
            return clean_company(found.group(1))

    entities = entity_keys(item.title)
    if entities:
        return sorted(entities)[0].replace("entity:", "").title()
    return "\u672a\u8bc6\u522b"


def clean_company(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw).strip(" -_\u300a\u300b:：，,。")
    value = re.sub(r"\u516c\u53f8$", "", value)
    value = re.sub(r"(\u8fde\u7eed|\u6b63\u5f0f|\u8fd1\u65e5)$", "", value)
    stop_words = [
        "\u7f8e\u56fe\u9886\u6295",
        "\u6295\u8d44\u754c",
        "\u5bfc\u8bed",
        "\u65e5\u6d88\u606f",
        "\u5ba3\u5e03",
        "\u5b8c\u6210",
        "\u83b7\u5f97",
        "AI",
        "The",
    ]
    for word in stop_words:
        if value == word:
            return "\u672a\u8bc6\u522b"
    return value[:60] if value else "\u672a\u8bc6\u522b"


def infer_region(item: Item) -> str:
    text = f"{item.title} {item.summary} {item.query} {item.url}".lower()
    china_signals = [
        "\u4e2d\u56fd",
        "\u5317\u4eac",
        "\u4e0a\u6d77",
        "\u6df1\u5733",
        "\u5e7f\u5dde",
        "\u676d\u5dde",
        "\u9999\u6e2f",
        "\u5b57\u8282",
        "\u817e\u8baf",
        "\u963f\u91cc",
        "\u767e\u5ea6",
        "\u534e\u4e3a",
        "\u7f8e\u56fe",
        "\u4ebf\u5143",
        "\u4eba\u6c11\u5e01",
        "\u6d2a\u6cf0\u57fa\u91d1",
        "\u6b63\u666f\u57fa\u91d1",
        "\u6e05\u534e",
        "\u7ca4\u79d1",
        "\u4e16\u7eaa\u534e\u901a",
        "\u963f\u91cc\u7cfb",
        "itjuzi",
        "boss\u76f4\u8058",
    ]
    overseas_signals = [
        "san francisco",
        "silicon valley",
        "new york",
        "london",
        "sheffield",
        "saudi",
        "yc",
        "y combinator",
        "a16z.com",
        "techcrunch.com",
        "venturebeat.com",
        "producthunt.com",
        "\u5317\u7f8e",
        "\u7f8e\u56fd",
        "\u7f8e\u5143",
        "ex-openai",
        "ex-google",
        "ex-meta",
    ]
    china_score = sum(1 for signal in china_signals if signal in text)
    overseas_score = sum(1 for signal in overseas_signals if signal in text)
    if china_score > overseas_score:
        return "\u4e2d\u56fd\u76f8\u5173"
    if overseas_score > china_score:
        return "\u6d77\u5916"
    return "\u5f85\u5224\u65ad"


def registry_line(item: Item) -> str:
    if item.region != "\u4e2d\u56fd\u76f8\u5173":
        return "\u975e\u4e2d\u56fd\u76f8\u5173\u6216\u5f85\u5224\u65ad\uff0c\u6682\u4e0d\u505a\u5de5\u5546\u6ce8\u518c\u4fe1\u606f\u8981\u6c42"
    company = item.company if item.company and item.company != "\u672a\u8bc6\u522b" else item.title[:32]
    q = urllib.parse.quote(company)
    return (
        f"{REGISTRY_NOTE}\uff1b\u5f85\u67e5\u8bcd\uff1a{company}\uff1b"
        f"\u5929\u773c\u67e5\uff1ahttps://www.tianyancha.com/search?key={q}\uff1b"
        f"\u4f01\u67e5\u67e5\uff1ahttps://www.qcc.com/web/search?key={q}"
    )


def score_item(item: Item) -> int:
    haystack = f"{item.title} {item.summary} {item.source} {item.query}".lower()
    score = 0
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in haystack:
            score += weight
    if item.discovered_by == OPEN_SEARCH:
        score += 1
    if "a16z" in haystack:
        score += 3
    return score


def credibility(item: Item) -> str:
    lower = f"{item.source} {item.url}".lower()
    if any(domain in lower for domain in ["a16z.com", "ycombinator.com", "producthunt.com"]):
        return "A/B"
    if any(name in lower for name in ["techcrunch", "venturebeat", "36kr", "pedaily", "cyzone", "leiphone", "huxiu"]):
        return "B"
    if item.discovered_by == OPEN_SEARCH:
        return "C"
    return "C"


def build_report(items: list[Item], errors: list[str], today: dt.date) -> str:
    ranked = sorted(items, key=score_item, reverse=True)
    top = ranked[:12]
    a16z = [item for item in ranked if "a16z" in f"{item.title} {item.source} {item.url}".lower()][:6]
    surprises = [item for item in ranked if item.discovered_by == OPEN_SEARCH][:8]

    lines = [
        f"{REPORT_TITLE} - {today.isoformat()}",
        "",
        "\u6267\u884c\u6982\u89c8",
        f"- \u5019\u9009\u7ebf\u7d22\uff1a{len(items)} \u6761\uff08\u5df2\u505a URL/\u6807\u9898/\u516c\u53f8/\u4e8b\u4ef6\u7ea7\u53bb\u91cd\uff09",
        f"- \u91c7\u96c6\u6e20\u9053\uff1a{len(RSS_FEEDS)} \u4e2a\u56fa\u5b9a RSS\uff0c{len(DIRECT_SEARCH_QUERIES)} \u7ec4\u5f00\u653e\u641c\u7d22\uff0c{len(SITE_QUERIES)} \u7ec4\u7ad9\u70b9\u641c\u7d22\uff0c{len(CHANNEL_QUERIES)} \u7ec4\u516c\u4f17\u53f7/\u5a92\u4f53\u540d\u641c\u7d22",
        "- \u8986\u76d6\u8fb9\u754c\uff1aGitHub Actions \u4e0d\u767b\u5f55\u5fae\u4fe1\uff0c\u4e0d\u4f1a\u9010\u7bc7\u6293\u53d6\u516c\u4f17\u53f7\u539f\u6587\uff1b\u5b83\u4f1a\u6bcf\u5929\u8dd1\u5b8c\u4e0a\u8ff0\u516c\u5f00 RSS \u548c\u641c\u7d22\u4efb\u52a1\u3002",
        "",
        "\u4eca\u65e5\u91cd\u70b9\u7ebf\u7d22",
    ]
    for index, item in enumerate(top, 1):
        lines.extend(format_item(index, item))

    lines.extend(["", "a16z\u8d8b\u52bf\u89c2\u5bdf"])
    if a16z:
        for index, item in enumerate(a16z, 1):
            lines.extend(format_item(index, item, compact=True))
    else:
        lines.append("- \u4eca\u65e5\u672a\u6293\u5230\u65b0\u7684 a16z \u9ad8\u76f8\u5173\u516c\u5f00\u7ebf\u7d22\u3002")

    lines.extend(["", "\u5f00\u653e\u641c\u7d22\u610f\u5916\u53d1\u73b0"])
    if surprises:
        for index, item in enumerate(surprises, 1):
            lines.extend(format_item(index, item, compact=True))
    else:
        lines.append("- \u4eca\u65e5\u5f00\u653e\u641c\u7d22\u672a\u53d1\u73b0\u9ad8\u76f8\u5173\u65b0\u589e\u7ebf\u7d22\u3002")

    lines.extend(
        [
            "",
            "\u5f85\u9a8c\u8bc1\u540d\u5355",
            "- \u878d\u8d44\u91d1\u989d\u3001\u8f6e\u6b21\u3001\u521b\u59cb\u4eba\u5c65\u5386\u548c\u6295\u8d44\u65b9\u4fe1\u606f\u9700\u7ee7\u7eed\u7528\u516c\u53f8\u5b98\u7f51\u3001\u6295\u8d44\u673a\u6784\u516c\u544a\u3001\u5de5\u5546\u4fe1\u606f\u3001\u62db\u8058\u9875\u6216\u6570\u636e\u5e93\u4ea4\u53c9\u9a8c\u8bc1\u3002",
            "- \u516c\u4f17\u53f7\u7ebf\u7d22\u82e5\u53ea\u6709\u8f6c\u8f7d\u6216\u5355\u4e00\u81ea\u5a92\u4f53\u6765\u6e90\uff0c\u9ed8\u8ba4\u4e0d\u4f5c\u4e3a\u5df2\u786e\u8ba4\u4e8b\u5b9e\u3002",
            "",
            "\u660e\u5929\u7ee7\u7eed\u8ddf\u8e2a\u7684\u95ee\u9898",
            "- \u4eca\u65e5\u9ad8\u5206\u7ebf\u7d22\u4e2d\uff0c\u54ea\u4e9b\u516c\u53f8\u51fa\u73b0\u65b0\u7684\u62db\u8058\u5c97\u4f4d\u6216\u5b98\u7f51\u53d1\u5e03\uff1f",
            "- a16z/YC/\u6d77\u5916 AI \u5de5\u5177\u699c\u5355\u91cc\u662f\u5426\u6709\u53ef\u6620\u5c04\u5230\u56fd\u5185\u7684\u65b0\u8d5b\u9053\uff1f",
            "- \u662f\u5426\u51fa\u73b0\u5927\u5382\u79bb\u804c\u521b\u4e1a\u56e2\u961f\u7684\u65b0\u878d\u8d44\u6216\u4ea7\u54c1\u53d1\u5e03\uff1f",
        ]
    )

    if errors:
        lines.extend(["", "\u6293\u53d6\u5907\u6ce8"])
        lines.extend(f"- {error}" for error in errors[:8])

    return "\n".join(lines).strip() + "\n"


def format_item(index: int, item: Item, compact: bool = False) -> list[str]:
    lines = [
        "",
        f"{index}. {item.company if item.company else item.title}",
        f"   \u6807\u9898\uff1a{item.title}",
        f"   \u5730\u533a\uff1a{item.region}\uff1b\u53ef\u4fe1\u5ea6\uff1a{credibility(item)}\uff1b\u53d1\u73b0\u65b9\u5f0f\uff1a{item.discovered_by}",
        f"   \u6765\u6e90\uff1a{item.source}",
    ]
    if item.published:
        lines.append(f"   \u65f6\u95f4\uff1a{item.published}")
    if item.query and item.query != item.source:
        lines.append(f"   \u89e6\u53d1\u8bcd\uff1a{item.query}")
    lines.append(f"   \u5224\u65ad\uff1a{reason_for(item)}")
    if not compact:
        lines.append(f"   \u5de5\u5546\u4fe1\u606f\uff1a{registry_line(item)}")
    lines.append(f"   \u94fe\u63a5\uff1a{item.url}")
    if not compact and item.summary:
        summary = re.sub(r"\s+", " ", item.summary).strip()
        if len(summary) > 220:
            summary = summary[:217] + "..."
        if summary:
            lines.append(f"   \u6458\u8981\uff1a{summary}")
    return lines


def reason_for(item: Item) -> str:
    text = f"{item.title} {item.summary} {item.query}".lower()
    reasons: list[str] = []
    if any(word in text for word in ["\u878d\u8d44", "funding", "raised", "seed", "series"]):
        reasons.append("\u7591\u4f3c\u6295\u878d\u8d44\u6216\u8d44\u672c\u4e8b\u4ef6")
    if any(word in text for word in ["\u62db\u8058", "hiring", "jobs", "boss\u76f4\u8058"]):
        reasons.append("\u51fa\u73b0\u62db\u8058/\u6269\u5f20\u4fe1\u53f7")
    if any(word in text for word in ["\u79bb\u804c", "ex-", "\u524d\u5b57\u8282", "\u524d\u817e\u8baf", "\u524d\u963f\u91cc", "\u524dopenai", "ex-openai"]):
        reasons.append("\u53ef\u80fd\u6d89\u53ca\u5927\u5382/\u660e\u661f\u56e2\u961f\u521b\u4e1a")
    if any(word in text for word in ["agent", "ai tool", "\u5de5\u5177", "launched", "launch"]):
        reasons.append("\u53ef\u80fd\u662f\u65b0 AI \u5de5\u5177\u6216 Agent \u65b9\u5411")
    if "a16z" in text:
        reasons.append("\u4e0e a16z \u6295\u8d44\u6216\u8d8b\u52bf\u53d9\u4e8b\u76f8\u5173")
    return "\uff1b".join(reasons) if reasons else "\u4e0e AI \u521b\u4e1a/\u521b\u6295\u5173\u952e\u8bcd\u76f8\u5173\uff0c\u9700\u7ee7\u7eed\u9a8c\u8bc1"


def send_report(subject: str, body_file: Path, to_addr: str, from_addr: str) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("send_ai_digest_email.py")),
        "--subject",
        subject,
        "--body-file",
        str(body_file),
        "--to",
        to_addr,
        "--from-addr",
        from_addr,
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and optionally email the AI investment digest.")
    parser.add_argument("--no-send", action="store_true", help="Only write the digest file.")
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--days", type=int, default=int(os.getenv("AI_DIGEST_MAX_AGE_DAYS", "7")))
    args = parser.parse_args()

    now = dt.datetime.now(CHINA_TZ)
    today = now.date()
    items, errors = collect_items(args.days)
    report = build_report(items, errors, today)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body_file = out_dir / f"ai_digest_{today.isoformat()}.txt"
    body_file.write_text(report, encoding="utf-8")
    print(f"Wrote {body_file} with {len(items)} collected items.")

    if args.no_send:
        print(report[:2000])
        return

    to_addr = os.getenv("AI_DIGEST_EMAIL_TO", "1530550584@qq.com")
    from_addr = os.getenv("AI_DIGEST_SMTP_USER", "huanghongwei0308@163.com")
    subject = f"{REPORT_TITLE} - {today.isoformat()}"
    send_report(subject, body_file, to_addr, from_addr)


if __name__ == "__main__":
    main()

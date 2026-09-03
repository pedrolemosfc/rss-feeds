#!/usr/bin/env python3
"""Scrape-to-RSS generators for sites lacking usable native feeds."""

from __future__ import annotations

import email.utils
import html as html_lib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "feeds")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

NATIVE_FEEDS = [
    {"name": "Piauí", "url": "https://piaui.uol.com.br/feed/", "notes": "native"},
    {"name": "Noize", "url": "https://feeds.feedburner.com/noize", "notes": "native"},
    {"name": "Ugly Things", "url": "https://ugly-things.com/feed/", "notes": "native"},
    {
        "name": "Panenka",
        "url": "https://www.panenka.org/feed/",
        "notes": "native (main covers all sections)",
    },
    {"name": "Treblezine", "url": "https://www.treblezine.com/feed/", "notes": "native"},
    {
        "name": "Folha Ilustrada",
        "url": "https://feeds.folha.uol.com.br/ilustrada/rss091.xml",
        "notes": "native approximate for jazz/críticas/show topics",
    },
    {
        "name": "Guia Folha site-wide",
        "url": "https://guia.folha.uol.com.br/rss.xml",
        "notes": "native site-wide",
    },
    {
        "name": "Estadão Cultura",
        "url": "https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/cultura/?body=%7B%22layout%22:%22google-news%22%7D",
        "notes": "native section feed (not author-specific)",
    },
    {
        "name": "Veja SP site-wide",
        "url": "https://vejasp.abril.com.br/feed/",
        "notes": "native site-wide (not column)",
    },
    {
        "name": "Correio site-wide",
        "url": "https://www.correiobraziliense.com.br/feed/",
        "notes": "native site-wide (not author)",
    },
    {
        "name": "Anthropic News (RSSHub)",
        "url": "https://rsshub.bestblogs.dev/anthropic/news",
        "notes": "closest to Claude via RSSHub, unofficial",
    },
]


def fetch(url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset, errors="replace"), None
            except LookupError:
                return raw.decode("utf-8", errors="replace"), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", s)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def abs_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    # ISO-ish
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%b %d %Y",
    ):
        try:
            v = value
            if fmt.endswith("%z") and re.search(r"[+-]\d{2}:\d{2}$", v):
                v = v[:-3] + v[-2:]
            if fmt.endswith("Z") and v.endswith("Z"):
                dt = datetime.strptime(v, fmt).replace(tzinfo=timezone.utc)
                return dt
            dt = datetime.strptime(v, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # RFC 2822
    try:
        tt = email.utils.parsedate_tz(value)
        if tt:
            return datetime.fromtimestamp(email.utils.mktime_tz(tt), tz=timezone.utc)
    except Exception:
        pass
    # "Aug 26, 2026" embedded
    m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})",
        value,
        re.I,
    )
    if m:
        try:
            return datetime.strptime(
                f"{m.group(1)[:3].title()} {m.group(2)} {m.group(3)}", "%b %d %Y"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    m = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})",
        value,
        re.I,
    )
    if m:
        try:
            return datetime.strptime(
                f"{m.group(1).title()} {m.group(2)} {m.group(3)}", "%B %d %Y"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # from URL /YYYY/MM/DD or /YYYY/MM/
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", value)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except ValueError:
            pass
    m = re.search(r"/(\d{4})/(\d{2})/", value)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def rfc822(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return email.utils.format_datetime(dt.astimezone(timezone.utc))


def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        link = (it.get("link") or "").rstrip("/")
        if not link or link in seen:
            continue
        seen.add(link)
        out.append(it)
    return out


def sort_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(it: Dict[str, Any]):
        dt = it.get("_dt")
        if isinstance(dt, datetime):
            return dt
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    return sorted(items, key=key, reverse=True)


def write_rss(
    path: str,
    title: str,
    link: str,
    description: str,
    items: List[Dict[str, Any]],
    language: str = "pt-BR",
) -> None:
    now = rfc822(datetime.now(timezone.utc))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{escape(title)}</title>",
        f"<link>{escape(link)}</link>",
        f"<description>{escape(description)}</description>",
        f"<language>{escape(language)}</language>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for it in items:
        lines.append("<item>")
        lines.append(f"<title>{escape(it['title'])}</title>")
        lines.append(f"<link>{escape(it['link'])}</link>")
        lines.append(f"<guid isPermaLink=\"true\">{escape(it.get('guid') or it['link'])}</guid>")
        if it.get("pubDate"):
            lines.append(f"<pubDate>{escape(it['pubDate'])}</pubDate>")
        if it.get("description"):
            lines.append(f"<description>{escape(it['description'])}</description>")
        lines.append("</item>")
    lines.extend(["</channel>", "</rss>", ""])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def item(
    title: str,
    link: str,
    description: str = "",
    date_raw: Optional[str] = None,
) -> Dict[str, Any]:
    title = strip_tags(title) if "<" in title else html_lib.unescape(title).strip()
    title = re.sub(r"\s+", " ", title).strip()
    description = strip_tags(description) if description else ""
    description = re.sub(r"\s+", " ", description).strip()
    if len(description) > 500:
        description = description[:497] + "..."
    dt = parse_date(date_raw) or parse_date(link)
    return {
        "title": title or link,
        "link": link,
        "guid": link,
        "description": description,
        "pubDate": rfc822(dt),
        "_dt": dt,
    }


# ---------------- scrapers ----------------


def scrape_espaco_unimed(html: str, base: str) -> List[Dict[str, Any]]:
    """One RSS item per show card on the Espaço Unimed agenda."""
    from zoneinfo import ZoneInfo

    months = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    }
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    year = now.year
    last_month: Optional[int] = None

    mlist = re.search(r'<ul class="clean shows">(.*?)</ul>', html, re.S | re.I)
    block = mlist.group(1) if mlist else html
    cards = re.findall(r"<li\b[^>]*>(.*?)</li>", block, re.S | re.I)
    items: List[Dict[str, Any]] = []
    for card in cards:
        hm = re.search(
            r'<h3>\s*<a href="(https://www\.espacounimed\.com\.br/show/[^"]+)"[^>]*>(.*?)</a>',
            card,
            re.S | re.I,
        )
        if not hm:
            continue
        link = hm.group(1).strip()
        title = strip_tags(hm.group(2))
        if not title:
            continue

        def _cls(name: str) -> str:
            mm = re.search(rf'class="{name}">(.*?)</p>', card, re.S | re.I)
            return strip_tags(mm.group(1)) if mm else ""

        day_s, month_s, weekday = _cls("day-of-month"), _cls("month"), _cls("day-of-week")
        sm = re.search(r'class="subtitle">(.*?)</span>', card, re.S | re.I)
        subtitle = strip_tags(sm.group(1)) if sm else ""
        tm = re.search(r"<article>.*?<p>(\d{1,2}:\d{2})</p>", card, re.S | re.I)
        time_s = tm.group(1) if tm else ""
        tickets = ""
        tkm = re.search(r"""ticketButton\(\d*\s*,\s*['\"](https?://[^'\"]+)['\"]""", card)
        if tkm:
            tickets = tkm.group(1)
        statuses = []
        for lab in re.findall(r"<label class='[^']+'>\s*<i></i>\s*<span>([^<]+)</span>", card):
            lab = strip_tags(lab)
            if lab:
                statuses.append(lab)

        month_i = months.get(month_s.lower()[:3])
        try:
            day_i = int(day_s)
        except ValueError:
            day_i = 1
        dt: Optional[datetime] = None
        if month_i:
            if last_month is None:
                trial = datetime(year, month_i, min(day_i, 28), tzinfo=tz)
                if (now - trial).days > 45:
                    year += 1
            elif month_i < last_month:
                year += 1
            last_month = month_i
            hh, mm = 12, 0
            if time_s:
                try:
                    hh, mm = [int(x) for x in time_s.split(":")[:2]]
                except ValueError:
                    pass
            try:
                dt = datetime(year, month_i, day_i, hh, mm, tzinfo=tz)
            except ValueError:
                dt = None

        date_label = f"{day_s} {month_s}".strip()
        if dt:
            date_label = dt.strftime("%d/%m/%Y")
        title_full = title
        extra = " ".join(x for x in (date_label, time_s) if x).strip()
        if extra:
            title_full = f"{title} — {extra}"

        desc_bits = []
        if subtitle:
            desc_bits.append(subtitle)
        when = "Espaço Unimed"
        if weekday:
            when += f", {weekday}"
        if date_label:
            when += f" {date_label}"
        if time_s:
            when += f" às {time_s}"
        desc_bits.append(when)
        desc_bits.extend(statuses)
        if tickets:
            desc_bits.append(f"Ingressos: {tickets}")

        it = item(title_full, link, " · ".join(desc_bits), None)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))



def scrape_folha_topico(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # Prefer headline URL + title + standfirst + datetime nearby
    for m in re.finditer(
        r'<a href="(https://www1\.folha\.uol\.com\.br/[^"]+)" class="c-headline__url"[^>]*>\s*'
        r'<h2 class="c-headline__title">(.*?)</h2>\s*'
        r'(?:<p class="c-headline__standfirst">\s*(.*?)\s*</p>)?\s*'
        r'(?:<time[^>]*datetime="([^"]*)"[^>]*>)?',
        html,
        re.S | re.I,
    ):
        link, title, desc, dt = m.group(1), m.group(2), m.group(3) or "", m.group(4)
        if "/folha-topicos/" in link:
            continue
        items.append(item(title, link, desc, dt))
    if not items:
        # fallback: any article .shtml with nearby title
        for m in re.finditer(
            r'href="(https://www1\.folha\.uol\.com\.br/[^"]+\.shtml)"[^>]*>\s*'
            r'<h2[^>]*class="[^"]*c-headline__title[^"]*"[^>]*>(.*?)</h2>',
            html,
            re.S | re.I,
        ):
            items.append(item(m.group(2), m.group(1), "", m.group(1)))
    return sort_items(dedupe_items(items))


def scrape_guia(html: str, section: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # title link pattern
    pat = re.compile(
        rf'href="(https://guia\.folha\.uol\.com\.br/{re.escape(section)}/\d{{4}}/\d{{2}}/[^"]+\.shtml)"[^>]*>\s*'
        rf'(?:<!--.*?-->\s*)*<div class="c-headline-content[^"]*">\s*'
        rf'<h2 class="c-headline-title[^"]*">(.*?)</h2>\s*'
        rf'(?:<p class="c-headline-subtitle[^"]*">(.*?)</p>)?',
        re.S | re.I,
    )
    for m in pat.finditer(html):
        link, title, desc = m.group(1), m.group(2), m.group(3) or ""
        # find datetime after this match in a short window
        window = html[m.end() : m.end() + 500]
        dm = re.search(r'datetime="([^"]+)"', window)
        dt = dm.group(1) if dm else link
        items.append(item(title, link, desc, dt))
    if not items:
        # looser: unique article URLs + title from slug or nearby h2
        links = re.findall(
            rf'href="(https://guia\.folha\.uol\.com\.br/{re.escape(section)}/\d{{4}}/\d{{2}}/[^"]+\.shtml)"',
            html,
        )
        seen = set()
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            # find h2 after an occurrence of this link
            idx = html.find(link)
            chunk = html[idx : idx + 1500]
            hm = re.search(r'<h2 class="c-headline-title[^"]*">(.*?)</h2>', chunk, re.S)
            sm = re.search(r'<p class="c-headline-subtitle[^"]*">(.*?)</p>', chunk, re.S)
            dm = re.search(r'datetime="([^"]+)"', chunk)
            title = hm.group(1) if hm else link.rstrip("/").split("/")[-1].replace("-", " ")
            desc = sm.group(1) if sm else ""
            items.append(item(title, link, desc, dm.group(1) if dm else link))
    return sort_items(dedupe_items(items))


def scrape_estadao_sergio(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # Fusion.contentCache stories
    m = re.search(r"Fusion\.contentCache\s*=\s*", html)
    if m:
        start = m.end()
        if start < len(html) and html[start] == "{":
            depth = 0
            for j, ch in enumerate(html[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            cache = json.loads(html[start : j + 1])
                        except json.JSONDecodeError:
                            cache = {}
                        break
            else:
                cache = {}

            def walk(obj: Any) -> None:
                if isinstance(obj, dict):
                    url = obj.get("canonical_url") or ""
                    if (
                        isinstance(url, str)
                        and "/cultura/sergio-martins/" in url
                        and not url.rstrip("/").endswith("sergio-martins")
                    ):
                        headlines = obj.get("headlines") or {}
                        title = headlines.get("basic") if isinstance(headlines, dict) else None
                        desc_obj = obj.get("description")
                        desc = (
                            desc_obj.get("basic", "")
                            if isinstance(desc_obj, dict)
                            else (desc_obj or "")
                        )
                        dt = (
                            obj.get("first_publish_date")
                            or obj.get("display_date")
                            or obj.get("publish_date")
                        )
                        link = abs_url("https://www.estadao.com.br", url)
                        if title:
                            items.append(item(title, link, str(desc), dt))
                    for v in obj.values():
                        walk(v)
                elif isinstance(obj, list):
                    for v in obj:
                        walk(v)

            walk(cache)

    # HTML fallback: title attribute on article anchors
    if not items:
        for m in re.finditer(
            r'href="(https://www\.estadao\.com\.br/cultura/sergio-martins/[^"]+/)"[^>]*title="([^"]+)"',
            html,
        ):
            link = m.group(1)
            if link.rstrip("/").endswith("sergio-martins"):
                continue
            items.append(item(m.group(2), link, "", link))
    return sort_items(dedupe_items(items))


def scrape_vejasp_tudo_de_som(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # Collect unique coluna links with titles from anchor text
    for m in re.finditer(
        r'href="(https://vejasp\.abril\.com\.br/coluna/tudo-de-som/([^"/]+)/)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{8,200})',
        html,
    ):
        link, slug, title = m.group(1), m.group(2), m.group(3).strip()
        if not title or title.lower() in ("leia mais", "read more", "continuar"):
            # use nearby stronger title if this is empty-ish
            continue
        items.append(item(title, link, "", None))
    # Also pick from ItemList JSON-LD if present
    for m in re.finditer(
        r'https://vejasp\.abril\.com\.br/coluna/tudo-de-som/([a-z0-9\-]+)/',
        html,
        re.I,
    ):
        slug = m.group(1)
        link = f"https://vejasp.abril.com.br/coluna/tudo-de-som/{slug}/"
        # try find title near this URL
        idx = html.find(link)
        if idx < 0:
            continue
        chunk = html[max(0, idx - 200) : idx + 800]
        tm = re.search(r">([^<]{12,160})</(?:a|h[1-6]|span|div)>", chunk)
        title = tm.group(1).strip() if tm else slug.replace("-", " ")
        if title.lower() in ("leia mais",):
            title = slug.replace("-", " ")
        items.append(item(title, link, "", None))
    # Prefer titles that look like article titles (not nav)
    cleaned = []
    for it in dedupe_items(items):
        t = it["title"]
        if t.lower() in ("tudo de som", "veja são paulo", "cultura & lazer", "blog"):
            continue
        cleaned.append(it)
    return sort_items(cleaned)


def scrape_correio_irlam(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    for m in re.finditer(
        r'href="(https://www\.correiobraziliense\.com\.br/opiniao/(\d{4})/(\d{2})/\d+-([^"]+)\.html)"[^>]*>\s*'
        r"<article>(.*?)</article>",
        html,
        re.S | re.I,
    ):
        link, y, mo, slug, inner = m.groups()
        hm = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", inner, re.S | re.I)
        title = strip_tags(hm.group(1)) if hm else slug.replace("-", " ")
        # excerpt
        pm = re.search(r"<p[^>]*>(.*?)</p>", inner, re.S | re.I)
        desc = strip_tags(pm.group(1)) if pm else ""
        items.append(item(title, link, desc, f"{y}-{mo}-01"))
    if not items:
        for m in re.finditer(
            r'href="(https://www\.correiobraziliense\.com\.br/opiniao/(\d{4})/(\d{2})/\d+-([^"]+)\.html)"',
            html,
        ):
            link, y, mo, slug = m.groups()
            items.append(item(slug.replace("-", " ").title(), link, "", f"{y}-{mo}-01"))
    return sort_items(dedupe_items(items))


def scrape_billboard_sergio(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # Prefer WP REST API (author slug sergio-martins -> id 41)
    api = "https://billboard.com.br/wp-json/wp/v2/posts?author=41&per_page=20"
    body, err = fetch(api)
    if body and not err:
        try:
            posts = json.loads(body)
            if isinstance(posts, list) and posts:
                for p in posts:
                    title = (p.get("title") or {}).get("rendered") or ""
                    link = p.get("link") or ""
                    excerpt = (p.get("excerpt") or {}).get("rendered") or ""
                    date = p.get("date_gmt") or p.get("date")
                    if link and title:
                        items.append(item(title, link, excerpt, date))
                return sort_items(dedupe_items(items))
        except json.JSONDecodeError:
            pass
    # HTML fallback: article cards / post titles
    for m in re.finditer(
        r'href="(https://billboard\.com\.br/([^"/]+)/)"[^>]*>\s*'
        r'(?:<[^>]+>\s*)*([^<]{10,160})',
        html,
    ):
        link, slug, title = m.group(1), m.group(2), m.group(3).strip()
        skip = {
            "author",
            "generos",
            "festivais",
            "agendas",
            "listas",
            "coluna",
            "cultura",
            "charts",
            "entrevista",
            "videos",
            "negocios",
            "wp-content",
            "wp-json",
            "page",
            "categoria",
            "tag",
        }
        if slug in skip or link.rstrip("/").endswith("sergio-martins"):
            continue
        items.append(item(title, link, "", None))
    return sort_items(dedupe_items(items))


def scrape_asil_insights(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    for m in re.finditer(
        r'href="(https://asil\.org/insights/volume-(\d+)-issue-(\d+)/)"[^>]*>(.*?)</a>',
        html,
        re.S | re.I,
    ):
        link, vol, iss, inner = m.groups()
        title = strip_tags(inner)
        if not title or title.lower() in ("read more", "insights"):
            continue
        # date near link
        idx = m.start()
        chunk = html[max(0, idx - 400) : idx + 800]
        dm = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            chunk,
        )
        date_raw = dm.group(0) if dm else None
        # also try og image path year/month as weak date
        if not date_raw:
            im = re.search(r"/uploads/(\d{4})/(\d{2})/", chunk)
            if im:
                date_raw = f"{im.group(1)}-{im.group(2)}-01"
        items.append(item(title, link, f"ASIL Insights Vol. {vol} Issue {iss}", date_raw))
    return sort_items(dedupe_items(items))


def scrape_xai_news(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # Anchors to /news/slug with mixed date+title text
    for m in re.finditer(r'href="(/news/([a-z0-9\-._]+))"[^>]*>(.*?)</a>', html, re.S | re.I):
        path, slug, inner = m.groups()
        if slug in ("", "news"):
            continue
        text = strip_tags(inner)
        if not text:
            continue
        dm = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
            text,
            re.I,
        )
        date_raw = dm.group(1) if dm else None
        title = text
        if date_raw:
            title = text.replace(date_raw, "").strip()
        # Sometimes date+title concatenated twice
        if date_raw and title.count(date_raw) or len(title) > 180:
            # split heuristically: take first sentence-like chunk
            title = re.split(r"(?<=[a-z.])(?=[A-Z])", title)[0].strip()
            if len(title) < 8:
                title = slug.replace("-", " ")
        link = abs_url("https://x.ai", path)
        items.append(item(title, link, "", date_raw))
    # Also plain href="/news/..." without useful text: invent title from slug only if missing
    if not items:
        for path in re.findall(r'href="(/news/[a-z0-9\-._]+)"', html, re.I):
            slug = path.rsplit("/", 1)[-1]
            if slug == "news":
                continue
            items.append(item(slug.replace("-", " ").title(), abs_url("https://x.ai", path), "", None))
    return sort_items(dedupe_items(items))


def scrape_claude_blog(html: str, base: str) -> List[Dict[str, Any]]:
    items = []
    # Collect /blog/slug with meaningful titles
    for m in re.finditer(r'href="(/blog/([a-z0-9\-]+))"[^>]*>(.*?)</a>', html, re.S | re.I):
        path, slug, inner = m.groups()
        if slug in ("blog", "tag", "category") or slug.startswith("tag"):
            continue
        title = strip_tags(inner)
        if not title or len(title) < 12:
            continue
        if title.lower() in ("read more", "blog", "all posts", "load more"):
            continue
        link = abs_url("https://claude.com", path)
        # date near this occurrence
        idx = m.start()
        chunk = html[max(0, idx - 500) : idx + 200]
        dm = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
            chunk,
            re.I,
        )
        items.append(item(title, link, "", dm.group(1) if dm else None))
    # Also h2/h3 near blog links
    if len(items) < 3:
        for m in re.finditer(
            r'<h[23][^>]*>(.*?)</h[23]>.*?href="(/blog/[a-z0-9\-]+)"',
            html,
            re.S | re.I,
        ):
            title = strip_tags(m.group(1))
            link = abs_url("https://claude.com", m.group(2))
            if title and len(title) > 12:
                items.append(item(title, link, "", None))
    return sort_items(dedupe_items(items))


SCRAPE_TARGETS = [
    {
        "name": "folha-jazz",
        "source_url": "https://www1.folha.uol.com.br/folha-topicos/jazz/",
        "output": "folha-jazz.xml",
        "title": "Folha — tópico Jazz",
        "description": "Artigos do tópico Jazz na Folha de S.Paulo (scraped)",
        "language": "pt-BR",
        "scraper": scrape_folha_topico,
    },
    {
        "name": "folha-criticas-de-musica",
        "source_url": "https://www1.folha.uol.com.br/folha-topicos/criticas-de-musica/",
        "output": "folha-criticas-de-musica.xml",
        "title": "Folha — Críticas de música",
        "description": "Artigos do tópico Críticas de música na Folha (scraped)",
        "language": "pt-BR",
        "scraper": scrape_folha_topico,
    },
    {
        "name": "folha-show",
        "source_url": "https://www1.folha.uol.com.br/folha-topicos/show/",
        "output": "folha-show.xml",
        "title": "Folha — tópico Show",
        "description": "Artigos do tópico Show na Folha de S.Paulo (scraped)",
        "language": "pt-BR",
        "scraper": scrape_folha_topico,
    },
    {
        "name": "guia-restaurantes",
        "source_url": "https://guia.folha.uol.com.br/restaurantes/",
        "output": "guia-restaurantes.xml",
        "title": "Guia Folha — Restaurantes",
        "description": "Restaurantes no Guia Folha (scraped)",
        "language": "pt-BR",
        "scraper": lambda html, base: scrape_guia(html, "restaurantes", base),
    },
    {
        "name": "guia-shows",
        "source_url": "https://guia.folha.uol.com.br/shows/",
        "output": "guia-shows.xml",
        "title": "Guia Folha — Shows",
        "description": "Shows no Guia Folha (scraped)",
        "language": "pt-BR",
        "scraper": lambda html, base: scrape_guia(html, "shows", base),
    },
    {
        "name": "estadao-sergio-martins",
        "source_url": "https://www.estadao.com.br/cultura/sergio-martins/",
        "output": "estadao-sergio-martins.xml",
        "title": "Estadão — Sérgio Martins",
        "description": "Coluna de Sérgio Martins no Estadão (scraped)",
        "language": "pt-BR",
        "scraper": scrape_estadao_sergio,
    },
    {
        "name": "vejasp-tudo-de-som",
        "source_url": "https://vejasp.abril.com.br/coluna/tudo-de-som/",
        "output": "vejasp-tudo-de-som.xml",
        "title": "Veja SP — Tudo de Som",
        "description": "Coluna Tudo de Som na Veja São Paulo (scraped)",
        "language": "pt-BR",
        "scraper": scrape_vejasp_tudo_de_som,
    },
    {
        "name": "correio-irlam-rocha-lima",
        "source_url": "https://www.correiobraziliense.com.br/autor/irlam-rocha-lima/page/1/",
        "output": "correio-irlam-rocha-lima.xml",
        "title": "Correio Braziliense — Irlam Rocha Lima",
        "description": "Artigos de Irlam Rocha Lima (scraped)",
        "language": "pt-BR",
        "scraper": scrape_correio_irlam,
    },
    {
        "name": "billboard-br-sergio-martins",
        "source_url": "https://billboard.com.br/author/sergio-martins/",
        "output": "billboard-br-sergio-martins.xml",
        "title": "Billboard Brasil — Sérgio Martins",
        "description": "Artigos de Sérgio Martins na Billboard Brasil (scraped via WP API/HTML)",
        "language": "pt-BR",
        "scraper": scrape_billboard_sergio,
    },
    {
        "name": "asil-insights",
        "source_url": "https://asil.org/insights/",
        "output": "asil-insights.xml",
        "title": "ASIL Insights",
        "description": "American Society of International Law Insights (scraped)",
        "language": "en",
        "scraper": scrape_asil_insights,
    },
    {
        "name": "xai-news",
        "source_url": "https://x.ai/news",
        "output": "xai-news.xml",
        "title": "xAI News",
        "description": "xAI / SpaceXAI news (scraped)",
        "language": "en",
        "scraper": scrape_xai_news,
    },
    {
        "name": "claude-blog",
        "source_url": "https://claude.com/blog",
        "output": "claude-blog.xml",
        "title": "Claude Blog",
        "description": "Claude / Anthropic blog posts (scraped)",
        "language": "en",
        "scraper": scrape_claude_blog,
    },
{
        "name": "espaco-unimed-agenda",
        "source_url": "https://www.espacounimed.com.br/agenda-de-shows/",
        "output": "espaco-unimed-agenda.xml",
        "title": "Espaço Unimed — Agenda de shows",
        "description": "Cada show da agenda do Espaço Unimed (São Paulo). Shows novos entram como itens novos.",
        "language": "pt-BR",
        "scraper": scrape_espaco_unimed,
    },
]


def run_one(target: Dict[str, Any]) -> Dict[str, Any]:
    name = target["name"]
    source = target["source_url"]
    out_name = target["output"]
    out_path = os.path.join(OUT, out_name)
    report: Dict[str, Any] = {
        "name": name,
        "source_url": source,
        "output": f"out/{out_name}",
        "items": 0,
        "ok": False,
        "notes": "",
    }
    html, err = fetch(source)
    if err or not html:
        report["notes"] = f"fetch failed: {err or 'empty body'}"
        return report
    if len(html) < 500:
        report["notes"] = f"page too small ({len(html)} bytes); possible bot wall"
        return report
    # soft bot-wall detection with no articles later
    try:
        items = target["scraper"](html, source)
    except Exception as e:
        report["notes"] = f"scraper error: {type(e).__name__}: {e}"
        return report
    items = [it for it in items if it.get("title") and it.get("link")]
    if not items:
        wall = False
        low = html.lower()
        for w in ("captcha", "cf-challenge", "just a moment", "access denied", "enable javascript"):
            if w in low:
                wall = True
                break
        report["notes"] = (
            "no article items found"
            + (" (possible bot wall / JS-only page)" if wall else " (empty or unparseable HTML)")
        )
        return report
    write_rss(
        out_path,
        target["title"],
        source,
        target["description"],
        items,
        target.get("language", "pt-BR"),
    )
    report["items"] = len(items)
    report["ok"] = True
    report["notes"] = f"scraped {len(items)} items"
    report["_items"] = items  # internal for combines
    return report


def merge_feeds(
    name: str,
    out_name: str,
    title: str,
    link: str,
    description: str,
    parts: List[Dict[str, Any]],
    language: str = "pt-BR",
) -> Dict[str, Any]:
    report = {
        "name": name,
        "source_url": link,
        "output": f"out/{out_name}",
        "items": 0,
        "ok": False,
        "notes": "",
    }
    ok_parts = [p for p in parts if p.get("ok") and p.get("_items")]
    if not ok_parts:
        report["notes"] = "no successful part feeds to merge"
        return report
    merged: List[Dict[str, Any]] = []
    for p in ok_parts:
        merged.extend(p["_items"])
    merged = sort_items(dedupe_items(merged))
    write_rss(os.path.join(OUT, out_name), title, link, description, merged, language)
    report["items"] = len(merged)
    report["ok"] = True
    report["notes"] = (
        f"merged {len(ok_parts)} feeds -> {len(merged)} unique items "
        f"(from {[p['name'] for p in ok_parts]})"
    )
    return report


def write_index_md(native: List[Dict], reports: List[Dict]) -> None:
    lines = [
        "# RSS feeds index",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Native feeds (not scraped)",
        "",
    ]
    for n in native:
        lines.append(f"- **{n['name']}**: {n['url']} — {n.get('notes','')}")
    lines += ["", "## Scraped feeds", ""]
    for r in reports:
        if r["name"].startswith("combined-") or "musica-topicos" in r["name"] or "restaurantes-shows" in r["name"]:
            continue
        status = "OK" if r["ok"] else "FAIL"
        lines.append(
            f"- **{r['name']}** [{status}] items={r['items']} → `{r['output']}`  "
            f"source: {r['source_url']}  \n  notes: {r['notes']}"
        )
    lines += ["", "## Combined feeds", ""]
    for r in reports:
        if r["name"] in ("folha-musica-topicos", "guia-folha-restaurantes-shows"):
            status = "OK" if r["ok"] else "FAIL"
            lines.append(
                f"- **{r['name']}** [{status}] items={r['items']} → `{r['output']}`  \n  notes: {r['notes']}"
            )
    lines.append("")
    with open(os.path.join(ROOT, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    # Save native feeds catalog
    with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "native_feeds": NATIVE_FEEDS,
                "scraped_feeds": [
                    {
                        "name": t["name"],
                        "source_url": t["source_url"],
                        "output": f"out/{t['output']}",
                    }
                    for t in SCRAPE_TARGETS
                ],
                "combined_feeds": [
                    {
                        "name": "folha-musica-topicos",
                        "parts": ["folha-jazz", "folha-criticas-de-musica", "folha-show"],
                        "output": "out/folha-musica-topicos.xml",
                    },
                    {
                        "name": "guia-folha-restaurantes-shows",
                        "parts": ["guia-restaurantes", "guia-shows"],
                        "output": "out/guia-folha-restaurantes-shows.xml",
                    },
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    reports: List[Dict[str, Any]] = []
    by_name: Dict[str, Dict[str, Any]] = {}
    print("Building scraped feeds...")
    for t in SCRAPE_TARGETS:
        print(f"  - {t['name']} ...", flush=True)
        r = run_one(t)
        by_name[t["name"]] = r
        print(f"      {'OK' if r['ok'] else 'FAIL'} items={r['items']} {r['notes']}")
        time.sleep(0.4)

    # Combined
    print("Building combined feeds...")
    r_folha = merge_feeds(
        "folha-musica-topicos",
        "folha-musica-topicos.xml",
        "Folha — Jazz + Críticas de música + Show",
        "https://www1.folha.uol.com.br/folha-topicos/",
        "Combined Folha topic scrapes (jazz, críticas de música, show); deduped by link",
        [
            by_name["folha-jazz"],
            by_name["folha-criticas-de-musica"],
            by_name["folha-show"],
        ],
    )
    print(f"  - folha-musica-topicos: {'OK' if r_folha['ok'] else 'FAIL'} items={r_folha['items']}")

    r_guia = merge_feeds(
        "guia-folha-restaurantes-shows",
        "guia-folha-restaurantes-shows.xml",
        "Guia Folha — Restaurantes + Shows",
        "https://guia.folha.uol.com.br/",
        "Combined Guia Folha scrapes (restaurantes, shows); deduped by link",
        [by_name["guia-restaurantes"], by_name["guia-shows"]],
    )
    print(f"  - guia-folha-restaurantes-shows: {'OK' if r_guia['ok'] else 'FAIL'} items={r_guia['items']}")

    # Public reports without internal _items
    all_reports = []
    for t in SCRAPE_TARGETS:
        r = dict(by_name[t["name"]])
        r.pop("_items", None)
        all_reports.append(r)
    for r in (r_folha, r_guia):
        rr = dict(r)
        rr.pop("_items", None)
        all_reports.append(rr)

    report_path = os.path.join(ROOT, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)

    write_index_md(NATIVE_FEEDS, all_reports)

    # Summary
    print("\n===== REPORT SUMMARY =====")
    ok_n = sum(1 for r in all_reports if r["ok"])
    print(f"Feeds OK: {ok_n}/{len(all_reports)}")
    for r in all_reports:
        flag = "OK  " if r["ok"] else "FAIL"
        print(f"  [{flag}] {r['name']}: items={r['items']} — {r['notes']}")
    print(f"Wrote {report_path}")
    print(f"Wrote {os.path.join(ROOT, 'index.md')}")
    print(f"Wrote {os.path.join(ROOT, 'index.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

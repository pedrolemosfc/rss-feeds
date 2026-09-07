"""Venue/show RSS helpers: native mirrors + scrapers."""

from __future__ import annotations

import gzip
import html as html_lib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

# Imported from build_all at runtime to avoid circular imports at load;
# fall back to local copies of shared helpers when imported standalone.

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PT_MONTHS = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "março": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}


def _bind_helpers(mod: Any) -> None:
    """Bind shared helpers from build_all module into this module's globals."""
    global fetch, strip_tags, abs_url, parse_date, rfc822, dedupe_items, sort_items, write_rss, item, OUT
    fetch = mod.fetch
    strip_tags = mod.strip_tags
    abs_url = mod.abs_url
    parse_date = mod.parse_date
    rfc822 = mod.rfc822
    dedupe_items = mod.dedupe_items
    sort_items = mod.sort_items
    write_rss = mod.write_rss
    item = mod.item
    OUT = mod.OUT


def fetch_raw(url: str, timeout: int = 40, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None, method: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    h = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset, errors="replace"), None
            except LookupError:
                return raw.decode("utf-8", errors="replace"), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def slug_title(slug: str) -> str:
    s = urllib.parse.unquote(slug).replace("-", " ").strip()
    return re.sub(r"\s+", " ", s).strip().title() if s else slug


def parse_pt_day_month(day: str, month: str, year: Optional[int] = None) -> Optional[datetime]:
    try:
        d = int(re.sub(r"\D", "", day) or "0")
        mo = PT_MONTHS.get(month.lower()[:3]) or PT_MONTHS.get(month.lower())
        if not d or not mo:
            return None
        y = year or datetime.now(timezone.utc).year
        dt = datetime(y, mo, d, 12, 0, tzinfo=timezone.utc)
        # if more than ~60 days in the past, assume next year
        now = datetime.now(timezone.utc)
        if (now - dt).days > 60:
            dt = datetime(y + 1, mo, d, 12, 0, tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def parse_br_date(text: str) -> Optional[datetime]:
    """Parse DD/MM/YYYY or DD/MM or 'Ter 08/09 21h30' etc."""
    if not text:
        return None
    text = html_lib.unescape(strip_tags(text))
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), 12, 0, tzinfo=timezone.utc)
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2})h(\d{2}))?", text)
    if m:
        year = datetime.now(timezone.utc).year
        try:
            hh = int(m.group(3) or 12)
            mm = int(m.group(4) or 0)
            dt = datetime(year, int(m.group(2)), int(m.group(1)), hh, mm, tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - dt).days > 60:
                dt = datetime(year + 1, int(m.group(2)), int(m.group(1)), hh, mm, tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    m = re.search(
        r"(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\s+(\d{4})",
        text,
        re.I,
    )
    if m:
        return parse_pt_day_month(m.group(1), m.group(2), int(m.group(3)))
    m = re.search(
        r"(\d{1,2})\s+(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(\d{4})",
        text,
        re.I,
    )
    if m:
        return parse_pt_day_month(m.group(1), m.group(2), int(m.group(3)))
    return parse_date(text)


# ---------------- native mirror ----------------


def count_rss_items(xml: str) -> int:
    return len(re.findall(r"<item[\s>]", xml, re.I))


def rewrite_native_rss(
    xml: str,
    title: str,
    link: str,
    description: str,
) -> str:
    """Rewrite channel metadata; keep items as-is when possible."""
    # Replace first channel title/link/description
    def repl_tag(doc: str, tag: str, value: str) -> str:
        pat = rf"(<channel[^>]*>[\s\S]*?<{tag}>)([\s\S]*?)(</{tag}>)"

        def _sub(m: re.Match) -> str:
            return m.group(1) + escape(value) + m.group(3)

        new, n = re.subn(pat, _sub, doc, count=1, flags=re.I)
        return new if n else doc

    out = xml.strip()
    if not out.startswith("<?xml"):
        out = '<?xml version="1.0" encoding="UTF-8"?>\n' + out
    out = repl_tag(out, "title", title)
    out = repl_tag(out, "link", link)
    out = repl_tag(out, "description", description)
    # bump lastBuildDate
    now = rfc822(datetime.now(timezone.utc)) or ""
    if re.search(r"<lastBuildDate>", out, re.I):
        out = re.sub(
            r"<lastBuildDate>[\s\S]*?</lastBuildDate>",
            f"<lastBuildDate>{now}</lastBuildDate>",
            out,
            count=1,
            flags=re.I,
        )
    else:
        out = re.sub(
            r"(<channel[^>]*>)",
            rf"\1\n<lastBuildDate>{now}</lastBuildDate>",
            out,
            count=1,
            flags=re.I,
        )
    if not out.endswith("\n"):
        out += "\n"
    return out


def mirror_native_rss(
    source_url: str,
    out_name: str,
    title: str,
    link: str,
    description: str,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "name": out_name.replace(".xml", ""),
        "source_url": source_url,
        "output": f"feeds/{out_name}",
        "items": 0,
        "ok": False,
        "notes": "",
        "kind": "native-mirror",
    }
    body, err = fetch_raw(source_url)
    if err or not body:
        report["notes"] = f"fetch failed: {err or 'empty'}"
        return report
    n = count_rss_items(body)
    if n < 1:
        report["notes"] = "native feed has 0 items"
        return report
    # basic sanity: looks like RSS/Atom
    low = body.lower()
    if "<rss" not in low and "<feed" not in low and "<item" not in low:
        report["notes"] = "response is not RSS/XML"
        return report
    rewritten = rewrite_native_rss(body, title, link, description)
    path = os.path.join(OUT, out_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(rewritten)
    report["items"] = n
    report["ok"] = True
    report["notes"] = f"mirrored {n} native items"
    return report


# ---------------- Opus APIs ----------------


def scrape_opus_events(api_base: str, venue_name: str, skip_categories: Optional[set] = None) -> List[Dict[str, Any]]:
    skip_categories = skip_categories or set()
    items: List[Dict[str, Any]] = []
    url = api_base if "?" in api_base else api_base + ("?page=1" if not api_base.endswith("/") else "?page=1")
    if "page=" not in url:
        url = api_base.rstrip("/") + "?page=1"
    seen_pages = set()
    while url and url not in seen_pages:
        seen_pages.add(url)
        body, err = fetch_raw(url)
        if err or not body:
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        page = (data.get("events") or {}) if isinstance(data, dict) else {}
        rows = page.get("data") if isinstance(page, dict) else None
        if not isinstance(rows, list):
            break
        for ev in rows:
            cat = (ev.get("category") or "").strip()
            if cat in skip_categories:
                continue
            title = (ev.get("title") or "").strip()
            link = (ev.get("url") or "").strip()
            if not title or not link:
                continue
            starts = ev.get("starts_at") or ""
            ends = ev.get("ends_at") or ""
            place = ev.get("place_name") or venue_name
            status = ev.get("status") or ""
            desc_bits = [place]
            if starts:
                desc_bits.append(f"início {starts}")
            if ends and ends != starts:
                desc_bits.append(f"até {ends}")
            if cat:
                desc_bits.append(cat)
            if status:
                desc_bits.append(status)
            it = item(title, link, " · ".join(desc_bits), starts)
            dt = parse_br_date(starts)
            if dt:
                it["_dt"] = dt
                it["pubDate"] = rfc822(dt)
            items.append(it)
        nxt = page.get("next_page_url") if isinstance(page, dict) else None
        url = nxt if nxt else None
        time.sleep(0.25)
    return sort_items(dedupe_items(items))


def scrape_teatro_bradesco(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    return scrape_opus_events(
        "https://sites.opusentretenimento.com/api/tbsp/events",
        "Teatro Bradesco",
    )


def scrape_vibra_sp(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    return scrape_opus_events(
        "https://sites.opusentretenimento.com/api/vibra/events",
        "Vibra São Paulo",
        skip_categories={"Estacionamento"},
    )


# ---------------- HTML / JSON scrapers ----------------


def scrape_theatro_municipal(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    cards = re.split(r"card-evento", html)
    for c in cards[1:]:
        lm = re.search(r'href="(https://theatromunicipal\.org\.br/eventos/[^"]+)"', c)
        if not lm:
            continue
        link = lm.group(1)
        titles = re.findall(r"elementor-heading-title[^>]*>(.*?)</", c, re.S | re.I)
        titles = [strip_tags(t) for t in titles]
        titles = [
            t
            for t in titles
            if t
            and t.lower()
            not in (
                "evento pago",
                "evento gratuito",
                "saiba mais",
                "ingressos",
            )
        ]
        # prefer longer title (show name) over category
        title = titles[-1] if titles else slug_title(link.rstrip("/").split("/")[-1])
        cat = titles[0] if len(titles) > 1 else ""
        desc = "Theatro Municipal de São Paulo"
        if cat:
            desc += f" · {cat}"
        items.append(item(title, link, desc, None))
    if not items:
        for m in re.finditer(
            r'href="(https://theatromunicipal\.org\.br/eventos/([^"/]+)/)"',
            html,
        ):
            link, slug = m.group(1), m.group(2)
            items.append(item(slug_title(slug), link, "Theatro Municipal de São Paulo", None))
    return sort_items(dedupe_items(items))


def scrape_multi_arena(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    skip = {
        "programacao",
        "noticias",
        "contato",
        "home",
        "sobre",
        "ingressos",
        "fotos",
        "videos",
        "feed",
        "wp-json",
        "a-multi-arena-campinas",
        "politica-de-privacidade",
        "faq",
        "o-espaco",
        "o-espaco-2",
    }
    # Prefer heading + nearby event permalink from programacao page
    for m in re.finditer(
        r'<h2[^>]*>\s*(?:<a[^>]+href="([^"]+)"[^>]*>)?\s*(.*?)\s*(?:</a>)?\s*</h2>',
        html,
        re.S | re.I,
    ):
        link = m.group(1) or ""
        title = strip_tags(m.group(2))
        if not title or title.lower() in ("programação", "programacao"):
            continue
        if not link:
            # search forward for show permalink
            window = html[m.end() : m.end() + 800]
            lm = re.search(r'href="(https://multiarenacampinas\.com\.br/([a-z0-9\-]+)/)"', window, re.I)
            if lm and lm.group(2).lower() not in skip:
                link = lm.group(1)
        if not link:
            continue
        slug = link.rstrip("/").split("/")[-1].lower()
        if slug in skip:
            continue
        link = abs_url(base, link)
        items.append(item(title, link, "Multi Arena Campinas", None))
    if not items:
        for m in re.finditer(
            r'href="(https://multiarenacampinas\.com\.br/([a-z0-9\-]+)/)"',
            html,
            re.I,
        ):
            link, slug = m.group(1), m.group(2).lower()
            if slug in skip or slug.startswith("page"):
                continue
            items.append(item(slug_title(slug), link, "Multi Arena Campinas", None))
    return sort_items(dedupe_items(items))


def scrape_suhai(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'<a class="[^"]*item-evento[^"]*"[^>]*href="(https://suhaimusichall\.com\.br/evento/[^"]+/)"[^>]*>(.*?)</a>',
        html,
        re.S | re.I,
    ):
        link, inner = m.group(1), m.group(2)
        texts = [strip_tags(t) for t in re.findall(r">([^<>]{1,80})<", inner)]
        texts = [t.strip() for t in texts if t and t.strip()]
        # weekday, day, month, title...
        weekdays = {"seg", "ter", "qua", "qui", "sex", "sáb", "sab", "dom"}
        day = month = None
        title = None
        for i, t in enumerate(texts):
            low = t.lower()
            if low in weekdays or low.replace("á", "a") in weekdays:
                if i + 2 < len(texts) and texts[i + 1].isdigit() and texts[i + 2].lower()[:3] in PT_MONTHS:
                    day, month = texts[i + 1], texts[i + 2]
            if low not in weekdays and not t.isdigit() and low[:3] not in PT_MONTHS and "ingresso" not in low and "venda" not in low and "desconto" not in low:
                if len(t) >= 3 and not title:
                    title = t
        if not title:
            title = slug_title(link.rstrip("/").split("/")[-1])
        dt = parse_pt_day_month(day, month) if day and month else None
        desc = "Suhai Music Hall"
        if day and month:
            desc += f" · {day} {month}"
        it = item(title, link, desc, None)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_blue_note(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # Prefer WP REST custom post type endpoint that worked in probe
    for api in (
        "https://bluenotesp.com/wp-json/wp/v2/shows?per_page=50",
        "https://bluenotesp.com/wp-json/wp/v2/eventos_bn?per_page=50",
    ):
        body, err = fetch_raw(api)
        if err or not body:
            continue
        try:
            posts = json.loads(body)
        except json.JSONDecodeError:
            continue
        if not isinstance(posts, list) or not posts:
            continue
        for p in posts:
            title = strip_tags((p.get("title") or {}).get("rendered") or "")
            link = p.get("link") or ""
            if not title or not link:
                continue
            dt_raw = p.get("date") or p.get("modified")
            desc = "Blue Note SP"
            items.append(item(title, link, desc, dt_raw))
        break
    if not items and _html:
        for m in re.finditer(
            r'<a href="(https://bluenotesp\.com/shows/([^"/]+)/)"[^>]*aria-label="([^"]+)"',
            _html,
            re.I,
        ):
            link, slug, title = m.group(1), m.group(2), html_lib.unescape(m.group(3))
            items.append(item(title or slug_title(slug), link, "Blue Note SP", None))
    return sort_items(dedupe_items(items))


def scrape_bileto_sympla_iframe(lp_url: str, venue_name: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    body, err = fetch_raw(lp_url)
    if err or not body:
        return items
    iframes = re.findall(
        r'(https://www\.sympla\.com\.br/agenda-eventos/[^"\'\s]+)',
        body,
    )
    if not iframes:
        return items
    iframe_url = html_lib.unescape(iframes[0])
    page, err2 = fetch_raw(iframe_url)
    if err2 or not page:
        return items
    # Parse sympla-cards: event-name + bileto link
    # Split by sympla-card or by bileto event links
    for m in re.finditer(
        r'(?:event-name[^>]*>(.*?)</[\w:]+>[\s\S]{0,400}?)?(https://bileto\.sympla\.com\.br/event/\d+)',
        page,
        re.I,
    ):
        title = strip_tags(m.group(1) or "")
        link = m.group(2)
        if not title:
            # look backwards
            chunk = page[max(0, m.start() - 500) : m.start()]
            nm = re.search(r"event-name[^>]*>(.*?)</", chunk, re.S | re.I)
            title = strip_tags(nm.group(1)) if nm else f"Evento {link.rstrip('/').split('/')[-1]}"
        items.append(item(title, link, venue_name, None))
    # Also try structured cards
    if not items:
        for m in re.finditer(
            r'href="(https://bileto\.sympla\.com\.br/event/\d+)"[^>]*>[\s\S]{0,300}?event-name[^>]*>(.*?)</',
            page,
            re.I,
        ):
            items.append(item(strip_tags(m.group(2)), m.group(1), venue_name, None))
    return sort_items(dedupe_items(items))


def scrape_arena_b3(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    return scrape_bileto_sympla_iframe(
        "https://site.bileto.sympla.com.br/arenab3/",
        "Arena B3",
    )


def scrape_bourbon_street(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    return scrape_bileto_sympla_iframe(
        "https://site.bileto.sympla.com.br/bourbonstreet/",
        "Bourbon Street",
    )


def scrape_jsonld_music_events(html: str, venue_name: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            types = node.get("@type")
            type_l = types if isinstance(types, list) else [types]
            if not any(t in ("MusicEvent", "Event", "TheaterEvent") for t in type_l if t):
                continue
            title = node.get("name") or ""
            link = node.get("url") or ""
            if isinstance(link, list):
                link = link[0] if link else ""
            if link:
                link = link.split("?")[0]
            start = node.get("startDate") or node.get("doorTime") or ""
            if not title or not link:
                continue
            items.append(item(title, link, venue_name, start))
    return sort_items(dedupe_items(items))


def scrape_fabrique(html: str, base: str) -> List[Dict[str, Any]]:
    return scrape_jsonld_music_events(html, "Fabrique Club")


def scrape_songkick_pacaembu(html: str, base: str) -> List[Dict[str, Any]]:
    return scrape_jsonld_music_events(html, "Mercado Livre Arena Pacaembu")


def scrape_live_nation_morumbis(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'href="(/event/(?!allevents)[^"]+-tickets-edp\d+)"[\s\S]{0,1200}?<time[^>]*dateTime="([^"]+)"[\s\S]{0,600}?data-testid="aedp-event-information-block-venuedetails"[^>]*>(.*?)</',
        html,
        re.I,
    ):
        path, dt_raw, title = m.group(1), m.group(2), strip_tags(m.group(3))
        link = abs_url("https://www.livenation.com.br", path)
        items.append(item(title, link, "Estádio Morumbis (Live Nation)", dt_raw))
    if not items:
        # looser: path + h4 title nearby
        seen = set()
        for m in re.finditer(
            r'href="(/event/(?!allevents)[^"]+-tickets-edp\d+)"',
            html,
        ):
            path = m.group(1)
            if path in seen:
                continue
            seen.add(path)
            chunk = html[m.start() : m.start() + 1500]
            tm = re.search(
                r'data-testid="aedp-event-information-block-venuedetails"[^>]*>(.*?)</',
                chunk,
                re.S | re.I,
            )
            dtm = re.search(r'dateTime="([^"]+)"', chunk)
            title = strip_tags(tm.group(1)) if tm else slug_title(path.split("/")[-1].split("-tickets-edp")[0])
            link = abs_url("https://www.livenation.com.br", path)
            items.append(item(title, link, "Estádio Morumbis (Live Nation)", dtm.group(1) if dtm else None))
    return sort_items(dedupe_items(items))


def scrape_carioca_club(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'ItemCarrousel__content">([\s\S]*?)</div>\s*</div>',
        html,
    ):
        block = m.group(1)
        lm = re.search(r'href="(/evento/[^"]+)"', block)
        if not lm:
            continue
        link = abs_url("https://www.clubedoingresso.com", lm.group(1))
        alt = re.search(r'alt="([^"]+)"', block)
        nome = re.search(r'ItemCarrousel__nome[^>]*>([^<]+)', block)
        title = html_lib.unescape((nome.group(1) if nome else None) or (alt.group(1) if alt else "") or "")
        title = strip_tags(title)
        if not title:
            title = slug_title(lm.group(1).rstrip("/").split("/")[-1])
        dm = re.search(r'(\d{2}/\d{2}/\d{4})', block)
        date_raw = dm.group(1) if dm else None
        it = item(title, link, "Carioca Club", date_raw)
        dt = parse_br_date(date_raw or "")
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    if not items:
        seen = set()
        for m in re.finditer(
            r'href="(/evento/[^"]+)"[\s\S]{0,400}?alt="([^"]+)"',
            html,
        ):
            path, title = m.group(1), html_lib.unescape(m.group(2))
            if path in seen:
                continue
            seen.add(path)
            items.append(item(title, abs_url("https://www.clubedoingresso.com", path), "Carioca Club", None))
    return sort_items(dedupe_items(items))


def scrape_juventus(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'href="((?:https://www\.juventus\.com\.br)?/\?event=([^"&]+))"',
        html,
    ):
        link = abs_url("https://www.juventus.com.br", m.group(1))
        slug = urllib.parse.unquote(m.group(2))
        # find title near
        idx = html.find(m.group(0))
        chunk = html[max(0, idx - 300) : idx + 500]
        tm = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", chunk, re.S | re.I)
        title = strip_tags(tm.group(1)) if tm else slug_title(slug)
        items.append(item(title, link, "Clube Atlético Juventus", None))
    return sort_items(dedupe_items(items))


def scrape_komplexo(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # Pair headings with nearby shotgun links
    for m in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", html, re.S | re.I):
        title = strip_tags(m.group(1))
        if not title or len(title) < 3:
            continue
        window = html[m.end() : m.end() + 1200]
        sm = re.search(r'(https://shotgun\.live/[^"\'\s]+)', window)
        if sm:
            link = sm.group(1).split("?")[0]
        else:
            # guid from title slug on agenda page
            link = base.rstrip("/") + "#" + re.sub(r"[^a-z0-9]+", "-", title.lower())[:60]
        items.append(item(title, link, "Komplexo Tempo", None))
    # Also capture shotgun links without heading
    if not items:
        for m in re.finditer(r'(https://shotgun\.live/[^"\'\s]+)', html):
            link = m.group(1).split("?")[0]
            slug = link.rstrip("/").split("/")[-1]
            items.append(item(slug_title(slug), link, "Komplexo Tempo", None))
    return sort_items(dedupe_items(items))


def scrape_btg_hall(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # Walk bileto links; take nearest preceding meaningful heading
    for m in re.finditer(r"(https://bileto\.sympla\.com\.br/event/\d+)", html):
        link = m.group(1)
        chunk = html[max(0, m.start() - 1000) : m.start()]
        heads = re.findall(r"<h[2-4][^>]*>(.*?)</h[2-4]>", chunk, re.S | re.I)
        heads = [strip_tags(h) for h in heads]
        skip = {"programação", "programacao", "festival de teatro de são paulo", "festival de teatro de sao paulo"}
        heads = [h for h in heads if h and h.lower() not in skip and not h.lower().startswith("até")]
        title = heads[-1] if heads else f"Evento {link.split('/')[-1]}"
        # date hint
        dm = re.search(r"(Até\s+\d{1,2}\s+de\s+\w+|\d{1,2}\s+de\s+\w+(?:\s+a\s+\d{1,2})?)", chunk, re.I)
        date_hint = dm.group(1) if dm else None
        items.append(item(title, link, "BTG Pactual Hall" + (f" · {date_hint}" if date_hint else ""), None))
    return sort_items(dedupe_items(items))


def scrape_sala_sao_paulo(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'href="((?:https://salasaopaulo\.art\.br)?/salasp/pt/concerto/(\d+)\?date=([^"&]+))"',
        html,
    ):
        path, cid, date_iso = m.group(1), m.group(2), urllib.parse.unquote(m.group(3))
        link = abs_url("https://salasaopaulo.art.br", path)
        # title from nearby text
        idx = m.start()
        chunk = html[max(0, idx - 400) : idx + 400]
        tm = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", chunk, re.S | re.I)
        title = strip_tags(tm.group(1)) if tm else f"Concerto {cid}"
        if not title or title.lower() in ("ingressos", "programação"):
            title = f"Concerto {cid}"
        items.append(item(title, link, "Sala São Paulo", date_iso))
    return sort_items(dedupe_items(items))


def scrape_audio_sp(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # POST AJAX endpoint
    data = urllib.parse.urlencode({"action": "fetch_data"}).encode()
    body, err = fetch_raw(
        "https://audiosp.com.br/programacao_load.php",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://audiosp.com.br/programacao",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    if err or not body:
        return items
    for m in re.finditer(
        r'<a href="(\d+-[^"]+)">\s*([\s\S]*?)</a>',
        body,
        re.I,
    ):
        path, inner = m.group(1), m.group(2)
        link = abs_url("https://audiosp.com.br/", path)
        hm = re.search(r"<h2>(.*?)</h2>", inner, re.S | re.I)
        raw_title = strip_tags(hm.group(1)) if hm else slug_title(path.split("-", 1)[-1])
        # h2 often embeds date: "Haikaiss 11 Setembro 2026"
        dm = re.search(
            r"(\d{1,2}\s+(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\s+\d{4})",
            raw_title,
            re.I,
        )
        date_raw = dm.group(1) if dm else None
        title = re.sub(
            r"\s*\d{1,2}\s+(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\s+\d{4}.*$",
            "",
            raw_title,
            flags=re.I,
        ).strip()
        title = re.sub(r"(Segunda|Terça|Terca|Quarta|Quinta|Sexta|Sábado|Sabado|Domingo)\s*$", "", title, flags=re.I).strip()
        if not title:
            title = raw_title
        it = item(title, link, "Audio SP" + (f" · {date_raw}" if date_raw else ""), date_raw)
        dt = parse_br_date(date_raw or "")
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_teatro_das_artes(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    skip = {"em cartaz", "teatro das artes", "programação", "programacao", "ingressos"}
    for m in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", html, re.S | re.I):
        title = strip_tags(m.group(1))
        if not title or title.lower() in skip:
            continue
        window = html[m.end() : m.end() + 800]
        lm = re.search(r'href="(https?://[^"]+)"', window)
        link = lm.group(1) if lm else f"https://teatrodasartessp.com.br/programacao/#{urllib.parse.quote(title)}"
        items.append(item(title, link, "Teatro das Artes SP", None))
    return sort_items(dedupe_items(items))


def scrape_casa_francisca(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    parts = re.split(r"<h2>", html, flags=re.I)
    for p in parts[1:]:
        tm = re.match(r"(.*?)</h2>", p, re.S | re.I)
        if not tm:
            continue
        title = strip_tags(tm.group(1))
        if not title or len(title) < 3:
            continue
        # dates in following block before next major section
        block = p[:2000]
        dates = re.findall(r'vermelho[^>]*>([^<]+)', block)
        date_raw = dates[0] if dates else None
        # stable-ish guid: programação + title slug + first date
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:80].strip("-")
        dslug = re.sub(r"[^0-9a-z]+", "-", (date_raw or "").lower())[:40]
        link = f"https://casadefrancisca.art.br/novo/programacao#{slug}-{dslug}"
        it = item(title, link, "Casa de Francisca" + (f" · {date_raw}" if date_raw else ""), date_raw)
        dt = parse_br_date(date_raw or "")
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_jazz_b(html: str, base: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'(https://www\.sympla\.com\.br/evento/([^/?"\']+)/(\d+))',
        html,
    ):
        link = m.group(1).split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        slug = m.group(2)
        title = slug_title(re.sub(r"-?(segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo)?-?\d{1,2}-?\d{1,2}-?\d{2,4}$", "", slug, flags=re.I))
        # date from slug like sexta-27-set-2026 or quinta-10-09-26
        dm = re.search(
            r"(\d{1,2})-(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)-(\d{2,4})",
            slug,
            re.I,
        )
        date_raw = None
        if dm:
            year = int(dm.group(3))
            if year < 100:
                year += 2000
            date_raw = f"{dm.group(1)} {dm.group(2)} {year}"
        else:
            dm2 = re.search(r"(\d{1,2})-(\d{1,2})-(\d{2,4})", slug)
            if dm2:
                year = int(dm2.group(3))
                if year < 100:
                    year += 2000
                date_raw = f"{dm2.group(1)}/{dm2.group(2)}/{year}"
        items.append(item(title or slug_title(slug), link, "Jazz B", date_raw))
    return sort_items(dedupe_items(items))


# ---------------- catalogs ----------------

VENUE_NATIVE_MIRRORS = [
    {
        "source_url": "https://nubankparque.com/category/agenda/shows/feed/",
        "out_name": "nubank-parque-shows.xml",
        "title": "Nubank Parque — Shows",
        "link": "https://nubankparque.com/category/agenda/shows/",
        "description": "Espelho do RSS nativo de shows do Nubank Parque (jsDelivr/Readwise)",
    },
    {
        "source_url": "https://terrasp.com/feed/",
        "out_name": "terra-sp.xml",
        "title": "Terra SP",
        "link": "https://terrasp.com/",
        "description": "Espelho do RSS nativo do Terra SP",
    },
    {
        "source_url": "https://mis-sp.org.br/eventos/feed/",
        "out_name": "mis-sp.xml",
        "title": "MIS-SP — Eventos",
        "link": "https://mis-sp.org.br/eventos/",
        "description": "Espelho do RSS nativo de eventos do MIS-SP",
    },
    {
        "source_url": "https://teatrob32.com.br/feed/",
        "out_name": "teatro-b32.xml",
        "title": "Teatro B32",
        "link": "https://teatrob32.com.br/",
        "description": "Espelho do RSS nativo do Teatro B32",
    },
    {
        "source_url": "https://www.tokiomarinehall.com.br/feed/",
        "out_name": "tokio-marine-hall.xml",
        "title": "Tokio Marine Hall",
        "link": "https://www.tokiomarinehall.com.br/",
        "description": "Espelho do RSS nativo do Tokio Marine Hall",
    },
    {
        "source_url": "https://casanaturamusical.com.br/eventos/feed/",
        "out_name": "casa-natura-musical.xml",
        "title": "Casa Natura Musical — Eventos",
        "link": "https://casanaturamusical.com.br/eventos/",
        "description": "Espelho do RSS nativo de eventos da Casa Natura Musical",
    },
    {
        "source_url": "https://guarulhoscultural.com.br/feed/",
        "out_name": "guarulhos-cultural.xml",
        "title": "Guarulhos Cultural",
        "link": "https://guarulhoscultural.com.br/",
        "description": "Espelho do RSS nativo do Guarulhos Cultural",
    },
    {
        "source_url": "https://concerto.com.br/rss.xml",
        "out_name": "concerto.xml",
        "title": "Concerto (revista) — RSS",
        "link": "https://concerto.com.br/",
        "description": "Espelho do RSS da revista Concerto (não é calendário de casa de shows)",
    },
]



def scrape_cavern_club(html: str, base: str) -> List[Dict[str, Any]]:
    """Agenda cards on thecavernclubsp.com.br/agenda/ (Elementor articles)."""
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(r"<article[^>]*>([\s\S]*?)</article>", html, re.I):
        block = m.group(1)
        lm = re.search(r'href="(https?://thecavernclubsp\.com\.br/[^"]+/)"', block)
        if not lm:
            lm = re.search(r'href="(https?://thecavernclubsp\.com\.br/[^"]+)"', block)
        if not lm:
            continue
        link = lm.group(1).split("?")[0]
        if link.rstrip("/") in (
            "https://thecavernclubsp.com.br",
            "https://thecavernclubsp.com.br/agenda",
            "https://thecavernclubsp.com.br/eventos",
        ):
            continue
        if link in seen:
            continue
        seen.add(link)
        title = strip_tags(block)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 2:
            title = slug_title(link.rstrip("/").split("/")[-1])
        # date hints in slug: 11set, 15-set, 26setembro
        slug = link.rstrip("/").split("/")[-1]
        date_raw = None
        dm = re.search(
            r"(\d{1,2})-?(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*-?(\d{2,4})?",
            slug,
            re.I,
        )
        dt = None
        if dm:
            year = None
            if dm.group(3):
                y = int(dm.group(3))
                year = y if y > 99 else 2000 + y
            dt = parse_pt_day_month(dm.group(1), dm.group(2), year)
            date_raw = dm.group(0)
        it = item(title, link, "The Cavern Club SP", date_raw)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_manifesto_bar(html: str, base: str) -> List[Dict[str, Any]]:
    """Programação Manifesto: posters linking to Clube do Ingresso."""
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'<a[^>]+href="(https://www\.clubedoingresso\.com/evento/[^"]+)"[^>]*>([\s\S]*?)</a>',
        html,
        re.I,
    ):
        link = m.group(1).split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        block = m.group(2)
        img = re.search(r'src="([^"]+)"', block)
        alt = re.search(r'alt="([^"]*)"', block)
        title = html_lib.unescape(alt.group(1)).strip() if alt and alt.group(1).strip() else ""
        if not title:
            title = slug_title(link.rstrip("/").split("/")[-1])
        date_raw = None
        dt = None
        if img:
            # filenames like 11-09instagram-... or 02-10instagram
            dm = re.search(r"/(\d{2})-(\d{2})(?:instagram|/)", img.group(1))
            if dm:
                day, month = int(dm.group(1)), int(dm.group(2))
                year = datetime.now(timezone.utc).year
                try:
                    dt = datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    if (now - dt).days > 60:
                        dt = datetime(year + 1, month, day, 12, 0, tzinfo=timezone.utc)
                    date_raw = f"{day:02d}/{month:02d}/{dt.year}"
                except ValueError:
                    dt = None
        it = item(title, link, "Manifesto Bar", date_raw)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_ticketmaster_multiplan(html: str, base: str) -> List[Dict[str, Any]]:
    """Ticketmaster BR venue page for Multiplan Hall SC."""
    items: List[Dict[str, Any]] = []
    seen = set()
    # TM BR uses single-quoted attrs in the event_list cards
    for m in re.finditer(
        r"href=(['\"])((?:\.\./)?event/([^'\"?#]+))\1[^>]*>([\s\S]*?)</a>",
        html,
        re.I,
    ):
        slug, inner = m.group(3), m.group(4)
        link = f"https://www.ticketmaster.com.br/event/{slug}"
        if link in seen:
            continue
        seen.add(link)
        alt = re.search(r"alt=(['\"])(.*?)\1", inner)
        h3 = re.search(r"<h3[^>]*>(.*?)</h3>", inner, re.S | re.I)
        title = ""
        if alt:
            title = html_lib.unescape(alt.group(2)).strip()
        if not title and h3:
            title = strip_tags(h3.group(1))
        if not title:
            title = strip_tags(inner)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 3:
            title = slug_title(slug)
        date_raw = None
        dt = None
        dm = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", title)
        if dm:
            date_raw = dm.group(1)
            dt = parse_br_date(date_raw)
        else:
            dm2 = re.search(
                r"(\d{1,2})\s+e\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
                title,
                re.I,
            )
            if dm2:
                dt = parse_pt_day_month(dm2.group(1), dm2.group(3), int(dm2.group(4)))
                date_raw = dm2.group(0)
            else:
                dm3 = re.search(
                    r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
                    title,
                    re.I,
                )
                if dm3:
                    dt = parse_pt_day_month(dm3.group(1), dm3.group(2), int(dm3.group(3)))
                    date_raw = dm3.group(0)
        it = item(title, link, "Multiplan Hall SC (Ticketmaster)", date_raw)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_rockambole_meaple(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    """Casa Rockambole via Meaple channel API (+ hardcoded Fastix extras in page JS ignored here)."""
    channel_id = "cly3c6lbd0317o0290komzimt"
    url = f"https://api.meaple.com.br/v1/channels/{channel_id}/events?type=FUTURE"
    body, err = fetch_raw(url, headers={"Accept": "application/json"})
    if err or not body:
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    items: List[Dict[str, Any]] = []
    for ev in data.get("events") or []:
        if not isinstance(ev, dict):
            continue
        name = ev.get("name") or ""
        slug = ev.get("slug") or ""
        ch = (ev.get("channel") or {}).get("slug") or "rockambole"
        if not name or not slug:
            continue
        link = f"https://meaple.com.br/{ch}/{slug}"
        starts = ev.get("startsAt") or ev.get("opensAt") or ""
        desc = "Casa Rockambole (Meaple)"
        it = item(name, link, desc, starts)
        dt = parse_date(starts)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    # Also include static Fastix promotions listed on the Meaple page bundle when present
    # (fetch current rockambole page chunk is fragile; leave API as source of truth)
    return sort_items(dedupe_items(items))


def scrape_itau_cultural_agenda(html: str, base: str) -> List[Dict[str, Any]]:
    """Itaú Cultural agenda from Next.js __NEXT_DATA__ (replaces Inti SPA)."""
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    schedules = (
        data.get("props", {})
        .get("pageProps", {})
        .get("schedules")
        or []
    )
    items: List[Dict[str, Any]] = []
    for ev in schedules:
        if not isinstance(ev, dict):
            continue
        title = ev.get("title") or ""
        slug = ev.get("slug") or ""
        if not title or not slug:
            continue
        link = f"https://www.itaucultural.org.br/secoes/agenda/{slug}"
        start = ev.get("startDate") or ev.get("initDate") or ev.get("publishedAt") or ""
        short = ev.get("shortDescription") or ""
        desc = f"Itaú Cultural — {short}".strip(" —")
        it = item(title, link, desc, start)
        dt = parse_date(start)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))




def scrape_cine_joia(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    """Cine Joia via WP REST Modern Events Calendar (bypasses HTML browser wall)."""
    items: List[Dict[str, Any]] = []
    page = 1
    while page <= 1:
        url = (
            "https://www.cinejoia.com.br/wp-json/wp/v2/mec-events"
            f"?per_page=50&page={page}&orderby=date&order=desc"  # recent announcements ≈ upcoming
        )
        body, err = fetch_raw(url, headers={"Accept": "application/json"})
        if err or not body:
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        if not isinstance(data, list) or not data:
            break
        for ev in data:
            if not isinstance(ev, dict):
                continue
            title_obj = ev.get("title") or {}
            title = title_obj.get("rendered") if isinstance(title_obj, dict) else str(title_obj or "")
            title = html_lib.unescape(strip_tags(title or ""))
            link = (ev.get("link") or "").split("?")[0]
            if not title or not link:
                continue
            # Event start dates live in MEC tables, not exposed on public REST;
            # use post date as weak pubDate so Reader still sorts somehow.
            date_raw = ev.get("date") or ev.get("modified") or ""
            items.append(item(title, link, "Cine Joia", date_raw))
        if len(data) < 50:
            break
        page += 1
        time.sleep(0.2)
    return sort_items(dedupe_items(items))


def scrape_porta_shotgun(html: str, base: str) -> List[Dict[str, Any]]:
    """PORTA on Shotgun — only works when HTML is not Vercel 429."""
    if not html or len(html) < 20000:
        return []
    low = html.lower()
    if "security checkpoint" in low or ("just a moment" in low and "/pt-br/events/" not in html):
        return []
    items: List[Dict[str, Any]] = []
    seen = set()
    # SSR cards: href="/pt-br/events/slug" ... alt="Title"
    for m in re.finditer(
        r'href="((?:https://shotgun\.live)?/pt-br/events/([a-z0-9\-]+))"([\s\S]{0,900}?)(?:alt="([^"]+)"|</a>)',
        html,
        re.I,
    ):
        path, slug = m.group(1), m.group(2)
        link = path if path.startswith("http") else f"https://shotgun.live{path}"
        link = link.split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        alt = m.group(4)
        title = html_lib.unescape(alt).strip() if alt else ""
        if not title:
            am = re.search(r'alt="([^"]+)"', m.group(3) or "")
            title = html_lib.unescape(am.group(1)).strip() if am else slug_title(slug)
        if title.lower() in ("shotgun", "blur background", "opens in a new window", "p o r t a"):
            continue
        items.append(item(title, link, "PORTA (Shotgun)", None))
    return sort_items(dedupe_items(items))


def scrape_cultura_artistica(html: str, base: str) -> List[Dict[str, Any]]:
    """Cultura Artística eventos — needs Cloudflare cleared HTML."""
    if not html or "sgcaptcha" in (html or "").lower() or len(html) < 2000:
        return []
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'href="(https://culturaartistica\.org/evento/[^"#?]+|/evento/[^"#?]+)"[^>]*>([\s\S]{0,300}?)</a>',
        html,
        re.I,
    ):
        path = m.group(1)
        link = abs_url("https://culturaartistica.org", path)
        if link in seen:
            continue
        seen.add(link)
        title = strip_tags(m.group(2))
        if not title or len(title) < 2:
            title = slug_title(link.rstrip("/").split("/")[-1])
        items.append(item(title, link, "Cultura Artística", None))
    return sort_items(dedupe_items(items))


def scrape_bona_eventim(html: str, base: str) -> List[Dict[str, Any]]:
    """Bona Casa de Música on Eventim artist page (often blocked)."""
    if not html or "Access Denied" in html or len(html) < 5000:
        return []
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'href="(https://www\.eventim\.com\.br/artist/bona-casa-musica/([^"/?#]+)-\d+/)"',
        html,
        re.I,
    ):
        link = m.group(1)
        if link in seen:
            continue
        seen.add(link)
        title = slug_title(re.sub(r"-\d+$", "", m.group(2)))
        items.append(item(title, link, "Bona Casa de Música (Eventim)", None))
    return sort_items(dedupe_items(items))



def scrape_farol_conde(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    """Farma Conde Arena via /lista-eventos JSON."""
    body, err = fetch_raw(
        "https://farmacondearena.com.br/lista-eventos",
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    if err or not body:
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    events = data if isinstance(data, list) else list((data or {}).values())
    items: List[Dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        title = (ev.get("title") or "").strip()
        feature = (ev.get("feature") or "").strip()
        if feature and feature.lower() not in title.lower():
            full = f"{title} — {feature}"
        else:
            full = title or feature
        if not full:
            continue
        ticket = (ev.get("ticketurl") or "").strip()
        eid = ev.get("id")
        link = ticket or (f"https://farmacondearena.com.br/agenda/evento/{eid}" if eid else "")
        if not link:
            slug = ev.get("slug") or ""
            link = f"https://farmacondearena.com.br/agenda/{slug}" if slug else ""
        if not link:
            continue
        dates = ev.get("dates") or {}
        if isinstance(dates, list) and dates:
            dates = dates[0] if isinstance(dates[0], dict) else {}
        if not isinstance(dates, dict):
            dates = {}
        date_s = dates.get("date") or ""
        time_s = (dates.get("time_start") or "")[:5]
        date_raw = f"{date_s}T{time_s}:00" if date_s and time_s else date_s
        desc = f"Farma Conde Arena · {ev.get('category') or 'evento'}"
        it = item(full, link, desc, date_raw or None)
        dt = parse_date(date_raw) if date_raw else None
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))


def scrape_tldb_livesets(html: str, base: str) -> List[Dict[str, Any]]:
    """TLDB homepage recent livesets (Upcoming events block is JS-empty)."""
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'href="(https://tldb\.co/set/[^"]+)"\s+class="mw-txt"[^>]*>([^<]+)</a>',
        html or "",
        re.I,
    ):
        link = m.group(1).split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        title = html_lib.unescape(m.group(2)).strip()
        if not title:
            continue
        items.append(item(title, link, "TLDB — Liveset", None))
    return sort_items(dedupe_items(items))


def scrape_bona_eventim_venue(html: str, base: str) -> List[Dict[str, Any]]:
    """Bona venue page on Eventim (city/.../venue/bona-89347/)."""
    if not html or "Access Denied" in html or len(html) < 5000:
        return []
    items: List[Dict[str, Any]] = []
    seen = set()
    for m in re.finditer(
        r'href="((?:https://www\.eventim\.com\.br)?/event/([a-z0-9\-]+)/?)"',
        html,
        re.I,
    ):
        path, slug = m.group(1), m.group(2)
        if "allevents" in slug:
            continue
        link = path if path.startswith("http") else abs_url("https://www.eventim.com.br", path)
        if not link.endswith("/"):
            link = link + "/"
        if link in seen:
            continue
        seen.add(link)
        pos = m.start()
        window = html[max(0, pos - 500) : pos + 800]
        tm = re.search(
            r'(?:product-list-headline|pc-list-product-name|event-list-item)[^>]*>\s*([^<]{3,120})',
            window,
            re.I,
        )
        title = strip_tags(tm.group(1)) if tm else ""
        if not title:
            title = slug_title(re.sub(r"-bona-casa-de-musica-\d+$", "", slug))
        dm = re.search(
            r'(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\.?\s+(\d{4}).{0,20}?(\d{1,2}):(\d{2})',
            window,
            re.I,
        )
        date_raw = None
        dt = None
        if dm:
            date_raw = dm.group(0)
            dt = parse_pt_day_month(dm.group(1), dm.group(2), int(dm.group(3)))
            if dt:
                try:
                    dt = dt.replace(hour=int(dm.group(4)), minute=int(dm.group(5)))
                except Exception:
                    pass
        it = item(title, link, "Bona Casa de Música (Eventim venue)", date_raw)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
    return sort_items(dedupe_items(items))



def scrape_cafe_brasil_premium(_html: str = "", _base: str = "") -> List[Dict[str, Any]]:
    """Café Brasil Premium via Inertia /app/busca (paginated; sort client-side)."""
    headers = {
        "Accept": "text/html, application/xhtml+xml",
        "X-Inertia": "true",
        "X-Requested-With": "XMLHttpRequest",
    }
    collected: List[Dict[str, Any]] = []
    max_pages = 12  # 12*30 ≈ 360 items, then take newest 80
    for page in range(1, max_pages + 1):
        url = f"https://www.cafebrasilpremium.com.br/app/busca?page={page}"
        body, err = fetch_raw(url, headers=headers, timeout=45)
        if err or not body:
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        pag = (
            (data.get("props") or {})
            .get("contents", {})
            .get("data")
            or {}
        )
        rows = pag.get("data") if isinstance(pag, dict) else None
        if not isinstance(rows, list) or not rows:
            break
        collected.extend(rows)
        last = pag.get("last_page") or page
        if page >= last:
            break
        time.sleep(0.25)

    def _pub(ev: Dict[str, Any]) -> str:
        return ev.get("published_at") or ev.get("created_at") or ""

    collected.sort(key=_pub, reverse=True)
    items: List[Dict[str, Any]] = []
    seen = set()
    for ev in collected:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("id")
        if eid in seen:
            continue
        seen.add(eid)
        title = (ev.get("title") or "").strip()
        if not title:
            continue
        full = ev.get("content_full_url") or ""
        if full:
            link = abs_url("https://www.cafebrasilpremium.com.br", full)
        else:
            cat = (ev.get("category") or {}).get("slug") or "conteudo"
            slug = ev.get("slug") or ""
            if not slug:
                continue
            link = f"https://www.cafebrasilpremium.com.br/app/{cat}/{slug}"
        summary = strip_tags(ev.get("summary") or "")
        cat_title = (ev.get("category") or {}).get("title") or ""
        typ = ev.get("type") or ""
        desc = " · ".join(x for x in (cat_title, typ, summary) if x)
        pub = _pub(ev)
        it = item(title, link, desc or "Café Brasil Premium", pub)
        dt = parse_date(pub)
        if dt:
            it["_dt"] = dt
            it["pubDate"] = rfc822(dt)
        items.append(it)
        if len(items) >= 80:
            break
    return sort_items(dedupe_items(items))


VENUE_IMPOSSIBLE = [
    {"name": "Itaú Cultural (Inti tickets)", "reason": "SPA byInti sem API; use itau-cultural-agenda.xml"},
]


# scraper can be None meaning custom runner that ignores html fetch
VENUE_SCRAPE_TARGETS: List[Dict[str, Any]] = [
    {
        "name": "teatro-bradesco",
        "source_url": "https://sites.opusentretenimento.com/api/tbsp/events",
        "output": "teatro-bradesco.xml",
        "title": "Teatro Bradesco — Agenda",
        "description": "Shows/espetáculos do Teatro Bradesco (API Opus)",
        "scraper": scrape_teatro_bradesco,
        "skip_fetch": True,
    },
    {
        "name": "vibra-sp",
        "source_url": "https://sites.opusentretenimento.com/api/vibra/events",
        "output": "vibra-sp.xml",
        "title": "Vibra São Paulo — Agenda",
        "description": "Shows do Vibra São Paulo (API Opus; sem estacionamento)",
        "scraper": scrape_vibra_sp,
        "skip_fetch": True,
    },
    {
        "name": "theatro-municipal",
        "source_url": "https://theatromunicipal.org.br/programacao/",
        "output": "theatro-municipal.xml",
        "title": "Theatro Municipal — Programação",
        "description": "Eventos da programação do Theatro Municipal de São Paulo",
        "scraper": scrape_theatro_municipal,
    },
    {
        "name": "multi-arena-campinas",
        "source_url": "https://multiarenacampinas.com.br/programacao/",
        "output": "multi-arena-campinas.xml",
        "title": "Multi Arena Campinas — Programação",
        "description": "Shows anunciados na Multi Arena Campinas",
        "scraper": scrape_multi_arena,
    },
    {
        "name": "suhai-music-hall",
        "source_url": "https://suhaimusichall.com.br/eventos/",
        "output": "suhai-music-hall.xml",
        "title": "Suhai Music Hall — Eventos",
        "description": "Eventos do Suhai Music Hall",
        "scraper": scrape_suhai,
    },
    {
        "name": "blue-note-sp",
        "source_url": "https://bluenotesp.com/shows/",
        "output": "blue-note-sp.xml",
        "title": "Blue Note SP — Shows",
        "description": "Shows do Blue Note São Paulo (WP REST / HTML)",
        "scraper": scrape_blue_note,
        "skip_fetch": True,
    },
    {
        "name": "arena-b3",
        "source_url": "https://site.bileto.sympla.com.br/arenab3/",
        "output": "arena-b3.xml",
        "title": "Arena B3 — Agenda",
        "description": "Eventos Arena B3 via iframe Sympla/Bileto",
        "scraper": scrape_arena_b3,
        "skip_fetch": True,
    },
    {
        "name": "bourbon-street",
        "source_url": "https://site.bileto.sympla.com.br/bourbonstreet/",
        "output": "bourbon-street.xml",
        "title": "Bourbon Street — Agenda",
        "description": "Eventos Bourbon Street via iframe Sympla/Bileto",
        "scraper": scrape_bourbon_street,
        "skip_fetch": True,
    },
    {
        "name": "songkick-pacaembu",
        "source_url": "https://www.songkick.com/venues/494316-mercado-livre-arena-pacaembu",
        "output": "songkick-pacaembu.xml",
        "title": "Mercado Livre Arena Pacaembu (Songkick)",
        "description": "Eventos da arena via Songkick JSON-LD",
        "scraper": scrape_songkick_pacaembu,
        "fetch_headers": {"Accept": "*/*"},
    },
    {
        "name": "fabrique-club",
        "source_url": "https://www.bandsintown.com/pt/v/10077222-fabrique-club",
        "output": "fabrique-club.xml",
        "title": "Fabrique Club (Bandsintown)",
        "description": "Shows no Fabrique Club via Bandsintown JSON-LD",
        "scraper": scrape_fabrique,
    },
    {
        "name": "morumbis-live-nation",
        "source_url": "https://www.livenation.com.br/est%C3%A1dio-morumbis-tickets-vdp1277377",
        "output": "morumbis-live-nation.xml",
        "title": "Estádio Morumbis (Live Nation)",
        "description": "Shows no Estádio Morumbis via Live Nation",
        "scraper": scrape_live_nation_morumbis,
    },
    {
        "name": "carioca-club",
        "source_url": "https://www.clubedoingresso.com/cariocaclub",
        "output": "carioca-club.xml",
        "title": "Carioca Club — Agenda",
        "description": "Eventos do Carioca Club (Clube do Ingresso)",
        "scraper": scrape_carioca_club,
    },
    {
        "name": "juventus-eventos",
        "source_url": "https://www.juventus.com.br/eventos/",
        "output": "juventus-eventos.xml",
        "title": "Juventus — Eventos",
        "description": "Eventos do Clube Atlético Juventus",
        "scraper": scrape_juventus,
    },
    {
        "name": "komplexo-tempo",
        "source_url": "https://komplexotempo.com.br/agenda-de-eventos/",
        "output": "komplexo-tempo.xml",
        "title": "Komplexo Tempo — Agenda",
        "description": "Agenda de eventos do Komplexo Tempo",
        "scraper": scrape_komplexo,
    },
    {
        "name": "btg-pactual-hall",
        "source_url": "https://btgpactualhall.com.br/programacao/",
        "output": "btg-pactual-hall.xml",
        "title": "BTG Pactual Hall — Programação",
        "description": "Programação do BTG Pactual Hall (links Bileto)",
        "scraper": scrape_btg_hall,
    },
    {
        "name": "sala-sao-paulo",
        "source_url": "https://salasaopaulo.art.br/salasp/pt/programacao-ingressos",
        "output": "sala-sao-paulo.xml",
        "title": "Sala São Paulo — Programação",
        "description": "Concertos da Sala São Paulo",
        "scraper": scrape_sala_sao_paulo,
    },
    {
        "name": "audio-sp",
        "source_url": "https://audiosp.com.br/programacao",
        "output": "audio-sp.xml",
        "title": "Audio SP — Programação",
        "description": "Shows do Audio SP (AJAX programacao_load.php)",
        "scraper": scrape_audio_sp,
        "skip_fetch": True,
    },
    {
        "name": "teatro-das-artes-sp",
        "source_url": "https://teatrodasartessp.com.br/programacao/",
        "output": "teatro-das-artes-sp.xml",
        "title": "Teatro das Artes SP — Programação",
        "description": "Espetáculos em cartaz no Teatro das Artes SP",
        "scraper": scrape_teatro_das_artes,
    },
    {
        "name": "casa-de-francisca",
        "source_url": "https://casadefrancisca.art.br/novo/programacao",
        "output": "casa-de-francisca.xml",
        "title": "Casa de Francisca — Programação",
        "description": "Programação da Casa de Francisca",
        "scraper": scrape_casa_francisca,
    },
    {
        "name": "jazz-b",
        "source_url": "https://www.jazzb.com.br/shows",
        "output": "jazz-b.xml",
        "title": "Jazz B — Shows",
        "description": "Shows do Jazz B (links Sympla no site Wix)",
        "scraper": scrape_jazz_b,
    },
    {
        "name": "cavern-club-sp",
        "source_url": "https://thecavernclubsp.com.br/agenda/",
        "output": "cavern-club-sp.xml",
        "title": "The Cavern Club SP — Agenda",
        "description": "Shows e eventos do The Cavern Club São Paulo",
        "scraper": scrape_cavern_club,
    },
    {
        "name": "manifesto-bar",
        "source_url": "https://manifestobar.com.br/bar/programacao/",
        "output": "manifesto-bar.xml",
        "title": "Manifesto Bar — Programação",
        "description": "Programação do Manifesto Bar (links Clube do Ingresso)",
        "scraper": scrape_manifesto_bar,
    },
    {
        "name": "multiplan-hall-sc",
        "source_url": "https://www.ticketmaster.com.br/venue/multiplan-hall-sc",
        "output": "multiplan-hall-sc.xml",
        "title": "Multiplan Hall SC (Ticketmaster)",
        "description": "Eventos no Multiplan Hall Park Shopping São Caetano",
        "scraper": scrape_ticketmaster_multiplan,
    },
    {
        "name": "rockambole-meaple",
        "source_url": "https://meaple.com.br/rockambole",
        "output": "rockambole-meaple.xml",
        "title": "Casa Rockambole (Meaple)",
        "description": "Shows da Casa Rockambole via API Meaple",
        "scraper": scrape_rockambole_meaple,
        "skip_fetch": True,
    },
    {
        "name": "itau-cultural-agenda",
        "source_url": "https://www.itaucultural.org.br/agenda",
        "output": "itau-cultural-agenda.xml",
        "title": "Itaú Cultural — Agenda",
        "description": "Agenda cultural do Itaú Cultural (substitui Inti para listagem pública)",
        "scraper": scrape_itau_cultural_agenda,
    },
    {
        "name": "cine-joia",
        "source_url": "https://www.cinejoia.com.br/agenda/",
        "output": "cine-joia.xml",
        "title": "Cine Joia — Agenda",
        "description": "Shows do Cine Joia (WP REST mec-events; datas = publish date)",
        "scraper": scrape_cine_joia,
        "skip_fetch": True,
    },
    {
        "name": "porta-shotgun",
        "source_url": "https://shotgun.live/pt-br/venues/p-o-r-t-a",
        "output": "porta-shotgun.xml",
        "title": "PORTA (Shotgun) — Agenda",
        "description": "Shows no PORTA via Shotgun (pode falhar com 429 no Actions)",
        "scraper": scrape_porta_shotgun,
    },
    {
        "name": "cultura-artistica",
        "source_url": "https://culturaartistica.org/eventos/",
        "output": "cultura-artistica.xml",
        "title": "Cultura Artística — Eventos",
        "description": "Eventos Cultura Artística (pode falhar com captcha no Actions)",
        "scraper": scrape_cultura_artistica,
    },
    {
        "name": "bona-casa-musica",
        "source_url": "https://www.eventim.com.br/artist/bona-casa-musica/",
        "output": "bona-casa-musica.xml",
        "title": "Bona Casa de Música (Eventim)",
        "description": "Agenda Bona via Eventim (timeouts/Access Denied frequentes)",
        "scraper": scrape_bona_eventim,
        "timeout": 15,
    },
{
        "name": "farol-conde-arena",
        "source_url": "https://farmacondearena.com.br/agenda",
        "output": "farol-conde-arena.xml",
        "title": "Farma Conde Arena — Agenda",
        "description": "Shows da Farma Conde Arena (API /lista-eventos)",
        "scraper": scrape_farol_conde,
        "skip_fetch": True,
    },
    {
        "name": "tldb-livesets",
        "source_url": "https://tldb.co/",
        "output": "tldb-livesets.xml",
        "title": "TLDB — Livesets",
        "description": "Livesets recentes do The Livesets Database",
        "scraper": scrape_tldb_livesets,
        "fetch_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    },
    {
        "name": "bona-eventim-venue",
        "source_url": "https://www.eventim.com.br/city/sao-paulo-943/venue/bona-89347/",
        "output": "bona-eventim-venue.xml",
        "title": "Bona Casa de Música (Eventim venue)",
        "description": "Agenda Bona via página de venue Eventim (pode falhar com wall)",
        "scraper": scrape_bona_eventim_venue,
        "timeout": 20,
    },
    {
        "name": "cafe-brasil-premium",
        "source_url": "https://www.cafebrasilpremium.com.br/app",
        "output": "cafe-brasil-premium.xml",
        "title": "Café Brasil Premium — Conteúdos",
        "description": "Novidades do app Café Brasil Premium (busca Inertia; paywall no player)",
        "scraper": scrape_cafe_brasil_premium,
        "skip_fetch": True,
    },
]


def run_venue_scrape(target: Dict[str, Any]) -> Dict[str, Any]:
    name = target["name"]
    source = target["source_url"]
    out_name = target["output"]
    out_path = os.path.join(OUT, out_name)
    report: Dict[str, Any] = {
        "name": name,
        "source_url": source,
        "output": f"feeds/{out_name}",
        "items": 0,
        "ok": False,
        "notes": "",
        "kind": "venue-scrape",
    }
    html = ""
    if not target.get("skip_fetch"):
        headers = target.get("fetch_headers") or {}
        # Always use fetch_raw (handles gzip, e.g. Sala São Paulo)
        html, err = fetch_raw(
            source,
            headers=headers or None,
            timeout=int(target.get("timeout") or 40),
        )
        if err or not html:
            report["notes"] = f"fetch failed: {err or 'empty body'}"
            return report
    try:
        items = target["scraper"](html, source)
    except Exception as e:
        report["notes"] = f"scraper error: {type(e).__name__}: {e}"
        return report
    items = [it for it in items if it.get("title") and it.get("link")]
    if not items:
        report["notes"] = "no event items found"
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
    report["notes"] = f"scraped {len(items)} events"
    return report


def run_all_venues() -> List[Dict[str, Any]]:
    reports: List[Dict[str, Any]] = []
    print("Building venue native mirrors...")
    for spec in VENUE_NATIVE_MIRRORS:
        print(f"  - mirror {spec['out_name']} ...", flush=True)
        r = mirror_native_rss(**spec)
        print(f"      {'OK' if r['ok'] else 'FAIL'} items={r['items']} {r['notes']}")
        reports.append(r)
        time.sleep(0.3)

    print("Building venue scrapes...")
    for t in VENUE_SCRAPE_TARGETS:
        print(f"  - {t['name']} ...", flush=True)
        r = run_venue_scrape(t)
        print(f"      {'OK' if r['ok'] else 'FAIL'} items={r['items']} {r['notes']}")
        reports.append(r)
        time.sleep(0.35)
    return reports



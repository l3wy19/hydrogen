"""
Pobiera informacje o wydarzeniach, konferencjach i możliwościach kariery w branży wodorowej:
- Hydrogen Europe RSS (zawiera m.in. events)
- Google News RSS (konferencje, webinary, staże hydrogen)

Zapisuje do data/career.json — lista kumulatywna, posortowana wg daty wydarzenia.
Dashboard czyta z tego pliku zamiast hardkodować.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from anthropic import Anthropic

from config import OUTPUT_DIR, CLAUDE_MODEL

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SOURCES = [
    (
        "Hydrogen Europe",
        "https://hydrogeneurope.eu/feed/",
    ),
    (
        "Clean Hydrogen JU",
        "https://www.clean-hydrogen.europa.eu/news-events/events/rss_en",
    ),
    (
        "Google News: hydrogen conference 2026",
        "https://news.google.com/rss/search?q=hydrogen+conference+summit+2026&hl=en&gl=US&ceid=US:en",
    ),
    (
        "Google News: hydrogen webinar training",
        "https://news.google.com/rss/search?q=hydrogen+webinar+training+internship+2026&hl=en&gl=US&ceid=US:en",
    ),
    (
        "Google News: konferencja wodór 2026",
        "https://news.google.com/rss/search?q=konferencja+wod%C3%B3r+szkolenie+2026&hl=pl&gl=PL&ceid=PL:pl",
    ),
]

EVENT_KEYWORDS = [
    "conference", "summit", "konferencja", "webinar", "workshop", "training",
    "academy", "internship", "staż", "event", "szkolenie", "forum", "expo",
    "hydrogen", "wodór", "h2", "fuel cell",
]

MAX_ITEMS = 40

MONTH_MAP = {
    "01": "STY", "02": "LUT", "03": "MAR", "04": "KWI",
    "05": "MAJ", "06": "CZE", "07": "LIP", "08": "SIE",
    "09": "WRZ", "10": "PAŹ", "11": "LIS", "12": "GRU",
}

TYPE_MAP = {
    "conference": ("conf", "Konferencja"),
    "summit":     ("conf", "Konferencja"),
    "konferencja":("conf", "Konferencja"),
    "forum":      ("conf", "Konferencja"),
    "expo":       ("conf", "Konferencja"),
    "webinar":    ("web",  "Webinar"),
    "workshop":   ("web",  "Webinar"),
    "academy":    ("acad", "Akademia"),
    "szkolenie":  ("acad", "Akademia"),
    "training":   ("acad", "Akademia"),
    "internship": ("int",  "Staż"),
    "staż":       ("int",  "Staż"),
}


def _is_relevant(entry: dict) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(k.lower() in text for k in EVENT_KEYWORDS)


def _fetch_raw() -> list[dict]:
    raw = []
    for name, url in SOURCES:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:6]:
                if not _is_relevant(e):
                    continue
                raw.append({
                    "source": name,
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "summary_raw": re.sub(r"<[^>]+>", " ", e.get("summary", ""))[:600],
                    "published": e.get("published", "")[:25],
                })
        except Exception as ex:
            print(f"[KARIERA] Błąd pobierania {name}: {ex}")
    return raw


def _enrich(items: list[dict]) -> list[dict]:
    if not items:
        return []

    block = "\n\n".join(
        f"[{i}] Źródło: {a['source']}\n"
        f"Tytuł: {a['title']}\n"
        f"Opis: {a['summary_raw'][:400]}"
        for i, a in enumerate(items)
    )

    prompt = f"""Analizujesz artykuły w poszukiwaniu wydarzeń, konferencji, \
webinarów, staży i szkoleń związanych z branżą wodorową lub energią odnawialną.

Dla każdego artykułu zwróć JSON:
[
  {{
    "index": 0,
    "relevant": true,
    "type": "conf|web|acad|int",
    "typeLabel": "Konferencja|Webinar|Akademia|Staż",
    "title": "pełna nazwa wydarzenia",
    "day": "DD",
    "mon": "STY|LUT|MAR|KWI|MAJ|CZE|LIP|SIE|WRZ|PAŹ|LIS|GRU",
    "year": "YYYY",
    "date_iso": "YYYY-MM-DD",
    "loc": "miasto, kraj lub Online",
    "org": "organizator",
    "desc": "1-2 zdania PO POLSKU – co to za wydarzenie i dlaczego warto"
  }}
]

- relevant: false jeśli to NIE jest wydarzenie (np. zwykły artykuł o regulacjach)
- type: conf=konferencja/szczyt, web=webinar/workshop, acad=akademia/szkolenie, int=staż/job
- Jeśli daty nie ma w artykule, pomiń pola day/mon/year/date_iso
- Odpowiedz WYŁĄCZNIE JSON tablicą, bez tekstu przed/po

{block}"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        parsed = json.loads(match.group(0))
        enriched = []
        for r in parsed:
            if not r.get("relevant"):
                continue
            idx = r.get("index", 0)
            src = items[idx] if idx < len(items) else items[0]
            enriched.append({
                "type":      r.get("type", "conf"),
                "typeLabel": r.get("typeLabel", "Konferencja"),
                "title":     r.get("title", src["title"]),
                "day":       r.get("day") or "",
                "mon":       r.get("mon") or "",
                "year":      r.get("year") or "",
                "date_iso":  r.get("date_iso") or "",
                "loc":       r.get("loc", ""),
                "org":       r.get("org", src["source"]),
                "desc":      r.get("desc", ""),
                "href":      src.get("link", ""),
            })
        return enriched
    except Exception as ex:
        print(f"[KARIERA] Błąd Claude: {ex}")
        return []


def update_career() -> list[dict]:
    path = Path(OUTPUT_DIR) / "career.json"

    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text("utf-8")).get("items", [])
        except Exception:
            pass

    existing_links = {i.get("href") for i in existing if i.get("href")}

    raw = _fetch_raw()
    new_raw = [r for r in raw if r.get("link") not in existing_links]
    print(f"[KARIERA] {len(new_raw)} nowych artykułów do wzbogacenia")

    new_items = _enrich(new_raw) if new_raw else []

    # Scal: nowe + istniejące, deduplikuj po href
    seen = {n.get("href") for n in new_items}
    merged = new_items + [e for e in existing if e.get("href") not in seen]

    # Sortuj: przyszłe wydarzenia według daty rosnąco, bez daty — na koniec
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def sort_key(item):
        d = item.get("date_iso", "")
        if d and d >= today_iso:
            return (0, d)     # przyszłe: rosnąco
        elif d:
            return (1, d)     # przeszłe: po przyszłych, rosnąco
        return (2, "")        # bez daty: na końcu

    merged.sort(key=sort_key)
    merged = merged[:MAX_ITEMS]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = {"updated": today, "items": merged}
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[KARIERA] +{len(new_items)} nowych, łącznie {len(merged)} wydarzeń → {path}")
    return merged

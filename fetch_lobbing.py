"""
Pobiera nowe informacje lobbingowe/regulacyjne dotyczące wodoru:
- EC Better Regulation Portal RSS (otwarte konsultacje)
- Google News RSS (pozycje branży, regulacje UE)

Zapisuje do data/lobbing.json — lista kumulatywna, najnowsze pierwsze.
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
        "EC Better Regulation",
        "https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives_rss_en",
    ),
    (
        "Google News: hydrogen EU regulation",
        "https://news.google.com/rss/search?q=hydrogen+EU+regulation+consultation+2026&hl=en&gl=US&ceid=US:en",
    ),
    (
        "Google News: hydrogen industry position",
        "https://news.google.com/rss/search?q=hydrogen+industry+lobbying+EU+position+RFNBO&hl=en&gl=US&ceid=US:en",
    ),
    (
        "Google News: wodór regulacja",
        "https://news.google.com/rss/search?q=wod%C3%B3r+regulacja+UE+konsultacje&hl=pl&gl=PL&ceid=PL:pl",
    ),
]

H2_KEYWORDS = [
    "hydrogen", "wodór", "wodorow", "h2", "electroly", "RFNBO", "fuel cell",
    "clean energy", "renewable energy", "hydrogen bank", "decarboni", "carbon",
    "green hydrogen", "electrolyz", "hydrogen strategy",
]

MAX_ITEMS = 60


def _is_relevant(entry: dict) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(k.lower() in text for k in H2_KEYWORDS)


def _fetch_raw() -> list[dict]:
    raw = []
    for name, url in SOURCES:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:8]:
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
            print(f"[LOBBING] Błąd pobierania {name}: {ex}")
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

    prompt = f"""Jesteś analitykiem regulacyjnym branży wodorowej.
Przeanalizuj poniższe artykuły/inicjatywy. Dla każdego określ czy dotyczy regulacji, \
konsultacji, lobbingu lub pozycji firm/org wobec wodoru lub energii odnawialnej.

Odpowiedz WYŁĄCZNIE JSON tablicą (bez tekstu przed/po):
[
  {{
    "index": 0,
    "relevant": true,
    "company": "nazwa org/firmy/instytucji",
    "country": "UE / Polska / Niemcy / itp.",
    "law": "tytuł aktu/inicjatywy/tematu",
    "stance": "sup|crit|mix|neu",
    "stanceLabel": "Popieramy|Krytyczna|Mieszana|Otwarte konsultacje",
    "stanceColor": "#10B981|#EF4444|#FBBF24|#06B6D4",
    "type": "Company/Business|NGO|Industry Association|Initiative|Rząd",
    "excerpt": "1-2 zdania PO POLSKU – o co chodzi i dlaczego ważne dla branży wodorowej"
  }}
]

- relevant: false jeśli artykuł nie dotyczy regulacji/lobbingu branży wodorowej
- stance sup=#10B981, crit=#EF4444, mix=#FBBF24, neu=#06B6D4

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
                "company":      r.get("company", src["source"]),
                "country":      r.get("country", "UE 🇪🇺"),
                "law":          r.get("law", src["title"]),
                "stance":       r.get("stance", "neu"),
                "stanceLabel":  r.get("stanceLabel", "Otwarte konsultacje"),
                "stanceColor":  r.get("stanceColor", "#06B6D4"),
                "type":         r.get("type", "Initiative"),
                "date":         src.get("published", "")[:10],
                "excerpt":      r.get("excerpt", ""),
                "href":         src.get("link", ""),
            })
        return enriched
    except Exception as ex:
        print(f"[LOBBING] Błąd Claude: {ex}")
        return []


def update_lobbing() -> list[dict]:
    path = Path(OUTPUT_DIR) / "lobbing.json"

    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text("utf-8")).get("items", [])
        except Exception:
            pass

    existing_links = {i.get("href") for i in existing if i.get("href")}

    raw = _fetch_raw()
    new_raw = [r for r in raw if r.get("link") not in existing_links]
    print(f"[LOBBING] {len(new_raw)} nowych artykułów do wzbogacenia")

    new_items = _enrich(new_raw) if new_raw else []

    # Scal: nowe na górze, deduplikuj po href
    seen_links = {n.get("href") for n in new_items}
    merged = new_items + [e for e in existing if e.get("href") not in seen_links]
    merged = merged[:MAX_ITEMS]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = {"updated": today, "items": merged}
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[LOBBING] +{len(new_items)} nowych, łącznie {len(merged)} pozycji → {path}")
    return merged

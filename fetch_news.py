"""
Zbiera artykuły ze skonfigurowanych źródeł RSS opublikowane w ostatnich N dniach.

Użycie:
    from fetch_news import fetch_all
    articles = fetch_all()
"""

import feedparser
from datetime import datetime, timedelta, timezone
from time import mktime

from config import RSS_SOURCES, KEYWORDS, LOOKBACK_DAYS


def _entry_published(entry):
    """Wyciąga datę publikacji z wpisu RSS, obsługując różne formaty."""
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
    # Jeśli feed nie podaje daty, zakładamy "teraz" żeby nie zgubić artykułu
    return datetime.now(timezone.utc)


def _matches_keywords(text: str) -> bool:
    """Sprawdza, czy tekst zawiera któreś ze słów kluczowych (wielkość liter ignorowana)."""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS)


def fetch_source(name: str, url: str, category: str, cutoff: datetime) -> list[dict]:
    """Pobiera i filtruje wpisy z jednego źródła RSS."""
    articles = []
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[BŁĄD] Nie udało się pobrać feedu '{name}': {e}")
        return articles

    if feed.bozo and not feed.entries:
        print(f"[OSTRZEŻENIE] Feed '{name}' może być uszkodzony lub niedostępny: {url}")
        return articles

    for entry in feed.entries:
        published = _entry_published(entry)
        if published < cutoff:
            continue  # za stary wpis

        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        full_text = f"{title} {summary}"

        if not _matches_keywords(full_text):
            continue  # nie dotyczy wodoru, pomijamy

        articles.append({
            "source": name,
            "source_category": category,
            "title": title,
            "link": getattr(entry, "link", ""),
            "summary_raw": summary,
            "published": published.isoformat(),
        })

    return articles


def fetch_all() -> list[dict]:
    """Pobiera artykuły ze wszystkich skonfigurowanych źródeł."""
    if not RSS_SOURCES:
        print("[UWAGA] Lista RSS_SOURCES w config.py jest pusta. Dodaj źródła przed uruchomieniem.")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    all_articles = []

    for name, url, category in RSS_SOURCES:
        found = fetch_source(name, url, category, cutoff)
        print(f"  {name}: znaleziono {len(found)} artykułów na temat wodoru")
        all_articles.extend(found)

    return all_articles


if __name__ == "__main__":
    print(f"Sprawdzam {len(RSS_SOURCES)} źródeł z ostatnich {LOOKBACK_DAYS} dni...\n")
    results = fetch_all()
    print(f"\nŁącznie znaleziono {len(results)} artykułów.")
    for article in results:
        print(f"- [{article['source']}] {article['title']}")

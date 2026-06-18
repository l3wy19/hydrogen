"""
Główny skrypt dnia: zbiera artykuły, wzbogaca je o podsumowania/klasyfikację,
i zapisuje jako plik JSON z dzisiejszą datą.

Użycie:
    python run_daily.py

To jest skrypt, który później podłączysz pod cron / GitHub Actions,
żeby się odpalał automatycznie raz dziennie.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fetch_news import fetch_all
from summarize import enrich_articles
from config import OUTPUT_DIR


def deduplicate(articles: list[dict]) -> list[dict]:
    """Usuwa duplikaty po linku (czasem ten sam artykuł trafia do wielu feedów)."""
    seen_links = set()
    unique = []
    for article in articles:
        link = article.get("link")
        if link and link in seen_links:
            continue
        seen_links.add(link)
        unique.append(article)
    return unique


def save_digest(articles: list[dict], date_str: str):
    output_path = Path(OUTPUT_DIR) / f"digest_{date_str}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    digest = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "articles": sorted(articles, key=lambda a: a.get("importance", 0), reverse=True),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, indent=2, ensure_ascii=False)

    # Aktualizuj index.json z listą wszystkich dat
    index_path = Path(OUTPUT_DIR) / "index.json"
    try:
        import json as _json
        existing = _json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"dates": []}
        if date_str not in existing["dates"]:
            existing["dates"].append(date_str)
            existing["dates"].sort()
        index_path.write_text(_json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[OSTRZEŻENIE] Nie udało się zaktualizować index.json: {e}")

    print(f"\nZapisano przegląd do: {output_path}")
    return output_path


def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"=== Przegląd branży wodorowej: {date_str} ===\n")

    print("1. Zbieram artykuły z RSS...")
    raw_articles = fetch_all()

    print(f"\n2. Usuwam duplikaty...")
    unique_articles = deduplicate(raw_articles)
    print(f"   Pozostało {len(unique_articles)} unikalnych artykułów (z {len(raw_articles)})")

    if not unique_articles:
        print("\nBrak nowych artykułów dzisiaj. Zapisuję pusty przegląd.")
        save_digest([], date_str)
        return

    print(f"\n3. Wysyłam do Claude do klasyfikacji i podsumowania...")
    enriched = enrich_articles(unique_articles)

    print(f"\n4. Zapisuję wynik...")
    save_digest(enriched, date_str)

    print("\n=== Gotowe ===")


if __name__ == "__main__":
    main()

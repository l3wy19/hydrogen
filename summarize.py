"""
Wysyła zebrane artykuły do Claude API, żeby:
1. sklasyfikować każdy artykuł do jednej z kategorii (regulacja, inwestycja, itd.)
2. napisać krótkie podsumowanie po polsku
3. ocenić istotność (1-5), żeby można było sortować dashboard

Działa w jednym wywołaniu API na cały batch artykułów (taniej i szybciej niż
osobne wywołanie na każdy artykuł), z prośbą o odpowiedź w czystym JSON.
"""

import json
import os
import re
from anthropic import Anthropic

from config import CLAUDE_MODEL, CATEGORIES

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = f"""Jesteś analitykiem rynku branży wodorowej (hydrogen economy).
Otrzymujesz listę artykułów (tytuł + skrót) i dla KAŻDEGO z nich masz:

1. Przypisać JEDNĄ kategorię z listy: {", ".join(CATEGORIES)}
2. Napisać podsumowanie w 1-2 zwięzłych zdaniach PO POLSKU, nawet jeśli oryginał jest w innym języku
3. Ocenić istotność dla branży w skali 1-5 (5 = przełomowa wiadomość, duża inwestycja, ważna regulacja; 1 = drobna wzmianka)

Odpowiedz WYŁĄCZNIE poprawnym JSON-em, bez żadnego tekstu przed/po, w formacie:
[
  {{"index": 0, "category": "...", "summary_pl": "...", "importance": 3}},
  {{"index": 1, "category": "...", "summary_pl": "...", "importance": 5}}
]

Liczba elementów w odpowiedzi MUSI równać się liczbie artykułów w wejściu, w tej samej kolejności (pole "index" odpowiada pozycji w liście wejściowej, licząc od 0)."""


def _build_user_prompt(articles: list[dict]) -> str:
    lines = []
    for i, article in enumerate(articles):
        lines.append(
            f"[{i}] Źródło: {article['source']}\n"
            f"Tytuł: {article['title']}\n"
            f"Skrót: {article['summary_raw'][:500]}\n"
        )
    return "Przeanalizuj poniższe artykuły:\n\n" + "\n".join(lines)


def _parse_llm_json(raw_text: str) -> list[dict]:
    """Wyciąga JSON z odpowiedzi LLM — obsługuje markdown fences i tekst po tablicy."""
    cleaned = raw_text.strip()

    # 1. Próba bezpośrednia
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. Wyciągnij zawartość bloku ```json ... ``` lub ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Znajdź pierwszą tablicę JSON [...] w tekście (ignoruje tekst przed/po)
    arr_match = re.search(r"\[[\s\S]*\]", cleaned)
    if arr_match:
        return json.loads(arr_match.group(0))

    raise ValueError(f"Nie można wyodrębnić JSON: {cleaned[:300]}")


def enrich_articles(articles: list[dict], batch_size: int = 15) -> list[dict]:
    """
    Dodaje do każdego artykułu: category, summary_pl, importance.
    Przetwarza w batchach, żeby nie przekroczyć limitów kontekstu przy dużej liczbie newsów.
    """
    if not articles:
        return []

    enriched = []

    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start:batch_start + batch_size]
        user_prompt = _build_user_prompt(batch)

        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = response.content[0].text
            results = _parse_llm_json(raw_text)

            for result in results:
                idx = result["index"]
                article = batch[idx].copy()
                article["category"] = result.get("category", "inne")
                article["summary_pl"] = result.get("summary_pl", "")
                article["importance"] = result.get("importance", 1)
                enriched.append(article)

        except Exception as e:
            print(f"[BŁĄD] Nie udało się przetworzyć batcha {batch_start}: {e}")
            # Dodajemy artykuły bez wzbogacenia, żeby nie zgubić danych
            for article in batch:
                article = article.copy()
                article["category"] = "inne"
                article["summary_pl"] = "[Błąd przetwarzania - sprawdź oryginał]"
                article["importance"] = 1
                enriched.append(article)

    return enriched


if __name__ == "__main__":
    # Szybki test na sztucznych danych - przydatne do sprawdzenia, czy API key działa
    test_articles = [
        {
            "source": "Test",
            "source_category": "news",
            "title": "EU announces new RFNBO delegated act for hydrogen",
            "link": "https://example.com",
            "summary_raw": "The European Commission published updated rules for renewable hydrogen production criteria.",
            "published": "2026-06-17T10:00:00+00:00",
        }
    ]
    result = enrich_articles(test_articles)
    print(json.dumps(result, indent=2, ensure_ascii=False))

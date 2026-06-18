# Przegląd branży wodorowej - szkielet projektu

## Co tu jest

- `config.py` — lista źródeł RSS, słowa kluczowe, kategorie. **To tutaj edytujesz najczęściej.**
- `fetch_news.py` — zbiera artykuły z RSS, filtruje po słowach kluczowych
- `summarize.py` — wysyła artykuły do Claude API, dostaje klasyfikację + podsumowanie PL
- `run_daily.py` — łączy wszystko, zapisuje wynik jako `data/digest_YYYY-MM-DD.json`

## Jak to uruchomić (Dzień 1)

### 1. Instalacja

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Klucz API

Załóż konto na https://console.anthropic.com, wygeneruj API key, potem:

```bash
export ANTHROPIC_API_KEY="twój-klucz-tutaj"
```

(albo dodaj do pliku `.env` — wtedy musisz dodać `from dotenv import load_dotenv; load_dotenv()`
na początku `run_daily.py`)

### 3. Dodaj źródła RSS

Otwórz `config.py`, w liście `RSS_SOURCES` dodaj prawdziwe adresy RSS, np.:

```python
RSS_SOURCES = [
    ("Hydrogen Insight", "https://www.hydrogeninsight.com/rss", "news"),
    ("Hydrogen Europe", "https://hydrogeneurope.eu/feed/", "industry"),
]
```

Możesz najpierw sprawdzić, czy feed działa, testując samodzielnie:
```bash
python fetch_news.py
```
To pokaże Ci, ile artykułów znaleziono z każdego źródła, bez wywoływania Claude API
(czyli za darmo, można testować ile chcesz).

### 4. Odpal cały pipeline

```bash
python run_daily.py
```

Wynik znajdziesz w `data/digest_2026-06-17.json` (z dzisiejszą datą).

## Co dalej (Dzień 2)

Gdy `run_daily.py` działa i generuje sensowny JSON:
1. Zbuduj prosty dashboard, który czyta ten plik i wyświetla artykuły (Streamlit najszybciej, Next.js solidniej)
2. Podłącz cron / GitHub Actions, żeby `run_daily.py` odpalał się sam raz dziennie
3. Przenieś zapis z plików JSON do bazy danych (Postgres/Supabase), żeby mieć historię i wyszukiwanie

## Typowe problemy

- **Feed nie zwraca artykułów**: sprawdź czy URL jest poprawny w przeglądarce, niektóre strony zmieniają adresy RSS
- **`feed.bozo` ostrzeżenie**: feed jest źle sformatowany, ale czasem nadal da się go odczytać — sprawdź `feed.entries`
- **JSON parsing error w summarize.py**: model czasem dodaje tekst przed JSON-em mimo instrukcji — `_parse_llm_json` próbuje to obsłużyć, ale przy częstych błędach rozważ dodanie `response_format` jeśli API to wspiera, albo zmniejszenie `batch_size`

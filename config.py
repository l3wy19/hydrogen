"""
Konfiguracja przeglądu branży wodorowej.

Zacznij od kilku źródeł, sprawdź czy działają, dodawaj kolejne stopniowo.
Każde źródło to zwykły RSS feed - jeśli firma/instytucja ma feed, zazwyczaj
jest pod adresem typu https://example.com/feed lub /rss lub /feed.xml

Jak znaleźć RSS feed danej strony:
1. Spróbuj dodać /feed lub /rss na końcu adresu
2. Szukaj ikonki RSS na stronie (często w stopce)
3. Wyszukaj w Google: "nazwa strony" RSS feed
4. Narzędzia jak https://www.rss.app pomagają stworzyć RSS z dowolnej strony

UWAGA: zanim dodasz źródło do produktu komercyjnego, sprawdź jego ToS/robots.txt.
RSS feedy są zwykle udostępniane właśnie do tego (agregacji), ale web scraping
bez RSS to już inna sprawa prawnie.
"""

# Format: (nazwa, url_rss, kategoria)
# kategoria pomaga w późniejszym filtrowaniu/sortowaniu na dashboardzie
RSS_SOURCES = [
    # --- Branżowe media wodorowe (działające) ---
    ("Fuel Cells Works",      "https://fuelcellsworks.com/feed/",                                                                "news"),
    ("H2 View",               "https://www.h2-view.com/feed/",                                                                  "news"),
    ("Hydrogen Central",      "https://hydrogen-central.com/feed/",                                                             "news"),
    ("Hydrogen Europe",       "https://hydrogeneurope.eu/feed/",                                                                "industry"),
    ("PV Magazine",           "https://www.pv-magazine.com/feed/",                                                             "news"),

    # --- Google News RSS (bardzo niezawodne, agregują z wielu źródeł) ---
    ("Google News: hydrogen EU",       "https://news.google.com/rss/search?q=hydrogen+europe+EU&hl=en&gl=US&ceid=US:en",       "news"),
    ("Google News: green hydrogen",    "https://news.google.com/rss/search?q=green+hydrogen+electrolyzer&hl=en&gl=US&ceid=US:en", "news"),
    ("Google News: RFNBO regulation",  "https://news.google.com/rss/search?q=RFNBO+hydrogen+regulation&hl=en&gl=US&ceid=US:en", "regulacja_UE"),
    ("Google News: hydrogen Poland",   "https://news.google.com/rss/search?q=hydrogen+Poland+wod%C3%B3r&hl=pl&gl=PL&ceid=PL:pl", "polska"),
    ("Google News: hydrogen investment","https://news.google.com/rss/search?q=hydrogen+investment+GW+MW&hl=en&gl=US&ceid=US:en", "news"),
]

# Słowa kluczowe do pierwszego, szybkiego filtrowania (przed wysłaniem do LLM)
# Pomaga odsiać artykuły, które przypadkiem trafiły do feedu, a nie dotyczą wodoru
KEYWORDS = [
    "hydrogen", "wodór", "wodorow", "h2", "electrolyser", "electrolyzer",
    "elektrolizer", "fuel cell", "ogniwo paliwowe", "green hydrogen",
    "zielony wodór", "hydrogen valley", "RFNBO",
]

# Ile dni wstecz sprawdzać (1 = tylko ostatnia doba)
LOOKBACK_DAYS = 1

# Model Claude do podsumowań i klasyfikacji
CLAUDE_MODEL = "claude-sonnet-4-6"

# Gdzie zapisywać wyniki
OUTPUT_DIR = "data"

# Kategorie do klasyfikacji - LLM przypisze każdy artykuł do jednej z nich
CATEGORIES = [
    "regulacja_UE",      # dyrektywy, akty delegowane, konsultacje
    "inwestycja",         # nowe projekty, finansowanie, FID
    "technologia",        # przełomy technologiczne, R&D
    "rynek",              # ceny, popyt, kontrakty
    "polska",             # newsy specyficzne dla polskiego rynku
    "inne",
]

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
    # --- Branżowe media wodorowe ---
    ("Fuel Cells Works",      "https://fuelcellsworks.com/feed/",                          "news"),
    ("H2 View",               "https://www.h2-view.com/feed/",                             "news"),
    ("Hydrogen Central",      "https://hydrogen-central.com/feed/",                        "news"),
    ("New Hydrogen Economy",  "https://newhydrogeneconomy.com/feed/",                      "news"),
    ("Recharge News",         "https://www.rechargenews.com/rss",                          "news"),

    # --- Instytucje i stowarzyszenia branżowe ---
    ("Hydrogen Europe",       "https://hydrogeneurope.eu/feed/",                           "industry"),
    ("Clean Hydrogen JU",     "https://www.clean-hydrogen.europa.eu/news-events/rss_en",   "industry"),
    ("IRENA",                 "https://www.irena.org/rss/news",                            "industry"),

    # --- Regulacje UE ---
    ("EUR-Lex Hydrogen",      "https://eur-lex.europa.eu/EN/display-feed.rss",             "regulacja_UE"),

    # --- Energia ogólnie (filtrujemy po keywords) ---
    ("IEA News",              "https://www.iea.org/feed/news",                             "news"),
    ("PV Magazine",           "https://www.pv-magazine.com/feed/",                        "news"),
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

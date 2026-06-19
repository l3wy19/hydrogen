"""
Pobiera aktualne ceny rynkowe z darmowych źródeł:
- Ropa Brent: Yahoo Finance BZ=F
- ETS CO2:    Yahoo Finance CARBZ.MI (EUA futures, Borsa Italiana)
- Metanol:    Methanex.com (aktualizowane co miesiąc)
- H2 stacje:  fallback do ostatniej wartości (brak darmowego publicznego API)

Zapisuje do data/prices.json — dashboard czyta z tego pliku zamiast hardkodować.
"""

import json
import re
import requests
from datetime import datetime, timezone
from pathlib import Path

from config import OUTPUT_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# ── Yahoo Finance helper ─────────────────────────────────────────────────────

def _yahoo(symbol: str, range_: str = "30d") -> dict | None:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&range={range_}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        closes = result["indicators"]["quote"][0].get("close") or []
        closes = [c for c in closes if c is not None]

        price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
        prev  = meta.get("previousClose")      or (closes[-2] if len(closes) >= 2 else price)
        if price is None:
            return None

        change = round((price - prev) / prev * 100, 1) if prev else 0.0
        spark  = [round(c, 2) for c in closes[-7:]] if len(closes) >= 7 else [round(c, 2) for c in closes]
        return {"price": round(price, 2), "change": change, "spark": spark}

    except Exception as e:
        print(f"[CENY] Yahoo {symbol}: {e}")
        return None


# ── Methanex methanol scraper ────────────────────────────────────────────────

def _methanex() -> dict | None:
    try:
        r = requests.get(
            "https://www.methanex.com/our-business/pricing/",
            headers=HEADERS, timeout=15
        )
        text = r.text

        # Szukaj wzorców ceny w USD, np. "$425" lub "425 USD" lub "425.00"
        matches = re.findall(r'\$\s*(\d{3,4}(?:\.\d{1,2})?)', text)
        if not matches:
            # Fallback: szukaj po "USD" z liczbą
            matches = re.findall(r'(\d{3,4}(?:\.\d{1,2})?)\s*USD', text)
        if matches:
            price_usd = float(matches[0])
            price_eur = round(price_usd * 0.93, 0)  # przybliżony kurs
            return {"price": price_eur, "change": None, "spark": []}
    except Exception as e:
        print(f"[CENY] Methanex scraping: {e}")
    return None


# ── Główna funkcja ───────────────────────────────────────────────────────────

PRICE_CONFIGS = [
    {
        "id": "h2",
        "name": "Wodór na stacji",
        "unit": "EUR/kg",
        "color": "#10B981",
        "source": "H2 Station Index",
        "fetch": None,                  # brak darmowego API — trzymamy ostatnią wartość
        "fallback": 14.80,
    },
    {
        "id": "methanol",
        "name": "Bio-Metanol",
        "unit": "EUR/t",
        "color": "#FBBF24",
        "source": "Methanex Europe",
        "fetch": "methanol",
        "fallback": 498,
    },
    {
        "id": "ets",
        "name": "ETS CO₂",
        "unit": "EUR/tCO₂",
        "color": "#8B5CF6",
        "source": "ICE EUA Futures",
        "fetch": "CARBZ.MI",
        "fallback": 68.40,
    },
    {
        "id": "oil",
        "name": "Ropa Brent",
        "unit": "USD/bbl",
        "color": "#06B6D4",
        "source": "ICE Brent Crude",
        "fetch": "BZ=F",
        "fallback": 77.20,
    },
]


def update_prices() -> list[dict]:
    path = Path(OUTPUT_DIR) / "prices.json"
    prev_map: dict[str, dict] = {}
    if path.exists():
        try:
            prev_map = {p["id"]: p for p in json.loads(path.read_text("utf-8")).get("prices", [])}
        except Exception:
            pass

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = []

    for cfg in PRICE_CONFIGS:
        prev = prev_map.get(cfg["id"], {})
        prev_spark = prev.get("spark", [cfg["fallback"]] * 7)

        # Pobierz świeże dane
        fetched = None
        if cfg["fetch"] == "methanol":
            fetched = _methanex()
        elif cfg["fetch"]:
            fetched = _yahoo(cfg["fetch"])

        if fetched and fetched["price"]:
            price  = fetched["price"]
            change = fetched["change"] if fetched["change"] is not None else prev.get("change", 0.0)
            # Dołącz dzisiejszą cenę do sparkline (max 30 wartości)
            spark = (prev_spark + [price])[-30:]
        else:
            price  = prev.get("price", cfg["fallback"])
            change = prev.get("change", 0.0)
            spark  = prev_spark

        item = {
            "id":     cfg["id"],
            "name":   cfg["name"],
            "price":  price,
            "unit":   cfg["unit"],
            "change": round(change, 1),
            "period": "30 dni",
            "color":  cfg["color"],
            "spark":  spark[-7:],   # dashboard pokazuje 7 punktów
            "source": cfg["source"],
        }
        results.append(item)
        sign = "+" if (change or 0) >= 0 else ""
        print(f"[CENY] {cfg['name']}: {price} {cfg['unit']} ({sign}{change}%)")

    data = {"updated": today, "prices": results}
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CENY] Zapisano {len(results)} cen → {path}")
    return results

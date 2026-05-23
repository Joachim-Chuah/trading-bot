import httpx
from bs4 import BeautifulSoup

_CBOE_URL = "https://www.cboe.com/markets/us/options/market-statistics/daily"


def get_put_call_ratio() -> float | None:
    try:
        response = httpx.get(_CBOE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Equity put/call ratio is in the first data table, "Equity" row, P/C Ratio column
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if cells and "equity" in cells[0].get_text(strip=True).lower():
                return float(cells[1].get_text(strip=True))
    except Exception:
        pass
    return None

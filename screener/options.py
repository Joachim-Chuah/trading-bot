from datetime import date, datetime
from models.stock import OptionsData

_MIN_DAYS_TO_EXPIRY = 365
_MAX_OTM_PCT = 0.10
_MAX_ITM_PCT = 0.05
_MAX_IV_RANK = 30.0
_MIN_OPEN_INTEREST = 100
_MAX_RELATIVE_SPREAD = 0.15


def _days_to_expiry(expiration_str: str) -> int:
    expiry = datetime.strptime(expiration_str, "%Y-%m-%d").date()
    return (expiry - date.today()).days


def _is_viable_leap(contract: dict, current_price: float) -> bool:
    details = contract.get("details", {})

    if details.get("contract_type", "").lower() != "call":
        return False

    expiry_str = details.get("expiration_date", "")
    if not expiry_str or _days_to_expiry(expiry_str) < _MIN_DAYS_TO_EXPIRY:
        return False

    strike = details.get("strike_price", 0)
    lower = current_price * (1 - _MAX_OTM_PCT)
    upper = current_price * (1 + _MAX_ITM_PCT)
    if not (lower <= strike <= upper):
        return False

    greeks = contract.get("greeks", {})
    iv = greeks.get("implied_volatility") or contract.get("implied_volatility", 0)
    if iv > _MAX_IV_RANK:
        return False

    oi = contract.get("open_interest", 0)
    if oi < _MIN_OPEN_INTEREST:
        return False

    quote = contract.get("day", {})
    bid = quote.get("bid", 0)
    ask = quote.get("ask", 0)
    mid = (bid + ask) / 2 if (bid + ask) > 0 else 0
    if mid > 0 and (ask - bid) / mid > _MAX_RELATIVE_SPREAD:
        return False

    return True


def evaluate_options(chain: list[dict], current_price: float) -> OptionsData | None:
    viable = [c for c in chain if _is_viable_leap(c, current_price)]
    if not viable:
        return None

    best = min(viable, key=lambda c: abs(c["details"]["strike_price"] - current_price))

    details = best["details"]
    greeks = best.get("greeks", {})
    quote = best.get("day", {})

    return OptionsData(
        iv_rank=greeks.get("implied_volatility") or best.get("implied_volatility", 0.0),
        open_interest=best.get("open_interest", 0),
        bid_ask_spread=quote.get("ask", 0) - quote.get("bid", 0),
        strike=details["strike_price"],
        expiration=datetime.strptime(details["expiration_date"], "%Y-%m-%d").date(),
        contract_symbol=details.get("ticker", ""),
    )

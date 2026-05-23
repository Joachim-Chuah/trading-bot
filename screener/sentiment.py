from typing import Literal
from models.stock import MacroSnapshot, SentimentData

_AGREEMENT_CONFIDENCE_BOOST = 0.1
_RECENT_HOURS = 48


def _load_finbert():
    from transformers import pipeline
    return pipeline("text-classification", model="ProsusAI/finbert")


def _finbert_label(label: str) -> Literal["bullish", "neutral", "bearish"]:
    mapping = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}
    return mapping.get(label.lower(), "neutral")


def _massive_label(insights: list[dict]) -> Literal["bullish", "neutral", "bearish"]:
    if not insights:
        return "neutral"
    raw = insights[0].get("sentiment", "neutral").lower()
    mapping = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}
    return mapping.get(raw, "neutral")


def _score_headlines(headlines: list[str], finbert) -> tuple[Literal["bullish", "neutral", "bearish"], float]:
    if not headlines:
        return "neutral", 0.0
    results = finbert(headlines, truncation=True, max_length=512)
    scores: dict[str, float] = {"bullish": 0.0, "neutral": 0.0, "bearish": 0.0}
    for r in results:
        label = _finbert_label(r["label"])
        scores[label] += r["score"]
    dominant = max(scores, key=lambda k: scores[k])
    confidence = scores[dominant] / len(headlines)
    return dominant, round(confidence, 4)


def evaluate_sentiment(news: list[dict], macro: MacroSnapshot, finbert=None) -> SentimentData:
    if finbert is None:
        finbert = _load_finbert()

    headlines = [a.get("title", "") for a in news if a.get("title")]
    massive_label = _massive_label(news[0].get("insights", []) if news else [])
    finbert_label, confidence = _score_headlines(headlines, finbert)

    if finbert_label == massive_label:
        signal = finbert_label
        confidence = min(1.0, confidence + _AGREEMENT_CONFIDENCE_BOOST)
    else:
        signal = "mixed"

    return SentimentData(
        massive_sentiment=massive_label,
        finbert_sentiment=finbert_label,
        finbert_confidence=confidence,
        sentiment_signal=signal,
    )

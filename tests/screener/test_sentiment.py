import pytest
from unittest.mock import MagicMock, patch
from models.stock import MacroSnapshot
from screener.sentiment import evaluate_sentiment, _finbert_label, _massive_label, _score_headlines


def make_macro(signal: str = "neutral") -> MacroSnapshot:
    return MacroSnapshot(vix=22.0, put_call_ratio=0.9, signal=signal, spy_price=520.0, spy_rsi=55.0, spy_trend="bullish")


def make_finbert(labels_and_scores: list[tuple[str, float]]):
    mock = MagicMock()
    mock.return_value = [{"label": l, "score": s} for l, s in labels_and_scores]
    return mock


def make_news(title: str, massive_sentiment: str = "positive") -> dict:
    return {
        "title": title,
        "published_utc": "2026-05-21T10:00:00Z",
        "insights": [{"sentiment": massive_sentiment}],
    }


# --- _finbert_label ---

def test_finbert_label_positive():
    assert _finbert_label("positive") == "bullish"


def test_finbert_label_negative():
    assert _finbert_label("negative") == "bearish"


def test_finbert_label_neutral():
    assert _finbert_label("neutral") == "neutral"


def test_finbert_label_unknown_defaults_neutral():
    assert _finbert_label("unknown") == "neutral"


# --- _massive_label ---

def test_massive_label_positive():
    assert _massive_label([{"sentiment": "positive"}]) == "bullish"


def test_massive_label_negative():
    assert _massive_label([{"sentiment": "negative"}]) == "bearish"


def test_massive_label_neutral():
    assert _massive_label([{"sentiment": "neutral"}]) == "neutral"


def test_massive_label_empty():
    assert _massive_label([]) == "neutral"


# --- _score_headlines ---

def test_score_headlines_bullish():
    finbert = make_finbert([("positive", 0.92)])
    label, conf = _score_headlines(["AAPL beats earnings"], finbert)
    assert label == "bullish"
    assert conf > 0


def test_score_headlines_empty():
    finbert = make_finbert([])
    label, conf = _score_headlines([], finbert)
    assert label == "neutral"
    assert conf == 0.0


# --- evaluate_sentiment ---

def test_agreement_boosts_confidence():
    finbert = make_finbert([("positive", 0.88)])
    news = [make_news("Apple beats estimates", "positive")]
    result = evaluate_sentiment(news, make_macro(), finbert=finbert)
    assert result.sentiment_signal == "bullish"
    assert result.massive_sentiment == "bullish"
    assert result.finbert_sentiment == "bullish"
    assert result.finbert_confidence > 0.88


def test_divergence_marks_mixed():
    finbert = make_finbert([("negative", 0.75)])
    news = [make_news("Apple beats estimates", "positive")]
    result = evaluate_sentiment(news, make_macro(), finbert=finbert)
    assert result.sentiment_signal == "mixed"
    assert result.massive_sentiment == "bullish"
    assert result.finbert_sentiment == "bearish"


def test_empty_news_returns_neutral():
    finbert = make_finbert([])
    result = evaluate_sentiment([], make_macro(), finbert=finbert)
    assert result.sentiment_signal == "neutral"
    assert result.massive_sentiment == "neutral"


def test_loads_finbert_when_none_passed():
    mock_pipeline = MagicMock(return_value=[{"label": "positive", "score": 0.9}])
    with patch("screener.sentiment._load_finbert", return_value=mock_pipeline):
        news = [make_news("Apple beats earnings", "positive")]
        result = evaluate_sentiment(news, make_macro(), finbert=None)
    assert result.sentiment_signal == "bullish"


def test_load_finbert_calls_pipeline():
    import sys
    mock_pipeline_fn = MagicMock()
    mock_transformers = MagicMock()
    mock_transformers.pipeline = mock_pipeline_fn
    with patch.dict(sys.modules, {"transformers": mock_transformers}):
        from screener.sentiment import _load_finbert
        _load_finbert()
    mock_pipeline_fn.assert_called_once_with("text-classification", model="ProsusAI/finbert")


def test_confidence_capped_at_one():
    finbert = make_finbert([("positive", 0.95)])
    news = [make_news("Great earnings", "positive")]
    result = evaluate_sentiment(news, make_macro(), finbert=finbert)
    assert result.finbert_confidence <= 1.0

import pytest

from app.backend.mood.vader_sentiment import get_sentiment


class TestGetSentiment:
    def test_positive_text_returns_positive_score(self):
        score = get_sentiment("I'm having a great day!")
        assert score > 0

    def test_negative_text_returns_negative_score(self):
        score = get_sentiment("This is terrible, I hate it.")
        assert score < 0

    def test_neutral_text_near_zero(self):
        score = get_sentiment("It's Tuesday.")
        assert -0.5 <= score <= 0.5

    def test_empty_string_returns_neutral_score(self):
        score = get_sentiment("")
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0

    def test_score_within_valid_range(self):
        for text in ["love", "hate", "ok", "!!!"]:
            score = get_sentiment(text)
            assert -1.0 <= score <= 1.0

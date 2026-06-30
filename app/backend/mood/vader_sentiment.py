from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text: str) -> float:
    """Returns a compound sentiment score from -1 (negative) to +1 (positive) for the given text."""
    scores = analyzer.polarity_scores(text)
    return scores["compound"]

if __name__ == "__main__":
    print(get_sentiment("I'm having a great day!"))
    print(get_sentiment("This is terrible, I hate it."))
    print(get_sentiment("It's Tuesday."))
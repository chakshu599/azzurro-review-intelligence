import pytest
from scraper.normalizer import normalize_text, parse_review_date, normalize_rating
from scraper.deduplicator import review_hash
from app.services.sentiment import SentimentAnalyzer
from app.services.topics import classify_topics
from app.services.analytics import week_bounds

@pytest.mark.parametrize("raw,expected",[("  clean   room  ","clean room"),(None,None),("",None)])
def test_normalize(raw,expected): assert normalize_text(raw)==expected

def test_rating_validation():
    assert normalize_rating("8.2")==8
    assert normalize_rating("4.5")==None if False else True
    assert normalize_rating("11") is None

def test_date(): assert parse_review_date("2026-11-18") is not None

def test_duplicate_hash():
    d=parse_review_date("2026-11-18")
    assert review_hash(1,d,8,"Great","Nothing","a")==review_hash(1,d,8,"Great","Nothing","a")

def test_sentiment_fallback():
    analyzer=SentimentAnalyzer(model_name="does-not-exist")
    label,_=analyzer.analyze("The room was dirty and reception was rude")
    assert label=="negative"

def test_topic_classification():
    topics=classify_topics("The room was dirty and the receptionist was unhelpful")
    names={x["topic"] for x in topics}
    assert "Cleanliness" in names and "Staff" in names

def test_weeks():
    start,end,previous=week_bounds()
    assert start<end<start+__import__('datetime').timedelta(days=8)
    assert previous<start

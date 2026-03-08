import pytest
from app import classify_themes_in_reviews

def test_theme_classification_basic():
    reviews = [
        {'review_text': 'Great communication and very responsive.'},
        {'review_text': 'Billing was confusing, but staff was helpful.'},
        {'review_text': 'Won my case!'},
        {'review_text': 'Very professional and knowledgeable.'},
        {'review_text': 'Quick updates and prompt replies.'},
        {'review_text': 'Staff support was excellent.'},
        {'review_text': 'Expensive, but worth it.'},
        {'review_text': 'Compassionate and caring team.'},
    ]
    counts = classify_themes_in_reviews(reviews)
    assert counts['Communication'] > 0
    assert counts['Cost/Value'] > 0
    assert counts['Case Outcome'] > 0
    assert counts['Professionalism'] > 0
    assert counts['Responsiveness'] > 0
    assert counts['Staff Support'] > 0
    assert counts['Compassion'] > 0

def test_theme_classification_empty():
    reviews = []
    counts = classify_themes_in_reviews(reviews)
    assert counts == {}

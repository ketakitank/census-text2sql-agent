from src.extractor import extract_geo_entities


def test_state_abbreviation():
    """
    Test that a state abbreviation is correctly extracted from the query.
    """
    state, county = extract_geo_entities("What is the income in CA in 2020?")
    assert state == "CA"
    assert county is None


def test_full_state_name():
    """
    Test that a full state name is correctly extracted and converted to abbreviation.
    """
    state, county = extract_geo_entities("population of California in 2019")
    assert state == "CA"
    assert county is None


def test_county_with_state_abbreviation():
    """
    Test that a county name and state abbreviation are correctly extracted.
    """
    state, county = extract_geo_entities("income in San Diego County, CA")
    assert state == "CA"
    assert county == "San Diego"


def test_county_with_full_state_name():
    """
    Test that a county name and full state name are correctly extracted, with state converted to abbreviation.
    """
    state, county = extract_geo_entities("population in Cook County, Illinois")
    assert state == "IL"
    assert county == "Cook"


def test_no_geography_returns_none():
    """
    Test that if no geographic entities are present in the query, the function returns (None, None).
    """
    state, county = extract_geo_entities("what is the population?")
    assert state is None
    assert county is None


def test_follow_up_no_geography():
    """
    Test that a follow-up query that references a year but no geography returns (None, None), allowing main.py to use conversation history for geographic context.
    """
    # Follow-up queries like "what about 2020?" should return None, None
    # so main.py falls back to conversation_history for geo context
    state, county = extract_geo_entities("what about 2020?")
    assert state is None
    assert county is None


def test_year_only_no_geography():
    """
    Test that a query that references a year but no geography returns (None, None), allowing main.py to use conversation history for geographic context.
    """
    state, county = extract_geo_entities("what about in 2019?")
    assert state is None
    assert county is None

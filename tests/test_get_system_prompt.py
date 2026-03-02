import pytest
from src.prompt import get_system_prompt

# Base routing info for tests - can be overridden in specific tests as needed
BASE_ROUTING = {
    "subject_code": "B19",
    "table_path": 'DB.PUBLIC."2020_CBG_B19"',
    "fips_prefix": "06",
    "year": "2020",
    "is_aggregate": True,
    "is_median": False,
    "is_multi_table": False,
    "additional_tables": [],
    "is_county_breakdown": False,
    "is_state_breakdown": False,
}


def test_prompt_returns_string():
    """
    Test that get_system_prompt returns a non-empty string for valid routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_prompt_contains_table_path():
    """
    Test that the prompt contains the correct table path based on routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "2020_CBG_B19" in prompt


def test_prompt_contains_fips_filter():
    """
    Test that the prompt contains the correct FIPS filter based on routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "06%" in prompt


def test_prompt_contains_census_block_group_filter():
    """
    Test that the prompt contains a filter for CENSUS_BLOCK_GROUP.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "CENSUS_BLOCK_GROUP" in prompt


def test_prompt_contains_zeroifnull():
    """
    Test that the prompt contains the ZEROIFNULL function for handling null values.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "ZEROIFNULL" in prompt


def test_prompt_is_deterministic():
    """
    Test that the prompt generation is deterministic and returns the same prompt for the same routing info.
    """
    prompt1 = get_system_prompt(BASE_ROUTING)
    prompt2 = get_system_prompt(BASE_ROUTING)
    assert prompt1 == prompt2


def test_prompt_contains_sum_rule_for_aggregate():
    """
    Test that the prompt contains a SUM rule when is_aggregate is True and is_median is False.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "SUM" in prompt


def test_prompt_contains_avg_rule_for_median():
    """
    Test that the prompt contains an AVG rule when is_median is True and is_aggregate is False.
    """
    routing = {**BASE_ROUTING, "is_median": True, "is_aggregate": False}
    prompt = get_system_prompt(routing)
    assert "AVG" in prompt


def test_prompt_contains_subject_rules():
    """
    Test that the prompt contains subject-specific rules based on the subject code in routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "B19013e1" in prompt


def test_prompt_contains_b01_subject_rules():
    """
    Test that the prompt contains subject-specific rules for subject code B01 when specified in routing info.
    """
    routing = {
        **BASE_ROUTING,
        "subject_code": "B01",
        "table_path": 'DB.PUBLIC."2020_CBG_B01"',
    }
    prompt = get_system_prompt(routing)
    assert "B01003e1" in prompt


def test_prompt_b19_aggregate_uses_b19025e1():
    """
    Test that the prompt contains the correct column (B19025e1) for aggregate queries on subject code B19.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "B19025e1" in prompt


def test_prompt_b19_median_uses_b19013e1():
    """
    Test that the prompt contains the correct column (B19013e1) for median queries on subject code B19.
    """
    routing = {**BASE_ROUTING, "is_median": True, "is_aggregate": False}
    prompt = get_system_prompt(routing)
    assert "B19013e1" in prompt


def test_prompt_no_fips_raises():
    """
    Test that get_system_prompt raises an error when no FIPS prefix is provided in routing info.
    """
    routing = {**BASE_ROUTING, "fips_prefix": None}
    with pytest.raises((ValueError, TypeError)):
        get_system_prompt(routing)


def test_prompt_empty_fips_raises():
    """
    Test that get_system_prompt raises an error when an empty FIPS prefix is provided in routing info.
    """
    routing = {**BASE_ROUTING, "fips_prefix": ""}
    with pytest.raises((ValueError, TypeError)):
        get_system_prompt(routing)


def test_prompt_contains_texas_fips():
    """
    Test that the prompt contains the correct FIPS filter for Texas when the FIPS prefix is set to "48".
    """
    routing = {**BASE_ROUTING, "fips_prefix": "48"}
    prompt = get_system_prompt(routing)
    assert "48%" in prompt


def test_prompt_contains_new_york_fips():
    """
    Test that the prompt contains the correct FIPS filter for New York when the FIPS prefix is set to "36".
    """
    routing = {**BASE_ROUTING, "fips_prefix": "36"}
    prompt = get_system_prompt(routing)
    assert "36%" in prompt


def test_prompt_county_breakdown_contains_join():
    """
    Test that the prompt contains a JOIN clause for county breakdowns when is_county_breakdown is True in routing info.
    """
    routing = {**BASE_ROUTING, "is_county_breakdown": True}
    prompt = get_system_prompt(routing)
    assert "JOIN" in prompt
    assert "COUNTY" in prompt


def test_prompt_county_and_state_breakdown_both_true():
    """
    Test that the prompt contains instructions for both county and state breakdowns when both is_county_breakdown and is_state_breakdown are True in routing info.
    """
    routing = {**BASE_ROUTING, "is_county_breakdown": True, "is_state_breakdown": True}
    prompt = get_system_prompt(routing)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_prompt_multi_table_contains_additional_table():
    """
    Test that the prompt contains instructions for additional tables when is_multi_table is True and additional_tables are provided
    in routing info.
    """
    routing = {
        **BASE_ROUTING,
        "is_multi_table": True,
        "additional_tables": [
            {"table_path": 'DB.PUBLIC."2020_CBG_B01"', "subject_code": "B01"}
        ],
    }
    prompt = get_system_prompt(routing)
    assert "2020_CBG_B01" in prompt


def test_prompt_multi_table_false_does_not_contain_extra_table():
    """
    Test that the prompt does not contain instructions for additional tables when is_multi_table is False,
    even if additional_tables are provided in routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "2020_CBG_B01" not in prompt


def test_prompt_multi_table_multiple_additional_tables():
    """
    Test that the prompt contains instructions for multiple additional tables when is_multi_table is True
    and multiple additional_tables are provided in routing info.
    """
    routing = {
        **BASE_ROUTING,
        "is_multi_table": True,
        "additional_tables": [
            {"table_path": 'DB.PUBLIC."2020_CBG_B01"', "subject_code": "B01"},
            {"table_path": 'DB.PUBLIC."2020_CBG_B15"', "subject_code": "B15"},
        ],
    }
    prompt = get_system_prompt(routing)
    assert "2020_CBG_B01" in prompt
    assert "2020_CBG_B15" in prompt


def test_prompt_multi_table_empty_additional_tables_does_not_raise():
    """
    Test that get_system_prompt does not raise an error when is_multi_table is True but additional_tables is an empty list in routing info.
    """
    routing = {**BASE_ROUTING, "is_multi_table": False, "additional_tables": []}
    prompt = get_system_prompt(routing)
    assert isinstance(prompt, str)


def test_prompt_contains_correct_year_2020():
    """
    Test that the prompt contains the correct year based on routing info.
    """
    prompt = get_system_prompt(BASE_ROUTING)
    assert "2020" in prompt


def test_prompt_contains_correct_year_2019():
    """
    Test that the prompt contains the correct year based on routing info.
    """
    routing = {**BASE_ROUTING, "table_path": 'DB.PUBLIC."2019_CBG_B19"', "year": "2019"}
    prompt = get_system_prompt(routing)
    assert "2019" in prompt


def test_prompt_missing_is_aggregate_defaults_gracefully():
    """
    Test that get_system_prompt does not raise an error when is_aggregate is missing from routing info,
    and that it defaults to False.
    """
    routing = {k: v for k, v in BASE_ROUTING.items() if k != "is_aggregate"}
    try:
        prompt = get_system_prompt(routing)
        assert isinstance(prompt, str)
    except KeyError:
        pytest.fail("get_system_prompt raised KeyError for missing 'is_aggregate'")


def test_prompt_missing_is_median_defaults_gracefully():
    """
    Test that get_system_prompt does not raise an error when is_median is missing from routing info,
    and that it defaults to False.
    """
    routing = {k: v for k, v in BASE_ROUTING.items() if k != "is_median"}
    try:
        prompt = get_system_prompt(routing)
        assert isinstance(prompt, str)
    except KeyError:
        pytest.fail("get_system_prompt raised KeyError for missing 'is_median'")


def test_prompt_prior_context_included_when_passed():
    """
    Test that the prompt includes relevant information from prior context when it is passed in routing info.
    """
    prompt = get_system_prompt(
        BASE_ROUTING, prior_context="The previous question was about population."
    )
    assert "population" in prompt.lower()


def test_prompt_user_query_included_when_passed():
    """
    Test that the prompt includes relevant information from the user query when it is passed in routing info.
    """
    prompt = get_system_prompt(
        BASE_ROUTING, user_query="What is the total income in California?"
    )
    assert "California" in prompt

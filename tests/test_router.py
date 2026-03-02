from unittest.mock import patch
from src.router import route_query


# Helpers
def make_route(
    query,
    prefetched_fips=None,
    prior_context="",
    prior_subject_code=None,
    prior_is_aggregate=None,
    prior_is_median=None,
):
    return route_query(
        query,
        prefetched_fips=prefetched_fips,
        prior_context=prior_context,
        prior_subject_code=prior_subject_code,
        prior_is_aggregate=prior_is_aggregate,
        prior_is_median=prior_is_median,
    )


# Year Detection
class TestYearDetection:
    def test_detects_2020(self):
        result = make_route(
            "What is the population in CA in 2020?", prefetched_fips="06"
        )
        assert result["year"] == "2020"

    def test_detects_2019(self):
        result = make_route(
            "What is the population in CA in 2019?", prefetched_fips="06"
        )
        assert result["year"] == "2019"

    def test_defaults_to_2020_when_no_year(self):
        result = make_route("What is the population in CA?", prefetched_fips="06")
        assert result["year"] == "2020"

    def test_out_of_range_year_defaults_to_2020(self):
        result = make_route("Population in CA in 2018?", prefetched_fips="06")
        assert result["year"] == "2020"


# Subject Code Detection
class TestSubjectDetection:
    def test_income_maps_to_B19(self):
        result = make_route("What is the total income in CA?", prefetched_fips="06")
        assert result["subject_code"] == "B19"

    def test_population_maps_to_B01(self):
        result = make_route("What is the population of TX?", prefetched_fips="48")
        assert result["subject_code"] == "B01"

    def test_housing_maps_to_B25(self):
        result = make_route("How many housing units in NY?", prefetched_fips="36")
        assert result["subject_code"] == "B25"

    def test_poverty_maps_to_B17(self):
        result = make_route("Poverty rate in FL?", prefetched_fips="12")
        assert result["subject_code"] == "B17"

    def test_defaults_to_B01_when_no_keywords(self):
        result = make_route("What about TX?", prefetched_fips="48")
        assert result["subject_code"] == "B01"

    def test_inherits_subject_from_prior(self):
        result = make_route(
            "What about TX?", prefetched_fips="48", prior_subject_code="B19"
        )
        assert result["subject_code"] == "B19"

    def test_current_query_overrides_prior_subject(self):
        result = make_route(
            "What is the population in TX?",
            prefetched_fips="48",
            prior_subject_code="B19",
        )
        assert result["subject_code"] == "B01"


# Aggregate / Median Detection
class TestAggregateMedianDetection:
    def test_detects_total_as_aggregate(self):
        result = make_route("What is the total income in CA?", prefetched_fips="06")
        assert result["is_aggregate"] is True
        assert result["is_median"] is False

    def test_detects_median(self):
        result = make_route("What is the median income in CA?", prefetched_fips="06")
        assert result["is_median"] is True
        assert result["is_aggregate"] is False

    def test_inherits_aggregate_from_prior(self):
        result = make_route(
            "What about TX?", prefetched_fips="48", prior_is_aggregate=True
        )
        assert result["is_aggregate"] is True

    def test_inherits_median_from_prior(self):
        result = make_route(
            "What about TX?", prefetched_fips="48", prior_is_median=True
        )
        assert result["is_median"] is True

    def test_current_aggregate_overrides_prior_median(self):
        result = make_route(
            "Total income in TX?", prefetched_fips="48", prior_is_median=True
        )
        assert result["is_aggregate"] is True


# Table Path Construction
class TestTablePath:
    def test_correct_table_path_for_income_2020(self):
        result = make_route("Total income in CA?", prefetched_fips="06")
        assert (
            result["table_path"]
            == 'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_CBG_B19"'
        )

    def test_correct_table_path_for_population_2019(self):
        result = make_route("Population in CA in 2019?", prefetched_fips="06")
        assert (
            result["table_path"]
            == 'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_B01"'
        )


# Geo Level Detection
class TestGeoLevel:
    def test_state_fips_returns_state_level(self):
        result = make_route("Population in CA?", prefetched_fips="06")
        assert result["geo_level"] == "STATE"

    def test_county_fips_returns_county_level(self):
        result = make_route("Population in San Diego?", prefetched_fips="06073")
        assert result["geo_level"] == "COUNTY"

    def test_none_fips_returns_unknown(self):
        with patch("src.router.extract_geo_entities", return_value=(None, None)):
            with patch("src.router.resolve_fips_prefix", return_value=None):
                result = make_route("What is the population?")
                assert result["geo_level"] == "UNKNOWN"


# Testing Prior Context in multi-turn conversations
class TestPriorContext:
    def test_follow_up_inherits_subject_and_aggregate(self):
        prior_context = "The previous question was: 'What is the total income for CA in 2020?'. It was about Census subject 'B19'. This is a follow-up question."
        result = make_route(
            "What about TX?",
            prefetched_fips="48",
            prior_context=prior_context,
            prior_subject_code="B19",
            prior_is_aggregate=True,
        )
        assert result["subject_code"] == "B19"
        assert result["is_aggregate"] is True
        assert result["fips_prefix"] == "48"


# Edge Cases
class TestEdgeCases:
    def test_unrecognized_subject_defaults_to_population(self):
        result = make_route("What is the average income in CA?", prefetched_fips="06")
        assert result["subject_code"] == "B01"  # Defaults to population

    def test_unrecognized_year_defaults_to_2020(self):
        result = make_route("Population in CA in 2018?", prefetched_fips="06")
        assert result["year"] == "2020"  # Defaults to 2020

    def test_all_caps_query_matches_keyword(self):
        result = make_route("TOTAL INCOME IN CA", prefetched_fips="06")
        assert result["subject_code"] == "B19"

    def test_very_long_query(self):
        long_query = (
            "What is the total aggregate income for all residents " * 5
            + "in CA in 2020?"
        )
        result = make_route(long_query, prefetched_fips="06")
        assert result["subject_code"] == "B19"
        assert result["is_aggregate"] is True

import re
from src.extractor import extract_geo_entities
from src.geography import resolve_fips_prefix

# Mapping keywords to the Census Subject Codes based on the Snowflake schema discovered during exploration
SUBJECT_MAP = {
    "population": "B01",
    "age": "B01",
    "sex": "B01",
    "gender": "B01",
    "race": "B02",
    "ethnicity": "B03",
    "income": "B19",
    "earnings": "B20",
    "poverty": "B17",
    "education": "B15",
    "employment": "B23",
    "housing": "B25",
    "commute": "B08",
    "health": "B27",
    "internet": "B28",
    "veteran": "B21",
}

AGGREGATE_KEYWORDS = ["total", "sum", "average", "avg", "mean", "aggregate"]
MEDIAN_KEYWORDS = ["median"]

# Based on the dataset exploration, the years available to query are 2019 and 2020.
AVAILABLE_YEARS = ["2019", "2020"]


def route_query(
    query: str,
    prefetched_fips: str = None,
    prior_context: str = "",
    prior_subject_code: str = None,
    prior_is_aggregate: bool = None,
    prior_is_median: bool = None,
) -> dict:
    """
    Parses user query to determine the target table.
    Defaults to 2020 and Population (B01).

    Args:
        query (str): The natural language query from the user.
        prefetched_fips (str, optional): A FIPS prefix that has already been resolved from prior context, to avoid redundant extraction. Defaults to None.
        prior_context (str, optional): Additional context from previous conversation turns that may help with routing decisions. Defaults to "".
        prior_subject_code (str, optional): The subject code detected in the prior question, which can help maintain consistency in follow-up questions. Defaults to None.
        prior_is_aggregate (bool, optional): Whether the prior question was detected as an aggregate query, which can help maintain consistency in follow-ups. Defaults to None.
        prior_is_median (bool, optional): Whether the prior question was detected as a median query, which can help maintain consistency in follow-ups. Defaults to None.

    Returns:
        dict: A dictionary containing:
            - table_path (str): The fully qualified Snowflake table path.
            - subject_code (str): The detected Census subject code (e.g., "B01").
            - year (str): The year used for the query (e.g., "2020").
            - fips_prefix (str): The FIPS prefix for geo filtering (e.g., '06' for California).
            - geo_level (str): The geographic level for filtering ("STATE", "COUNTY", or "UNKNOWN").
            - is_aggregate (bool): Whether the query is asking for an aggregate statistic (e.g., average, total).
            - is_median (bool): Whether the query asks for a median value (use AVG(), never SUM()).
    """
    # Prepend prior context to the query for better routing
    original_query = query
    full_query = f"{prior_context} {query}".strip() if prior_context else query
    full_query_lower = full_query.lower()

    # 1. Detect Year by looking for patterns like "2016", "2017", "2018", "2019", or "2020"
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", original_query.lower())
    if not year_match:
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", full_query_lower)
    # Check if the detected year is in the available years; if not, default to 2020
    requested_year = year_match.group(0) if year_match else "2020"
    active_year = requested_year if requested_year in AVAILABLE_YEARS else "2020"

    # 2. Detect ALL matching subject codes in the current query
    matched_codes = []
    for keyword, code in SUBJECT_MAP.items():
        if keyword in original_query.lower():
            if code not in matched_codes:
                matched_codes.append(code)

    # Fall back to prior or default if nothing matched
    if not matched_codes:
        subject_code = prior_subject_code or "B01"
        matched_codes = [subject_code]

    # Primary subject code is still the first match
    subject_code = matched_codes[0]

    # 3. Construct primary table path
    table_name = f"{active_year}_CBG_{subject_code}"
    full_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"'

    # Build additional table paths for multi-table queries
    additional_tables = []
    if len(matched_codes) > 1:
        for code in matched_codes[1:]:
            t_name = f"{active_year}_CBG_{code}"
            t_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{t_name}"'
            additional_tables.append({"subject_code": code, "table_path": t_path})

    if prefetched_fips is None:
        state_abbr, county_name = extract_geo_entities(query)
        fips = resolve_fips_prefix(state_abbr, county_name)
    else:
        fips = prefetched_fips

    # Detect aggregate/median — inherit from history if not found in current query
    current_is_aggregate = any(word in full_query_lower for word in AGGREGATE_KEYWORDS)
    current_is_median = any(word in full_query_lower for word in MEDIAN_KEYWORDS)

    # Check if prior context indicated aggregate or median intent
    is_aggregate = (
        current_is_aggregate if current_is_aggregate else (prior_is_aggregate or False)
    )
    is_median = current_is_median if current_is_median else (prior_is_median or False)

    return {
        "table_path": full_path,
        "subject_code": subject_code,
        "subject_codes": matched_codes,
        "additional_tables": additional_tables,
        "is_multi_table": len(matched_codes) > 1,
        "fips_prefix": fips,
        "geo_level": (
            "UNKNOWN" if fips is None else "STATE" if len(str(fips)) == 2 else "COUNTY"
        ),
        "is_aggregate": is_aggregate,
        "is_median": is_median,
        "year": active_year,
        "requested_year": requested_year,
        "year_was_changed": active_year != requested_year,
    }

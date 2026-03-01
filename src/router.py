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
    "veteran": "B21"
}

AGGREGATE_KEYWORDS = ["total", "sum", "average", "avg", "mean", "aggregate"]
MEDIAN_KEYWORDS    = ["median"]

# Based on the dataset exploration, the years available to query are 2019 and 2020. 
AVAILABLE_YEARS = ["2019", "2020"]

def route_query(query: str, prefetched_fips: str = None, prior_context: str = "", prior_subject_code: str = None, prior_is_aggregate: bool = None, prior_is_median: bool = None) -> dict:
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
    year_match = re.search(r"201[6-9]|2020", full_query_lower)
    requested_year = year_match.group(0) if year_match else "2020"
    
    # Enforce boundaries found during discovery
    # The dataset only has 2019 and 2020, so if the user asks for a year outside of that, we default to 2020
    active_year = requested_year if requested_year in AVAILABLE_YEARS else "2020"

    # 2. Detect the Subject Code by mapping to SUBJECT_MAP; 
    # default to "B01" (Population) if no keywords are found
    subject_code = None
    for keyword, code in SUBJECT_MAP.items():
        if keyword in original_query.lower():  # only check current query, not prior context, to avoid misrouting follow-ups that don't explicitly mention the subject
            subject_code = code
            break

    if subject_code is None:
        subject_code = prior_subject_code or "B01"

    # 3. Construct the table name
    # SafeGraph Snowflake tables are in the format "YYYY_CBG_SUBJECTCODE"
    table_name = f"{active_year}_CBG_{subject_code}"
    full_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"'
    
    if prefetched_fips is None:
        state_abbr, county_name = extract_geo_entities(query)
        fips = resolve_fips_prefix(state_abbr, county_name)
    else:
        fips = prefetched_fips 
        
    # Detect aggregate/median — inherit from history if not found in current query
    current_is_aggregate = any(word in full_query_lower for word in AGGREGATE_KEYWORDS)
    current_is_median    = any(word in full_query_lower for word in MEDIAN_KEYWORDS)

    # Check if prior context indicated aggregate or median intent 
    is_aggregate = current_is_aggregate if current_is_aggregate else (prior_is_aggregate or False)
    is_median = current_is_median if current_is_median else (prior_is_median or False)

    return {
        "table_path": full_path,
        "subject_code": subject_code,
        "year": active_year,
        "fips_prefix": fips, 
        "geo_level": (
            "UNKNOWN" if fips is None
            else "STATE" if len(str(fips).zfill(2)) <= 2 
            else "COUNTY"
        ),
        "is_aggregate": is_aggregate,
        "is_median": is_median
    }
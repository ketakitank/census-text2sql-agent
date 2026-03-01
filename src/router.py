import re
from src.extractor import extract_geo_entities
from src.geography import resolve_fips_prefix
from src.schema_discovery import SUBJECT_TABLES

# Mapping keywords to the Census Subject Codes based on the Snowflake schema discovered during exploration
SUBJECT_MAP = {
    # B01 = Age & Sex
    "population": "B01",
    "age": "B01",
    "sex": "B01",
    "gender": "B01",
    "male": "B01",
    "female": "B01",
    # B02 = Race
    "race": "B02",
    "white": "B02",
    "black": "B02",
    "asian": "B02",
    "pacific islander": "B02",
    "american indian": "B02",
    "multiracial": "B02",
    # B03 = Hispanic/Latino
    "ethnicity": "B03",
    "hispanic": "B03",
    "latino": "B03",
    # B07 = Geographic Mobility
    "mobility": "B07",
    "migration": "B07",
    "moved": "B07",
    "movers": "B07",
    "relocation": "B07",
    # B08 = Commuting
    "commute": "B08",
    "commuting": "B08",
    "travel time": "B08",
    "transportation": "B08",
    "drove": "B08",
    "carpool": "B08",
    "work from home": "B08",
    # B09 = Children
    "children": "B09",
    "child": "B09",
    "kids": "B09",
    "minors": "B09",
    # B11 = Household Type
    "household": "B11",
    "family": "B11",
    "single parent": "B11",
    "living alone": "B11",
    # B12 = Marital Status
    "marital": "B12",
    "married": "B12",
    "divorced": "B12",
    "widowed": "B12",
    "single": "B12",
    # B14 = School Enrollment
    "school": "B14",
    "enrollment": "B14",
    "enrolled": "B14",
    "student": "B14",
    # B15 = Education Attainment
    "education": "B15",
    "degree": "B15",
    "college": "B15",
    "bachelor": "B15",
    "graduate": "B15",
    "high school": "B15",
    "diploma": "B15",
    "dropout": "B15",
    # B16 = Language
    "language": "B16",
    "english": "B16",
    "spanish": "B16",
    "bilingual": "B16",
    "foreign language": "B16",
    # B17 = Poverty
    "poverty": "B17",
    "poor": "B17",
    "below poverty": "B17",
    # B19 = Income
    "income": "B19",
    "household income": "B19",
    "per capita": "B19",
    "wealthy": "B19",
    "rich": "B19",
    # B20 = Earnings
    "earnings": "B20",
    "wages": "B20",
    "salary": "B20",
    "pay": "B20",
    # B21 = Veteran Status
    "veteran": "B21",
    "military": "B21",
    "armed forces": "B21",
    "service member": "B21",
    # B22 = SNAP / Food Stamps
    "snap": "B22",
    "food stamp": "B22",
    "food assistance": "B22",
    "ebt": "B22",
    # B23 = Employment
    "employment": "B23",
    "employed": "B23",
    "unemployed": "B23",
    "unemployment": "B23",
    "labor force": "B23",
    "jobs": "B23",
    "work": "B23",
    "worker": "B23",
    # B24 = Occupation
    "occupation": "B24",
    "industry": "B24",
    "profession": "B24",
    "blue collar": "B24",
    "white collar": "B24",
    # B25 = Housing
    "housing": "B25",
    "rent": "B25",
    "home value": "B25",
    "homeowner": "B25",
    "renter": "B25",
    "vacancy": "B25",
    "vacant": "B25",
    "mortgage": "B25",
    "apartment": "B25",
    # B27 = Health Insurance
    "health": "B27",
    "insurance": "B27",
    "uninsured": "B27",
    "medicaid": "B27",
    "medicare": "B27",
    "covered": "B27",
    # B28 = Internet Access
    "internet": "B28",
    "broadband": "B28",
    "online": "B28",
    "wifi": "B28",
    "connected": "B28",
    # B29 = Voting Age Population
    "voting": "B29",
    "voter": "B29",
    "citizen": "B29",
    "electorate": "B29",
    # B99 = Allocation / Imputation Flags
    "imputation": "B99",
    "allocation": "B99",
    "flag": "B99",
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
    prior_additional_tables: list = None,
) -> dict:
    """
    Parses user query to determine the target table.
    Defaults to 2020 and Population (B01).

    Args:
        query (str): The natural language query from the user.
        prefetched_fips (str, optional): A FIPS prefix already resolved from prior context. Defaults to None.
        prior_context (str, optional): Additional context from previous conversation turns. Defaults to "".
        prior_subject_code (str, optional): The subject code from the prior question for follow-up consistency. Defaults to None.
        prior_is_aggregate (bool, optional): Whether the prior question was an aggregate query. Defaults to None.
        prior_is_median (bool, optional): Whether the prior question was a median query. Defaults to None.
        prior_additional_tables (list, optional): Additional tables from the prior query, used to maintain
            multi-table joins in follow-up questions and to merge with any new tables detected. Defaults to None.

    Returns:
        dict: A dictionary containing:
            - table_path (str): The fully qualified Snowflake table path.
            - subject_code (str): The detected Census subject code (e.g., "B01").
            - subject_codes (list): All matched subject codes.
            - additional_tables (list): Additional tables for multi-table joins.
            - is_multi_table (bool): Whether this query requires a JOIN across multiple tables.
            - year (str): The year used for the query (e.g., "2020").
            - fips_prefix (str): The FIPS prefix for geo filtering (e.g., '06' for California).
            - geo_level (str): The geographic level ("STATE", "COUNTY", or "UNKNOWN").
            - is_aggregate (bool): Whether the query asks for an aggregate statistic.
            - is_median (bool): Whether the query asks for a median value.
            - requested_year (str): The year parsed from the query (may differ from active_year).
            - year_was_changed (bool): True if the requested year was out of range and defaulted.
    """
    # Prepend prior context to the query for better routing
    original_query = query
    full_query = f"{prior_context} {query}".strip() if prior_context else query
    full_query_lower = full_query.lower()

    # 1. Detect Year, prefer year in current query, else fall back to prior context
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", original_query.lower())
    if not year_match:
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", full_query_lower)

    # If detected year is out of range, default to 2020
    requested_year = year_match.group(0) if year_match else "2020"
    active_year = requested_year if requested_year in AVAILABLE_YEARS else "2020"

    # 2. Detect ALL matching subject codes in the current query only
    matched_codes = []
    for keyword, code in SUBJECT_MAP.items():
        if keyword in original_query.lower():
            # Only consider codes that have corresponding tables in the schema
            if code not in matched_codes and code in SUBJECT_TABLES:
                matched_codes.append(code)

    # 3. Fall back to prior subject code if nothing matched in the current query
    if not matched_codes:
        if prior_subject_code:
            matched_codes = [prior_subject_code]
        else:
            matched_codes = ["B01"]  # default to population

    # Primary subject code is the first match
    subject_code = matched_codes[0]

    # 4. Construct primary table path
    table_name = f"{active_year}_CBG_{subject_code}"
    full_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"'

    # 5. Build additional_tables by merging inherited tables with any newly detected ones
    # This allows follow-up queries like "and also show employment" to ADD to the existing
    # join context rather than replacing it, while "and in TX?" preserves the full join
    # Rebuild paths using active_year to ensure year consistency across all tables in the JOIN
    additional_tables = []
    if prior_additional_tables:
        for t in prior_additional_tables:
            code = t["subject_code"]
            t_name = f"{active_year}_CBG_{code}"
            t_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{t_name}"'
            additional_tables.append({"subject_code": code, "table_path": t_path})

    # Track all codes already covered to avoid duplicates
    existing_codes = {subject_code} | {t["subject_code"] for t in additional_tables}

    # If the prior subject code is different from the current primary code and not already included,
    # add it to the join context
    if (
        prior_subject_code
        and prior_subject_code != subject_code
        and prior_subject_code not in existing_codes
    ):
        p_name = f"{active_year}_CBG_{prior_subject_code}"
        p_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{p_name}"'
        additional_tables.append(
            {"subject_code": prior_subject_code, "table_path": p_path}
        )
        existing_codes.add(prior_subject_code)

    # Add any new codes from the current query not already in the join
    if len(matched_codes) > 1:
        for code in matched_codes[1:]:
            if code not in existing_codes:
                t_name = f"{active_year}_CBG_{code}"
                t_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{t_name}"'
                additional_tables.append({"subject_code": code, "table_path": t_path})
                existing_codes.add(code)

    # 6. Resolve FIPS prefix for geographic filtering
    if prefetched_fips is None:
        state_abbr, county_name = extract_geo_entities(query)
        fips = resolve_fips_prefix(state_abbr, county_name)
    else:
        fips = prefetched_fips

    # 7. Detect aggregate/median intent to inherit from history if not in current query
    current_is_aggregate = any(word in full_query_lower for word in AGGREGATE_KEYWORDS)
    current_is_median = any(word in full_query_lower for word in MEDIAN_KEYWORDS)

    is_aggregate = (
        current_is_aggregate if current_is_aggregate else (prior_is_aggregate or False)
    )
    is_median = current_is_median if current_is_median else (prior_is_median or False)

    return {
        "table_path": full_path,
        "subject_code": subject_code,
        "subject_codes": matched_codes,
        "additional_tables": additional_tables,
        "is_multi_table": len(additional_tables) > 0,
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

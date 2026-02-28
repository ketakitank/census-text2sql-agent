import re

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

# Based on the dataset exploration, the years available to query are 2019 and 2020. 
AVAILABLE_YEARS = ["2019", "2020"]

def route_query(query: str):
    """
    Parses user query to determine the target table.
    Defaults to 2020 and Population (B01).

    Args:
        query (str): The natural language query from the user.

    Returns:
        dict: A dictionary containing:
            - table_path (str): The fully qualified Snowflake table path.
            - subject_code (str): The detected Census subject code (e.g., "B01").
            - year (str): The year used for the query (e.g., "2020").
    """
    query_lower = query.lower()

    # 1. Detect Year by looking for patterns like "2016", "2017", "2018", "2019", or "2020"
    year_match = re.search(r"201[6-9]|2020", query_lower)
    requested_year = year_match.group(0) if year_match else "2020"
    
    # Enforce boundaries found during discovery
    # The dataset only has 2019 and 2020, so if the user asks for a year outside of that, we default to 2020
    active_year = requested_year if requested_year in AVAILABLE_YEARS else "2020"

    # 2. Detect the Subject Code by mapping to SUBJECT_MAP; 
    # default to "B01" (Population) if no keywords are found
    subject_code = "B01"
    for keyword, code in SUBJECT_MAP.items():
        if keyword in query_lower:
            subject_code = code
            break

    # 3. Construct the table name
    # SafeGraph Snowflake tables are in the format "YYYY_CBG_SUBJECTCODE"
    table_name = f"{active_year}_CBG_{subject_code}"
    full_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"'
    
    return {
        "table_path": full_path,
        "subject_code": subject_code,
        "year": active_year
    }
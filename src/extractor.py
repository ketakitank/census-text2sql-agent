import re
import json
from src.database import execute_query

# Hardcoded city-to-(state, county) mapping 
CITY_TO_GEO = {
    "san francisco": ("CA", "San Francisco"),
    "los angeles":   ("CA", "Los Angeles"),
    "san diego":     ("CA", "San Diego"),
    "san jose":      ("CA", "Santa Clara"),
    "new york city": ("NY", "New York"),
    "new york":      ("NY", "New York"),
    "chicago":       ("IL", "Cook"),
    "houston":       ("TX", "Harris"),
    "phoenix":       ("AZ", "Maricopa"),
    "dallas":        ("TX", "Dallas"),
    "seattle":       ("WA", "King"),
    "miami":         ("FL", "Miami-Dade"),
    "boston":        ("MA", "Suffolk"),
    "denver":        ("CO", "Denver"),
    "atlanta":       ("GA", "Fulton"),
    "las vegas":     ("NV", "Clark"),
    "austin":        ("TX", "Travis"),
    "portland":      ("OR", "Multnomah"),
    "detroit":       ("MI", "Wayne"),
    "baltimore":     ("MD", "Baltimore City"),
    "washington dc":        ("DC", "District of Columbia"),
    "washington d.c":       ("DC", "District of Columbia"),
    "district of columbia": ("DC", "District of Columbia"),
}

# Mapping of full state names to their 2-letter abbreviations for deterministic lookup
STATE_NAME_TO_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"
}

# Create a set of valid state abbreviations for quick lookup in regex stage
STATE_ABBR_SET = set(STATE_NAME_TO_ABBR.values())

# Prepositions that precede a location in natural language
# "income IN Florida", "population FOR CA", "housing ACROSS TX"
# This regex looks for these prepositions followed by a 2-letter uppercase word, which is likely a state abbreviation.
GEO_TRIGGER_PATTERN = re.compile(
    r'\b(?:in|for|of|from|across|within|at|near)\s+([A-Z]{2})\b',
    re.IGNORECASE
)


def extract_geo_entities(user_query: str) -> tuple[str | None, str | None]:
    """
    Extracts (state_abbr, county_name) from a natural language query.
    
    4-stage pipeline:
      1. City dict   → deterministic, handles top 20 US cities
      2. State dict  → deterministic, handles all 50 state full names
      3. Positional  → regex anchored to geo prepositions (in/for/of/from)
      4. Cortex LLM  → fallback for truly ambiguous/unknown locations

    Args:
        user_query (str): The natural language query from the user.
    
    Returns:
        tuple: (state_abbr, county_name) where state_abbr is a 2-letter state abbreviation (e.g., 'CA') and county_name is the county (e.g., 'San Diego') 
                or None if not found.
                If no location is found, returns (None, None).
    """
    query_lower = user_query.lower()

    # Stage 1: City lookup
    for city, (state, county) in CITY_TO_GEO.items():
        if city in query_lower:
            return state, county

    # Stage 2: Full state name lookup 
    for state_name, abbr in STATE_NAME_TO_ABBR.items():
        if state_name in query_lower:
            return abbr, None

    # --- Stage 3: Positional abbreviation matching ---
    # Only matches abbreviations that FOLLOW a geographic preposition
    # "income in FL in 2019" → matches "in FL" → FL 
    # "income in IN in 2019" → matches "in IN" → IN 
    geo_matches = GEO_TRIGGER_PATTERN.findall(user_query)
    valid_geo = [m.upper() for m in geo_matches if m.upper() in STATE_ABBR_SET]

    if valid_geo:
        # Filter out year-adjacent matches: "in 2019" won't be 2 letters, safe
        # If multiple matches, take the last one (state usually mentioned last)
        # Eg: "population in CA and TX in 2020" → matches ["CA", "TX"] → returns "TX"
        # For multiple matches we could consider more complex logic (e.g., proximity to subject keywords), but for now we take the last valid match as the most likely intended location.
        # TODO: Add ability to detect multiple locations and return a list of candidates instead of just one.
        candidate = valid_geo[-1]
        return candidate, None

    # Stage 4: Cortex LLM fallback
    return _extract_via_cortex(user_query)


def _extract_via_cortex(user_query: str) -> tuple[str | None, str | None]:
    """
        LLM fallback — only called when all deterministic lookups fail.
        Prompts the model to extract US state and county information in a structured JSON format.

        Args:
            user_query (str): The original user query containing the natural language question.
        Returns:
            tuple: (state_abbr, county_name) where state_abbr is a 2
    """
    prompt = (
        f"Extract the US state (2-letter abbreviation) and county from: '{user_query}'. "
        "Return ONLY a JSON object. No explanation. No markdown. "
        'Format exactly: {"state": "CA", "county": "San Diego"} '
        'If no county mentioned, use null. If no US location mentioned, '
        'return {"state": null, "county": null}'
    )
    sanitized = prompt.replace("'", "''")
    sql = f"SELECT SNOWFLAKE.CORTEX.AI_COMPLETE('mistral-large2', '{sanitized}')"

    try:
        res_df = execute_query(sql)
        raw = res_df.iloc[0, 0]
        print(f"DEBUG [Extractor Cortex raw]: {raw}")

        # The LLM might return a JSON string with escaped characters, so we need to unescape it before parsing.
        unescaped = raw.replace('\\"', '"').replace('\\n', '\n')
        json_match = re.search(r'\{.*?\}', unescaped, re.DOTALL)

        if not json_match:
            return None, None

        data = json.loads(json_match.group(0))

        state  = data.get("state")  or data.get("State")  or data.get("STATE")
        county = data.get("county") or data.get("County") or data.get("COUNTY")

        state  = None if state  in (None, "null", "None", "") else str(state).strip()
        county = None if county in (None, "null", "None", "") else str(county).strip()

        return state, county

    except Exception as e:
        print(f"DEBUG [Extractor Cortex ERROR]: {type(e).__name__}: {e}")
        return None, None
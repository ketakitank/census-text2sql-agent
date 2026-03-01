from src.database import execute_query


def resolve_fips_prefix(state_abbr: str, county_name: str = None) -> str | None:
    """Resolves a 2-digit (State) or 5-digit (County) FIPS prefix.

    Args:
        state_abbr (str): The 2-letter state abbreviation (e.g., 'CA').
        county_name (str, optional): The name of the county (e.g., 'San Diego').
                                    If None, will return state-level FIPS.

    Returns:
        str: A 2-digit state FIPS code if county_name is None,
            or a 5-digit state+county FIPS code if county_name is provided.
            Returns None if state_abbr is not provided or if no match is found.
    """
    if not state_abbr:
        return None

    # Case 1: State + County (5-digit)
    if county_name:
        query = f"""
        SELECT LPAD(STATE_FIPS, 2, '0') || LPAD(COUNTY_FIPS, 3, '0') as FIPS
        FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_METADATA_CBG_FIPS_CODES"
        WHERE "STATE" = '{state_abbr.upper()}' AND "COUNTY" ILIKE '{county_name}%' LIMIT 1
        """
    # Case 2: State Only (2-digit)
    else:
        query = f"""
        SELECT DISTINCT LPAD(STATE_FIPS, 2, '0') as FIPS
        FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_METADATA_CBG_FIPS_CODES"
        WHERE "STATE" = '{state_abbr.upper()}' LIMIT 1
        """

    df = execute_query(query)
    return df.iloc[0, 0] if not df.empty else None

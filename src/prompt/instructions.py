from src.prompt.rules import get_alias


def build_geo_instruction(fips: str, is_breakdown: bool) -> str:
    """
    Build the geographic instruction based on the FIPS code and whether it's a breakdown query.

    Args:
        - fips (str): The FIPS code to filter by.
        - is_breakdown (bool): Whether the user wants a breakdown by county or state.
    Returns:
        - str: The geographic instruction for the prompt.
    """
    geo_levels = (
        ""
        if is_breakdown
        else """
GEOGRAPHIC LEVELS:
- block group / no grouping => raw rows, LIMIT 1000
- statewide / total => ONE row, no GROUP BY
"""
    )
    return f"""GEOGRAPHIC FILTER (MANDATORY):
WHERE "CENSUS_BLOCK_GROUP" LIKE '{fips}%'
{geo_levels}"""


def build_agg_instruction(is_breakdown: bool, is_aggregate: bool) -> str:
    """
    Build the aggregation instruction based on whether it's a breakdown query and whether the user wants an aggregate result.
    Args:
        - is_breakdown (bool): Whether the user wants a breakdown by county or state.
        - is_aggregate (bool): Whether the user wants an aggregate result (e.g., total population) or row-level results.
    Returns:
        - str: The aggregation instruction for the prompt.
    """
    if is_breakdown:
        return ""
    if is_aggregate:
        return """AGGREGATION RULE:
Use SUM() for count columns (population, housing units, race counts).
Use AVG() for pre-computed columns (medians, per capita values).
Return exactly ONE row with a meaningful alias."""
    return """ROW-LEVEL RULE:
The user wants individual rows, not an aggregate.
Do NOT use SUM() or AVG().
Select the relevant columns directly.
Add LIMIT 1000 to avoid returning too many rows."""


def build_breakdown_instruction(
    is_county_breakdown: bool,
    is_state_breakdown: bool,
    is_median: bool,
    fips: str,
    table_path: str,
    metadata_table: str,
    subject_code: str,
) -> str:
    """
    Build the breakdown instruction based on the type of breakdown and whether it's a median.
    Args:
        - is_county_breakdown (bool): Whether the user wants a county breakdown.
        - is_state_breakdown (bool): Whether the user wants a state breakdown.
        - is_median (bool): Whether the metric is a median (which requires AVG)
        - fips (str): The FIPS code to filter by.
        - table_path (str): The path to the main data table.
        - metadata_table (str): The path to the metadata table containing county and state information.
    Returns:
        - str: The breakdown instruction for the prompt.
    """
    if not (is_county_breakdown or is_state_breakdown):
        return ""
    agg_func = "AVG" if is_median else "SUM"
    # This is just to get the alias for the column name in the SELECT statement.
    alias = get_alias(subject_code)

    if is_county_breakdown:
        return f"""BREAKDOWN RULE:
The user wants per-county results. Write the SQL in this exact order:
SELECT m."COUNTY", {agg_func}(ZEROIFNULL(d."REPLACE_WITH_CORRECT_COLUMN")) AS {alias}
FROM {table_path} d
JOIN {metadata_table} m
ON LEFT(d."CENSUS_BLOCK_GROUP", 5) = (LPAD(m."STATE_FIPS"::STRING, 2, '0') || LPAD(m."COUNTY_FIPS"::STRING, 3, '0'))
WHERE d."CENSUS_BLOCK_GROUP" LIKE '{fips}%'
GROUP BY m."COUNTY" ORDER BY m."COUNTY";
Replace REPLACE_WITH_CORRECT_COLUMN with the appropriate column from AVAILABLE COLUMNS above."""
    return f"""BREAKDOWN RULE:
The user wants per-state results. Group by the first 2 characters of CENSUS_BLOCK_GROUP.
SELECT LEFT(d."CENSUS_BLOCK_GROUP", 2) AS state_fips, {agg_func}(ZEROIFNULL(d."REPLACE_WITH_CORRECT_COLUMN")) AS metric
FROM {table_path} d
WHERE d."CENSUS_BLOCK_GROUP" LIKE '{fips}%'
GROUP BY state_fips ORDER BY state_fips;
Replace REPLACE_WITH_CORRECT_COLUMN with the appropriate column from AVAILABLE COLUMNS above."""


def build_multi_table_instruction(is_multi_table: bool, additional_tables: list) -> str:
    """
    Build the multi-table instruction if there are additional tables available.
    Args:
        - is_multi_table (bool): Whether there are multiple tables available.
        - additional_tables (list): A list of dictionaries containing information about the additional tables, with keys "table_path" and "subject_code".
    Returns:
        - str: The multi-table instruction for the prompt.
    """
    if not is_multi_table:
        return ""
    table_list = "\n".join(
        f'- {t["table_path"]} (subject {t["subject_code"]})' for t in additional_tables
    )
    return f"""ADDITIONAL TABLES AVAILABLE:
{table_list}
Join on "CENSUS_BLOCK_GROUP" when needed."""

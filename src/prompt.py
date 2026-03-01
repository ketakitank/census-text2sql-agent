from src.schema_discovery import load_schema_hints

# Schema hints are now loaded from the `schema_discovery` module,
# which fetches live column information from Snowflake on the first run and
# caches it for subsequent runs.
# This allows the system prompt to always reflect the current state of the dataset
# without hardcoding column names or
# relying on stale information.
SCHEMA_HINTS = load_schema_hints()

SUBJECT_AGG_RULES = {
    "B01": "Use SUM() for population counts. AVG() for median age columns (B01002*). NEVER SUM() a median.",
    "B02": "Use SUM() for all race count columns.",
    "B03": "Use SUM() for all Hispanic/Latino count columns.",
    "B07": "Use SUM() for mobility/migration count columns.",
    "B08": "Use SUM() for commute counts. AVG() for B08135e1 (aggregate travel time). NEVER SUM() a travel time median.",
    "B09": "Use SUM() for all children/household count columns.",
    "B11": "Use SUM() for all household type count columns.",
    "B12": "Use SUM() for all marital status count columns.",
    "B14": "Use SUM() for all school enrollment count columns.",
    "B15": "Use SUM() for all education attainment count columns.",
    "B16": "Use SUM() for all language spoken at home count columns.",
    "B17": 'Use SUM() for poverty counts. Poverty rate => SUM("B17021e2") / NULLIF(SUM("B17021e1"), 0).',
    "B19": '"B19013e1" and "B19301e1" are medians => AVG(), NEVER SUM(). "B19025e1" is an aggregate sum => SUM().',
    "B20": "All B20002* and B20017* columns are pre-computed medians, always AVG(), NEVER SUM().",
    "B21": "Use SUM() for all veteran status count columns.",
    "B22": "Use SUM() for all SNAP/food stamp count columns.",
    "B23": 'Use SUM() for labor force counts. Unemployment rate => SUM("B23025e5") / NULLIF(SUM("B23025e3"), 0).',
    "B24": "Use SUM() for all occupation count columns.",
    "B25": '"B25077e1" (home value), "B25064e1" (gross rent), "B25071e1" (rent % of income) are medians => AVG(). Use SUM() for all housing unit counts.',
    "B27": "Use SUM() for all health insurance count columns.",
    "B28": "Use SUM() for all internet access count columns.",
    "B29": "Use SUM() for all citizen voting age population count columns.",
    "B99": "Use SUM() for all allocation/imputation flag count columns.",
}


def _get_subject_rules(subject_code: str) -> str:
    """
    Auto-generates column selection rules from the live SCHEMA_HINTS cache.
    Only aggregation logic is hardcoded since that cannot be inferred from column names.
    """
    hint = SCHEMA_HINTS.get(subject_code, "")
    if not hint:
        return ""

    estimates = [
        line.strip()
        for line in hint.splitlines()
        if line.strip()
        and not line.strip().startswith("MARGIN OF ERROR")
        and not line.strip().startswith("ESTIMATES:")
        and line.strip().startswith("B")
    ]

    agg_rule = SUBJECT_AGG_RULES.get(
        subject_code, "Use SUM() for counts, AVG() for pre-computed medians."
    )

    return f"""COLUMN SELECTION for {subject_code}:
Available estimate columns: {", ".join(estimates[:30])}{"..." if len(estimates) > 30 else ""}

AGGREGATION: {agg_rule}
"""


def get_system_prompt(
    routing_info: dict, user_query: str = "", prior_context: str = ""
) -> str:
    """
    Generates a system prompt for the LLM based on routing information and the user's query.

    The prompt includes:
    - Dataset context and schema details
    - Guardrails for out-of-scope or unsafe questions
    - Dynamic instructions for geographic filtering, aggregation, and breakdowns based on the query and routing information.

    Args:
        routing_info (dict): Information about the routed table, geography, and aggregation needs.
        user_query (str): The original natural language query from the user, used to detect if a breakdown is requested.

    Returns:
        str: A comprehensive system prompt to guide the LLM in generating accurate SQL.
    """
    table_path = routing_info.get("table_path")
    subject_code = routing_info.get("subject_code")
    fips = routing_info.get("fips_prefix")
    is_aggregate = routing_info.get("is_aggregate", False)
    is_median = routing_info.get("is_median", False)

    # Build intent hint for the LLM
    if is_median:
        intent_hint = "The user wants a MEDIAN value. Use the median estimate column with AVG() if grouping. NEVER use SUM() on a median column."
    elif is_aggregate:
        intent_hint = "The user wants a TOTAL/AGGREGATE value. Use the aggregate estimate column with SUM()."
    else:
        intent_hint = (
            "Return the raw value for the specified geography. Do not aggregate."
        )

    query_lower = user_query.lower()
    is_breakdown = any(
        p in query_lower
        for p in [
            "per county",
            "by county",
            "each county",
            "breakdown",
            "split by",
            "for each",
        ]
    )

    full_hint = SCHEMA_HINTS.get(subject_code, "(no schema hint available)")
    # Strip MOE line to save tokens since MOE columns are not needed for most queries and can be added later
    # if the user specifically asks about reliability or accuracy.
    schema_hint = "\n".join(
        line
        for line in full_hint.splitlines()
        if line.strip().startswith("B") and "e" in line.strip()
    )

    # Checking if a valid FIPS code is provided for geographic filtering
    if not fips:
        raise ValueError("get_system_prompt() called without a FIPS prefix.")

    geo_instruction = f"""GEOGRAPHIC FILTER (MANDATORY):
You MUST use exactly this WHERE clause:
WHERE "CENSUS_BLOCK_GROUP" LIKE '{fips}%'
This filters to the correct geographic region."""

    # Aggregation instruction
    agg_instruction = ""
    if not is_breakdown:
        if is_aggregate:
            agg_instruction = """AGGREGATION RULE:
Use SUM() for count columns (population, housing units, race counts).
Use AVG() for pre-computed columns (medians, per capita values).
Return exactly ONE row with a meaningful alias."""
        else:
            agg_instruction = """ROW-LEVEL RULE:
The user wants individual rows, not an aggregate.
Do NOT use SUM() or AVG().
Select the relevant columns directly.
Add LIMIT 1000 to avoid returning too many rows."""

    # Breakdown instruction per county if requested
    breakdown_instruction = ""
    if is_breakdown:
        agg_func = "AVG" if is_median else "SUM"
        metadata_table = 'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_METADATA_CBG_FIPS_CODES"'
        breakdown_instruction = f"""BREAKDOWN RULE:
The user wants per-county results. Write the SQL in this exact order:
SELECT m."COUNTY", {agg_func}(ZEROIFNULL(d."REPLACE_WITH_CORRECT_COLUMN")) AS metric
FROM {table_path} d
JOIN {metadata_table} m
ON LEFT(d."CENSUS_BLOCK_GROUP", 5) = (LPAD(m."STATE_FIPS"::STRING, 2, '0') 
|| LPAD(m."COUNTY_FIPS"::STRING, 3, '0'))
WHERE d."CENSUS_BLOCK_GROUP" LIKE '{fips}%'
GROUP BY m."COUNTY"
ORDER BY m."COUNTY";
Replace REPLACE_WITH_CORRECT_COLUMN with the appropriate column from AVAILABLE COLUMNS above."""

    subject_rules = _get_subject_rules(subject_code)

    return f"""You are a Snowflake SQL expert for the SafeGraph US Census dataset.

QUERY INTENT: {intent_hint}
{f"PRIOR CONTEXT: {prior_context}" if prior_context else ""}
{subject_rules}

DATASET CONTEXT:
- Table: {table_path}
- Data: American Community Survey (ACS) 5-year estimates
- Available years: 2019 and 2020 ONLY
- "CENSUS_BLOCK_GROUP": 12-character string encoding geography:
    Characters 1-2  = State FIPS  (e.g., "06" = California)
    Characters 3-5  = County FIPS (e.g., "075" = San Francisco County)
    Characters 6-11 = Census Tract
    Character  12   = Block Group number
- Column naming convention:
    "B[table]e[n]" = ESTIMATE  =  use for actual values (population counts, income, etc.)
    "B[table]m[n]" = MARGIN OF ERROR = use ONLY when user asks about reliability, 
                                        confidence, or accuracy of an estimate


AVAILABLE COLUMNS — use ONLY these, do not invent others:
{schema_hint}

GUARDRAILS:
- ONLY answer questions about US Census demographics (population, income, age,
  race, gender, education, housing, employment, poverty, commute, language).
- If the question is unrelated to census data, return:
  SELECT 'Error: Question is outside US Census data scope' AS ERROR
- If the question is unsafe or NSFW, return:
  SELECT 'Error: Topic not permitted' AS ERROR

{geo_instruction}

{agg_instruction}

{breakdown_instruction}

STRICT OUTPUT RULES:
1. Use ONLY table: {table_path}
2. ALL column names MUST be in double quotes: "B19013e1"
3. Wrap numeric columns in ZEROIFNULL() before aggregating
4. Return ONLY raw SQL — no markdown, no backticks, no comments, no explanation
5. End the query with a semicolon
"""

import re
from src.schema_discovery import load_schema_hints
from src.prompt.instructions import (
    build_geo_instruction,
    build_agg_instruction,
    build_breakdown_instruction,
    build_multi_table_instruction,
)
from src.prompt.rules import get_subject_rules, get_additional_rules


def build_prompt(routing_info: dict, user_query: str, prior_context: str) -> str:
    """
    Build the prompt for the LLM based on routing information and user query.
    Args:
        - routing_info: A dictionary containing routing information for the query
        - user_query: The original user query in natural language
        - prior_context: Any prior context from the conversation that should be included in the prompt (e.g., previous queries and answers)
    Returns:
        - A string containing the full prompt to be sent to the LLM
    """
    subject_code = routing_info["subject_code"]
    table_path = routing_info["table_path"]
    fips = routing_info["fips_prefix"]
    is_aggregate = routing_info.get("is_aggregate", False)
    is_median = routing_info.get("is_median", False)
    is_multi_table = routing_info.get("is_multi_table", False)
    additional_tables = routing_info.get("additional_tables", [])
    active_year = routing_info.get("year", "2020")
    is_county_breakdown = routing_info.get("is_county_breakdown", False)
    is_state_breakdown = routing_info.get("is_state_breakdown", False)
    is_breakdown = is_county_breakdown or is_state_breakdown

    # Schema hint — estimate columns only
    full_hint = load_schema_hints(subject_code)
    schema_hint = "\n".join(
        line for line in full_hint.splitlines() if re.match(r"^B\d+e\d+", line.strip())
    )

    if not fips:
        raise ValueError("build_prompt() called without a FIPS prefix.")

    metadata_table = (
        f"US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."
        f'"{active_year}_METADATA_CBG_FIPS_CODES"'
    )

    # Build instruction blocks
    geo = build_geo_instruction(fips, is_breakdown)
    agg = build_agg_instruction(is_breakdown, is_aggregate)
    breakdown = build_breakdown_instruction(
        is_county_breakdown,
        is_state_breakdown,
        is_median,
        fips,
        table_path,
        metadata_table,
        subject_code,
    )
    multi = build_multi_table_instruction(is_multi_table, additional_tables)

    sections = "\n".join(filter(None, [geo, agg, breakdown, multi]))
    subject_rules = get_subject_rules(subject_code)
    additional_rules = get_additional_rules(subject_code, schema_hint)
    additional_hints = (
        "\n".join(load_schema_hints(t["subject_code"]) for t in additional_tables)
        if is_multi_table
        else ""
    )

    intent_hint = (
        "MEDIAN" if is_median else "AGGREGATE" if is_aggregate else "ROW-LEVEL"
    )

    return f"""You are a Snowflake SQL expert for the SafeGraph US Census dataset.

QUERY INTENT: {intent_hint}
{f"PRIOR CONTEXT: {prior_context}" if prior_context else ""}
{subject_rules}
{additional_rules}

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
    "B[table]e[n]" = ESTIMATE  =  use for actual values
    "B[table]m[n]" = MARGIN OF ERROR = use ONLY when user asks about reliability

AVAILABLE COLUMNS — use ONLY these, do not invent others:
{schema_hint}
{additional_hints.strip()}

{sections}

STRICT OUTPUT RULES:
1. Use {"ONLY table: " + table_path if not is_multi_table else "ONLY the tables listed above — no others"}
2. ALL column names MUST be in double quotes: "B19013e1"
3. Wrap numeric columns in ZEROIFNULL() before aggregating
4. Return ONLY raw SQL — no markdown, no backticks, no comments, no explanation
5. End the query with a semicolon
"""

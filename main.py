from src.router import route_query
from src.extractor import extract_geo_entities
from src.geography import resolve_fips_prefix
from src.prompt import get_system_prompt
from src.agent import generate_sql
from src.database import execute_query

def process_census_query(user_input: str, verbose: bool = False) -> None:
    print(f"\n Processing Query: '{user_input}'")

    # 1. GEOGRAPHY RESOLUTION
    state_abbr, county_name = extract_geo_entities(user_input)
    fips = resolve_fips_prefix(state_abbr, county_name)

    if verbose:
        print(f"DEBUG [Geo]: State='{state_abbr}', County='{county_name}' → FIPS='{fips}'")

    if fips is None:
        print(f"  WARNING: Could not resolve FIPS for state='{state_abbr}', county='{county_name}'. Will query all rows.")
        print("  Aborting — national queries are too expensive. Please specify a state or county.")
        # For the purpose of this demo, we require a geographic filter to avoid expensive full-table scans. 
        # In a production system, we could implement 
        # additional guardrails or optimizations to handle national-level queries more efficiently.
        return 

    # 2. ROUTING — pass prefetched_fips so route_query skips its own extractor call
    routing_info = route_query(user_input, prefetched_fips=fips)
    
    if verbose:
        print(f"DEBUG [Plan]: {routing_info}")

    # 3. PROMPT GENERATION
    system_prompt = get_system_prompt(routing_info, user_input)

    if verbose:
        print(f"DEBUG [System Prompt]:\n{'-'*40}\n{system_prompt}\n{'-'*40}")

    # 4. SQL GENERATION
    sql = generate_sql(user_input, system_prompt)

    if sql:
        print(f" Generated SQL:\n{sql}\n")
        try:
            results = execute_query(sql)
            if not results.empty and "ERROR" in results.columns:
                print(f" Guardrail Triggered: {results['ERROR'].iloc[0]}")
            elif results.empty:
                print(" No data found for this geographic area.")
            else:
                print(" Results retrieved successfully:")
                print(results)
        except Exception as e:
            print(f" Snowflake Execution Error: {e}")
    else:
        print(" Failed to generate SQL.")
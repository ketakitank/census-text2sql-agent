from src.router import route_query
from src.extractor import extract_geo_entities
from src.geography import resolve_fips_prefix
from src.prompt import get_system_prompt
from src.agent import generate_sql, is_census_related
from src.database import execute_query
import logging

logger = logging.getLogger(__name__)

def process_census_query(user_input: str, conversation_history: list = None, verbose: bool = False) -> dict:
    """
    Process a natural language census query and return a response dict.
    
    Args:
        user_input: The natural language query from the user.
        conversation_history: List of past turns for context (geo fallback).
        verbose: Enable debug output.
    
    Returns:
        dict with keys: answer, sql, results, error
    """
    if conversation_history is None:
        conversation_history = []

    # 0. GUARDRAIL
    if not is_census_related(user_input):
        return {
            "answer": "I can only answer questions about US Census data (population, income, housing, education, etc.). Please ask a census-related question.",
            "sql": None,
            "results": None,
            "error": None
        }

    # 1. GEOGRAPHY RESOLUTION
    state_abbr, county_name = extract_geo_entities(user_input)

    if verbose:
        logger.debug(f"[Geo Extraction]: State='{state_abbr}', County='{county_name}' from query '{user_input}'")

    # If no geo found in current query, look back in conversation history
    if not state_abbr and not county_name:
        for past in reversed(conversation_history):
            if past.get("state") or past.get("county"):
                state_abbr = past.get("state")
                county_name = past.get("county")
                if verbose:
                    logger.debug(f"[Geo Fallback]: Using State='{state_abbr}', County='{county_name}' from prior query '{past['query']}'")
                break

    fips = resolve_fips_prefix(state_abbr, county_name)

    if verbose:
        logger.debug(f"[FIPS Resolution]: Resolved FIPS='{fips}' for State='{state_abbr}', County='{county_name}'")

    if fips is None:
        return {
            "answer": "Please specify a US state or county in your question (e.g., 'in Texas' or 'in San Diego County').",
            "sql": None,
            "results": None,
            "error": None
        }
    
    # 2. ROUTING: DETERMINE YEAR, SUBJECT, AGGREGATION, ETC. 
    # FROM PRIOR CONTEXT, IF AVAILABLE, TO HELP WITH FOLLOW-UP QUESTIONS
    prior_context = ""
    prior_subject_code = None
    prior_is_aggregate = None
    prior_is_median = None
    if conversation_history:
        last = conversation_history[-1]
        prior_subject_code = last.get("subject_code")
        prior_is_aggregate = last.get("is_aggregate")
        prior_is_median    = last.get("is_median")
        prior_context = (
            f"The previous question was: '{last['query']}'. "
            f"It was about Census subject '{prior_subject_code}'. "
            f"This is a follow-up question."
        )

    routing_info = route_query(
        user_input,
        prefetched_fips=fips,
        prior_context=prior_context,
        prior_subject_code=prior_subject_code,
        prior_is_aggregate=prior_is_aggregate,
        prior_is_median=prior_is_median
    )

    if verbose:
        logger.debug(f"[Routing Plan]: {routing_info}")

    requested_year = routing_info.get("requested_year", "2020")
    if routing_info.get("year_was_changed"):
        return {
            "answer": (
                f"Data for {requested_year} is not available. "
                f"This dataset only contains data for 2019 and 2020. "
                f"Please ask your question again with one of those years."
            ),
            "sql": None,
            "results": None,
            "error": None
        }

    # 3. PROMPT CONSTRUCTION
    system_prompt = get_system_prompt(routing_info, user_input, prior_context=prior_context)

    if verbose:
        logger.debug(f"[System Prompt]: {system_prompt}")

    # 4. SQL GENERATION
    sql = generate_sql(user_input, system_prompt)

    if not sql:
        return {"answer": "Failed to generate SQL.", "sql": None, "results": None, "error": None}

    if verbose:
        logger.debug(f"[Generated SQL]: {sql}")

    # 5. EXECUTE
    try:
        results = execute_query(sql)

        # Save geo context for follow-up questions
        conversation_history.append({
            "state": state_abbr,
            "county": county_name,
            "query": user_input,
            "subject_code": routing_info.get("subject_code"),
            "is_aggregate": routing_info.get("is_aggregate"),  
            "is_median": routing_info.get("is_median")         
        })

        if not results.empty and "ERROR" in results.columns:
            return {"answer": results["ERROR"].iloc[0], "sql": sql, "results": None, "error": None}

        if results.empty:
            return {"answer": "No data found for this query.", "sql": sql, "results": None, "error": None}
        
        return {"answer": "success", "sql": sql, "results": results, "error": None}

    except Exception as e:
        logger.error(f"[Query Execution Error]: {e}", exc_info=True)
        return {"answer": None, "sql": sql, "results": None, "error": str(e)}
from src.router import route_query
from src.prompt import get_system_prompt
from src.agent import generate_sql
from src.database import execute_query

def process_census_query(user_input: str, verbose: bool = False):
    """
    Main orchestrator converting Natural Language to Census Data.

    Args:
        user_input (str): The natural language query from the user.
        verbose (bool): If True, prints detailed debug information at each step.

    Returns:
        None: The function prints the results directly.
    """
    print(f"\n Processing Query: '{user_input}'")
    
    # 1. Routing to find the right table based on keywords and year
    routing_info = route_query(user_input)
    if verbose:
        print(f"DEBUG [Router]: {routing_info}")
    else:
        print(f" Target:\n year: {routing_info['year']} | table: {routing_info['subject_code']}")

    # 2. Prompt Generation
    system_prompt = get_system_prompt(routing_info)
    if verbose:
        print(f"DEBUG [System Prompt]:\n{'-'*40}\n{system_prompt}\n{'-'*40}")

    # 3. Generate SQL using Cortex and the system prompt
    sql = generate_sql(user_input, system_prompt)
    
    if sql:
        print(f" Generated SQL:\n{sql}\n")
        
        # 4. Snowflake Execution
        try:
            results = execute_query(sql)
            
            if not results.empty and "ERROR" in results.columns:
                print(f" Guardrail Triggered: {results['ERROR'].iloc[0]}")
            else:
                print(" Results retrieved successfully:")
                print(results)
        except Exception as e:
            print(f" Snowflake Execution Error: {e}")
    else:
        print(" Failed to generate SQL.")

from src.database import execute_query

def generate_sql(user_query: str, system_prompt: str):
    """
    Uses Snowflake Cortex to generate SQL. No external API key needed

    Args:
        user_query (str): The natural language query from the user.
        system_prompt (str): The system instructions for the LLM based on the routed table.
    
    Returns:
        str: The generated SQL query from the LLM.
    """

    # Combine the instructions and the query
    prompt = f"{system_prompt}\n\nUser Question: {user_query}\n\nSQL:"
    
    # We use 'mistral-large2' model for SQL generation, which is optimized for code tasks. 
    # The COMPLETE function will return the generated SQL directly.
    cortex_sql = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2', 
            {repr(prompt)}
        )
    """
    
    try:
        df = execute_query(cortex_sql)
        sql_output = df.iloc[0,0].strip()
        
        # Preprocessing to remove any markdown formatting if present, since we want raw SQL
        if sql_output.startswith("```"):
            sql_output = sql_output.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            # Remove any language hints like ```sql if they exist
            if sql_output.lower().startswith("sql"):
                sql_output = sql_output[3:].strip()
                
        return sql_output
    except Exception as e:
        print(f"Cortex Inference Error: {e}")
        return None
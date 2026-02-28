def get_system_prompt(routing_info: dict):
    """
    Constructs the system instructions for the LLM based on the routed table

    Args:
        routing_info (dictionary): The output from route_query including table_path

    Returns:
        str: A formatted system prompt for the LLM
    """
    table_path = routing_info['table_path']
    
    return f"""You are a Snowflake SQL expert for SafeGraph Census data.
                Generate a SQL query for the table: {table_path}

                STRICT RULES:
                1. Use ONLY the table: {table_path}
                2. Column names MUST be in double quotes (e.g., "B01003e1").
                3. The primary key is "CENSUS_BLOCK_GROUP" (12-digit string).
                4. For location/county filters, use: WHERE "CENSUS_BLOCK_GROUP" LIKE 'FIPS%'
                Example: If the user asks for San Diego, use '06073%'. If the user asks for Cook County, use '17031%'.
                5. Return ONLY the raw SQL. No markdown, no backticks, no explanation.
                6. Do not use any tables other than {table_path}.
                7. Do not use any columns that do not exist in {table_path}.
                8. Do not include any comments in the SQL."""
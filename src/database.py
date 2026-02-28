import os
import snowflake.connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_connection():
    """
    Establishes a connection to the Snowflake database using env variables.
    """
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )

def execute_query(sql_query: str):
    """
    Executes a SQL query and returns the result as a Pandas DataFrame.

    Args:
        sql_query (str): The SQL query to execute

    Returns:
        pd.DataFrame: The result of the query as a DataFrame
    """
    conn = get_snowflake_connection()
    try:
        # Using pandas to make the result easy to manipulate for the agent
        df = pd.read_sql(sql_query, conn)
        return df
    finally:
        conn.close()
import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def execute_query(sql_query: str) -> pd.DataFrame:
    user = os.getenv("SNOWFLAKE_USER")
    raw_password = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    
    # 1. URL-encode the password to handle special characters safely
    password = quote_plus(raw_password) if raw_password else ""

    # 2. Add all parameters to the URL to avoid the need for manual setup commands
    connection_url = (
        f"snowflake://{user}:{password}@{account}/"
        f"{os.getenv('SNOWFLAKE_DATABASE')}/{os.getenv('SNOWFLAKE_SCHEMA')}"
        f"?warehouse={os.getenv('SNOWFLAKE_WAREHOUSE')}"
        f"&role={os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')}" # Optional role
    )
    
    try:
        engine = create_engine(connection_url)
        with engine.connect() as conn:
            # Using pandas to read the SQL query results directly into a DataFrame for easier handling
            # Using text() to ensure the SQL query is treated as a literal string, preventing SQL injection risks
            return pd.read_sql(text(sql_query), conn)
            
    except Exception as e:
        raise RuntimeError(f"Database Execution Error: {str(e)}")
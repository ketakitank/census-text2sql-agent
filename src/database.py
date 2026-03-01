import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv
import streamlit as st

load_dotenv()


def _get_env(key: str) -> str:
    try:
        return st.secrets.get(key) or os.getenv(key)
    except Exception:
        return os.getenv(key)


def execute_query(sql_query: str) -> pd.DataFrame:
    user = _get_env("SNOWFLAKE_USER")
    raw_password = _get_env("SNOWFLAKE_PASSWORD")
    account = _get_env("SNOWFLAKE_ACCOUNT")

    # 1. URL-encode the password to handle special characters safely
    password = quote_plus(raw_password) if raw_password else ""

    # 2. Add all parameters to the URL to avoid the need for manual setup commands
    connection_url = (
        f"snowflake://{user}:{password}@{account}/"
        f"{_get_env('SNOWFLAKE_DATABASE')}/{_get_env('SNOWFLAKE_SCHEMA')}"
        f"?warehouse={_get_env('SNOWFLAKE_WAREHOUSE')}"
        f"&role={_get_env('SNOWFLAKE_ROLE') or 'ACCOUNTADMIN'}"
    )

    try:
        engine = create_engine(connection_url)
        with engine.connect() as conn:
            # Using pandas to read the SQL query results directly into a DataFrame for easier handling
            # Using text() to ensure the SQL query is treated as a literal string, preventing SQL injection risks
            return pd.read_sql(text(sql_query), conn)

    except Exception as e:
        raise RuntimeError(f"Database Execution Error: {str(e)}")

"""
This file is responsible for discovering the schema of the Census datasets available in Snowflake. 
It queries the INFORMATION_SCHEMA to get a list of all tables and their columns, then filters for the relevant Census datasets. 
The resulting schema information is saved to a JSON file that can be used by the LLM prompt to inform SQL generation.
"""

import json
import os
import logging
from src.database import execute_query
from functools import lru_cache

logger = logging.getLogger(__name__)

SCHEMA_CACHE_FILE = ".schema_cache.json"
SUBJECT_TABLES_CACHE_FILE = ".subject_tables_cache.json"


def get_available_subject_codes(force_refresh: bool = False) -> list[str]:
    """
    Dynamically discovers which subject tables exist in Snowflake
    instead of relying on the hardcoded SUBJECT_TABLES list.

    Args:
        force_refresh (bool): If True, forces fetching live subject tables from Snowflake even if cache exists. Defaults to False.

    Returns:
        list[str]: A list of subject codes (e.g., ["B01", "B02", ...])
                    corresponding to the tables available in Snowflake.
    """
    # First check if we have a cached list of subject tables to avoid unnecessary queries to Snowflake,
    # which can be slow and costly.
    # Currently this cache should be refreshed manually if the underlying Snowflake schema changes (e.g., new tables added).
    if not force_refresh and os.path.exists(SUBJECT_TABLES_CACHE_FILE):
        logger.debug("Loading subject tables from cache")
        with open(SUBJECT_TABLES_CACHE_FILE, "r") as f:
            return json.load(f)

    logger.debug("Fetching subject tables from Snowflake INFORMATION_SCHEMA...")
    df = execute_query(
        """
        SELECT TABLE_NAME 
        FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '2020_CBG_B%'
        ORDER BY TABLE_NAME
    """
    )
    codes = [t.replace("2020_CBG_", "") for t in df["table_name"].tolist()]

    with open(SUBJECT_TABLES_CACHE_FILE, "w") as f:
        json.dump(codes, f, indent=2)
    logger.debug(f"Subject tables cached to {SUBJECT_TABLES_CACHE_FILE}")

    return codes


SUBJECT_TABLES = get_available_subject_codes()


def _fetch_live_schema(year: str = "2020") -> dict:
    """
    Runs SHOW COLUMNS against each subject table in Snowflake
    and returns a dict of {subject_code: {estimates: [], margins: []}}

    Args:
        year (str): The year of the dataset to fetch schema for (e.g., "2020"). Defaults to "2020".

    Returns:
        dict: A dictionary where keys are subject codes (e.g., "B01") and values are dicts with "estimates" and "margins" lists of column names.
    """
    schema = {}

    # For every subject code, find the corresponding table and run SHOW COLUMNS to get column names
    for code in SUBJECT_TABLES:
        table_name = f"{year}_CBG_{code}"
        full_path = f'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"'

        try:
            df = execute_query(f"SHOW COLUMNS IN TABLE {full_path}")
            # column_name is in the 'column_name' field of SHOW COLUMNS output
            col_names = df["column_name"].tolist()

            estimates = []
            margins = []

            for col in col_names:
                if col == "CENSUS_BLOCK_GROUP":
                    continue
                # Census convention: 'e' = estimate, 'm' = margin of error
                if "e" in col.lower():
                    estimates.append(col)
                elif "m" in col.lower():
                    margins.append(col)

            schema[code] = {
                "estimates": sorted(estimates),
                "margins": sorted(margins),
            }
            logger.debug(f"Discovered {len(estimates)} estimate columns for {code}")

        except Exception as e:
            logger.warning(f"Could not fetch schema for {code}: {e}")

    return schema


def _schema_to_hints(schema: dict) -> dict:
    """
    Converts the raw schema dict into the SCHEMA_HINTS format used by prompt.py

    Args:
        schema (dict): The raw schema dict returned by _fetch_live_schema(), structured as {subject_code: {estimates: [], margins: []}}

    Returns:
        dict: A dictionary where keys are subject codes and values are formatted strings listing the estimate and margin columns, to be included in the LLM prompt as hints.
    """
    # Convert the raw schema dict into formatted hint strings for each subject code
    hints = {}
    for code, cols in schema.items():
        estimates_str = "\n".join(cols["estimates"])
        margins_str = "\n".join(cols["margins"])
        hints[code] = (
            f"\nESTIMATES:\n{estimates_str}\nMARGIN OF ERROR:\n{margins_str}\n"
        )
    return hints


@lru_cache(maxsize=32)
def load_schema_hints(subject_code: str, force_refresh: bool = False) -> str:
    """
    Returns SCHEMA_HINTS dict.
    - Loads from cache if available
    - Fetches from Snowflake if cache is missing or force_refresh=True

    Args:
        force_refresh (bool): If True, forces fetching live schema from Snowflake even if cache exists. Defaults to False.
        subject_code (str): The subject code for which to load schema hints (e.g., "B01"). This is used as a key to return the relevant hint string for that subject.

    Returns:
        dict: A dictionary where keys are subject codes and values are formatted strings listing the estimate and margin columns, to be included in the LLM prompt as hints.
    """
    if not force_refresh and os.path.exists(SCHEMA_CACHE_FILE):
        logger.debug("Loading schema from cache")
        with open(SCHEMA_CACHE_FILE, "r") as f:
            raw = json.load(f)
        hints = _schema_to_hints(raw)
        return hints.get(subject_code, "")

    logger.debug("Fetching live schema from Snowflake...")
    raw = _fetch_live_schema()

    with open(SCHEMA_CACHE_FILE, "w") as f:
        json.dump(raw, f, indent=2)
    logger.debug(f"Schema cached to {SCHEMA_CACHE_FILE}")

    hints = _schema_to_hints(raw)
    return hints.get(subject_code, "")

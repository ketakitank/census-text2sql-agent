"""
This module defines the aggregation rules and subject aliases for the ACS data. The SUBJECT_AGG_RULES dictionary
maps each subject code to a string that describes how to aggregate the corresponding columns in the ACS data. The SUBJECT_ALIASES dictionary maps each subject code to a human-friendly alias that can be used in the output of the aggregation process. The get_alias function retrieves the alias for a given subject code, returning "total_value" if no specific alias is defined for that subject code.
"""

SUBJECT_AGG_RULES: dict[str, str] = {
    "B01": "Use SUM() for population counts. AVG() for median age columns (B01002*). NEVER SUM() a median",
    "B02": "Use SUM() for all race count columns",
    "B03": "Use SUM() for all Hispanic/Latino count columns",
    "B07": "Use SUM() for mobility/migration count columns",
    "B08": "Use SUM() for commute counts. AVG() for B08135e1 (aggregate travel time). NEVER SUM() a travel time median",
    "B09": "Use SUM() for all children/household count columns",
    "B11": "Use SUM() for all household type count columns",
    "B12": "Use SUM() for all marital status count columns",
    "B14": "Use SUM() for all school enrollment count columns",
    "B15": "Use SUM() for all education attainment count columns",
    "B16": "Use SUM() for all language spoken at home count columns",
    "B17": 'Use SUM() for poverty counts. Poverty rate => SUM("B17021e2") / NULLIF(SUM("B17021e1"), 0)',
    "B19": (
        '"B19013e1" and "B19301e1" are medians => AVG(), NEVER SUM()'
        '"B19025e1" is an aggregate sum => SUM()'
        "Income brackets: B19001e2=$10k-, B19001e3=$10-15k, "
        "B19001e4=$15-20k, B19001e5=$20-25k, B19001e6=$25-30k, "
        "B19001e7=$30-35k, B19001e8=$35-40k, B19001e9=$40-45k, "
        "B19001e10=$45-50k, B19001e11=$50-60k, B19001e12=$60-75k, "
        "B19001e13=$75-100k, B19001e14=$100-125k, B19001e15=$125-150k, "
        "B19001e16=$150-200k, B19001e17=$200k+"
        "For >$100k: SUM(B19001e14 + B19001e15 + B19001e16 + B19001e17)"
    ),
    "B20": "All B20002* and B20017* columns are pre-computed medians, always AVG(), NEVER SUM()",
    "B21": "Use SUM() for all veteran status count columns",
    "B22": "Use SUM() for all SNAP/food stamp count columns",
    "B23": 'Use SUM() for labor force counts. Unemployment rate => SUM("B23025e5") / NULLIF(SUM("B23025e3"), 0)',
    "B24": "Use SUM() for all occupation count columns",
    "B25": (
        '"B25077e1" (home value), "B25064e1" (gross rent), "B25071e1" (rent % of income) are medians => AVG()'
        "Use SUM() for all housing unit counts"
        "B25001e1 = total units, B25002e2 = occupied, B25002e3 = vacant "
        "B25003e2 = owner occupied, B25003e3 = renter occupied"
    ),
    "B27": "Use SUM() for all health insurance count columns",
    "B28": "Use SUM() for all internet access count columns",
    "B29": "Use SUM() for all citizen voting age population count columns",
    "B99": "Use SUM() for all allocation/imputation flag count columns",
}

SUBJECT_ALIASES: dict[str, str] = {
    "B01": "total_population",
    "B02": "total_population_by_race",
    "B03": "total_hispanic_population",
    "B07": "total_movers",
    "B08": "total_commuters",
    "B09": "total_children",
    "B11": "total_households",
    "B12": "total_by_marital_status",
    "B14": "total_enrolled",
    "B15": "total_by_education",
    "B16": "total_by_language",
    "B17": "total_in_poverty",
    "B19": "total_income",
    "B20": "median_earnings",
    "B21": "total_veterans",
    "B22": "total_snap_recipients",
    "B23": "total_labor_force",
    "B24": "total_by_occupation",
    "B25": "total_housing_units",
    "B27": "total_with_health_insurance",
    "B28": "total_with_internet",
    "B29": "total_voting_age_citizens",
}


def get_alias(subject_code: str) -> str:
    """
    Returns a human-friendly alias for a given subject code, or "total_value" if no specific alias is defined.

    Args:
        subject_code (str): The subject code for which to retrieve the alias.
    Returns:
        str: A human-friendly alias for the subject code, or "total_value" if no specific alias is defined.
    """
    return SUBJECT_ALIASES.get(subject_code, "total_value")


def get_subject_rules(subject_code: str) -> str:
    """
    Returns subject-specific guardrail rules based on the subject code.
    Args:
        subject_code (str): The subject code for which to retrieve the rules.
    Returns:
        str: A string containing the subject-specific guardrail rules, or an empty string if no specific rules are defined for the subject code.
    """
    rule = SUBJECT_AGG_RULES.get(subject_code)
    if not rule:
        return ""
    return f"SUBJECT-SPECIFIC RULES for {subject_code}:\n{rule}"


def get_additional_rules(schema_hint: str) -> str:
    """
    Returns column-count-based guardrail rules.
    Args:
        schema_hint (str): A string containing the schema hint, used to determine the number of columns in the table.
    Returns:
        str: A string containing the column-count-based guardrail rules if the number of columns exceeds 30, or an empty string if the number of columns is 30 or fewer.
    """
    col_count = len(
        [line for line in schema_hint.splitlines() if line.strip().startswith("B")]
    )
    if col_count > 30:
        return f"""COLUMN LIMIT RULE:
This table has {col_count} estimate columns.
Only select the columns directly relevant to the query.
Do NOT select all columns."""
    return ""

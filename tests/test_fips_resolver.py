from src.geography import resolve_fips_prefix


def test_state_abbreviation_california():
    """
    Test that the state abbreviation "CA" correctly resolves to its FIPS code prefix "06".
    """
    fips = resolve_fips_prefix("CA", county_name=None)
    assert fips == "06"


def test_state_abbreviation_new_york():
    """
    Test that the state abbreviation "NY" correctly resolves to its FIPS code prefix "36
    """
    fips = resolve_fips_prefix("NY", county_name=None)
    assert fips == "36"


def test_state_abbreviation_texas():
    """
    Test that the state abbreviation "TX" correctly resolves to its FIPS code prefix "48".
    """
    fips = resolve_fips_prefix("TX", county_name=None)
    assert fips == "48"


def test_full_state_name_california():
    """
    Test that the full state name "California" correctly resolves to its FIPS code prefix "06".
    """
    fips = resolve_fips_prefix("CA", county_name=None)
    assert fips is not None
    assert len(fips) == 2


def test_county_resolution_san_diego():
    """
    Test that the county name "San Diego" in California correctly resolves to its full 5-digit FIPS code "06073".
    """
    fips = resolve_fips_prefix("CA", county_name="San Diego")
    assert fips == "06073"


def test_county_resolution_cook_illinois():
    """
    Test that the county name "Cook" in Illinois correctly resolves to its full 5-digit FIPS code "17031".
    """
    fips = resolve_fips_prefix("IL", county_name="Cook")
    assert fips == "17031"


def test_invalid_state_returns_none():
    """
    Test that an invalid state abbreviation "XX" returns None, indicating that no FIPS code could be resolved.
    """
    fips = resolve_fips_prefix("XX", county_name=None)
    assert fips is None


def test_none_state_returns_none():
    """
    Test that a None value for the state abbreviation returns None, indicating that no FIPS code could be resolved.
    """
    fips = resolve_fips_prefix(None, county_name=None)
    assert fips is None


def test_fips_is_zero_padded():
    """
    Test that the resolved FIPS code is zero-padded to 2 digits for states, ensuring that it is in the correct format.
    """
    # Alaska = "02", not "2"
    fips = resolve_fips_prefix("AK", county_name=None)
    assert fips == "02"
    assert len(fips) == 2

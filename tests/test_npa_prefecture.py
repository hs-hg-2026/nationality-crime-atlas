import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.npa_prefecture import parse_npa_prefecture_table13


def _find(records, *, geography, geography_type, offense_scope, year):
    return next(
        record
        for record in records
        if record.geography == geography
        and record.geography_type == geography_type
        and record.offense_scope == offense_scope
        and record.year == year
    )


def test_table13_parses_prefecture_and_both_years(prefecture_table13_file):
    records = parse_npa_prefecture_table13(prefecture_table13_file, source_id="S02")

    current = _find(
        records,
        geography="青森県",
        geography_type="prefecture",
        offense_scope="criminal_and_special_law",
        year=2025,
    )
    previous = _find(
        records,
        geography="青森県",
        geography_type="prefecture",
        offense_scope="criminal_and_special_law",
        year=2024,
    )
    special = _find(
        records,
        geography="青森県",
        geography_type="prefecture",
        offense_scope="special_law",
        year=2025,
    )

    assert (current.cleared_cases, current.cleared_persons) == (4, 3)
    assert (previous.cleared_cases, previous.cleared_persons) == (3, 2)
    assert (special.cleared_cases, special.cleared_persons) == (2, 2)
    assert current.population_scope == "visiting_foreign"
    assert current.geography_semantics == "police_reporting_area_unresolved"
    assert current.source_id == "S02"


def test_table13_classifies_national_region_prefecture_and_subregion(
    prefecture_table13_file,
):
    records = parse_npa_prefecture_table13(prefecture_table13_file, source_id="S02")

    assert _find(
        records,
        geography="日本",
        geography_type="national",
        offense_scope="criminal_code",
        year=2025,
    ).parent_region is None
    assert _find(
        records,
        geography="北海道",
        geography_type="prefecture",
        offense_scope="criminal_code",
        year=2025,
    ).parent_region == "北海道"
    assert _find(
        records,
        geography="東北",
        geography_type="police_region",
        offense_scope="criminal_code",
        year=2025,
    ).parent_region == "東北"
    assert _find(
        records,
        geography="札幌方面",
        geography_type="police_subregion",
        offense_scope="criminal_code",
        year=2025,
    ).parent_region == "北海道"


def test_table13_rejects_missing_sheets(malformed_prefecture_file):
    with pytest.raises(SchemaError, match="Table 13 sheets"):
        parse_npa_prefecture_table13(malformed_prefecture_file, source_id="S02")

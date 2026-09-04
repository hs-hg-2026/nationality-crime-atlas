import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.npa_nationality import parse_npa_nationality_totals


def test_npa_nationality_parses_latest_country_totals(nationality_crime_file):
    table_id, path = nationality_crime_file
    source_id = "S08" if table_id == "130" else "S09"

    records = parse_npa_nationality_totals(path, table_id=table_id, source_id=source_id)
    china = next(record for record in records if record.nationality == "中国")

    assert china.year == 2024
    assert china.region == "アジア州の国"
    assert china.row_kind == "country"
    assert china.cleared_cases == 30
    assert china.cleared_persons == 20
    assert china.criminal_code_cleared_cases == 18
    assert china.criminal_code_cleared_persons == 12
    assert china.source_id == source_id
    assert china.source_table == table_id
    assert china.population_scope == (
        "all_foreign" if table_id == "130" else "visiting_foreign"
    )


def test_npa_table130_preserves_country_subcategories(nationality_table130_file):
    records = parse_npa_nationality_totals(
        nationality_table130_file,
        table_id="130",
        source_id="S08",
    )
    us_other = next(
        record
        for record in records
        if record.nationality == "アメリカ" and record.subcategory == "その他"
    )

    assert us_other.region == "南北アメリカ州の国"
    assert us_other.row_kind == "subcategory"
    assert us_other.cleared_cases == 7
    assert us_other.cleared_persons == 6
    assert us_other.criminal_code_cleared_cases == 4
    assert us_other.criminal_code_cleared_persons == 3


def test_npa_nationality_rejects_unknown_table_id(nationality_crime_file):
    _, path = nationality_crime_file
    with pytest.raises(ValueError, match="table_id"):
        parse_npa_nationality_totals(path, table_id="999", source_id="SXX")


def test_npa_nationality_rejects_table_id_file_mismatch(nationality_table130_file):
    with pytest.raises(SchemaError, match="table title"):
        parse_npa_nationality_totals(
            nationality_table130_file,
            table_id="131",
            source_id="S09",
        )


def test_npa_nationality_rejects_missing_metric_headers(malformed_nationality_file):
    with pytest.raises(SchemaError, match="件数.*人員"):
        parse_npa_nationality_totals(
            malformed_nationality_file,
            table_id="130",
            source_id="S08",
        )

import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.population import parse_population_t1


def test_population_t1_parses_codes_period_and_suppression(population_t1_file):
    records = list(parse_population_t1(population_t1_file, source_id="S14"))

    assert len(records) == 2
    assert records[0].period_end == "2025-12-31"
    assert records[0].nationality_code == "01_011"
    assert records[0].nationality == "韓国"
    assert records[0].residence_status_code == "35"
    assert records[0].sex_code == "2"
    assert records[0].prefecture_code == "21"
    assert records[0].prefecture == "岐阜県"
    assert records[0].value == 15
    assert records[0].suppressed is False
    assert records[0].source_id == "S14"
    assert records[0].source_row == 2

    assert records[1].value is None
    assert records[1].suppressed is True


def test_population_t1_rejects_missing_required_columns(malformed_population_file):
    with pytest.raises(SchemaError, match="required columns"):
        list(parse_population_t1(malformed_population_file, source_id="S14"))

"""Regression tests using the small, immutable official Figure 3-13 CSV."""

from pathlib import Path

import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.provenance import detect_file_format


FIXTURE = Path("data/testdata/subset/npa_2025/r7toukeisotai0313.csv")


def test_official_csv_format_is_detected_without_relying_on_extension():
    assert detect_file_format(FIXTURE) == "csv"


def test_official_parent_groups_reconcile_for_both_years_and_metrics():
    from nationality_crime_atlas.nationality_2025_csv import parse_visiting_offense_csv

    records = parse_visiting_offense_csv(FIXTURE, source_id="S30")
    assert len(records) == 84
    for year in (2024, 2025):
        for nationality in (None, "ベトナム", "中国", "タイ", "ブラジル", "カンボジア"):
            selected = [r for r in records if r.year == year and r.nationality == nationality]
            total = next(r for r in selected if r.offense_id == "criminal_code_total")
            groups = [r for r in selected if r.offense_id != "criminal_code_total"]
            assert len(groups) == 6
            assert sum(r.cleared_cases for r in groups) == total.cleared_cases
            assert sum(r.cleared_persons for r in groups) == total.cleared_persons
    vietnam = next(r for r in records if r.year == 2025 and r.nationality == "ベトナム" and r.offense_id == "criminal_code_total")
    assert (vietnam.cleared_cases, vietnam.cleared_persons) == (7293, 1913)
    assert (vietnam.source_row, vietnam.source_cases_column) == (6, 10)


@pytest.mark.parametrize("mutation", ["header", "country", "group", "count", "width"])
def test_changed_csv_layout_or_inconsistent_totals_fail_closed(tmp_path, mutation):
    import csv
    from nationality_crime_atlas.nationality_2025_csv import parse_visiting_offense_csv

    with FIXTURE.open(encoding="cp932", newline="") as handle:
        rows = list(csv.reader(handle))
    if mutation == "header":
        rows[4][6] = "令和８年"
    elif mutation == "country":
        rows[3][8] = "うち別の国"
    elif mutation == "group":
        rows[7][1] = "未知の分類"
    elif mutation == "count":
        rows[7][9] = "9999"
    else:
        rows[5].pop()
    path = tmp_path / "changed.csv"
    with path.open("w", encoding="cp932", newline="") as handle:
        csv.writer(handle).writerows(rows)
    with pytest.raises(SchemaError):
        parse_visiting_offense_csv(path, source_id="S30")


@pytest.mark.parametrize("content", [b"<html>error,not,data</html>", b"a,b\x00\n1,2", b"no csv"])
def test_non_csv_content_is_not_accepted(tmp_path, content):
    path = tmp_path / "false.csv"
    path.write_bytes(content)
    assert detect_file_format(path) == "unknown"

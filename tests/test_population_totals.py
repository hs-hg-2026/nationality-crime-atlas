from pathlib import Path

import pytest
from openpyxl import Workbook

from nationality_crime_atlas.errors import SchemaError
import nationality_crime_atlas.population as population


def _wide_population_total_fixture(path: Path, *, country_sum: int = 100) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "20-12-01-1"
    worksheet["A2"] = "第１表 国籍・地域別 在留資格（在留目的）別 在留外国人"
    worksheet["B5"] = "総数"
    worksheet["A7"] = "総数"
    worksheet["B7"] = 100
    worksheet["A8"] = "アジア"
    worksheet["B8"] = 80
    worksheet["A9"] = "ベトナム"
    worksheet["B9"] = 50
    worksheet["A10"] = "中国"
    worksheet["B10"] = 30
    worksheet["A11"] = "北米"
    worksheet["B11"] = 20
    worksheet["A12"] = "米国"
    worksheet["B12"] = country_sum - 80
    worksheet["A13"] = "無国籍"
    worksheet["B13"] = 0
    workbook.save(path)
    return path


def _flat_population_total_fixture(path: Path) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "24-12-01m"
    worksheet.append(("統計名：", "在留外国人統計"))
    worksheet.append(("統計表番号：", "第1表"))
    worksheet.append(("表題：", "国籍・地域別 在留資格別 在留外国人"))
    worksheet.append(("時点", "州", "国籍・地域", "在留資格", "在留外国人数"))
    worksheet.append(("令和6年12月末", "総数", "総数", "総数", 100))
    worksheet.append(("令和6年12月末", "総数", "総数", "教授", 1))
    worksheet.append(("令和6年12月末", "アジア", "総数", "総数", 80))
    worksheet.append(("令和6年12月末", "アジア", "ベトナム", "総数", 50))
    worksheet.append(("令和6年12月末", "アジア", "中国", "総数", 30))
    worksheet.append(("令和6年12月末", "北アメリカ", "総数", "総数", 20))
    worksheet.append(("令和6年12月末", "北アメリカ", "米国", "総数", 20))
    worksheet.append(("令和6年12月末", "無国籍", "総数", "総数", 0))
    worksheet.append(
        ("令和6年12月末", "アジア", "うち中国〔香港〕", "総数", 5)
    )
    workbook.save(path)
    return path


def test_population_nationality_totals_parse_legacy_wide_layout(tmp_path):
    path = _wide_population_total_fixture(tmp_path / "20-12-01-1.xlsx")

    records = population.parse_population_nationality_totals(
        path,
        source_id="S19_2020",
    )

    assert len(records) == 7
    assert {record.period_end for record in records} == {"2020-12-31"}
    national = next(record for record in records if record.row_kind == "national_total")
    vietnam = next(record for record in records if record.nationality == "ベトナム")
    north_america = next(
        record
        for record in records
        if record.row_kind == "region_total" and record.region == "北アメリカ"
    )
    assert national.population == 100
    assert national.source_nationality == "総数"
    assert vietnam.region == "アジア"
    assert vietnam.row_kind == "country_or_area"
    assert vietnam.population == 50
    assert vietnam.source_row == 9
    assert vietnam.source_column == 2
    assert north_america.source_region == "北米"


def test_population_nationality_totals_parse_flat_layout_and_keep_subcategories(
    tmp_path,
):
    path = _flat_population_total_fixture(tmp_path / "24-12-01-1.xlsx")

    records = population.parse_population_nationality_totals(
        path,
        source_id="S19_2024",
    )

    assert len(records) == 8
    assert {record.period_end for record in records} == {"2024-12-31"}
    hong_kong = next(
        record for record in records if record.source_nationality == "うち中国〔香港〕"
    )
    stateless = next(record for record in records if record.nationality == "無国籍")
    assert hong_kong.row_kind == "subcategory"
    assert hong_kong.population == 5
    assert hong_kong.source_column == 5
    assert stateless.region is None
    assert stateless.row_kind == "country_or_area"


def test_population_nationality_totals_reject_country_sum_mismatch(tmp_path):
    path = _wide_population_total_fixture(
        tmp_path / "20-12-01-1.xlsx",
        country_sum=99,
    )

    with pytest.raises(SchemaError, match="country-or-area total"):
        population.parse_population_nationality_totals(
            path,
            source_id="S19_2020",
        )

"""Parsers for the 2025 Population Census preliminary reference tables."""

from pathlib import Path
from typing import List, Optional, Tuple

from openpyxl import load_workbook

from .errors import SchemaError
from .models import PrefecturePopulationRecord
from .npa_all_residents import PREFECTURE_PARENT_REGION


def _split_code_label(value: object) -> Tuple[str, str]:
    text = str(value or "").strip()
    if "_" not in text:
        raise SchemaError("Census geography must contain a code and label: %r" % text)
    code, label = text.split("_", 1)
    return code, label.strip()


def _integer(value: object, *, row: int) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise SchemaError("Missing census population at row %d" % row) from error
    if not numeric.is_integer() or numeric < 0:
        raise SchemaError("Invalid census population at row %d" % row)
    return int(numeric)


def _population_record(
    *,
    geography: str,
    population: int,
    scope: str,
    semantics: str,
    source_id: str,
    source_table: str,
    source_sheet: str,
    source_row: int,
) -> PrefecturePopulationRecord:
    national = geography == "日本"
    return PrefecturePopulationRecord(
        year=2025,
        reference_date="2025-10-01",
        population_scope=scope,
        geography=geography,
        geography_type="national" if national else "prefecture",
        parent_region=None if national else PREFECTURE_PARENT_REGION[geography],
        geography_semantics=semantics,
        population=population,
        source_value=population,
        source_unit="persons",
        rounding="none",
        source_id=source_id,
        source_table=source_table,
        source_sheet=source_sheet,
        source_row=source_row,
    )


def _canonical_census_geography(code: str, label: str) -> Optional[str]:
    if code == "00000" and label == "全国":
        return "日本"
    if len(code) == 5 and code.endswith("000") and label in PREFECTURE_PARENT_REGION:
        return label
    return None


def parse_census_preliminary_population(
    path: Path, *, source_id: str
) -> List[PrefecturePopulationRecord]:
    """Parse exact-person preliminary total population for Japan and 47 prefectures."""

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        title = " ".join(
            str(worksheet.cell(row, 1).value or "") for row in (1, 2)
        )
        if "令和７年国勢調査" not in title or "人口速報集計" not in title:
            raise SchemaError("2025 census preliminary population title was not recognized")
        records = []
        for row, values in enumerate(
            worksheet.iter_rows(min_row=14, values_only=True), start=14
        ):
            code, label = _split_code_label(values[2])
            geography = _canonical_census_geography(code, label)
            if geography is None:
                continue
            records.append(
                _population_record(
                    geography=geography,
                    population=_integer(values[3], row=row),
                    scope="total_population",
                    semantics="census_preliminary_population",
                    source_id=source_id,
                    source_table="1",
                    source_sheet=worksheet.title,
                    source_row=row,
                )
            )
        return records
    finally:
        workbook.close()


def parse_census_estimated_foreign_population(
    path: Path, *, source_id: str
) -> List[PrefecturePopulationRecord]:
    """Parse the explicitly estimated foreign population reference table."""

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        if "外国人（推計）" not in str(worksheet.cell(1, 1).value or ""):
            raise SchemaError("2025 census estimated foreign-population title was not recognized")
        records = []
        for row, values in enumerate(
            worksheet.iter_rows(min_row=4, values_only=True), start=4
        ):
            code, label = _split_code_label(values[1])
            geography = _canonical_census_geography(code, label)
            if geography is None:
                continue
            records.append(
                _population_record(
                    geography=geography,
                    population=_integer(values[2], row=row),
                    scope="foreign_population_estimate",
                    semantics="census_reference_estimate",
                    source_id=source_id,
                    source_table="reference_foreign_population",
                    source_sheet=worksheet.title,
                    source_row=row,
                )
            )
        return records
    finally:
        workbook.close()

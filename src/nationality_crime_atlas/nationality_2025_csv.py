"""Strict reader for NPA Figure 3-13 (CSV, CP932, logical row coordinates)."""

import csv
import re
from pathlib import Path

from .errors import SchemaError
from .models import NationalityOffenseGroupRecord


GROUPS = (
    (6, "criminal_code_total", "刑法犯", 0),
    (8, "heinous", "凶悪犯", 1),
    (18, "assaultive", "粗暴犯", 1),
    (20, "theft", "窃盗犯", 1),
    (34, "intellectual", "知能犯", 1),
    (36, "morals", "風俗犯", 1),
    (38, "other", "その他の刑法犯", 1),
)
COUNTRIES = (None, "ベトナム", "中国", "タイ", "ブラジル", "カンボジア")


def parse_visiting_offense_csv(path: Path, *, source_id: str):
    """Read parent groups only and reject schema changes or unreconciled totals."""
    try:
        with Path(path).open(encoding="cp932", newline="") as handle:
            rows = list(csv.reader(handle, strict=True))
    except (UnicodeError, csv.Error) as error:
        raise SchemaError("Invalid Figure 3-13 CSV") from error
    clean = lambda value: re.sub(r"\s+", "", value)
    if len(rows) != 39 or any(len(row) != 23 for row in rows):
        raise SchemaError("Figure 3-13 must have 39 logical rows and 23 columns")
    if clean(rows[0][0]) != "図表３－13国籍等別・包括罪種等別刑法犯検挙状況":
        raise SchemaError("Unexpected Figure 3-13 title")
    if rows[4][5:] != ["R6", "R7", "増減数"] * 6:
        raise SchemaError("Unexpected year columns")
    if clean(rows[2][5]) != "総数" or any(rows[3][8 + 3 * i] != "うち" + country for i, country in enumerate(COUNTRIES[1:])):
        raise SchemaError("Unexpected nationality columns")
    records = []
    for row, offense_id, label, level in GROUPS:
        label_column = 0 if level == 0 else 1
        if clean(rows[row - 1][label_column]) != label:
            raise SchemaError("Unexpected parent offense label")
        if rows[row - 1][4] != "件数" or rows[row][4] != "人員":
            raise SchemaError("Unexpected cases/persons pairing")
        for country_index, country in enumerate(COUNTRIES):
            for year_index, year in enumerate((2024, 2025)):
                column = 6 + country_index * 3 + year_index
                raw_values = [rows[row - 1][column - 1], rows[row][column - 1]]
                if any(not re.fullmatch(r"\d+", value.replace(",", "")) for value in raw_values):
                    raise SchemaError("Counts must be published non-negative integers")
                cases, persons = (int(value.replace(",", "")) for value in raw_values)
                records.append(NationalityOffenseGroupRecord(
                    year=year, population_scope="visiting_foreign", region=None,
                    nationality=country, subcategory=None,
                    row_kind="national_total" if country is None else "country",
                    offense_id=offense_id, offense_label=label,
                    offense_parent_id=None if level == 0 else "criminal_code_total",
                    offense_level=level, official_severity_role="official_offense_group",
                    cleared_cases=cases, cleared_persons=persons, source_id=source_id,
                    source_table="3-13", source_sheet="CSV logical rows", source_row=row,
                    source_cases_column=column, source_persons_column=column,
                ))
    for year in (2024, 2025):
        for country in COUNTRIES:
            selected = [record for record in records if record.year == year and record.nationality == country]
            total = next(record for record in selected if record.offense_level == 0)
            groups = [record for record in selected if record.offense_level == 1]
            for metric in ("cleared_cases", "cleared_persons"):
                if sum(getattr(record, metric) for record in groups) != getattr(total, metric):
                    raise SchemaError("Parent offense groups do not reconcile with total")
    return records

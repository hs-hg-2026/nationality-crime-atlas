"""Parser for ISA resident-foreigner statistics table 1."""

import calendar
import re
from pathlib import Path
from typing import Dict, Iterator, Optional, Sequence, Tuple

from openpyxl import load_workbook

from .errors import SchemaError
from .models import PopulationRecord


REQUIRED_HEADERS = (
    "国籍・地域",
    "在留資格",
    "性別",
    "年齢（５歳階級）",
    "年齢",
    "都道府県",
    "在留外国人数",
)


def _split_label(value: object, separators: Sequence[str]) -> Tuple[str, str]:
    text = "" if value is None else str(value).strip()
    for separator in separators:
        if separator in text:
            code, label = text.split(separator, 1)
            return code.strip(), label.strip()
    return "", text


def _period_end_from_sheet_name(sheet_name: str) -> str:
    match = re.search(r"令和\s*(\d+)年\s*(\d+)月末", sheet_name)
    if not match:
        raise SchemaError("Could not derive period_end from sheet name: %s" % sheet_name)
    year = 2018 + int(match.group(1))
    month = int(match.group(2))
    day = calendar.monthrange(year, month)[1]
    return "%04d-%02d-%02d" % (year, month, day)


def _find_data_sheet(workbook) -> Tuple[object, int, Dict[str, int]]:
    required = set(REQUIRED_HEADERS)
    for worksheet in workbook.worksheets:
        for row_index, row in enumerate(
            worksheet.iter_rows(min_row=1, max_row=30, values_only=True),
            start=1,
        ):
            values = [str(value).strip() if value is not None else "" for value in row]
            if required.issubset(set(values)):
                return worksheet, row_index, {
                    header: values.index(header) for header in REQUIRED_HEADERS
                }
    raise SchemaError("Population table 1 required columns were not found")


def _population_value(value: object) -> Tuple[Optional[int], bool]:
    if isinstance(value, str) and value.strip() == "-":
        return None, True
    if value in (None, ""):
        return None, False
    numeric = float(value)
    if not numeric.is_integer():
        raise SchemaError("Population count is not an integer: %r" % value)
    return int(numeric), False


def parse_population_t1(
    path: Path,
    *,
    source_id: str,
    period_end: Optional[str] = None,
) -> Iterator[PopulationRecord]:
    """Yield normalized rows without loading the complete official workbook into memory."""

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        worksheet, header_row, columns = _find_data_sheet(workbook)
        effective_period_end = period_end or _period_end_from_sheet_name(worksheet.title)
        for source_row, row in enumerate(
            worksheet.iter_rows(min_row=header_row + 1, values_only=True),
            start=header_row + 1,
        ):
            if not any(value not in (None, "") for value in row):
                continue

            nationality_code, nationality = _split_label(
                row[columns["国籍・地域"]], ("：", ":")
            )
            status_code, status = _split_label(
                row[columns["在留資格"]], ("：", ":")
            )
            sex_code, sex = _split_label(row[columns["性別"]], ("：", ":"))
            age_group_code, age_group = _split_label(
                row[columns["年齢（５歳階級）"]], ("_",)
            )
            prefecture_code, prefecture = _split_label(
                row[columns["都道府県"]], ("：", ":")
            )
            value, suppressed = _population_value(row[columns["在留外国人数"]])

            required_labels = (nationality, status, sex, age_group, prefecture)
            if not all(required_labels):
                raise SchemaError("Incomplete population labels at source row %d" % source_row)

            yield PopulationRecord(
                period_end=effective_period_end,
                nationality_code=nationality_code,
                nationality=nationality,
                residence_status_code=status_code,
                residence_status=status,
                sex_code=sex_code,
                sex=sex,
                age_group_code=age_group_code,
                age_group=age_group,
                age=str(row[columns["年齢"]]).strip(),
                prefecture_code=prefecture_code,
                prefecture=prefecture,
                value=value,
                suppressed=suppressed,
                source_id=source_id,
                source_sheet=worksheet.title,
                source_row=source_row,
            )
    finally:
        workbook.close()

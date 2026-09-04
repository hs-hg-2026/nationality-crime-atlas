"""Parser for the NPA Table 13 prefectural visiting-foreigner totals."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import xlrd

from .errors import SchemaError
from .models import PrefectureCrimeRecord


PREFECTURES = {
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
}


def _clean(value: object) -> str:
    return "".join(str(value or "").split())


def _integer(value: object, source_row: int) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise SchemaError("Missing Table 13 count at source row %d" % source_row)
    if not numeric.is_integer():
        raise SchemaError("Non-integer Table 13 count at source row %d" % source_row)
    return int(numeric)


def _year(value: object) -> int:
    match = re.search(r"(\d{4})年", str(value or ""))
    if not match:
        raise SchemaError("Table 13 year header was not recognized: %r" % value)
    return int(match.group(1))


def _classify_geography(primary: str, detail: str) -> Tuple[str, str, Optional[str]]:
    if primary == "総数":
        return "日本", "national", None
    if detail == "計":
        if primary == "北海道":
            return "北海道", "prefecture", "北海道"
        return primary, "police_region", primary
    if detail in PREFECTURES:
        return detail, "prefecture", primary or detail
    if primary in PREFECTURES and not detail:
        return primary, "prefecture", primary
    if detail:
        return detail, "police_subregion", primary or None
    raise SchemaError("Could not classify Table 13 geography: %r / %r" % (primary, detail))


def _sheet_map(workbook) -> Dict[str, object]:
    combined = None
    special = None
    for name in workbook.sheet_names():
        if "１３表" not in name:
            continue
        if "特別法犯" in name:
            special = workbook.sheet_by_name(name)
        elif "刑法犯" in name:
            combined = workbook.sheet_by_name(name)
    if combined is None or special is None:
        raise SchemaError("Required Table 13 sheets were not found")
    return {"combined": combined, "special": special}


def _parse_sheet(
    worksheet,
    *,
    source_id: str,
    metric_specs: Tuple[Tuple[str, int, int], ...],
) -> List[PrefectureCrimeRecord]:
    if worksheet.nrows < 7:
        raise SchemaError("Table 13 sheet is shorter than expected")

    records = []
    for offense_scope, cases_start, persons_start in metric_specs:
        if worksheet.ncols <= max(cases_start + 1, persons_start + 1):
            raise SchemaError("Table 13 metric columns are missing")
        years = (_year(worksheet.cell_value(5, cases_start)), _year(worksheet.cell_value(5, cases_start + 1)))
        for row_index in range(6, worksheet.nrows):
            primary = _clean(worksheet.cell_value(row_index, 0))
            detail = _clean(worksheet.cell_value(row_index, 1))
            if not primary and not detail:
                continue
            if primary.startswith("注") or detail.startswith("注"):
                break
            geography, geography_type, parent_region = _classify_geography(primary, detail)
            for offset, year in enumerate(years):
                records.append(
                    PrefectureCrimeRecord(
                        year=year,
                        population_scope="visiting_foreign",
                        offense_scope=offense_scope,
                        geography=geography,
                        geography_type=geography_type,
                        parent_region=parent_region,
                        geography_semantics="police_reporting_area_unresolved",
                        cleared_cases=_integer(
                            worksheet.cell_value(row_index, cases_start + offset),
                            row_index + 1,
                        ),
                        cleared_persons=_integer(
                            worksheet.cell_value(row_index, persons_start + offset),
                            row_index + 1,
                        ),
                        source_id=source_id,
                        source_table="13",
                        source_sheet=worksheet.name,
                        source_row=row_index + 1,
                    )
                )
    return records


def parse_npa_prefecture_table13(
    path: Path,
    *,
    source_id: str,
) -> List[PrefectureCrimeRecord]:
    """Parse current and prior-year Table 13 counts from the official legacy XLS."""

    workbook = xlrd.open_workbook(str(Path(path)), on_demand=True)
    try:
        sheets = _sheet_map(workbook)
        records = _parse_sheet(
            sheets["combined"],
            source_id=source_id,
            metric_specs=(
                ("criminal_and_special_law", 2, 6),
                ("criminal_code", 10, 14),
            ),
        )
        records.extend(
            _parse_sheet(
                sheets["special"],
                source_id=source_id,
                metric_specs=(("special_law", 2, 6),),
            )
        )
        return records
    finally:
        workbook.release_resources()

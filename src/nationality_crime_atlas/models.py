"""Normalized records emitted by the source parsers."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PopulationRecord:
    """One row from the ISA nationality-by-prefecture population table."""

    period_end: str
    nationality_code: str
    nationality: str
    residence_status_code: str
    residence_status: str
    sex_code: str
    sex: str
    age_group_code: str
    age_group: str
    age: str
    prefecture_code: str
    prefecture: str
    value: Optional[int]
    suppressed: bool
    source_id: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class NationalityCrimeRecord:
    """Latest-year national clearance totals for one source nationality row."""

    year: int
    population_scope: str
    region: Optional[str]
    nationality: Optional[str]
    subcategory: Optional[str]
    row_kind: str
    cleared_cases: int
    cleared_persons: int
    criminal_code_cleared_cases: int
    criminal_code_cleared_persons: int
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class NationalityOffenseGroupRecord:
    """One published nationwide nationality row for one official offense group."""

    year: int
    population_scope: str
    region: Optional[str]
    nationality: Optional[str]
    subcategory: Optional[str]
    row_kind: str
    offense_id: str
    offense_label: str
    offense_parent_id: Optional[str]
    offense_level: int
    official_severity_role: str
    cleared_cases: int
    cleared_persons: int
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int
    source_cases_column: int
    source_persons_column: int


@dataclass(frozen=True)
class AllPersonOffenseGroupRecord:
    """One national all-person total for an official criminal-code group."""

    year: int
    population_scope: str
    geography: str
    offense_id: str
    offense_label: str
    offense_parent_id: Optional[str]
    offense_level: int
    official_severity_role: str
    recognized_cases: int
    cleared_cases: int
    cleared_persons: int
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class PrefectureCrimeRecord:
    """A Table 13 clearance record at one published geography and year."""

    year: int
    population_scope: str
    offense_scope: str
    geography: str
    geography_type: str
    parent_region: Optional[str]
    geography_semantics: str
    cleared_cases: int
    cleared_persons: int
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class OverallPrefectureCrimeRecord:
    """Published all-person criminal-code counts at one NPA geography."""

    year: int
    population_scope: str
    offense_scope: str
    geography: str
    geography_type: str
    parent_region: Optional[str]
    geography_semantics: str
    recognized_cases: int
    cleared_cases: int
    cleared_persons: int
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class PrefecturePopulationRecord:
    """Published October 1 total population at national or prefecture level."""

    year: int
    reference_date: str
    population_scope: str
    geography: str
    geography_type: str
    parent_region: Optional[str]
    geography_semantics: str
    population: int
    source_value: int
    source_unit: str
    rounding: str
    source_id: str
    source_table: str
    source_sheet: str
    source_row: int

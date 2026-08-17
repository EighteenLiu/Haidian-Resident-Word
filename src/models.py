from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class CaseRecord:
    month: str = ""
    remark: str = ""
    case_id: str = ""
    source: str = ""
    status: str = ""
    case_category: str = ""
    report_unit: str = ""
    report_time: datetime | None = None
    deadline_time: datetime | None = None
    close_time: datetime | None = None
    area: str = ""
    community: str = ""
    description: str = ""
    tags: str = ""
    road: str = ""
    park: str = ""
    point_level_1: str = ""
    point_level_2: str = ""
    point_level_3: str = ""
    indicator_level_1: str = ""
    indicator_level_2: str = ""
    indicator_level_3: str = ""
    street_center: str = ""
    district_department: str = ""
    district_department_level_2: str = ""
    operation_unit: str = ""
    operation_unit_level_2: str = ""
    rectification_unit: str = ""
    disposal_department: str = ""
    rectification_time: datetime | None = None
    on_time_rectification: str = ""
    coordinate: str = ""
    merchant_id: str = ""
    merchant_name: str = ""
    is_deduct_case: str = ""
    is_solved: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class VillageEntry:
    town_name: str
    village_name: str


@dataclass
class IndicatorMapping:
    category_name: str
    subcategory_name: str
    indicator_level_3: str


@dataclass
class RoadLedgerEntry:
    street: str
    village: str
    road: str
    alias: str = ""
    normalized_keys: set[str] = field(default_factory=set)


@dataclass
class RoadMatchResult:
    record: CaseRecord
    status: str
    matched_entry: RoadLedgerEntry | None = None
    matched_key: str = ""
    message: str = ""


@dataclass
class ReportOptions:
    report_year: int
    report_month: int
    start_date: date | None
    end_date: date | None
    inspection_rounds: int = 2
    output_dir: Path | None = None

    @property
    def month_text(self) -> str:
        return f"{self.report_month}月"


@dataclass
class CategoryRow:
    seq: int | str
    name: str
    count: int
    rate: float
    rate_text: str


@dataclass
class ProblemTypeRow:
    seq: int | str
    category_name: str
    problem_name: str
    count: int
    rate: float
    rate_text: str


@dataclass
class TownRow:
    seq: int | str
    town_name: str
    count: int
    rate: float
    rate_text: str


@dataclass
class VillageRow:
    town_name: str
    village_name: str
    garbage_count: int
    village_appearance_count: int
    sewage_count: int
    toilet_count: int
    total_count: int


@dataclass
class AnalysisItem:
    name: str
    count: int
    rate_text: str
    village_summary_text: str = ""


@dataclass
class ValidationWarning:
    kind: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportStats:
    total_problem_count: int
    resolved_count: int
    resolved_rate: float
    average_per_round: int
    category_rows: list[CategoryRow]
    problem_type_rows: list[ProblemTypeRow]
    town_rows: list[TownRow]
    village_rows: list[VillageRow]
    category_analysis_items: list[AnalysisItem]
    high_frequency_problem_items: list[AnalysisItem]
    validation_warnings: list[ValidationWarning]
    village_indicator_counts: dict[tuple[str, str], dict[str, int]]
    unmapped_indicator_counts: dict[str, int]

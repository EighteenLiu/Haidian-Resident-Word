from __future__ import annotations

from datetime import date

from .models import CaseRecord, IndicatorMapping, VillageEntry
from .utils import normalize_text


def _village_matches(record: CaseRecord, villages: list[VillageEntry]) -> bool:
    value = normalize_text(record.point_level_3)
    town = normalize_text(record.point_level_2 or record.street_center)
    for entry in villages:
        village = normalize_text(entry.village_name)
        entry_town = normalize_text(entry.town_name)
        if value == village or value == normalize_text(entry.town_name + entry.village_name) or value.endswith(village):
            if not town or town == entry_town:
                return True
    return False


def filter_effective_records(
    records: list[CaseRecord],
    month_text: str,
    rules: dict,
    indicator_mappings: dict[str, IndicatorMapping] | None = None,
    villages: list[VillageEntry] | None = None,
    report_year: int | None = None,
    report_month: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CaseRecord]:
    filters = rules.get("filters", {})
    point_level_1 = filters.get("point_level_1")
    deduct_case = filters.get("deduct_case")
    case_status = filters.get("case_status")
    solved_required = filters.get("solved_required")
    require_report_time_year = bool(filters.get("require_report_time_year", False))
    filter_report_time_range = bool(filters.get("filter_report_time_range", False))
    require_deadline_in_report_month = bool(filters.get("require_deadline_in_report_month", False))
    require_indicator_mapped = bool(filters.get("require_indicator_mapped", False))
    require_village_in_dict = bool(filters.get("require_village_in_dict", False))
    excluded_case_ids = {str(case_id) for case_id in filters.get("excluded_case_ids", [])}

    effective: list[CaseRecord] = []
    for record in records:
        if record.case_id in excluded_case_ids:
            continue
        if record.month != month_text:
            continue
        if point_level_1 and record.point_level_1 != point_level_1:
            continue
        if deduct_case and record.is_deduct_case != deduct_case:
            continue
        if case_status and record.status != case_status:
            continue
        if solved_required and record.is_solved != solved_required:
            continue
        if require_report_time_year and report_year:
            if not record.report_time or record.report_time.year != report_year:
                continue
        if filter_report_time_range and start_date and (not record.report_time or record.report_time.date() < start_date):
            continue
        if filter_report_time_range and end_date and (not record.report_time or record.report_time.date() > end_date):
            continue
        if require_deadline_in_report_month and report_year and report_month:
            if not record.deadline_time or record.deadline_time.year != report_year or record.deadline_time.month != report_month:
                continue
        if require_indicator_mapped and indicator_mappings is not None and normalize_text(record.indicator_level_3) not in indicator_mappings:
            continue
        if require_village_in_dict and villages is not None and not _village_matches(record, villages):
            continue
        effective.append(record)
    return effective

from __future__ import annotations

from .models import CaseRecord, RoadLedgerEntry, RoadMatchResult
from .utils import normalize_text


def _road_name_parts(value: str) -> list[str]:
    road = normalize_text(value)
    if not road:
        return []
    if "(" not in road or ")" not in road:
        return [road]
    before = road.split("(", 1)[0].strip()
    after_left = road.split("(", 1)[1]
    inside = after_left.split(")", 1)[0].strip()
    return list(dict.fromkeys(part for part in (before, inside, road) if part))


def _candidate_villages(record: CaseRecord, ledger_villages: set[str] | None = None) -> list[str]:
    street = normalize_text(record.street_center or record.point_level_2)
    raw_village = normalize_text(record.point_level_3)
    villages = [raw_village]
    if street and raw_village.startswith(street):
        villages.append(raw_village[len(street) :])
    for ledger_village in ledger_villages or set():
        if raw_village.endswith(ledger_village):
            villages.append(ledger_village)
    return list(dict.fromkeys(v for v in villages if v))


def _candidate_auxiliary_keys(record: CaseRecord, ledger_villages: set[str] | None = None) -> list[str]:
    road_parts = _road_name_parts(record.road)
    if not road_parts:
        return []
    return [village + road for village in _candidate_villages(record, ledger_villages) for road in road_parts]


def match_roads(records: list[CaseRecord], ledger: list[RoadLedgerEntry]) -> list[RoadMatchResult]:
    auxiliary_index: dict[str, RoadLedgerEntry] = {}
    for entry in ledger:
        key = normalize_text(entry.village_road_key)
        if key:
            auxiliary_index[key] = entry

    known_villages = {normalize_text(e.street) + "|" + normalize_text(e.village) for e in ledger}
    ledger_villages = {normalize_text(e.village) for e in ledger}
    results: list[RoadMatchResult] = []
    for record in records:
        if not normalize_text(record.road):
            results.append(RoadMatchResult(record, "ROAD_EMPTY", message="道路字段为空"))
            continue
        keys = _candidate_auxiliary_keys(record, ledger_villages)
        matched_key = next((key for key in keys if key in auxiliary_index), "")
        if matched_key:
            results.append(RoadMatchResult(record, "MATCHED", auxiliary_index[matched_key], matched_key))
            continue
        street = normalize_text(record.street_center or record.point_level_2)
        raw_village = normalize_text(record.point_level_3)
        villages = _candidate_villages(record, ledger_villages)
        if not any(street + "|" + village in known_villages for village in villages if village):
            results.append(RoadMatchResult(record, "VILLAGE_NOT_IN_LEDGER", message="镇村未命中道路台账"))
        else:
            results.append(RoadMatchResult(record, "ROAD_NOT_IN_LEDGER", message="道路未命中台账"))
    return results


def apply_road_statistics_policy(results: list[RoadMatchResult], policy: str = "matched_or_non_assessment_empty") -> list[CaseRecord]:
    if policy == "warn_and_keep":
        return [result.record for result in results]
    kept: list[CaseRecord] = []
    for result in results:
        if result.status in {"MATCHED", "MATCHED_ALIAS"}:
            kept.append(result.record)
        elif result.status == "ROAD_EMPTY" and result.record.case_category != "考评上报":
            kept.append(result.record)
    return kept

from __future__ import annotations

from .models import CaseRecord, RoadLedgerEntry, RoadMatchResult
from .utils import normalize_text


def _candidate_keys(record: CaseRecord, ledger_villages: set[str] | None = None) -> list[str]:
    roads = _road_variants(record.road)
    if not roads:
        return []
    street = normalize_text(record.street_center or record.point_level_2)
    raw_village = normalize_text(record.point_level_3)
    villages = [raw_village]
    if street and raw_village.startswith(street):
        villages.append(raw_village[len(street) :])
    for ledger_village in ledger_villages or set():
        if raw_village.endswith(ledger_village):
            villages.append(ledger_village)
    keys = []
    for road in roads:
        for village in dict.fromkeys(v for v in villages if v):
            if street:
                keys.append(street + "|" + village + "|" + road)
            keys.append(village + "|" + road)
    return keys


def _road_variants(value: str) -> list[str]:
    road = normalize_text(value)
    if not road:
        return []
    variants = [road]
    for left, right in (("(", ")"),):
        if left in road and right in road:
            before = road.split(left, 1)[0]
            inside = road.split(left, 1)[1].split(right, 1)[0]
            variants.extend([before, inside])
    return list(dict.fromkeys(v for v in variants if v))


def match_roads(records: list[CaseRecord], ledger: list[RoadLedgerEntry]) -> list[RoadMatchResult]:
    index: dict[str, RoadLedgerEntry] = {}
    alias_keys: set[str] = set()
    for entry in ledger:
        primary_keys = set()
        ns, nv, nr = normalize_text(entry.street), normalize_text(entry.village), normalize_text(entry.road)
        if ns and nv and nr:
            primary_keys.add(ns + "|" + nv + "|" + nr)
        if nv and nr:
            primary_keys.add(nv + "|" + nr)
        for key in entry.normalized_keys:
            index[key] = entry
            if key not in primary_keys:
                alias_keys.add(key)

    known_villages = {normalize_text(e.street) + "|" + normalize_text(e.village) for e in ledger}
    ledger_villages = {normalize_text(e.village) for e in ledger}
    results: list[RoadMatchResult] = []
    for record in records:
        if not normalize_text(record.road):
            results.append(RoadMatchResult(record, "ROAD_EMPTY", message="道路字段为空"))
            continue
        keys = _candidate_keys(record, ledger_villages)
        matched_key = next((key for key in keys if key in index), "")
        if matched_key:
            status = "MATCHED_ALIAS" if matched_key in alias_keys else "MATCHED"
            results.append(RoadMatchResult(record, status, index[matched_key], matched_key))
            continue
        street = normalize_text(record.street_center or record.point_level_2)
        raw_village = normalize_text(record.point_level_3)
        villages = [raw_village]
        if street and raw_village.startswith(street):
            villages.append(raw_village[len(street) :])
        for ledger_village in ledger_villages:
            if raw_village.endswith(ledger_village):
                villages.append(ledger_village)
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

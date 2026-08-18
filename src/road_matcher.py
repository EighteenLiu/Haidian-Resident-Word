from __future__ import annotations

import re

from .models import CaseRecord, RoadLedgerEntry, RoadMatchResult
from .utils import normalize_text


PRIMARY_MATCH_WITH_PARENTHESES = {normalize_text("前章村路（前章村主路）")}


def _parenthesized_road_alias(value: str) -> str:
    road = normalize_text(value)
    if "(" not in road or ")" not in road:
        return ""
    after_left = road.split("(", 1)[1]
    return after_left.split(")", 1)[0].strip()


def _candidate_keys(record: CaseRecord, road: str, ledger_villages: set[str] | None = None) -> list[str]:
    if not road:
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
    for village in dict.fromkeys(v for v in villages if v):
        if street:
            keys.append(street + "|" + village + "|" + road)
        keys.append(village + "|" + road)
    return keys


def match_roads(records: list[CaseRecord], ledger: list[RoadLedgerEntry]) -> list[RoadMatchResult]:
    primary_index: dict[str, RoadLedgerEntry] = {}
    alias_index: dict[str, RoadLedgerEntry] = {}
    for entry in ledger:
        ns, nv, nr = normalize_text(entry.street), normalize_text(entry.village), normalize_text(entry.road)
        if ns and nv and nr:
            primary_index[ns + "|" + nv + "|" + nr] = entry
        if nv and nr:
            primary_index[nv + "|" + nr] = entry
        for alias in re.split(r"[;；、,，/]+", entry.alias or ""):
            na = normalize_text(alias)
            if ns and nv and na:
                alias_index[ns + "|" + nv + "|" + na] = entry
            if nv and na:
                alias_index[nv + "|" + na] = entry

    known_villages = {normalize_text(e.street) + "|" + normalize_text(e.village) for e in ledger}
    ledger_villages = {normalize_text(e.village) for e in ledger}
    results: list[RoadMatchResult] = []
    for record in records:
        if not normalize_text(record.road):
            results.append(RoadMatchResult(record, "ROAD_EMPTY", message="道路字段为空"))
            continue
        road = normalize_text(record.road)
        if road in PRIMARY_MATCH_WITH_PARENTHESES:
            keys = _candidate_keys(record, road, ledger_villages)
            matched_key = next((key for key in keys if key in primary_index), "")
            if matched_key:
                results.append(RoadMatchResult(record, "MATCHED", primary_index[matched_key], matched_key))
                continue
        alias = _parenthesized_road_alias(record.road)
        if alias:
            keys = _candidate_keys(record, alias, ledger_villages)
            matched_key = next((key for key in keys if key in alias_index), "")
            if matched_key:
                results.append(RoadMatchResult(record, "MATCHED_ALIAS", alias_index[matched_key], matched_key))
                continue
        else:
            keys = _candidate_keys(record, road, ledger_villages)
            matched_key = next((key for key in keys if key in primary_index), "")
            if matched_key:
                results.append(RoadMatchResult(record, "MATCHED", primary_index[matched_key], matched_key))
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

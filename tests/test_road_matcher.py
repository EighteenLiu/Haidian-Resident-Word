from __future__ import annotations

from src.models import CaseRecord, RoadLedgerEntry
from src.road_matcher import match_roads


def test_road_match_statuses():
    ledger = [
        RoadLedgerEntry("上庄镇", "八家村", "沙阳路", "别名路", {"上庄镇|八家村|沙阳路", "八家村|沙阳路", "上庄镇|八家村|别名路", "八家村|别名路"})
    ]
    records = [
        CaseRecord(case_id="1", street_center="上庄镇", point_level_3="八家村", road="沙阳路"),
        CaseRecord(case_id="2", street_center="上庄镇", point_level_3="八家村", road="别名路"),
        CaseRecord(case_id="3", street_center="上庄镇", point_level_3="八家村", road=""),
        CaseRecord(case_id="4", street_center="上庄镇", point_level_3="八家村", road="未知路"),
        CaseRecord(case_id="5", street_center="上庄镇", point_level_3="未知村", road="未知路"),
    ]
    statuses = [r.status for r in match_roads(records, ledger)]
    assert statuses == ["MATCHED", "MATCHED_ALIAS", "ROAD_EMPTY", "ROAD_NOT_IN_LEDGER", "VILLAGE_NOT_IN_LEDGER"]

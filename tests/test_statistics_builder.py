from __future__ import annotations

def test_statistics_match_reference(report_stats):
    stats = report_stats
    assert stats.total_problem_count == 663
    assert {row.name: row.count for row in stats.category_rows if row.name != "总计"} == {
        "农村生活垃圾治理": 337,
        "村容村貌整治": 304,
        "农村生活污水": 21,
        "农村厕所革命": 1,
    }
    assert {row.town_name: row.count for row in stats.town_rows} == {"苏家坨镇": 154, "上庄镇": 509}
    top3 = [(row.problem_name, row.count) for row in stats.problem_type_rows[:3]]
    assert top3 == [("清扫保洁不到位", 291), ("非法小广告", 124), ("堆物堆料", 122)]

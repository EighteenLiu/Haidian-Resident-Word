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
    assert stats.problem_type_rows[-1].seq == "总计"
    assert stats.problem_type_rows[-1].category_name == "总计"
    assert stats.problem_type_rows[-1].problem_name == "总计"
    assert stats.problem_type_rows[-1].count == 663
    assert stats.problem_type_rows[-1].rate_text == "100.00%"
    assert stats.village_rows[-1].town_name == "总计"
    assert stats.village_rows[-1].village_name == "总计"
    assert stats.village_rows[-1].garbage_count == 337
    assert stats.village_rows[-1].village_appearance_count == 304
    assert stats.village_rows[-1].sewage_count == 21
    assert stats.village_rows[-1].toilet_count == 1
    assert stats.village_rows[-1].total_count == 663
    top3 = [(item.name, item.count) for item in stats.high_frequency_problem_items]
    assert top3 == [("清扫保洁不到位", 291), ("非法小广告", 124), ("堆物堆料", 122)]
    category_summaries = {item.name: item.village_summary_text for item in stats.category_analysis_items}
    assert category_summaries["农村生活垃圾治理"] == "涉及上庄镇皂甲屯村（35个），常乐村（30个），后章村和前章村（各26个）等24个村"
    assert category_summaries["村容村貌整治"] == "涉及上庄镇八家村（30个）、前章村（27个）、后章村（21个）等23个村"
    assert category_summaries["农村生活污水"] == "涉及上庄镇梅所屯村（5个）和皂甲屯村（4个）等9个村"
    assert category_summaries["农村厕所革命"] == "具体发生在上庄镇八家村"
    high_summaries = {item.name: item.village_summary_text for item in stats.high_frequency_problem_items}
    assert high_summaries["清扫保洁不到位"] == "主要集中在上庄镇皂甲屯村（31个）、常乐村（29个）等24个村"
    assert high_summaries["非法小广告"] == "主要集中在上庄镇八家村（15个）、梅所屯村（13个）等18个村"
    assert high_summaries["堆物堆料"] == "主要集中在苏家坨镇柳林村（13个）、上庄镇后章村（12个）等22个村"

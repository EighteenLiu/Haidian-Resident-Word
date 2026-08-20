from __future__ import annotations

from src.docx_context import build_docx_context
from src.models import ReportOptions


def test_docx_context_core_values(report_stats):
    context = build_docx_context(report_stats, ReportOptions(2026, 6, None, None, 2))
    assert context["total_problem_count"] == 664
    assert context["average_problem_count_per_round"] == 332
    assert context["town_join_text"] == "上庄和苏家坨"
    assert context["high_frequency_names_text"] == "清扫保洁不到位、非法小广告、堆物堆料"
    assert context["high_frequency_total_count"] == 538
    assert context["village_rows"][0].garbage_count == report_stats.village_rows[0].village_appearance_count
    assert context["village_rows"][0].village_appearance_count == report_stats.village_rows[0].garbage_count

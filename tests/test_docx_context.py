from __future__ import annotations

from src.docx_context import build_docx_context
from src.models import ReportOptions


def test_docx_context_core_values(report_stats):
    context = build_docx_context(report_stats, ReportOptions(2026, 6, None, None, 2))
    assert context["total_problem_count"] == 663
    assert context["average_problem_count_per_round"] == 332
    assert context["town_join_text"] == "苏家坨和上庄"
    assert context["high_frequency_total_count"] == 537

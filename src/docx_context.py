from __future__ import annotations

from .models import ReportOptions, ReportStats
from .statistics_builder import summarize_towns, summarize_villages
from .utils import compact_pct_text, natural_join, pct_text


def build_docx_context(stats: ReportStats, options: ReportOptions) -> dict:
    town_names = [row.town_name.replace("镇", "") for row in stats.town_rows]
    village_data_rows = [row for row in stats.village_rows if row.town_name != "总计" and row.village_name != "总计"]
    categories = [row.name for row in stats.category_rows if row.name != "总计"]
    high_items = stats.high_frequency_problem_items
    high_total = sum(item.count for item in high_items)
    top_category = max((row for row in stats.category_rows if row.name != "总计"), key=lambda row: row.count, default=None)
    return {
        "report_year": options.report_year,
        "report_month": options.report_month,
        "town_join_text": natural_join(town_names),
        "town_count": len(town_names),
        "village_count": len({row.village_name for row in village_data_rows}),
        "inspection_rounds": options.inspection_rounds,
        "total_problem_count": stats.total_problem_count,
        "average_problem_count_per_round": stats.average_per_round,
        "resolved_rate_text": compact_pct_text(stats.resolved_count, stats.total_problem_count),
        "category_join_text": natural_join(categories),
        "top_category": top_category,
        "high_frequency_names_text": "、".join(item.name for item in high_items),
        "high_frequency_total_count": high_total,
        "high_frequency_total_rate_text": compact_pct_text(high_total, stats.total_problem_count),
        "town_problem_summary_text": summarize_towns(stats.town_rows),
        "village_problem_summary_text": summarize_villages(village_data_rows),
        "category_analysis_items": stats.category_analysis_items,
        "high_frequency_problem_items": stats.high_frequency_problem_items,
        "category_rows": stats.category_rows,
        "problem_type_rows": stats.problem_type_rows,
        "town_rows": stats.town_rows,
        "village_rows": stats.village_rows,
    }

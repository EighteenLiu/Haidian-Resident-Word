from __future__ import annotations

import os
import time
import traceback
import calendar
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from openpyxl import load_workbook

from .data_filter import filter_effective_records
from .docx_context import build_docx_context
from .docx_writer import render_docx_report
from .excel_reader import read_dictionary, read_main_records, read_road_ledger
from .file_classifier import FileType, classify_files, require_single
from .models import ReportOptions, ReportStats
from .road_matcher import apply_road_statistics_policy, match_roads
from .statistics_builder import build_report_stats
from .utils import PROJECT_ROOT, ensure_project_runtime, find_first_by_patterns, load_yaml, strip_lock_files
from .validation import validate_classification, validate_output_dir
from .xlsx_writer import write_road_checklist, write_statistics_xlsx


Progress = Callable[[str], None]


@dataclass
class PipelineResult:
    output_dir: Path
    xlsx_path: Path
    docx_path: Path
    road_checklist_path: Path
    log_path: Path
    stats: ReportStats
    elapsed_seconds: float


def default_word_template() -> Path | None:
    return find_first_by_patterns(
        PROJECT_ROOT / "input",
        ["海淀区2026年6月份农村人居环境检查分析报告模板.docx", "*农村人居环境检查分析报告模板*.docx"],
    )


def default_xlsx_template() -> Path | None:
    input_hit = find_first_by_patterns(PROJECT_ROOT / "input", ["附件3：海淀区农村人居环境检查情况统计表模板.xlsx", "*农村人居环境检查情况统计表模板*.xlsx"])
    if input_hit:
        return input_hit
    candidates = [p for p in (PROJECT_ROOT / "data").rglob("*.xlsx") if not p.name.startswith("~$") and "附件3" in p.name]
    return candidates[0] if candidates else None


def parse_report_options(
    records,
    report_year: int | None = None,
    report_month: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    inspection_rounds: int = 2,
    default_start_day_previous_month: int = 18,
) -> ReportOptions:
    months = [r.month for r in records if r.month]
    if report_month is None:
        for text in months:
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                report_month = int(digits)
                break
    if report_year is None:
        month_text = f"{report_month}月" if report_month else None
        deadline_years = [r.deadline_time.year for r in records if r.deadline_time and (not month_text or r.month == month_text)]
        if deadline_years:
            report_year = max(deadline_years)
        else:
            dates = [r.report_time for r in records if r.report_time] + [r.deadline_time for r in records if r.deadline_time]
            report_year = dates[0].year if dates else datetime.now().year
    if start_date is None:
        prev_month = report_month - 1
        start_year = report_year
        if prev_month == 0:
            prev_month = 12
            start_year -= 1
        start_date = date(start_year, prev_month, default_start_day_previous_month)
    if end_date is None:
        end_date = date(report_year, report_month, calendar.monthrange(report_year, report_month)[1])
    if not report_month:
        raise ValueError("无法解析报告月份，请手动填写")
    return ReportOptions(report_year, report_month, start_date, end_date, inspection_rounds)


def run_pipeline(
    source_files: list[Path],
    word_template: Path | None = None,
    xlsx_template: Path | None = None,
    options: ReportOptions | None = None,
    output_dir: Path | None = None,
    progress: Progress | None = None,
) -> PipelineResult:
    started = time.perf_counter()
    ensure_project_runtime()
    os.environ.setdefault("TMP", str(PROJECT_ROOT / ".runtime" / "tmp"))
    os.environ.setdefault("TEMP", str(PROJECT_ROOT / ".runtime" / "tmp"))
    Path(os.environ["TMP"]).mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = []

    def emit(message: str) -> None:
        log_lines.append(message)
        if progress:
            progress(message)

    try:
        config = load_yaml(PROJECT_ROOT / "config" / "default_rules.yaml")
        emit("正在识别源文件...")
        source_paths = strip_lock_files(source_files)
        classified = classify_files(source_paths)
        validate_classification(classified)
        main_file = require_single(classified, FileType.MAIN_DATA)
        dict_file = require_single(classified, FileType.DICTIONARY)
        road_file = require_single(classified, FileType.ROAD_LEDGER)
        emit("正在读取主数据...")
        all_records = read_main_records(main_file.path, main_file.sheet_name)
        if options is None:
            options = parse_report_options(
                all_records,
                inspection_rounds=int(config.get("inspection", {}).get("rounds", 2)),
                default_start_day_previous_month=int(config.get("inspection", {}).get("default_start_day_previous_month", 18)),
            )
        emit("正在读取字典和道路台账...")
        villages, mappings = read_dictionary(dict_file.path)
        roads = read_road_ledger(road_file.path, road_file.sheet_name)
        effective = filter_effective_records(
            all_records,
            options.month_text,
            config,
            mappings,
            villages,
            options.report_year,
            options.report_month,
            options.start_date,
            options.end_date,
        )
        if not effective:
            raise ValueError("有效数据为 0，请检查报告月份和筛选条件")
        emit(f"有效案件：{len(effective)} 条")
        emit("正在匹配道路台账...")
        road_results = match_roads(effective, roads)
        effective_for_stats = apply_road_statistics_policy(road_results, config.get("road_filter", {}).get("statistics_policy", "matched_or_non_assessment_empty"))
        road_status_counts = {}
        for item in road_results:
            road_status_counts[item.status] = road_status_counts.get(item.status, 0) + 1
        emit("道路匹配统计：" + "，".join(f"{k}={v}" for k, v in sorted(road_status_counts.items())))
        emit("正在统计问题数量...")
        emit(f"纳入统计案件：{len(effective_for_stats)} 条")
        stats = build_report_stats(effective_for_stats, villages, mappings, config)
        word_template = Path(word_template) if word_template else default_word_template()
        xlsx_template = Path(xlsx_template) if xlsx_template else default_xlsx_template()
        if not word_template or not word_template.exists():
            raise ValueError("未找到 Word 模板，请手动选择模板文件")
        if not xlsx_template or not xlsx_template.exists():
            raise ValueError("未找到 xlsx 模板或参考提交表，请手动选择模板文件")
        output_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "output" / datetime.now().strftime("%Y%m%d_%H%M%S")
        validate_output_dir(output_dir)
        xlsx_path = output_dir / f"附件3：海淀区农村人居环境检查情况统计表-城环建平台（{options.report_month}月）.xlsx"
        docx_path = output_dir / f"海淀区{options.report_year}年{options.report_month}月份农村人居环境检查分析报告.docx"
        road_checklist_path = output_dir / "道路匹配校验清单.xlsx"
        log_path = output_dir / "运行日志.txt"
        emit("正在生成统计表...")
        write_statistics_xlsx(xlsx_template, xlsx_path, stats, effective_for_stats, villages)
        write_road_checklist(road_checklist_path, road_results)
        emit("正在生成 Word 报告...")
        context = build_docx_context(stats, options)
        render_docx_report(word_template, docx_path, context, config)
        elapsed = time.perf_counter() - started
        emit(f"生成完成，用时 {elapsed:.2f} 秒")
        emit(f"输出目录：{output_dir}")
        log_lines.extend(
            [
                "",
                f"主数据：{main_file.path}",
                f"村指标字典：{dict_file.path}",
                f"道路台账：{road_file.path}",
                f"Word 模板：{word_template}",
                f"xlsx 模板/参考：{xlsx_template}",
                f"报告年月：{options.report_year}年{options.report_month}月",
                f"有效案件数量：{len(effective)}",
                f"未映射指标数量：{sum(stats.unmapped_indicator_counts.values())}",
                f"统计表：{xlsx_path}",
                f"Word 报告：{docx_path}",
                f"道路校验：{road_checklist_path}",
            ]
        )
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        return PipelineResult(output_dir, xlsx_path, docx_path, road_checklist_path, log_path, stats, elapsed)
    except Exception:
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            (Path(output_dir) / "运行日志.txt").write_text("\n".join(log_lines) + "\n\n" + traceback.format_exc(), encoding="utf-8")
        raise


def parse_dates_from_main_file(path: Path, sheet_name: str | None = None) -> ReportOptions:
    records = read_main_records(path, sheet_name)
    config = load_yaml(PROJECT_ROOT / "config" / "default_rules.yaml")
    return parse_report_options(records, default_start_day_previous_month=int(config.get("inspection", {}).get("default_start_day_previous_month", 18)))

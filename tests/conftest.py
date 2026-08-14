from __future__ import annotations

from pathlib import Path

import pytest

from src.data_filter import filter_effective_records
from src.excel_reader import read_dictionary, read_main_records
from src.file_classifier import FileType, classify_files
from src.pipeline import parse_report_options
from src.road_matcher import apply_road_statistics_policy, match_roads
from src.statistics_builder import build_report_stats
from src.utils import load_yaml


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def sample_files(project_root: Path) -> list[Path]:
    data_root = project_root / "data"
    return [p for p in data_root.rglob("*.xlsx") if not p.name.startswith("~$") and p.parent.parent == data_root]


@pytest.fixture(scope="session")
def classified_files(sample_files):
    return classify_files(sample_files)


@pytest.fixture(scope="session")
def rules(project_root):
    return load_yaml(project_root / "config" / "default_rules.yaml")


@pytest.fixture(scope="session")
def main_records(classified_files):
    main = next(item for item in classified_files if item.file_type == FileType.MAIN_DATA)
    return read_main_records(main.path, main.sheet_name)


@pytest.fixture(scope="session")
def effective_records(main_records, rules, dictionary_data):
    options = parse_report_options(main_records, default_start_day_previous_month=int(rules.get("inspection", {}).get("default_start_day_previous_month", 18)))
    villages, mappings = dictionary_data
    return filter_effective_records(main_records, options.month_text, rules, mappings, villages, options.report_year, options.report_month, options.start_date, options.end_date)


@pytest.fixture(scope="session")
def statistic_records(effective_records, classified_files, rules):
    road_file = next(item for item in classified_files if item.file_type == FileType.ROAD_LEDGER)
    from src.excel_reader import read_road_ledger

    road_results = match_roads(effective_records, read_road_ledger(road_file.path, road_file.sheet_name))
    return apply_road_statistics_policy(road_results, rules.get("road_filter", {}).get("statistics_policy", "matched_or_non_assessment_empty"))


@pytest.fixture(scope="session")
def dictionary_data(classified_files):
    dictionary = next(item for item in classified_files if item.file_type == FileType.DICTIONARY)
    return read_dictionary(dictionary.path)


@pytest.fixture(scope="session")
def report_stats(statistic_records, dictionary_data, rules):
    villages, mappings = dictionary_data
    return build_report_stats(statistic_records, villages, mappings, rules)

from __future__ import annotations

from src.file_classifier import FileType, classify_files


def test_classify_sample_files(classified_files):
    types = {item.file_type for item in classified_files}
    assert FileType.MAIN_DATA in types
    assert FileType.DICTIONARY in types
    assert FileType.ROAD_LEDGER in types

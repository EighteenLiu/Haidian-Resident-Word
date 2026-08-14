from __future__ import annotations

from pathlib import Path

from .file_classifier import ClassifiedFile, FileType


def validate_classification(classified: list[ClassifiedFile]) -> None:
    unknown = [item for item in classified if item.file_type == FileType.UNKNOWN]
    if unknown:
        details = "；".join(f"{item.path.name}: {item.reason}" for item in unknown)
        raise ValueError(f"存在未识别文件，请删除或更换后再运行：{details}")
    for file_type in (FileType.MAIN_DATA, FileType.DICTIONARY, FileType.ROAD_LEDGER):
        if not any(item.file_type == file_type for item in classified):
            raise ValueError(f"缺少{file_type.value}文件")


def validate_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write_test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)

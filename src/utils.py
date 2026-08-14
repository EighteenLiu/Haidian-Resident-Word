from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"


def ensure_project_runtime() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


def normalize_header(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", "", text).strip()


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s\u3000]+", "", text).strip()


def display_village_name(village: str) -> str:
    village = str(village or "").strip()
    return village[:-1] if village.endswith("村") else village


def clean_street_name(value: str) -> str:
    return str(value or "").strip()


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def pct_text(count: int, total: int) -> str:
    if not total:
        return "0.00%"
    return f"{count / total * 100:.2f}%"


def compact_pct_text(count: int, total: int) -> str:
    text = pct_text(count, total)
    if text.endswith(".00%"):
        return text.replace(".00%", "%")
    return text


def natural_join(items: Iterable[str], sep: str = "、", last_sep: str = "和") -> str:
    parts = [str(x) for x in items if str(x or "").strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return last_sep.join(parts)
    return sep.join(parts[:-1]) + last_sep + parts[-1]


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def strip_lock_files(paths: Iterable[Path]) -> list[Path]:
    return [Path(p) for p in paths if not Path(p).name.startswith("~$")]


def find_first_by_patterns(base: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        hits = [p for p in base.glob(pattern) if not p.name.startswith("~$")]
        if hits:
            return hits[0]
    return None

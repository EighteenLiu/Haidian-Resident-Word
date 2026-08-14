from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH


@dataclass
class MergeRule:
    table_index: int
    column_index: int
    start_row: int = 1
    key_columns: tuple[int, ...] = (0,)
    merge_empty: bool = False
    table_name: str = ""


def _cell_text(cell) -> str:
    return "\n".join(p.text for p in cell.paragraphs).strip()


def _merge_key(row, rule: MergeRule) -> str:
    return "|".join(_cell_text(row.cells[idx]) for idx in rule.key_columns if idx < len(row.cells))


def _center_cell(cell) -> None:
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def merge_same_cells_in_column(table, rule: MergeRule) -> None:
    if len(table.rows) <= rule.start_row:
        return
    group_start = rule.start_row
    last_key = _merge_key(table.rows[group_start], rule)
    for row_idx in range(rule.start_row + 1, len(table.rows) + 1):
        current_key = _merge_key(table.rows[row_idx], rule) if row_idx < len(table.rows) else None
        if current_key != last_key:
            group_end = row_idx - 1
            if group_end > group_start and (last_key or rule.merge_empty):
                top = table.cell(group_start, rule.column_index)
                bottom = table.cell(group_end, rule.column_index)
                merged = top.merge(bottom)
                merged.text = last_key.split("|")[0]
                _center_cell(merged)
            group_start = row_idx
            last_key = current_key


def merge_vertical_same_cells(docx_path: Path, output_path: Path, rules: list[MergeRule]) -> None:
    doc = Document(docx_path)
    for rule in rules:
        if rule.table_index >= len(doc.tables):
            continue
        merge_same_cells_in_column(doc.tables[rule.table_index], rule)
    doc.save(output_path)


def rules_from_config(config: dict) -> list[MergeRule]:
    items = config.get("word_postprocess", {}).get("merge_rules", [])
    return [
        MergeRule(
            table_index=int(item["table_index"]),
            column_index=int(item["column_index"]),
            start_row=int(item.get("start_row", 1)),
            key_columns=tuple(int(x) for x in item.get("key_columns", [0])),
            merge_empty=bool(item.get("merge_empty", False)),
            table_name=str(item.get("table_name", "")),
        )
        for item in items
    ]

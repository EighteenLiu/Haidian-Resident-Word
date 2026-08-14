from __future__ import annotations

from pathlib import Path

from docxtpl import DocxTemplate

from .word_postprocess import merge_vertical_same_cells, rules_from_config


def render_docx_report(template_path: Path, output_path: Path, context: dict, config: dict) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.stem + ".rendered.docx")
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    tpl.save(temp_path)
    rules = rules_from_config(config)
    if rules:
        merge_vertical_same_cells(temp_path, output_path, rules)
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.replace(output_path)
    return output_path

from __future__ import annotations

from pathlib import Path

from docxtpl import DocxTemplate

from .word_postprocess import (
    apply_word_postprocess,
    horizontal_rules_from_config,
    paragraph_replacements_from_config,
    paragraph_styles_from_config,
    rules_from_config,
)


def render_docx_report(template_path: Path, output_path: Path, context: dict, config: dict) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.stem + ".rendered.docx")
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    tpl.save(temp_path)
    vertical_rules = rules_from_config(config)
    horizontal_rules = horizontal_rules_from_config(config)
    paragraph_replacements = paragraph_replacements_from_config(config)
    paragraph_styles = paragraph_styles_from_config(config)
    if vertical_rules or horizontal_rules or paragraph_replacements or paragraph_styles:
        apply_word_postprocess(temp_path, output_path, vertical_rules, horizontal_rules, paragraph_replacements, paragraph_styles)
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.replace(output_path)
    return output_path

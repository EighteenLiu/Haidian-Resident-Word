from __future__ import annotations

from docx import Document

from src.word_postprocess import MergeRule, merge_vertical_same_cells


def test_merge_vertical_same_cells(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "output.docx"
    doc = Document()
    table = doc.add_table(rows=4, cols=2)
    table.cell(0, 0).text = "镇"
    table.cell(0, 1).text = "村"
    table.cell(1, 0).text = "上庄镇"
    table.cell(1, 1).text = "八家村"
    table.cell(2, 0).text = "上庄镇"
    table.cell(2, 1).text = "皂甲屯村"
    table.cell(3, 0).text = "苏家坨镇"
    table.cell(3, 1).text = "柳林村"
    doc.save(source)
    merge_vertical_same_cells(source, output, [MergeRule(table_index=0, column_index=0, start_row=1, key_columns=(0,))])
    assert output.exists()
    checked = Document(output)
    assert checked.tables[0].cell(1, 0).text == "上庄镇"

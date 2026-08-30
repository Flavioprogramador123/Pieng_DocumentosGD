"""
Inserção de imagens inline em DOCX (memorial e anexos).
"""

from __future__ import annotations

from pathlib import Path


def insert_image_at_placeholders(
    docx_path: Path,
    image_path: Path,
    placeholders: tuple[str, ...],
    *,
    width_cm: float = 12.0,
) -> bool:
    try:
        from docx import Document
        from docx.shared import Cm
    except ImportError:
        return False

    doc = Document(str(docx_path))

    def replace_in_paragraph(paragraph) -> bool:
        text = paragraph.text or ''
        if not any(p in text for p in placeholders):
            return False
        for run in paragraph.runs:
            run.text = ''
        paragraph.text = ''
        run = paragraph.add_run()
        run.add_picture(str(image_path), width=Cm(width_cm))
        return True

    for paragraph in doc.paragraphs:
        if replace_in_paragraph(paragraph):
            doc.save(str(docx_path))
            return True

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if replace_in_paragraph(paragraph):
                        doc.save(str(docx_path))
                        return True

    return False

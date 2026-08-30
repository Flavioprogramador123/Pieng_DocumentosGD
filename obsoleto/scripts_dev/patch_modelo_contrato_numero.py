"""Parametriza ModeloContrato.docx → ModeloContrato_marcadores.docx (número + texto pagamento)."""
import re
import shutil
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'templates' / 'ModeloContrato.docx'
TARGET = ROOT / 'templates' / 'ModeloContrato_marcadores.docx'
NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': NS_W}


def patch_header1(text: str) -> str:
    return re.sub(
        r'<w:r w:rsidR="00945755"><w:rPr>.*?</w:rPr><w:t>122/</w:t></w:r>'
        r'<w:r><w:rPr>.*?</w:rPr><w:t>2026</w:t></w:r>',
        '<w:r w:rsidR="00945755"><w:rPr><w:rFonts w:ascii="Arial" w:eastAsia="Arial" w:hAnsi="Arial"/>'
        '<w:b/><w:sz w:val="19"/></w:rPr><w:t>{{NUMERO_CONTRATO}}</w:t></w:r>',
        text,
        count=1,
        flags=re.DOTALL,
    )


def patch_header2(text: str) -> str:
    return re.sub(
        r'(<w:t>)CONTRATO N[^<]* \d+/\d{4}(</w:t>)',
        r'\1CONTRATO N° {{NUMERO_CONTRATO}}\2',
        text,
        count=1,
    )


def patch_payment_clause(root) -> bool:
    """Substitui parágrafo fixo da Cláusula Sexta por {{TEXTO_VALOR_PAGAMENTO_CONTRATO}}."""
    for paragraph in root.xpath('.//w:p', namespaces=NS):
        combined = ''.join(paragraph.xpath('.//w:t/text()', namespaces=NS))
        if 'investimento objeto deste contrato' not in combined.lower():
            continue
        for child in list(paragraph):
            if child.tag != f'{{{NS_W}}}pPr':
                paragraph.remove(child)
        run = etree.SubElement(paragraph, f'{{{NS_W}}}r')
        text_node = etree.SubElement(run, f'{{{NS_W}}}t')
        text_node.text = '{{TEXTO_VALOR_PAGAMENTO_CONTRATO}}'
        text_node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        return True
    return False


def patch_date_signature(root) -> bool:
    """Substitui 'Goiânia/GO, 15 de agosto de 2026' por tokens de data."""
    for paragraph in root.xpath('.//w:p', namespaces=NS):
        combined = ''.join(paragraph.xpath('.//w:t/text()', namespaces=NS))
        if 'agosto' not in combined.lower() or ' de 20' not in combined:
            continue
        if '/' not in combined and 'goi' not in combined.lower():
            continue
        for child in list(paragraph):
            if child.tag != f'{{{NS_W}}}pPr':
                paragraph.remove(child)
        run = etree.SubElement(paragraph, f'{{{NS_W}}}r')
        text_node = etree.SubElement(run, f'{{{NS_W}}}t')
        text_node.text = '{{CIDADE_DOCUMENTO}}/{{UF}}, {{DATA_DOCUMENTO_EXTENSO}}.'
        text_node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        return True
    return False


def patch_document_xml(document_xml: bytes) -> bytes:
    root = etree.fromstring(document_xml)
    if not patch_payment_clause(root):
        raise RuntimeError('Parágrafo de pagamento não encontrado em word/document.xml')
    if not patch_date_signature(root):
        raise RuntimeError('Linha de data/assinatura não encontrada em word/document.xml')
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f'Template não encontrado: {SOURCE}')
    shutil.copy2(SOURCE, TARGET)

    buf = BytesIO()
    with ZipFile(TARGET, 'r') as zin, ZipFile(buf, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/header1.xml':
                data = patch_header1(data.decode('utf-8')).encode('utf-8')
            elif item.filename == 'word/header2.xml':
                data = patch_header2(data.decode('utf-8')).encode('utf-8')
            elif item.filename == 'word/document.xml':
                data = patch_document_xml(data)
            zout.writestr(item, data)
    TARGET.write_bytes(buf.getvalue())
    print(f'Atualizado: {TARGET}')
    print(
        'Tokens: {{NUMERO_CONTRATO}}, {{TEXTO_VALOR_PAGAMENTO_CONTRATO}}, '
        '{{CIDADE_DOCUMENTO}}/{{UF}}, {{DATA_DOCUMENTO_EXTENSO}}'
    )


if __name__ == '__main__':
    main()

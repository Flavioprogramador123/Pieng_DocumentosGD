from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

SOURCE = Path('/home/ubuntu/upload/cliente_procuracao.docx')
OUTPUT = Path('/home/ubuntu/work_equatorial/modelo_procuracao_marcadores.docx')


def qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def paragraph_text(paragraph) -> str:
    return ''.join(paragraph.xpath('.//w:t/text()', namespaces=NS))


def make_run(text: str, rpr=None):
    run = etree.Element(qn('r'))
    if rpr is not None:
        run.append(deepcopy(rpr))
    text_node = etree.SubElement(run, qn('t'))
    if text[:1].isspace() or text[-1:].isspace() or '  ' in text:
        text_node.set(XML_SPACE, 'preserve')
    text_node.text = text
    return run


def replace_paragraph_runs(paragraph, chunks, normal_rpr, bold_rpr=None):
    # Keep paragraph properties, remove only text/run content, then rebuild runs.
    for child in list(paragraph):
        if child.tag != qn('pPr'):
            paragraph.remove(child)
    for text, is_bold in chunks:
        if text:
            paragraph.append(make_run(text, bold_rpr if is_bold else normal_rpr))


def replace_text_in_paragraph(paragraph, replacements):
    for text_node in paragraph.xpath('.//w:t', namespaces=NS):
        if text_node.text:
            value = text_node.text
            for old, new in replacements.items():
                value = value.replace(old, new)
            text_node.text = value


def build_template(xml_bytes: bytes) -> bytes:
    root = etree.fromstring(xml_bytes)
    paragraphs = root.xpath('.//w:body/w:p', namespaces=NS)

    body_paragraph = next((p for p in paragraphs if paragraph_text(p).startswith('Por este instrumento')), None)
    date_paragraph = next((p for p in paragraphs if paragraph_text(p).startswith('Anápolis, 22 de agosto de 2026.')), None)
    owner_paragraph = next((p for p in paragraphs if paragraph_text(p).startswith('LAESTE MENDES FERREIRA') and '319.257.231-00' in paragraph_text(p)), None)
    attorney_name_paragraph = next((p for p in paragraphs if 'IURY RODRIGUES LOPES DE ASSIS' in paragraph_text(p)), None)
    attorney_cpf_paragraph = next((p for p in paragraphs if 'CPF: 708.869.371-24' in paragraph_text(p)), None)

    if body_paragraph is None or date_paragraph is None or owner_paragraph is None:
        raise RuntimeError('Não foi possível localizar todos os parágrafos esperados no modelo da procuração.')

    all_rpr = body_paragraph.xpath('./w:r/w:rPr', namespaces=NS)
    normal_rpr = next((r for r in all_rpr if not r.xpath('./w:b', namespaces=NS)), None)
    bold_rpr = next((r for r in all_rpr if r.xpath('./w:b', namespaces=NS)), normal_rpr)

    body_chunks = [
        ('Por este instrumento de procuração e na melhor forma de direito, o Outorgante: ', False),
        ('{{NOME_CLIENTE}}', True),
        (', portador do CPF nº ', False),
        ('{{CPF}}', True),
        (', RG nº ', False),
        ('{{RG}}', True),
        (', residente e domiciliado à ', False),
        ('{{ENDERECO}}', True),
        (', Bairro: ', False),
        ('{{BAIRRO}}', True),
        (', CEP: ', False),
        ('{{CEP}}', True),
        (', em ', False),
        ('{{CIDADE}}/{{UF}}', True),
        (', nomeia e constitui como seu bastante procurador o Outorgado(a): Sr(a). ', False),
        ('{{NOME_PROCURADOR}}', True),
        (', portador do CPF nº ', False),
        ('{{CPF_PROCURADOR}}', True),
        (', RG nº ', False),
        ('{{RG_PROCURADOR}}', True),
        (' expedido pelo ', False),
        ('{{ORGAO_EMISSOR_RG_PROCURADOR}}', True),
        (', registro geral CRT nº ', False),
        ('{{REGISTRO_PROFISSIONAL}}', True),
        (', residente e domiciliado em ', False),
        ('{{ENDERECO_PROCURADOR}}', True),
        (', telefone ', False),
        ('{{TELEFONE_PROCURADOR}}', True),
        (', com poderes para, junto à ', False),
        ('{{CONCESSIONARIA}}', True),
        (', solicitar Liberação de Carga, assinar documentos, cadastros, projetos, firmar termos de compromisso e responsabilidades, enfim praticar todos os atos necessários ao fiel cumprimento deste mandato e, em especial, a viabilidade para instalar o sistema de ', False),
        ('{{OBJETO_PROCURACAO}}', True),
        (' no imóvel supracitado', False),
    ]
    replace_paragraph_runs(body_paragraph, body_chunks, normal_rpr, bold_rpr)

    replace_paragraph_runs(
        date_paragraph,
        [('{{CIDADE_DOCUMENTO}}, {{DATA_DOCUMENTO_EXTENSO}}.', False)],
        normal_rpr,
        bold_rpr,
    )

    replace_text_in_paragraph(owner_paragraph, {
        'LAESTE MENDES FERREIRA': '{{NOME_CLIENTE}}',
        '319.257.231-00': '{{CPF}}',
    })

    if attorney_name_paragraph is not None:
        replace_text_in_paragraph(attorney_name_paragraph, {
            'IURY RODRIGUES LOPES DE ASSIS': '{{NOME_PROCURADOR}}',
        })
    if attorney_cpf_paragraph is not None:
        replace_text_in_paragraph(attorney_cpf_paragraph, {
            '708.869.371-24': '{{CPF_PROCURADOR}}',
        })

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE, 'r') as source_zip, ZipFile(OUTPUT, 'w', ZIP_DEFLATED) as target_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename == 'word/document.xml':
                data = build_template(data)
            target_zip.writestr(item, data)
    print(f'Template criado: {OUTPUT}')


if __name__ == '__main__':
    main()

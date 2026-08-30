"""
Converte marcadores legados (** variável, + cálculo +) em {{TOKEN}} no memorial.
Gera backup .bak antes de alterar.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W_NS}

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / 'templates' / 'MEMORIAL_DESCRITIVO_marcadores.docx'

# (texto_exato_ou_trecho, substituto) — ordem: trechos mais longos primeiro
GLOBAL_REPLACEMENTS: list[tuple[str, str]] = [
    ('**+Figura tirado do maps da localização do imóvel+**', '{{FIGURA_LOCALIZACAO}}'),
    ('**+ AQUI VAI COLOCAR O CALCULO CORRENTE DO SISTEMA +**', '{{CALCULO_CORRENTE_SISTEMA}}'),
    ('**+ AQUI VAI COLOCAR O CALCULO CORRENTE POR INVEROSR +**', '{{CALCULO_CORRENTE_INVERSOR}}'),
    ('Cálculo: PD = 220 × **63** × **3** × 0,92 = **38.253,6 W**',
     'Cálculo: PD = {{TENSAO_NOMINAL}} × {{CORRENTE_ENTRADA}} × {{NUM_FASES}} × {{FATOR_POTENCIA}} = {{POTENCIA_DISP_KW_W}} W'),
    ('Disjuntor recomendado: 25 A (Curva C) — dimensionado com fator de segurança de 125% sobre a corrente contínua (20,45 A × 1,25  = 25A → padronizado para 25 A)',
     '{{DISJUNTOR_RECOMENDADO_QDCA}}'),
    ('Corrente total: 20,45 A vs. disjuntor de 25A', '{{COMPARATIVO_CORRENTE_DISJUNTOR}}'),
    ('Margem de segurança: 36,1% (20,45 A vs. 32 A)+**', 'Margem de segurança: {{MARGEM_SEGURANCA_DISJUNTOR}}'),
    ('Imáx-ca (inversor) = 9,78 A × 2 = 19,8 A → Cabo suporta 35 A (4 mm²), dimensionado  +**',
     '{{CALCULO_IMAX_CA}}'),
    (' **+ Cálculo da Corrente Total dos 2 Microinversores SAJ:',
     '{{CALCULO_CORRENTE_INVERSORES_TOTAL}}'),
    ('Proteção: Disjuntor tripolar 63 A (curva C), conforme item 6.2.4 da mesma norma.+**',
     'Proteção: Disjuntor tripolar {{CORRENTE_ENTRADA}} A (curva {{CURVA_ATUACAO_DISJUNTOR}}), conforme item 6.2.4 da mesma norma.'),
    ('**+Configuração: Circuito trifásico a 4 condutores (3 fases + 1 neutro).',
     '{{DESCRICAO_CIRCUITO_PADRAO}}'),
    ('Proteção do QDCA (Quadro de Distribuição CA):**+',
     'Proteção do QDCA (Quadro de Distribuição CA):'),
    ('Corrente do disjuntor: 63 A+**', 'Corrente do disjuntor: {{CORRENTE_ENTRADA}} A'),
    ('Características dos Cabos**+', 'Características dos Cabos'),
    ('Isc (módulo) = **14,98 A\u00a0**', 'Isc (módulo) = {{CORRENTE_CURTO_CIRCUITO}} A'),
    ('Isc (módulo) = **14,98 A **', 'Isc (módulo) = {{CORRENTE_CURTO_CIRCUITO}} A'),
    ('Corrente Máxima: **10 A x 2 = 20 A **', 'Corrente Máxima: {{CALCULO_CORRENTE_CA}}'),
    ('Tensão nominal CA [V]: **220**', 'Tensão nominal CA [V]: {{TENSAO_DPS}}'),
    ('Corrente Nominal [A]: **32**', 'Corrente Nominal [A]: {{CORRENTE_PROTECAO_CA}}'),
    ('IDG (Corrente do Disjuntor Geral): **63 A**', 'IDG (Corrente do Disjuntor Geral): {{CORRENTE_ENTRADA}} A'),
    ('NF (Número de Fases): **3**', 'NF (Número de Fases): {{NUM_FASES}}'),
    ('**220/380 V**', '{{TENSAO_ATENDIMENTO_FORMATADA}}'),
    ('**AUTOCONSUMO LOCAL**', '{{MODALIDADE_COMPENSACAO}}'),
    ('**Residencial**', '{{CLASSE}}'),
    ('**microinversores**', 'microinversores'),
    ('**4,50 kW**', '{{POTENCIA_INVERSOR_TOTAL}} kW'),
    ('**4,5 kW**', '{{POTENCIA_GERACAO}} kW'),
    ('**220 V**', '{{TENSAO_NOMINAL}} V'),
    ('**micro inversores monofásicos**', '{{DESCRICAO_TIPO_INVERSOR}}'),
    ('**16 mm² **', '{{BITOLA_CABO_PADRAO}}'),
    ('**16 mm²**', '{{BITOLA_CABO_PADRAO}}'),
    ('**+', ''),
    ('+**', ''),
]

ROW_REPLACEMENTS: list[tuple[str, str, str]] = [
    ('Tensão de circuito aberto', '**49,8**', '{{TENSAO_CIRCUITO_ABERTO}}'),
    ('Corrente de curto-circuito', '**14,5**', '{{CORRENTE_CURTO_CIRCUITO}}'),
    ('Tensão de máxima potência', '**41,0**', '{{TENSAO_MAX_POTENCIA}}'),
    ('Corrente de máxima potência', '**16,8**', '{{CORRENTE_MAX_POTENCIA}}'),
    ('Eficiência', '*22,0**', '{{EFICIENCIA_MODULO}}'),
    ('Eficiência', '**22,0**', '{{EFICIENCIA_MODULO}}'),
    ('Bifacialidade', '**80**', '{{BIFACIALIDADE_MODULO}}'),
    ('Potência do Inversor', '**4,50 kW**', '{{POTENCIA_INVERSOR_TOTAL}} kW'),
]


def text_nodes(element):
    return element.xpath('.//w:t', namespaces=NS)


def element_text(element) -> str:
    return ''.join(node.text or '' for node in text_nodes(element))


def replace_across_nodes(nodes, old: str, new: str) -> bool:
    if not nodes:
        return False
    texts = [node.text or '' for node in nodes]
    combined = ''.join(texts)
    start = combined.find(old)
    if start < 0:
        return False
    end = start + len(old)
    start_idx = end_idx = None
    start_offset = end_offset = 0
    cursor = 0
    for idx, text in enumerate(texts):
        next_cursor = cursor + len(text)
        if start_idx is None and cursor <= start < next_cursor:
            start_idx = idx
            start_offset = start - cursor
        if cursor < end <= next_cursor:
            end_idx = idx
            end_offset = end - cursor
            break
        cursor = next_cursor
    if start_idx is None or end_idx is None:
        return False
    if start_idx == end_idx:
        texts[start_idx] = texts[start_idx][:start_offset] + new + texts[start_idx][end_offset:]
    else:
        texts[start_idx] = texts[start_idx][:start_offset] + new
        for idx in range(start_idx + 1, end_idx):
            texts[idx] = ''
        texts[end_idx] = texts[end_idx][end_offset:]
    for node, text in zip(nodes, texts):
        node.text = text
    return True


def replace_in_element(element, old: str, new: str) -> bool:
    return replace_across_nodes(text_nodes(element), old, new)


def process_rows(root) -> int:
    count = 0
    in_inverter_block = False
    for row in root.xpath('.//w:tr', namespaces=NS):
        row_text = element_text(row)
        if '{{FABRICANTE_INVERSOR}}' in row_text or '{{MODELO_INVERSOR}}' in row_text:
            in_inverter_block = True
        if '{{FABRICANTE_MODULO}}' in row_text:
            in_inverter_block = False

        for label, old, new in ROW_REPLACEMENTS:
            if label in row_text and old in row_text:
                if replace_in_element(row, old, new):
                    count += 1

        if in_inverter_block and row_text.strip().startswith('Quantidade') and '**2**' in row_text:
            if replace_in_element(row, '**2**', '{{QTD_INVERSORES}}'):
                count += 1
    return count


def process_paragraphs(root) -> int:
    count = 0
    for paragraph in root.xpath('.//w:p', namespaces=NS):
        for old, new in GLOBAL_REPLACEMENTS:
            if old in element_text(paragraph):
                if replace_in_element(paragraph, old, new):
                    count += 1
    return count


def backup_docx() -> Path:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DOCX.with_suffix(f'.docx.bak_{stamp}')
    shutil.copy2(DOCX, backup)
    return backup


def main() -> None:
    if not DOCX.exists():
        raise SystemExit(f'Arquivo não encontrado: {DOCX}')

    backup = backup_docx()
    print(f'Backup: {backup.name}')

    with ZipFile(DOCX, 'r') as source_zip:
        entries = {item.filename: source_zip.read(item.filename) for item in source_zip.infolist()}

    root = etree.fromstring(entries['word/document.xml'])
    n_para = process_paragraphs(root)
    n_row = process_rows(root)
    entries['word/document.xml'] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True
    )

    with ZipFile(DOCX, 'w', ZIP_DEFLATED) as target_zip:
        for name, data in entries.items():
            target_zip.writestr(name, data)

    print(f'Substituições: {n_para} parágrafos, {n_row} linhas de tabela')
    print(f'Atualizado: {DOCX}')


if __name__ == '__main__':
    main()

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W_NS}
SOURCE = Path('/home/ubuntu/upload/MEMORIAL_DESCRITIVO.docx')
OUTPUT = Path('/home/ubuntu/work_equatorial/templates/MEMORIAL_DESCRITIVO_marcadores.docx')


def text_nodes(element):
    return element.xpath('.//w:t', namespaces=NS)


def element_text(element):
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


def replace_in_element(element, old: str, new: str) -> None:
    replace_across_nodes(text_nodes(element), old, new)


def replace_first_in_element(element, old: str, new: str) -> bool:
    return replace_across_nodes(text_nodes(element), old, new)


def process_paragraphs(root) -> None:
    for paragraph in root.xpath('.//w:p', namespaces=NS):
        text = element_text(paragraph)
        if not text:
            continue
        if 'MICROGERAÇÃO DISTRIBUÍDA UTILIZANDO UM SISTEMA SOLAR FOTOVOLTAICO DE 4,5 kW' in text:
            replace_in_element(paragraph, '4,5 kW', '{{POTENCIA_GERACAO}} kW')
        if 'composto por 8 módulos fotovoltaicos e 2 microinversores' in text:
            replace_in_element(paragraph, '8 módulos', '{{QTD_MODULOS}} módulos')
            replace_in_element(paragraph, '2 microinversores', '{{QTD_INVERSORES}} microinversores')
        if 'estado de (o) [Goiás]' in text:
            replace_in_element(paragraph, '[Goiás]', '[{{UF}}]')
        if 'Anápolis – GO' in text:
            replace_in_element(paragraph, 'Anápolis – GO', '{{CIDADE}} – {{UF}}')
        if 'agosto – 2026' in text:
            replace_in_element(paragraph, 'agosto – 2026', '{{MES_DOCUMENTO}} – {{ANO_DOCUMENTO}}')
        if 'Número da Conta Contrato:' in text:
            replace_in_element(paragraph, '4.275.682.012-90', '{{CONTA_CONTRATO}}')
        if 'Nome do Titular da CC:' in text:
            replace_in_element(paragraph, 'MIZAEL MATHEUS CARDOSO DA SILVA', '{{NOME_CLIENTE}}')
        if 'Endereço Completo:' in text:
            replace_in_element(paragraph, 'RUA CJ-5, Q. 11, L. 14, S/N, RESIDENCIAL CAMPOS DO JORDAO, ANÁPOLIS/GO', '{{ENDERECO_COMPLETO}}')
        if 'Número de identificação do poste' in text:
            replace_in_element(paragraph, 'Ilegível', '{{NUM_POSTE}}')
        if 'Coordenadas georrefenciadas:' in text:
            replace_in_element(paragraph, 'X: 722950.00 m E, Y: 8196162.00 m N (Fuso 22S)', 'X: {{COORDENADA_UTM_X}} m E, Y: {{COORDENADA_UTM_Y}} m N (Fuso {{FUSO_UTM}})')
        if text.startswith('Uma unidade consumidora é ligada'):
            replace_in_element(paragraph, 'trifásico a dois condutores', '{{TIPO_REDE}}')
            replace_in_element(paragraph, 'três condutor FASE', '{{QTD_CONDUTORES_FASE}} condutores FASE')
            replace_in_element(paragraph, 'um condutor NEUTRO', '{{QTD_CONDUTORES_NEUTRO}} condutor NEUTRO')
            replace_in_element(paragraph, '16 mm²', '{{BITOLA_CABO_PADRAO}}')
            replace_in_element(paragraph, '220/380 V', '{{TENSAO_ATENDIMENTO_FORMATADA}}')
            replace_in_element(paragraph, 'GOIÁS', '{{ESTADO_CONCESSAO}}')
        if 'A potência disponibilizada para unidades consumidora' in text:
            replace_in_element(paragraph, 'é (será) igual à:', 'é (será) igual à: {{POTENCIA_DISPONIBILIZADA_FORMATADA}}')
        if 'Fórmula: PD = VN × IDG × NF × FP' in text:
            replace_in_element(paragraph, '220 × 63 × 3 × 0,92', '{{TENSAO_NOMINAL}} × {{CORRENTE_ENTRADA}} × {{NUM_FASES}} × {{FATOR_POTENCIA}}')
            replace_in_element(paragraph, '38.253,6 W = 38,25 kW', '{{POTENCIA_DISP_KW_W}} W = {{POTENCIA_DISP_KW}} kW')
        if 'Potência total dos inversores: 2 × 2,25 kW = 4,50 kW' in text:
            replace_in_element(paragraph, '2 × 2,25 kW = 4,50 kW', '{{QTD_INVERSORES}} × {{POTENCIA_INVERSOR_UNITARIO}} kW = {{POTENCIA_INVERSOR_TOTAL}} kW')
        if 'Cabo Fotovoltaico (CC)' in text:
            replace_in_element(paragraph, '4 mm²', '{{BITOLA_CABO_CC}}')
        if 'Cabo de Energia (CA)' in text:
            replace_in_element(paragraph, '6 mm²', '{{BITOLA_CABO_CA}}')
            replace_in_element(paragraph, '4 mm²', '{{BITOLA_CABO_CA}}')


def process_tables(root) -> None:
    for table in root.xpath('.//w:tbl', namespaces=NS):
        for row in table.xpath('./w:tr', namespaces=NS):
            cells = row.xpath('./w:tc', namespaces=NS)
            texts = [element_text(cell) for cell in cells]
            row_text = ' | '.join(texts)
            if 'Número de Polos' in row_text:
                replace_in_element(row, '3 (tripolar)', '{{NUM_POLOS_DISJUNTOR}} ({{DESCRICAO_POLOS_DISJUNTOR}})')
            elif 'Tensão Nominal' in row_text and '380V / 220V' in row_text:
                replace_in_element(row, '380V / 220V', '{{TENSAO_NOMINAL_DISJUNTOR}}')
            elif 'Corrente Nominal' in row_text and '63A' in row_text:
                replace_in_element(row, '63A', '{{CORRENTE_NOMINAL_DISJUNTOR}}')
            elif 'Frequência Nominal' in row_text:
                replace_in_element(row, '60 Hz', '{{FREQUENCIA_DISJUNTOR}}')
            elif 'Elemento de Proteção' in row_text:
                replace_in_element(row, 'Termomagnético', '{{ELEMENTO_PROTECAO_DISJUNTOR}}')
            elif 'Capacidade Máxima de Interrupção' in row_text:
                replace_in_element(row, '10 kA', '{{CAPACIDADE_INT_DISJUNTOR}}')
            elif 'Tipo de Acionamento' in row_text:
                replace_in_element(row, 'Alavanca Manual', '{{ACIONAMENTO_DISJUNTOR}}')
            elif 'Curva de Atuação' in row_text:
                replace_in_element(row, 'Curva C', '{{CURVA_ATUACAO_DISJUNTOR}}')
            elif 'Tensão Nominal' in row_text and '220 V' in row_text:
                replace_in_element(row, '220 V', '{{TENSAO_NOMINAL}} V')
            elif 'Corrente do Disjuntor' in row_text:
                replace_in_element(row, '63 A', '{{CORRENTE_ENTRADA}} A')
            elif 'Número de Fases' in row_text:
                replace_in_element(row, '3', '{{NUM_FASES}}')
            elif 'Fator de Potência' in row_text:
                replace_in_element(row, '0,92', '{{FATOR_POTENCIA}}')
            elif 'PD (kVA)' in row_text:
                replace_in_element(row, '41,58 kVA', '{{POTENCIA_DISP_KVA}} kVA')
            elif 'PD (kW)' in row_text:
                replace_in_element(row, '38,25 kW', '{{POTENCIA_DISP_KW}} kW')
            elif 'Potência do Inversor' in row_text:
                replace_in_element(row, '4,5 0 kW*', '{{POTENCIA_INVERSOR_TOTAL}} kW*')
            elif 'Fabricante' in row_text and 'RENEPV' in row_text:
                replace_in_element(row, 'RENEPV', '{{FABRICANTE_MODULO}}')
            elif 'Módulo 690 Wp Bifacial' in row_text:
                replace_in_element(row, 'Módulo 690 Wp Bifacial', '{{MODELO_MODULO}}')
            elif 'Potência nominal – Pn [W]' in row_text and '690' in row_text:
                replace_in_element(row, '690', '{{POTENCIA_MODULO}}')
            elif 'Quantidade' in row_text and '8 módulos' in row_text:
                replace_in_element(row, '8 módulos', '{{QTD_MODULOS}} módulos')
            elif 'Potência do gerador [kW]' in row_text:
                replace_in_element(row, '5,52 kW', '{{POTENCIA_GERADOR}} kW')
            elif 'Fabricante' in row_text and 'SAJ' in row_text:
                replace_in_element(row, 'SAJ', '{{FABRICANTE_INVERSOR}}')
            elif 'Modelo' in row_text and 'M2-2.25K-S4' in row_text:
                replace_in_element(row, 'M2-2.25K-S4', '{{MODELO_INVERSOR}}')
            elif 'Quantidade' in row_text and row_text.strip().endswith('2'):
                replace_in_element(row, '2', '{{QTD_INVERSORES}}')
            elif 'Potência máx. do arranjo' in row_text:
                replace_in_element(row, '2.250', '{{POTENCIA_MAX_CC_INVERSOR}}')
            elif 'Tensão de rastreamento MPPT' in row_text:
                replace_in_element(row, '28~45', '{{FAIXA_TENSAO_MPPT_INVERSOR}}')
            elif 'Faixa de tensão de operação' in row_text:
                replace_in_element(row, '16~60', '{{FAIXA_TENSAO_INVERSOR}}')
            elif 'Tensão de entrada máx.' in row_text:
                replace_in_element(row, '60', '{{TENSAO_MAX_CC_INVERSOR}}')
            elif 'Corrente de entrada CC máx.' in row_text:
                replace_in_element(row, '20', '{{CORRENTE_MAX_CC_INVERSOR}}')
            elif 'Número de MPPTs' in row_text:
                replace_in_element(row, '4', '{{QTD_ENTRADAS_MPPT_INVERSOR}}')
            elif 'Potência máx. de saída' in row_text:
                replace_in_element(row, '2.250', '{{POTENCIA_MAX_SAIDA_CA_INVERSOR}}')
            elif 'Potência total dos inversores' in row_text:
                replace_in_element(row, '4,5', '{{POTENCIA_INVERSOR_TOTAL}}')
            elif 'Corrente de saída máx.' in row_text:
                replace_in_element(row, '9,78', '{{CORRENTE_MAX_SAIDA_CA_INVERSOR}}')
            elif 'Tensão CA nominal/Faixa' in row_text:
                replace_in_element(row, '220 / 180~264', '{{TENSAO_NOMINAL_CA_INVERSOR}} / {{FAIXA_TENSAO_CA_INVERSOR}}')
            elif 'Frequência nominal/Faixa' in row_text:
                replace_in_element(row, '60 / 55~65', '{{FREQUENCIA_NOMINAL_INVERSOR}} / {{FAIXA_FREQUENCIA_INVERSOR}}')
            elif 'Fator de potência' in row_text and '>0,99' in row_text:
                replace_in_element(row, '>0,99', '{{FATOR_POTENCIA_INVERSOR}}')
            elif 'THD de corrente' in row_text:
                replace_in_element(row, '<3%', '{{THD_CORRENTE_INVERSOR}}')
            elif 'Eficiência de pico' in row_text:
                replace_in_element(row, '97,0', '{{EFICIENCIA_MAX_INVERSOR}}')
            elif 'Corrente Nominal [A]' in row_text and '32' in row_text:
                replace_in_element(row, '32', '{{CORRENTE_PROTECAO_CA}}')
            elif 'Tipo' in row_text and 'CA' in row_text and 'DPS' in row_text:
                replace_in_element(row, 'CA', '{{TIPO_DPS}}')
            elif 'Classe' in row_text and 'II' in row_text:
                replace_in_element(row, 'II', '{{CLASSE_DPS}}')
            elif 'Tensão [V]' in row_text and '275' in row_text:
                replace_in_element(row, '275', '{{TENSAO_DPS}}')
            elif 'Corrente nominal [kA]' in row_text and '20' in row_text:
                replace_in_element(row, '20', '{{CORRENTE_NOMINAL_DPS}}')
            elif 'Corrente máxima [kA]' in row_text and '40' in row_text:
                replace_in_element(row, '40', '{{CORRENTE_MAXIMA_DPS}}')


def replace_global(root) -> None:
    replacements = {
        'MIZAEL MATHEUS CARDOSO DA SILVA': '{{NOME_CLIENTE}}',
        '016.312.311-03': '{{CPF}}',
        'Iury Rodrigues Lopes de Assis': '{{NOME_RESP_TECNICO}}',
        'IURY RODRIGUES LOPES DE ASSIS': '{{NOME_RESP_TECNICO}}',
        'Técnico em Eletrotécnica': '{{TITULO_PROFISSIONAL}}',
        'Técnico em Eletrotécnica': '{{TITULO_PROFISSIONAL}}',
        '70886937124': '{{REGISTRO_PROFISSIONAL}}',
    }
    for node in root.xpath('.//w:t', namespaces=NS):
        if node.text:
            for old, new in replacements.items():
                node.text = node.text.replace(old, new)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE, 'r') as source_zip, ZipFile(OUTPUT, 'w', ZIP_DEFLATED) as target_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename == 'word/document.xml':
                root = etree.fromstring(data)
                replace_global(root)
                process_paragraphs(root)
                process_tables(root)
                data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
            target_zip.writestr(item, data)
    print(f'Template criado: {OUTPUT}')


if __name__ == '__main__':
    main()

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from datetime import date, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
S_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_W = {'w': W_NS}
NS_S = {'s': S_NS}
TOKEN_RE = re.compile(r'\{\{([A-Z0-9_]+)\}\}')

MONTHS_PT = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro',
}

LABEL_ALIASES = {
    'nome': 'NOME_CLIENTE',
    'nome do cliente': 'NOME_CLIENTE',
    'titular': 'NOME_CLIENTE',
    'razao social': 'NOME_CLIENTE',
    'cpf': 'CPF',
    'rg': 'RG_RAW',
    'data de nascimento': 'DATA_NASCIMENTO',
    'validade cnh': 'VALIDADE_CNH',
    'endereco': 'ENDERECO',
    'endereço': 'ENDERECO',
    'bairro': 'BAIRRO',
    'cidade/uf': 'CIDADE_UF',
    'cidade / uf': 'CIDADE_UF',
    'municipio/uf': 'CIDADE_UF',
    'cidade': 'CIDADE',
    'uf': 'UF',
    'cep': 'CEP',
    'unidade consumidora (uc)': 'CONTA_CONTRATO',
    'unidade consumidora': 'CONTA_CONTRATO',
    'uc': 'CONTA_CONTRATO',
    'conta contrato': 'CONTA_CONTRATO',
    'telefone': 'TELEFONE_CELULAR',
    'telefone celular': 'TELEFONE_CELULAR',
    'email': 'EMAIL',
    'e-mail': 'EMAIL',
    'e mail': 'EMAIL',
    'data do documento': 'DATA_DOCUMENTO',
    'data da procuracao': 'DATA_DOCUMENTO',
    'data da procuração': 'DATA_DOCUMENTO',
    'cidade do documento': 'CIDADE_DOCUMENTO',
    'numero': 'NUMERO',
    'número': 'NUMERO',
    'numero do imovel': 'NUMERO',
    'número do imóvel': 'NUMERO',
    'logradouro': 'LOGRADOURO',
    'rua': 'LOGRADOURO',
    'avenida': 'LOGRADOURO',
    'quadra': 'QUADRA',
    'lote': 'LOTE',
    'complemento': 'COMPLEMENTO',
    'classe': 'CLASSE',
    'tipo de ligacao': 'TIPO_LIGACAO',
    'tipo de ligação': 'TIPO_LIGACAO',
    'tensao de atendimento (v)': 'TENSAO_ATENDIMENTO',
    'padrão de conexão': 'TENSAO_ATENDIMENTO',
    'padrao de conexao': 'TENSAO_ATENDIMENTO',
    'tensão de atendimento (v)': 'TENSAO_ATENDIMENTO',
    'disjuntor de entrada (a)': 'DISJUNTOR_ENTRADA',
    'disjuntor de proteção ac': 'DISJUNTOR_ENTRADA',
    'disjuntor de protecao ac': 'DISJUNTOR_ENTRADA',
    'nº poste/transformador': 'NUM_POSTE',
    'n° poste/transformador': 'NUM_POSTE',
    'coordenada utm x': 'COORDENADA_UTM_X',
    'coordenada utm y': 'COORDENADA_UTM_Y',
    'tipo de fonte': 'TIPO_FONTE',
    'modalidade de compensacao': 'MODALIDADE_COMPENSACAO',
    'modalidade de compensação': 'MODALIDADE_COMPENSACAO',
    'potencia de geracao (kw)': 'POTENCIA_GERACAO',
    'potência de geração (kw)': 'POTENCIA_GERACAO',
    'potencia total instalada (kw)': 'POTENCIA_TOTAL_INSTALADA',
    'potência total instalada (kw)': 'POTENCIA_TOTAL_INSTALADA',
    'quantidade de modulos': 'QTD_MODULOS',
    'módulos fotovoltaicos': 'EQUIPAMENTO_MODULOS_RAW',
    'modulos fotovoltaicos': 'EQUIPAMENTO_MODULOS_RAW',
    'quantidade de módulos': 'QTD_MODULOS',
    'fabricante dos modulos': 'FABRICANTE_MODULO',
    'fabricante dos módulos': 'FABRICANTE_MODULO',
    'modelo dos modulos': 'MODELO_MODULO',
    'modelo dos módulos': 'MODELO_MODULO',
    'potencia unitaria dos modulos (wp)': 'POTENCIA_MODULO',
    'potência unitária dos módulos (wp)': 'POTENCIA_MODULO',
    'potencia do modulo (w)': 'POTENCIA_MODULO',
    'potência do módulo (w)': 'POTENCIA_MODULO',
    'area dos arranjos (m²)': 'AREA_ARRANJO',
    'tipo de arranjo': 'TIPO_ARRANJO',
    'área dos arranjos (m²)': 'AREA_ARRANJO',
    'tensão de circuito aberto (voc) [v]': 'TENSAO_CIRCUITO_ABERTO',
    'corrente de curto circuito (isc) [a]': 'CORRENTE_CURTO_CIRCUITO',
    'tensão de máxima potência (vpmp) [v]': 'TENSAO_MAX_POTENCIA',
    'corrente de máxima potência (ipmp) [a]': 'CORRENTE_MAX_POTENCIA',
    'eficiência do módulo (%)': 'EFICIENCIA_MODULO',
    'comprimento do módulo (m)': 'COMPRIMENTO_MODULO',
    'largura do módulo (m)': 'LARGURA_MODULO',
    'área do módulo (m²)': 'AREA_MODULO',
    'peso do módulo (kg)': 'PESO_MODULO',
    'quantidade de inversores': 'QTD_INVERSORES',
    'inversores': 'EQUIPAMENTO_INVERSORES_RAW',
    'fabricante dos inversores': 'FABRICANTE_INVERSOR',
    'modelo dos inversores': 'MODELO_INVERSOR',
    'potência nominal dos inversores (kw)': 'POTENCIA_INVERSOR',
    'corrente nominal dos inversores (a)': 'CORRENTE_INVERSOR',
    'faixa de tensão dos inversores (v)': 'FAIXA_TENSAO_INVERSOR',
    'fator de potência': 'FATOR_POTENCIA',
    'rendimento (%)': 'RENDIMENTO',
    'dht de corrente (%)': 'DHT',
    'demanda alvo da unidade (kw)': 'DEMANDA_ALVO_KW',
    'máxima potência na entrada cc (kw)': 'POTENCIA_MAX_CC_INVERSOR',
    'máxima tensão cc (v)': 'TENSAO_MAX_CC_INVERSOR',
    'máxima corrente cc (a)': 'CORRENTE_MAX_CC_INVERSOR',
    'máxima tensão mppt (v)': 'TENSAO_MPPT_MAX_INVERSOR',
    'mínima tensão mppt (v)': 'TENSAO_MPPT_MIN_INVERSOR',
    'tensão cc de partida (v)': 'TENSAO_PARTIDA_CC_INVERSOR',
    'quantidade de strings': 'QTD_STRINGS_INVERSOR',
    'quantidade de entradas mppt': 'QTD_ENTRADAS_MPPT_INVERSOR',
    'potência nominal ca (kw)': 'POTENCIA_NOMINAL_CA_INVERSOR',
    'máxima potência na saída ca (kw)': 'POTENCIA_MAX_SAIDA_CA_INVERSOR',
    'máxima corrente na saída ca (a)': 'CORRENTE_MAX_SAIDA_CA_INVERSOR',
    'tensão nominal ca (v)': 'TENSAO_NOMINAL_CA_INVERSOR',
    'frequência nominal (hz)': 'FREQUENCIA_NOMINAL_INVERSOR',
    'máxima tensão ca (v)': 'TENSAO_MAX_CA_INVERSOR',
    'mínima tensão ca (v)': 'TENSAO_MIN_CA_INVERSOR',
    'thd de corrente (%)': 'THD_CORRENTE_INVERSOR',
    'fator de potência do inversor': 'FATOR_POTENCIA_INVERSOR',
    'tipo de conexão do inversor': 'TIPO_CONEXAO_INVERSOR',
    'eficiência máxima do inversor (%)': 'EFICIENCIA_MAX_INVERSOR',
    'data prevista de operação': 'DATA_OPERACAO',
    'armazenamento (se houver)': 'ARMAZENAMENTO',
    'potência máxima injetável (kw)': 'POTENCIA_MAX_INJETAVEL',
    'potência disponibilizada (kw)': 'POTENCIA_DISPONIBILIZADA',
    'endereço completo': 'ENDERECO_COMPLETO',
    'tipo de rede': 'TIPO_REDE',
    'quantidade de condutores fase': 'QTD_CONDUTORES_FASE',
    'quantidade de condutores neutro': 'QTD_CONDUTORES_NEUTRO',
    'bitola cabo padrão': 'BITOLA_CABO_PADRAO',
    'bitola do cabo padrão': 'BITOLA_CABO_PADRAO',
    'bitola cabo cc': 'BITOLA_CABO_CC',
    'bitola do cabo cc': 'BITOLA_CABO_CC',
    'bitola cabo ca': 'BITOLA_CABO_CA',
    'bitola do cabo ca': 'BITOLA_CABO_CA',
    'tensão de atendimento formatada': 'TENSAO_ATENDIMENTO_FORMATADA',
    'estado da concessão': 'ESTADO_CONCESSAO',
    'fuso utm': 'FUSO_UTM',
    'número de polos do disjuntor': 'NUM_POLOS_DISJUNTOR',
    'descrição dos polos do disjuntor': 'DESCRICAO_POLOS_DISJUNTOR',
    'potência do inversor unitário (kw)': 'POTENCIA_INVERSOR_UNITARIO',
    'potência total dos inversores (kw)': 'POTENCIA_INVERSOR_TOTAL',
    'potência disponibilizada formatada': 'POTENCIA_DISPONIBILIZADA_FORMATADA',
    'tensão nominal': 'TENSAO_NOMINAL',
    'corrente de entrada': 'CORRENTE_ENTRADA',
    'número de fases': 'NUM_FASES',
    'mês do documento': 'MES_DOCUMENTO',
    'ano do documento': 'ANO_DOCUMENTO',
    'número de polos do disjuntor': 'NUM_POLOS_DISJUNTOR',
    'tensão nominal do disjuntor (v)': 'TENSAO_NOMINAL_DISJUNTOR',
    'corrente nominal do disjuntor (a)': 'CORRENTE_NOMINAL_DISJUNTOR',
    'frequência do disjuntor (hz)': 'FREQUENCIA_DISJUNTOR',
    'capacidade máxima de interrupção (ka)': 'CAPACIDADE_INT_DISJUNTOR',
    'curva de atuação': 'CURVA_ATUACAO_DISJUNTOR',
    'elemento de proteção do disjuntor': 'ELEMENTO_PROTECAO_DISJUNTOR',
    'acionamento do disjuntor': 'ACIONAMENTO_DISJUNTOR',
    'tipo dps': 'TIPO_DPS',
    'classe dps': 'CLASSE_DPS',
    'tensão dps (v)': 'TENSAO_DPS',
    'corrente nominal dps (ka)': 'CORRENTE_NOMINAL_DPS',
    'corrente máxima dps (ka)': 'CORRENTE_MAXIMA_DPS',
    'valor do investimento (r$)': 'VALOR_INVESTIMENTO',
    'forma de pagamento': 'FORMA_PAGAMENTO',
    'banco': 'BANCO',
    'agência': 'AGENCIA',
    'conta': 'CONTA',
    'cnpj integrador': 'CNPJ_INTEGRADOR',
    'pix integrador': 'PIX_INTEGRADOR',
    'nome testemunha 1': 'NOME_TESTEMUNHA_1',
    'cpf testemunha 1': 'CPF_TESTEMUNHA_1',
    'nome testemunha 2': 'NOME_TESTEMUNHA_2',
    'cpf testemunha 2': 'CPF_TESTEMUNHA_2',
}


def deaccent(value: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value) if not unicodedata.combining(ch))


def normalize_alias_key(value: str) -> str:
    value = deaccent(value.casefold())
    value = value.replace('º', '').replace('°', '')
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def load_external_depara() -> dict[str, str]:
    path = Path(__file__).with_name('depara_chaves.json')
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {str(key): str(value) for key, value in data.items()}
    except (OSError, json.JSONDecodeError):
        return {}


LABEL_ALIASES.update(load_external_depara())
NORMALIZED_LABEL_ALIASES = {normalize_alias_key(key): target for key, target in LABEL_ALIASES.items()}


OPTIONAL_KEYS = {

    'COMPLEMENTO', 'TELEFONE_FIXO', 'ARMAZENAMENTO',
    'NOME_TESTEMUNHA_1', 'CPF_TESTEMUNHA_1',
    'NOME_TESTEMUNHA_2', 'CPF_TESTEMUNHA_2',
    'VALOR_INVESTIMENTO', 'FORMA_PAGAMENTO', 'BANCO', 'AGENCIA', 'CONTA',
    'CNPJ_INTEGRADOR', 'PIX_INTEGRADOR',
}

NUMERIC_KEYS = {
    'QTD_MODULOS', 'POTENCIA_MODULO', 'AREA_ARRANJO', 'QTD_INVERSORES',
    'POTENCIA_INVERSOR', 'CORRENTE_INVERSOR', 'FATOR_POTENCIA', 'RENDIMENTO',
    'DHT', 'POTENCIA_GERACAO', 'POTENCIA_TOTAL_INSTALADA',
    'POTENCIA_MAX_INJETAVEL', 'POTENCIA_DISPONIBILIZADA', 'TENSAO_ATENDIMENTO',
    'DISJUNTOR_ENTRADA', 'COORDENADA_UTM_X', 'COORDENADA_UTM_Y',
    'POTENCIA_MAX_CC_INVERSOR', 'TENSAO_MAX_CC_INVERSOR',
    'CORRENTE_MAX_CC_INVERSOR', 'TENSAO_MPPT_MAX_INVERSOR',
    'TENSAO_MPPT_MIN_INVERSOR', 'TENSAO_PARTIDA_CC_INVERSOR',
    'QTD_STRINGS_INVERSOR', 'QTD_ENTRADAS_MPPT_INVERSOR',
    'POTENCIA_NOMINAL_CA_INVERSOR', 'POTENCIA_MAX_SAIDA_CA_INVERSOR',
    'CORRENTE_MAX_SAIDA_CA_INVERSOR', 'TENSAO_NOMINAL_CA_INVERSOR',
    'FREQUENCIA_NOMINAL_INVERSOR', 'TENSAO_MAX_CA_INVERSOR',
    'TENSAO_MIN_CA_INVERSOR', 'THD_CORRENTE_INVERSOR',
    'FATOR_POTENCIA_INVERSOR', 'EFICIENCIA_MAX_INVERSOR',
    'TENSAO_CIRCUITO_ABERTO', 'CORRENTE_CURTO_CIRCUITO',
    'TENSAO_MAX_POTENCIA', 'CORRENTE_MAX_POTENCIA', 'EFICIENCIA_MODULO',
    'COMPRIMENTO_MODULO', 'LARGURA_MODULO', 'AREA_MODULO', 'PESO_MODULO',
    'POTENCIA_GERADOR', 'NUM_POLOS_DISJUNTOR', 'TENSAO_NOMINAL_DISJUNTOR',
    'CORRENTE_NOMINAL_DISJUNTOR', 'FREQUENCIA_DISJUNTOR',
    'CAPACIDADE_INT_DISJUNTOR', 'TENSAO_NOMINAL', 'CORRENTE_ENTRADA',
    'NUM_FASES', 'POTENCIA_DISP_KVA', 'POTENCIA_DISP_KW',
}


def normalize_label(value: str) -> str:
    value = value.strip().strip('*').strip()
    value = re.sub(r'\s+', ' ', value)
    return value.casefold()


def clean_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r'^\*+\s*', '', value)
    return value.strip()


def parse_txt(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        line = re.sub(r'^[-*]\s*', '', line)
        label, value = line.split(':', 1)
        label_key = normalize_label(label)
        value = clean_value(value)
        if not value:
            continue
        target = LABEL_ALIASES.get(label_key) or NORMALIZED_LABEL_ALIASES.get(normalize_alias_key(label))
        if target:
            values[target] = value
    return values


def only_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def format_cpf(value: str) -> str:
    raw = value.split('/')[0].strip()
    digits = only_digits(raw)
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return raw


def format_cep(value: str) -> str:
    digits = only_digits(value)
    if len(digits) == 8:
        return f'{digits[:5]}-{digits[5:]}'
    return value.strip()


def parse_city_uf(value: str) -> tuple[str, str]:
    value = value.strip().replace('\\u00a0', ' ')
    match = re.match(r'^(.+?)[\s/,-]+([A-Za-z]{2})$', value)
    if match:
        return match.group(1).strip(), match.group(2).upper()
    return value.strip(), ''


def parse_rg(raw: str) -> tuple[str, str, str]:
    raw = raw.strip()
    parts = raw.split()
    if len(parts) >= 3 and len(parts[-1]) == 2:
        return ' '.join(parts[:-2]), parts[-2], parts[-1].upper()
    if len(parts) == 2 and len(parts[-1]) == 2:
        return parts[0], '', parts[-1].upper()
    return raw, '', ''


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    return None


def date_extended(value: str | None) -> str:
    parsed = parse_date(value)
    if not parsed:
        return value or ''
    return f'{parsed.day} de {MONTHS_PT[parsed.month]} de {parsed.year}'


def numeric_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace('%', '').replace(' ', '')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    else:
        text = text.replace(',', '.')
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', text):
        return None
    return text


def load_defaults(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def build_values(raw: dict[str, str], defaults: dict) -> dict[str, str]:
    values: dict[str, str] = dict(raw)

    for key in ('QTD_MODULOS', 'QTD_INVERSORES', 'NUM_POLOS_DISJUNTOR', 'NUM_FASES'):
        if key in values and numeric_value(values[key]) is None:
            match = re.search(r'-?\d+(?:[.,]\d+)?', str(values[key]))
            if match:
                values[key] = match.group(0).replace(',', '.')

    if 'CPF' in values:
        values['CPF'] = format_cpf(values['CPF'])
    if 'CEP' in values:
        values['CEP'] = format_cep(values['CEP'])
    if 'RG_RAW' in values:
        rg, issuer, uf = parse_rg(values['RG_RAW'])
        values['RG'] = rg
        values['ORGAO_EMISSOR_RG'] = issuer
        values['UF_RG'] = uf
    if 'CIDADE_UF' in values:
        city, uf = parse_city_uf(values['CIDADE_UF'])
        values.setdefault('CIDADE', city)
        values.setdefault('UF', uf)
    if 'ENDERECO' in values and 'NUMERO' not in values:
        number_match = re.search(r'\b(?:N[.º°]?|NÚMERO)\s*([0-9A-Za-z-]+)', values['ENDERECO'], re.I)
        if number_match:
            values['NUMERO'] = number_match.group(1)

    # Address De/Para: accept either one complete address or fragmented fields.
    # Explicit ENDERECO_COMPLETO always has precedence; otherwise compose the
    # available parts in a stable order without duplicating the street text.
    if not values.get('ENDERECO') and values.get('LOGRADOURO'):
        address_parts = [values['LOGRADOURO']]
        if values.get('NUMERO'):
            address_parts.append(f'Nº {values["NUMERO"]}')
        if values.get('QUADRA'):
            address_parts.append(f'Q. {values["QUADRA"]}')
        if values.get('LOTE'):
            address_parts.append(f'L. {values["LOTE"]}')
        values['ENDERECO'] = ', '.join(address_parts)
    if not values.get('ENDERECO_COMPLETO'):
        address_parts = [values.get('ENDERECO', '')]
        if values.get('BAIRRO'):
            address_parts.append(values['BAIRRO'])
        if values.get('CIDADE') and values.get('UF'):
            address_parts.append(f'{values["CIDADE"]}/{values["UF"]}')
        values['ENDERECO_COMPLETO'] = ', '.join(part for part in address_parts if part)
    values.setdefault('COMPLEMENTO', '')
    raw_modules = values.get('EQUIPAMENTO_MODULOS_RAW', '')
    if raw_modules:
        match = re.search(r'(\d+)\s*(?:unidades?|módulos?)', raw_modules, re.I)
        if match:
            values.setdefault('QTD_MODULOS', match.group(1))
        power = re.search(r'(\d+(?:[.,]\d+)?)\s*W', raw_modules, re.I)
        if power:
            values.setdefault('POTENCIA_MODULO', power.group(1).replace(',', '.'))
        maker = re.search(r'\b(RENEPV)\b', raw_modules, re.I)
        if maker:
            values.setdefault('FABRICANTE_MODULO', maker.group(1).upper())
        values.setdefault('MODELO_MODULO', raw_modules)
    raw_inverters = values.get('EQUIPAMENTO_INVERSORES_RAW', '')
    if raw_inverters:
        match = re.search(r'(\d+)\s*(?:unidades?|inversores?)', raw_inverters, re.I)
        if match:
            values.setdefault('QTD_INVERSORES', match.group(1))
        power = re.search(r'(\d+(?:[.,]\d+)?)\s*kW', raw_inverters, re.I)
        if power:
            values.setdefault('POTENCIA_INVERSOR', power.group(1).replace(',', '.'))
        values.setdefault('FABRICANTE_INVERSOR', 'DEYE')
        values.setdefault('MODELO_INVERSOR', raw_inverters)
    values.setdefault('TELEFONE_FIXO', '')

    procurador = defaults.get('procurador', {})
    tecnico = defaults.get('responsavel_tecnico', {})
    procuracao = defaults.get('procuracao', {})

    values.setdefault('NOME_PROCURADOR', procurador.get('nome', ''))
    values.setdefault('CPF_PROCURADOR', procurador.get('cpf', ''))
    values.setdefault('RG_PROCURADOR', procurador.get('rg', ''))
    values.setdefault('ORGAO_EMISSOR_RG_PROCURADOR', procurador.get('orgao_emissor_rg', ''))
    values.setdefault('UF_RG_PROCURADOR', procurador.get('uf_rg', ''))
    values.setdefault('ENDERECO_PROCURADOR', procurador.get('endereco', ''))
    values.setdefault('TELEFONE_PROCURADOR', procurador.get('telefone', ''))
    values.setdefault('EMAIL_PROCURADOR', procurador.get('email', ''))

    values.setdefault('NOME_RESP_TECNICO', tecnico.get('nome', ''))
    values.setdefault('TITULO_PROFISSIONAL', tecnico.get('titulo_profissional', ''))
    values.setdefault('REGISTRO_PROFISSIONAL', tecnico.get('registro_profissional', ''))
    values.setdefault('UF_REGISTRO', tecnico.get('uf_registro', ''))
    values.setdefault('EMAIL_TECNICO', tecnico.get('email', ''))
    values.setdefault('TELEFONE_TECNICO', tecnico.get('telefone', ''))
    values.setdefault('ENDERECO_TECNICO', tecnico.get('endereco', ''))
    values.setdefault('BAIRRO_TECNICO', tecnico.get('bairro', ''))
    values.setdefault('CIDADE_TECNICO', tecnico.get('cidade', ''))
    values.setdefault('UF_TECNICO', tecnico.get('uf', ''))
    values.setdefault('CEP_TECNICO', tecnico.get('cep', ''))

    values.setdefault('CONCESSIONARIA', procuracao.get('concessionaria', 'Equatorial Energia Goiás'))
    values.setdefault('ESTADO_CONCESSAO', values.get('UF', ''))
    values.setdefault('ENDERECO_COMPLETO', values.get('ENDERECO', ''))
    if values.get('COMPLEMENTO') and values.get('ENDERECO_COMPLETO') and values['COMPLEMENTO'] not in values['ENDERECO_COMPLETO']:
        values['ENDERECO_COMPLETO'] = f'{values["ENDERECO_COMPLETO"]}, {values["COMPLEMENTO"]}'
    values.setdefault('TENSAO_ATENDIMENTO_FORMATADA', values.get('TENSAO_ATENDIMENTO', ''))
    values.setdefault('POTENCIA_INVERSOR_UNITARIO', values.get('POTENCIA_INVERSOR', ''))
    values.setdefault('CORRENTE_ENTRADA', values.get('DISJUNTOR_ENTRADA', ''))
    values.setdefault('NUM_FASES', '3' if 'TRIF' in values.get('TIPO_LIGACAO', '').upper() else '')
    if values.get('TENSAO_ATENDIMENTO') and '/' in values['TENSAO_ATENDIMENTO']:
        values.setdefault('TENSAO_NOMINAL', values['TENSAO_ATENDIMENTO'].split('/')[0].strip())
    if values.get('DATA_DOCUMENTO'):
        parsed_document_date = parse_date(values['DATA_DOCUMENTO'])
        if parsed_document_date:
            values.setdefault('MES_DOCUMENTO', MONTHS_PT[parsed_document_date.month])
            values.setdefault('ANO_DOCUMENTO', str(parsed_document_date.year))
    values.setdefault('OBJETO_PROCURACAO', procuracao.get('objeto', 'Energia Fotovoltaica'))
    values.setdefault('CIDADE_DOCUMENTO', values.get('CIDADE', procuracao.get('cidade_documento', '')))
    values.setdefault('DATA_DOCUMENTO', procuracao.get('data_documento', ''))
    if values.get('DATA_DOCUMENTO'):
        values.setdefault('DATA_DOCUMENTO_EXTENSO', date_extended(values.get('DATA_DOCUMENTO')))
    if values.get('DATA_DOCUMENTO') and not values.get('DATA_OPERACAO'):
        values['DATA_OPERACAO'] = values['DATA_DOCUMENTO']

    # Derived values used by the main Equatorial workbook. They are only
    # calculated when the necessary equipment data is present; otherwise the
    # field remains pending for technical confirmation.
    try:
        qtd_modulos = float(values.get('QTD_MODULOS', ''))
        potencia_modulo = float(values.get('POTENCIA_MODULO', ''))
        potencia_modulos = qtd_modulos * potencia_modulo / 1000
        values.setdefault('POTENCIA_TOTAL_INSTALADA', f'{potencia_modulos:g}')
        values.setdefault('POTENCIA_GERADOR', f'{potencia_modulos:g}')
        if not values.get('AREA_ARRANJO') and values.get('AREA_MODULO'):
            values['AREA_ARRANJO'] = f'{qtd_modulos * float(values["AREA_MODULO"]):g}'
    except (TypeError, ValueError):
        pass
    try:
        qtd_inversores = float(values.get('QTD_INVERSORES', ''))
        potencia_inversor = float(values.get('POTENCIA_INVERSOR', ''))
        potencia_inversores = qtd_inversores * potencia_inversor
        values.setdefault('POTENCIA_INVERSOR_TOTAL', f'{potencia_inversores:g}')
        if values.get('POTENCIA_TOTAL_INSTALADA'):
            potencia_modulos = float(values['POTENCIA_TOTAL_INSTALADA'])
            values.setdefault('POTENCIA_GERACAO', f'{min(potencia_modulos, potencia_inversores):g}')
        else:
            values.setdefault('POTENCIA_GERACAO', f'{potencia_inversores:g}')
    except (TypeError, ValueError):
        pass

    # Calculate the available power only when all source values are provided.
    try:
        vn = float(values.get('TENSAO_NOMINAL') or values.get('TENSAO_ATENDIMENTO') or '')
        corrente = float(values.get('CORRENTE_ENTRADA') or values.get('DISJUNTOR_ENTRADA') or '')
        fases = float(values.get('NUM_FASES') or '')
        fp = float(values.get('FATOR_POTENCIA') or '0.92')
        kva = vn * corrente * fases / 1000
        kw = kva * fp
        values.setdefault('POTENCIA_DISP_KVA', f'{kva:g}')
        values.setdefault('POTENCIA_DISP_KW', f'{kw:g}')
        values.setdefault('POTENCIA_DISPONIBILIZADA', f'{kw:g}')
        values.setdefault('POTENCIA_DISPONIBILIZADA_FORMATADA', f'{kw:g} kW')
    except (TypeError, ValueError):
        pass

    # Convenient aliases used by the main Equatorial workbook.
    values.setdefault('TIPO_FONTE', 'SOLAR FOTOVOLTAICA')
    values.setdefault('TIPO_ARRANJO', values.get('ARRANJO', values.get('TIPO_DE_ARRANJO', '')))
    values.setdefault('MODALIDADE_COMPENSACAO', 'AUTOCONSUMO LOCAL')
    values.setdefault('ARMAZENAMENTO', 'NÃO')

    return values


def token_replacer(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        value = values.get(key)
        if value is None or str(value).strip() == '':
            return '' if key in OPTIONAL_KEYS else match.group(0)
        return str(value)
    return TOKEN_RE.sub(replace, text)


def set_text_node(node, value: str) -> None:
    node.text = value
    if value[:1].isspace() or value[-1:].isspace() or '  ' in value:
        node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    else:
        node.attrib.pop('{http://www.w3.org/XML/1998/namespace}space', None)


def replace_tokens_in_text_nodes(nodes, values: dict[str, str]) -> None:
    if not nodes:
        return
    texts = [node.text or '' for node in nodes]
    combined = ''.join(texts)
    matches = list(TOKEN_RE.finditer(combined))
    if not matches:
        for node in nodes:
            if node.text:
                set_text_node(node, token_replacer(node.text, values))
        return

    for match in reversed(matches):
        key = match.group(1)
        if key not in values:
            continue
        value = values.get(key)
        replacement = '' if value is None or str(value).strip() == '' else str(value)
        if (value is None or str(value).strip() == '') and key not in OPTIONAL_KEYS:
            replacement = match.group(0)

        start, end = match.span()
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
            continue

        if start_idx == end_idx:
            texts[start_idx] = texts[start_idx][:start_offset] + replacement + texts[start_idx][end_offset:]
        else:
            texts[start_idx] = texts[start_idx][:start_offset] + replacement
            for idx in range(start_idx + 1, end_idx):
                texts[idx] = ''
            texts[end_idx] = texts[end_idx][end_offset:]

    for node, text in zip(nodes, texts):
        set_text_node(node, text)


def fill_docx(source: Path, destination: Path, values: dict[str, str]) -> set[str]:
    unresolved: set[str] = set()
    with ZipFile(source, 'r') as source_zip, ZipFile(destination, 'w', ZIP_DEFLATED) as target_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                try:
                    root = etree.fromstring(data)
                    for paragraph in root.xpath('.//w:p', namespaces=NS_W):
                        replace_tokens_in_text_nodes(paragraph.xpath('.//w:t', namespaces=NS_W), values)
                    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                except etree.XMLSyntaxError:
                    pass
            target_zip.writestr(item, data)
    for token in discover_tokens_docx(destination):
        if token not in values:
            unresolved.add(token)
    return unresolved


def discover_tokens_docx(path: Path) -> set[str]:
    tokens: set[str] = set()
    with ZipFile(path, 'r') as archive:
        for name in archive.namelist():
            if name.startswith('word/') and name.endswith('.xml'):
                tokens.update(TOKEN_RE.findall(archive.read(name).decode('utf-8', errors='ignore')))
    return tokens


def cell_value_from_shared(cell, shared_strings: list[str]) -> str | None:
    if cell.get('t') != 's':
        return None
    value_node = cell.find(f'{{{S_NS}}}v')
    if value_node is None or value_node.text is None:
        return None
    try:
        return shared_strings[int(value_node.text)]
    except (ValueError, IndexError):
        return None


def shared_string_text(si) -> str:
    return ''.join(si.xpath('.//s:t/text()', namespaces=NS_S))


def set_shared_string(si, value: str) -> None:
    text_nodes = si.xpath('.//s:t', namespaces=NS_S)
    if text_nodes:
        text_nodes[0].text = value
        for node in text_nodes[1:]:
            node.text = ''
    else:
        text_node = etree.SubElement(si, f'{{{S_NS}}}t')
        text_node.text = value


def set_numeric_cell(cell, value: str | None) -> None:
    cell.attrib.pop('t', None)
    for inline in cell.findall(f'{{{S_NS}}}is'):
        cell.remove(inline)
    value_node = cell.find(f'{{{S_NS}}}v')
    if value_node is None:
        value_node = etree.SubElement(cell, f'{{{S_NS}}}v')
    value_node.text = value or ''


def fill_workbook(source: Path, destination: Path, values: dict[str, str]) -> set[str]:
    unresolved: set[str] = set()
    with ZipFile(source, 'r') as source_zip, ZipFile(destination, 'w', ZIP_DEFLATED) as target_zip:
        shared_root = None
        shared_strings: list[str] = []
        if 'xl/sharedStrings.xml' in source_zip.namelist():
            shared_root = etree.fromstring(source_zip.read('xl/sharedStrings.xml'))
            shared_strings = [shared_string_text(si) for si in shared_root.findall(f'{{{S_NS}}}si')]

        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename == 'xl/sharedStrings.xml' and shared_root is not None:
                data = etree.tostring(shared_root, xml_declaration=True, encoding='UTF-8', standalone=True)
            elif item.filename.startswith('xl/worksheets/') and item.filename.endswith('.xml'):
                try:
                    root = etree.fromstring(data)
                    for cell in root.findall(f'.//{{{S_NS}}}c'):
                        current = cell_value_from_shared(cell, shared_strings)
                        if current is not None:
                            token_match = re.fullmatch(r'\{\{([A-Z0-9_]+)\}\}', current.strip())
                            if token_match:
                                key = token_match.group(1)
                                if key in values:
                                    raw = values[key]
                                    if key in NUMERIC_KEYS:
                                        set_numeric_cell(cell, numeric_value(raw))
                                    elif shared_root is not None:
                                        value_node = cell.find(f'{{{S_NS}}}v')
                                        if value_node is not None:
                                            idx = int(value_node.text)
                                            set_shared_string(shared_root.findall(f'{{{S_NS}}}si')[idx], str(raw))
                                else:
                                    unresolved.add(key)
                            else:
                                replaced = token_replacer(current, values)
                                if replaced != current and shared_root is not None:
                                    value_node = cell.find(f'{{{S_NS}}}v')
                                    if value_node is not None:
                                        idx = int(value_node.text)
                                        set_shared_string(shared_root.findall(f'{{{S_NS}}}si')[idx], replaced)
                        elif cell.get('t') == 'inlineStr':
                            for text_node in cell.xpath('.//s:t', namespaces=NS_S):
                                if text_node.text:
                                    text_node.text = token_replacer(text_node.text, values)
                    data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
                except etree.XMLSyntaxError:
                    pass
            target_zip.writestr(item, data)

        if shared_root is not None:
            # Rewrite the shared strings part after all worksheet references were processed.
            temp_items = []
            for item in target_zip.infolist():
                if item.filename != 'xl/sharedStrings.xml':
                    temp_items.append(item)
            # ZIP entries cannot be replaced in place; sharedStrings.xml was written before
            # worksheets, so the second copy is intentionally avoided by rebuilding below.

    # Rebuild once so the updated sharedStrings.xml is written exactly once.
    if shared_root is not None:
        with ZipFile(source, 'r') as source_zip, ZipFile(destination, 'w', ZIP_DEFLATED) as target_zip:
            shared_bytes = etree.tostring(shared_root, xml_declaration=True, encoding='UTF-8', standalone=True)
            for item in source_zip.infolist():
                data = source_zip.read(item.filename)
                if item.filename == 'xl/sharedStrings.xml':
                    data = shared_bytes
                elif item.filename.startswith('xl/worksheets/') and item.filename.endswith('.xml'):
                    data = transform_worksheet(data, shared_strings, shared_root, values, unresolved)
                target_zip.writestr(item, data)

    return unresolved


def transform_worksheet(data: bytes, shared_strings: list[str], shared_root, values: dict[str, str], unresolved: set[str]) -> bytes:
    root = etree.fromstring(data)
    shared_items = shared_root.findall(f'{{{S_NS}}}si')
    for cell in root.findall(f'.//{{{S_NS}}}c'):
        current = cell_value_from_shared(cell, shared_strings)
        if current is not None:
            token_match = re.fullmatch(r'\{\{([A-Z0-9_]+)\}\}', current.strip())
            if token_match:
                key = token_match.group(1)
                if key in values:
                    raw = values[key]
                    if key in NUMERIC_KEYS:
                        set_numeric_cell(cell, numeric_value(raw))
                    else:
                        value_node = cell.find(f'{{{S_NS}}}v')
                        if value_node is not None:
                            set_shared_string(shared_items[int(value_node.text)], str(raw))
                else:
                    unresolved.add(key)
            else:
                replaced = token_replacer(current, values)
                if replaced != current:
                    value_node = cell.find(f'{{{S_NS}}}v')
                    if value_node is not None:
                        set_shared_string(shared_items[int(value_node.text)], replaced)
        elif cell.get('t') == 'inlineStr':
            for text_node in cell.xpath('.//s:t', namespaces=NS_S):
                if text_node.text:
                    text_node.text = token_replacer(text_node.text, values)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def discover_tokens_workbook(path: Path) -> set[str]:
    tokens: set[str] = set()
    with ZipFile(path, 'r') as archive:
        for name in archive.namelist():
            if name.startswith('xl/') and name.endswith('.xml'):
                tokens.update(TOKEN_RE.findall(archive.read(name).decode('utf-8', errors='ignore')))
    return tokens


def main() -> None:
    parser = argparse.ArgumentParser(description='Preenche os documentos Equatorial a partir de um TXT.')
    parser.add_argument('--input', required=True, type=Path, help='Arquivo TXT com os dados do cliente e dados técnicos.')
    parser.add_argument('--templates-dir', type=Path, default=Path('templates'), help='Pasta com DOCX/XLSX/XLT(X) parametrizados.')
    parser.add_argument('--output-dir', type=Path, default=Path('saida'), help='Pasta de saída.')
    parser.add_argument('--config', type=Path, default=Path('config_padrao.json'), help='Configuração dos dados padrão do Iury.')
    args = parser.parse_args()

    raw = parse_txt(args.input)
    defaults = load_defaults(args.config)
    values = build_values(raw, defaults)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        'RELATÓRIO DE PREENCHIMENTO',
        f'Arquivo de entrada: {args.input}',
        '',
        'Valores interpretados:',
    ]
    for key in sorted(values):
        report_lines.append(f'- {key}: {values[key]}')

    all_unresolved: dict[str, list[str]] = {}
    for template in sorted(args.templates_dir.iterdir()):
        if template.suffix.lower() not in {'.docx', '.xlsx', '.xltx'}:
            continue
        destination = args.output_dir / template.name
        if template.suffix.lower() == '.xltx':
            destination = destination.with_suffix('.xlsx')
        if template.suffix.lower() == '.docx':
            unresolved = fill_docx(template, destination, values)
        else:
            unresolved = fill_workbook(template, destination, values)
        if unresolved:
            all_unresolved[template.name] = sorted(unresolved)

    report_lines.extend(['', 'Marcadores ainda não preenchidos:'])
    if all_unresolved:
        for filename, tokens in all_unresolved.items():
            report_lines.append(f'- {filename}: {", ".join("{{" + t + "}}" for t in tokens)}')
    else:
        report_lines.append('- Nenhum marcador pendente.')

    report_path = args.output_dir / 'relatorio_preenchimento.txt'
    report_path.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')
    print(f'Documentos gerados em: {args.output_dir.resolve()}')
    print(f'Relatório: {report_path.resolve()}')
    if all_unresolved:
        print('ATENÇÃO: existem marcadores pendentes. Consulte o relatório.')


if __name__ == '__main__':
    main()

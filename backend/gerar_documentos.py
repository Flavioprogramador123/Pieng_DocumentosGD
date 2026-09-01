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
TOKEN_RE = re.compile(r'\{\{([A-Za-z0-9_]+)\}\}')


def normalize_token(key: str) -> str:
    return str(key or '').upper()

SKIP_TEMPLATE_FILENAMES = frozenset({
    'ModeloContrato_marcadores.docx',
    'MEMORIAL_DESCRITIVO_marcadores_patched.docx',
    'NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xltx',
    'NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates00.xltx',
})


def iter_document_templates(templates_dir: Path):
    """Templates ativos para preenchimento (exclui rascunhos duplicados)."""
    xlsx_stems = {
        p.stem for p in templates_dir.iterdir()
        if p.suffix.lower() == '.xlsx' and not p.name.startswith('~$')
    }
    for template in sorted(templates_dir.iterdir()):
        if template.name in SKIP_TEMPLATE_FILENAMES:
            continue
        if template.name.startswith('~$'):
            continue
        if template.suffix.lower() not in {'.docx', '.xlsx', '.xltx'}:
            continue
        # Preferir .xlsx editado (listas suspensas pré-selecionadas) em vez do .xltx legado
        if template.suffix.lower() == '.xltx' and template.stem in xlsx_stems:
            continue
        yield template

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
    'data expedição': 'DT_EXP',
    'data expedição rg': 'DT_EXP',
    'data expedição cnh': 'DT_EXP',
    'dt exp': 'DT_EXP',
    'endereco': 'ENDERECO',
    'endereço': 'ENDERECO',
    'bairro': 'BAIRRO',
    'cidade/uf': 'CIDADE_UF',
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
  'celular': 'TELEFONE_CELULAR',
  'fone': 'TELEFONE_CELULAR',
  'fone celular': 'TELEFONE_CELULAR',
  'tel': 'TELEFONE_CELULAR',
  'whatsapp': 'TELEFONE_CELULAR',
  'whats': 'TELEFONE_CELULAR',
    'email': 'EMAIL',
    'e-mail': 'EMAIL',
    'e mail': 'EMAIL',
    'data do documento': 'DATA_DOCUMENTO',
    'data da procuracao': 'DATA_DOCUMENTO',
    'data da procuração': 'DATA_DOCUMENTO',
    'cidade do documento': 'CIDADE_DOCUMENTO',
    'numero': 'NUMERO',
    'número': 'NUMERO',
    'complemento': 'COMPLEMENTO',
    'classe': 'CLASSE',
    'tipo de ligacao': 'TIPO_LIGACAO',
    'tipo de ligação': 'TIPO_LIGACAO',
    'ligação existente': 'LIGACAO_EXISTENTE',
    'ligacao existente': 'LIGACAO_EXISTENTE',
    'tensao de atendimento (v)': 'TENSAO_ATENDIMENTO',
    'tensão de atendimento (v)': 'TENSAO_ATENDIMENTO',
    'disjuntor de entrada (a)': 'DISJUNTOR_ENTRADA',
    'disjuntor de proteção ac': 'DISJUNTOR_ENTRADA',
    'disjuntor de protecao ac': 'DISJUNTOR_ENTRADA',
    'disjuntor de proteção': 'DISJUNTOR_ENTRADA',
    'disjuntor de protecao': 'DISJUNTOR_ENTRADA',
    'disjuntor geral': 'DISJUNTOR_ENTRADA',
    'nº poste/transformador': 'NUM_POSTE',
    'n° poste/transformador': 'NUM_POSTE',
    'coordenada utm x': 'COORDENADA_UTM_X',
    'coordenada utm y': 'COORDENADA_UTM_Y',
    'coordenadas': 'COORDENADAS',
    'coordenadas georreferenciadas': 'COORDENADAS_GEORREFERENCIADAS',
    'latitude': 'LATITUDE',
    'longitude': 'LONGITUDE',
    'zoom figura localização': 'FIGURA_MAP_ZOOM',
    'zoom figura localizacao': 'FIGURA_MAP_ZOOM',
    'figura map zoom': 'FIGURA_MAP_ZOOM',
    'tipo de fonte': 'TIPO_FONTE',
    'modalidade de compensacao': 'MODALIDADE_COMPENSACAO',
    'modalidade de compensação': 'MODALIDADE_COMPENSACAO',
    'potencia de geracao (kw)': 'POTENCIA_GERACAO',
    'potência de geração (kw)': 'POTENCIA_GERACAO',
    'potencia total instalada (kw)': 'POTENCIA_TOTAL_INSTALADA',
    'potência total instalada (kw)': 'POTENCIA_TOTAL_INSTALADA',
    'demanda alvo da unidade (kw)': 'DEMANDA_ALVO_KW',
    'demanda alvo (kw)': 'DEMANDA_ALVO_KW',
    'tabela de demanda': 'TABELA_DEMANDA',
    'tabela de demanda json': 'TABELA_DEMANDA_JSON',
    'quantidade de modulos': 'QTD_MODULOS',
    'quantidade de módulos': 'QTD_MODULOS',
    'fabricante dos modulos': 'FABRICANTE_MODULO',
    'fabricante dos módulos': 'FABRICANTE_MODULO',
    'modelo dos modulos': 'MODELO_MODULO',
    'modelo dos módulos': 'MODELO_MODULO',
    'potencia unitaria dos modulos (wp)': 'POTENCIA_MODULO',
    'potência unitária dos módulos (wp)': 'POTENCIA_MODULO',
    'potencia do modulo (w)': 'POTENCIA_MODULO',
    'potência do módulo (w)': 'POTENCIA_MODULO',
    'potencia dos modulos': 'POTENCIA_MODULO',
    'potência dos módulos': 'POTENCIA_MODULO',
    'potencia dos modulos (wp)': 'POTENCIA_MODULO',
    'potencia dos modulos wp': 'POTENCIA_MODULO',
    'potencia do modulo': 'POTENCIA_MODULO',
    'potência do módulo': 'POTENCIA_MODULO',
    'area dos arranjos (m²)': 'AREA_ARRANJO',
    'área dos arranjos (m²)': 'AREA_ARRANJO',
    'tensão de circuito aberto (voc) [v]': 'TENSAO_CIRCUITO_ABERTO',
    'corrente de curto circuito (isc) [a]': 'CORRENTE_CURTO_CIRCUITO',
    'tensão de máxima potência (vpmp) [v]': 'TENSAO_MAX_POTENCIA',
    'corrente de máxima potência (ipmp) [a]': 'CORRENTE_MAX_POTENCIA',
    'eficiência do módulo (%)': 'EFICIENCIA_MODULO',
    'eficiencia do modulo (%)': 'EFICIENCIA_MODULO',
    'eficiencia do modulo': 'EFICIENCIA_MODULO',
    'eficiência do modulo': 'EFICIENCIA_MODULO',
    'comprimento do módulo (m)': 'COMPRIMENTO_MODULO',
    'largura do módulo (m)': 'LARGURA_MODULO',
    'área do módulo (m²)': 'AREA_MODULO',
    'peso do módulo (kg)': 'PESO_MODULO',
    'quantidade de inversores': 'QTD_INVERSORES',
    'fabricante dos inversores': 'FABRICANTE_INVERSOR',
    'modelo dos inversores': 'MODELO_INVERSOR',
    'potência nominal dos inversores (kw)': 'POTENCIA_INVERSOR',
    'potencia nominal dos inversores (kw)': 'POTENCIA_INVERSOR',
    'potencia dos inversores (kw)': 'POTENCIA_INVERSOR',
    'potência dos inversores (kw)': 'POTENCIA_INVERSOR',
    'corrente nominal dos inversores (a)': 'CORRENTE_INVERSOR',
    'faixa de tensão dos inversores (v)': 'FAIXA_TENSAO_INVERSOR',
    'fator de potência': 'FATOR_POTENCIA',
    'rendimento (%)': 'RENDIMENTO',
    'dht de corrente (%)': 'DHT',
    'máxima potência na entrada cc (kw)': 'POTENCIA_MAX_CC_INVERSOR',
    'máxima tensão cc (v)': 'TENSAO_MAX_CC_INVERSOR',
    'máxima corrente cc (a)': 'CORRENTE_MAX_CC_INVERSOR',
    'máxima tensão mppt (v)': 'TENSAO_MPPT_MAX_INVERSOR',
    'mínima tensão mppt (v)': 'TENSAO_MPPT_MIN_INVERSOR',
    'tensão cc de partida (v)': 'TENSAO_PARTIDA_CC_INVERSOR',
    'quantidade de strings': 'QTD_STRINGS_INVERSOR',
    'quantidade de entradas mppt': 'QTD_ENTRADAS_MPPT_INVERSOR',
    'módulos por string': 'MODULOS_POR_STRING',
    'modulos por string': 'MODULOS_POR_STRING',
    'strings em paralelo por mppt': 'STRINGS_POR_MPPT',
    'strings por mppt': 'STRINGS_POR_MPPT',
    'tipo de inversor (topologia)': 'TIPO_INVERSOR',
    'tipo de inversor': 'TIPO_INVERSOR',
    'tipo equipamento inversor': 'TIPO_EQUIPAMENTO_INVERSOR',
    'equipamento inversor (tipo)': 'TIPO_EQUIPAMENTO_INVERSOR',
    'microinversores por grupo ca': 'MICROS_POR_GRUPO_CA',
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
    'endereço uc': 'ENDERECO_UC',
    'endereco uc': 'ENDERECO_UC',
    'endereço completo': 'ENDERECO_COMPLETO',
    'rg completo': 'RG_COMPLETO',
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
    'texto valor pagamento contrato': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'valor e forma de pagamento (contrato)': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'cláusula valor pagamento contrato': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'clausula valor pagamento contrato': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'texto pagamento': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'texto de pagamento': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'valor pagamento': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'pagamento contrato': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'clausula pagamento': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'cláusula pagamento': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'clausula sexta': 'TEXTO_VALOR_PAGAMENTO_CONTRATO',
    'contrato': 'NUMERO_CONTRATO',
    'número do contrato': 'NUMERO_CONTRATO',
    'numero do contrato': 'NUMERO_CONTRATO',
    'nº do contrato': 'NUMERO_CONTRATO',
    'no do contrato': 'NUMERO_CONTRATO',
    'contrato n': 'NUMERO_CONTRATO',
    'banco': 'BANCO',
    'agência': 'AGENCIA',
    'conta': 'CONTA',
    'cnpj integrador': 'CNPJ_INTEGRADOR',
    'pix integrador': 'PIX_INTEGRADOR',
    'nome integrador': 'NOME_INTEGRADOR',
    'nome da integradora': 'NOME_INTEGRADOR',
    'razão social integrador': 'NOME_INTEGRADOR',
    'endereço integrador': 'ENDERECO_INTEGRADOR',
    'endereco integrador': 'ENDERECO_INTEGRADOR',
    'contratante': 'NOME_CONTRATANTE',
    'nome contratante': 'NOME_CONTRATANTE',
    'nome testemunha 1': 'NOME_TESTEMUNHA_1',
    'cpf testemunha 1': 'CPF_TESTEMUNHA_1',
    'nome testemunha 2': 'NOME_TESTEMUNHA_2',
    'cpf testemunha 2': 'CPF_TESTEMUNHA_2',
    'corrente de entrada': 'CORRENTE_ENTRADA',
    'corrente de entrada (a)': 'CORRENTE_ENTRADA',
} 


OPTIONAL_KEYS = {
    'COMPLEMENTO', 'TELEFONE_FIXO', 'ARMAZENAMENTO',
    'NOME_TESTEMUNHA_1', 'CPF_TESTEMUNHA_1',
    'NOME_TESTEMUNHA_2', 'CPF_TESTEMUNHA_2',
    'VALOR_INVESTIMENTO', 'FORMA_PAGAMENTO', 'TEXTO_VALOR_PAGAMENTO_CONTRATO', 'NUMERO_CONTRATO',
    'BANCO', 'AGENCIA', 'CONTA',
    'CNPJ_INTEGRADOR', 'PIX_INTEGRADOR',
    'NOME_INTEGRADOR', 'ENDERECO_INTEGRADOR', 'TELEFONE_INTEGRADOR', 'EMAIL_INTEGRADOR',
    'NOME_CONTRATANTE',
    'FIGURA_LOCALIZACAO', 'FIGURA_CAIXA', 'TEXTO_CAIXA',
    'CALCULO_CORRENTE_SISTEMA', 'CALCULO_CORRENTE_INVERSOR',
    'CALCULO_CORRENTE_INVERSORES_TOTAL', 'CALCULO_IMAX_CA', 'CALCULO_CORRENTE_CA',
    'DISJUNTOR_RECOMENDADO_QDCA', 'COMPARATIVO_CORRENTE_DISJUNTOR',
    'MARGEM_SEGURANCA_DISJUNTOR', 'DESCRICAO_TIPO_INVERSOR', 'TIPO_EQUIPAMENTO_INVERSOR',
    'DESCRICAO_CIRCUITO_PADRAO',
    'DESCRICAO_CONEXAO_INVERSORES', 'DESCRICAO_DISJUNTOR_PADRAO',
    'CONFIGURACAO_STRINGS_CC', 'PROTECAO_CC_DESCRICAO', 'PROTECAO_CA_DESCRICAO',
    'POTENCIA_DISP_KW_W', 'CORRENTE_PROTECAO_CA', 'TENSAO_DPS',
    'POTENCIA_MAX_INJETAVEL', 'DT_EXP',
    'FORMULA_PD', 'TEXTO_PD_PARAMETROS', 'CALCULO_PD',
}

NUMERIC_KEYS = {
    'QTD_MODULOS', 'POTENCIA_MODULO', 'AREA_ARRANJO', 'DEMANDA_ALVO_KW', 'QTD_INVERSORES',
    'POTENCIA_INVERSOR', 'CORRENTE_INVERSOR', 'FATOR_POTENCIA', 'RENDIMENTO',
    'POTENCIA_GERACAO', 'POTENCIA_TOTAL_INSTALADA',
    'POTENCIA_DISPONIBILIZADA', 'TENSAO_ATENDIMENTO',
    'DISJUNTOR_ENTRADA', 'COORDENADA_UTM_X', 'COORDENADA_UTM_Y',
    'POTENCIA_MAX_CC_INVERSOR', 'TENSAO_MAX_CC_INVERSOR',
    'CORRENTE_MAX_CC_INVERSOR', 'TENSAO_MPPT_MAX_INVERSOR',
    'TENSAO_MPPT_MIN_INVERSOR', 'TENSAO_PARTIDA_CC_INVERSOR',
    'QTD_STRINGS_INVERSOR', 'QTD_ENTRADAS_MPPT_INVERSOR',
    'POTENCIA_NOMINAL_CA_INVERSOR', 'POTENCIA_MAX_SAIDA_CA_INVERSOR',
    'CORRENTE_MAX_SAIDA_CA_INVERSOR', 'TENSAO_NOMINAL_CA_INVERSOR',
    'FREQUENCIA_NOMINAL_INVERSOR', 'TENSAO_MAX_CA_INVERSOR',
    'TENSAO_MIN_CA_INVERSOR',
    'FATOR_POTENCIA_INVERSOR', 'EFICIENCIA_MAX_INVERSOR',
    'TENSAO_CIRCUITO_ABERTO', 'CORRENTE_CURTO_CIRCUITO',
    'TENSAO_MAX_POTENCIA', 'CORRENTE_MAX_POTENCIA', 'EFICIENCIA_MODULO',
    'COMPRIMENTO_MODULO', 'LARGURA_MODULO', 'AREA_MODULO', 'PESO_MODULO',
    'POTENCIA_GERADOR', 'NUM_POLOS_DISJUNTOR', 'TENSAO_NOMINAL_DISJUNTOR',
    'CORRENTE_NOMINAL_DISJUNTOR', 'FREQUENCIA_DISJUNTOR',
    'CAPACIDADE_INT_DISJUNTOR', 'TENSAO_NOMINAL', 'CORRENTE_ENTRADA',
    'NUM_FASES', 'POTENCIA_DISP_KVA', 'POTENCIA_DISP_KW',
    'POTENCIA_INVERSOR_TOTAL', 'POTENCIA_INVERSOR_UNITARIO',
    'QTD_CONDUTORES_FASE', 'QTD_CONDUTORES_NEUTRO',
}


def normalize_label(value: str) -> str:
    value = value.strip().strip('*').strip()
    value = re.sub(r'\s+', ' ', value)
    value = unicodedata.normalize('NFD', value)
    value = ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')
    return value.casefold()


def lookup_label_alias(label: str) -> str | None:
    return _LABEL_ALIAS_INDEX.get(normalize_label(label))


def _build_label_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for raw_key, target in LABEL_ALIASES.items():
        index[normalize_label(raw_key)] = target
    return index


_LABEL_ALIAS_INDEX = _build_label_alias_index()


def clean_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r'^\*+\s*', '', value)
    return value.strip()


def parse_txt(path: Path) -> dict[str, str]:
    return parse_txt_content(path.read_text(encoding='utf-8-sig'))


MULTILINE_LABEL_KEYS = {
    'texto valor pagamento contrato',
    'texto pagamento',
    'texto de pagamento',
    'valor pagamento',
    'pagamento contrato',
    'clausula pagamento',
    'cláusula pagamento',
    'clausula valor pagamento contrato',
    'cláusula valor pagamento contrato',
    'clausula sexta',
    'valor e forma de pagamento (contrato)',
}


def _parse_label_line(raw_line: str) -> tuple[str, str, str] | None:
    line = raw_line.strip()
    if not line or ':' not in line:
        return None
    line = re.sub(r'^[-*#]\s*', '', line)
    label, value = line.split(':', 1)
    label_key = normalize_label(label)
    target = lookup_label_alias(label)
    if not target:
        return None
    return label_key, clean_value(value), target


def parse_txt_content(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        parsed = _parse_label_line(lines[i])
        if not parsed:
            loose = re.match(
                r'^(?:fone|telefone|celular|tel|whatsapp|whats)\s*:?\s*(.+)$',
                re.sub(r'^[-*#]\s*', '', lines[i].strip()),
                re.I,
            )
            if loose and loose.group(1).strip():
                values['TELEFONE_CELULAR'] = clean_value(loose.group(1))
            i += 1
            continue
        label_key, value, target = parsed
        if not value and label_key in MULTILINE_LABEL_KEYS:
            parts: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = _parse_label_line(lines[j])
                if nxt:
                    break
                chunk = lines[j].strip()
                if chunk:
                    parts.append(chunk)
                j += 1
            value = '\n'.join(parts)
            i = j - 1
        if value:
            values[target] = value
        i += 1
    from coordinate_utils import enrich_coordinate_tokens
    enrich_coordinate_tokens(values)
    return values


def _token_is_filled(values: dict[str, str], token: str) -> bool:
    value = values.get(token)
    return value is not None and str(value).strip() != ''


def preview_token_mapping(
    txt_content: str,
    config_path: Path,
    templates_dir: Path,
) -> dict:
    """Pré-visualiza DE/PARA: rótulo TXT → token → valor final (incl. derivados)."""
    raw = parse_txt_content(txt_content)
    defaults = load_defaults(config_path)
    values = build_values(raw, defaults)

    mappings: list[dict] = []
    seen_tokens: set[str] = set()
    for raw_line in txt_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        line = re.sub(r'^[-*]\s*', '', line)
        label, _ = line.split(':', 1)
        label_key = normalize_label(label)
        target = lookup_label_alias(label)
        if not target or target in seen_tokens:
            continue
        seen_tokens.add(target)
        final_value = values.get(target, '')
        mappings.append({
            'label': label.strip(),
            'token': target,
            'placeholder': f'{{{{{target}}}}}',
            'raw_value': raw.get(target, ''),
            'value': final_value,
            'filled': _token_is_filled(values, target),
            'source': 'form' if target in raw else 'derived',
        })

    derived_tokens: list[dict] = []
    for token in sorted(values):
        if token in seen_tokens:
            continue
        derived_tokens.append({
            'token': token,
            'placeholder': f'{{{{{token}}}}}',
            'value': values[token],
            'filled': _token_is_filled(values, token),
            'source': 'default' if token.startswith(('NOME_PROCURADOR', 'CPF_PROCURADOR', 'NOME_RESP')) else 'derived',
        })

    unresolved_by_template: dict[str, list[str]] = {}
    all_template_tokens: set[str] = set()
    for template in iter_document_templates(templates_dir):
        if template.suffix.lower() == '.docx':
            tokens = discover_tokens_docx(template)
        else:
            tokens = discover_tokens_workbook(template)
        all_template_tokens.update(tokens)
        missing = sorted(t for t in tokens if not _token_is_filled(values, t))
        if missing:
            unresolved_by_template[template.name] = missing

    filled_count = sum(1 for t in all_template_tokens if _token_is_filled(values, t))
    token_to_files: dict[str, list[str]] = {}
    for template in iter_document_templates(templates_dir):
        if template.suffix.lower() == '.docx':
            tokens = discover_tokens_docx(template)
        else:
            tokens = discover_tokens_workbook(template)
        for token in tokens:
            token_to_files.setdefault(token, []).append(template.name)

    template_placeholders = [
        {
            'token': token,
            'placeholder': f'{{{{{token}}}}}',
            'value': values.get(token, ''),
            'filled': _token_is_filled(values, token),
            'in_templates': token_to_files.get(token, []),
        }
        for token in sorted(all_template_tokens)
    ]

    return {
        'mappings': mappings,
        'derived_tokens': derived_tokens,
        'template_placeholders': template_placeholders,
        'values': {k: values[k] for k in sorted(values)},
        'unresolved_by_template': unresolved_by_template,
        'stats': {
            'form_fields': len(mappings),
            'form_filled': sum(1 for m in mappings if m['filled']),
            'total_values': len(values),
            'template_tokens': len(all_template_tokens),
            'template_filled': filled_count,
            'template_pending': len(all_template_tokens) - filled_count,
        },
    }


def only_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def normalize_conta_contrato(value: str) -> str:
    """
    UC / conta contrato — apenas dígitos.
    Se vier duplicada (com e sem separadores), fica a sequência numérica mais longa.
    Ex.: '688.899.012-35 / 000068889901235' → '000068889901235'
    """
    if not value:
        return ''
    raw = str(value).strip()
    parts = [p.strip() for p in re.split(r'[/|;]', raw) if p.strip()]
    if not parts:
        parts = [raw]
    best = ''
    for part in parts:
        digits = only_digits(part)
        if len(digits) > len(best):
            best = digits
    return best


def format_conta_contrato(value: str) -> str:
    """Formato Equatorial com pontos e traço (últimos 12 dígitos significativos)."""
    digits = normalize_conta_contrato(value)
    if len(digits) < 12:
        return digits
    d = digits[-12:]
    return f'{d[0]}.{d[1:4]}.{d[4:7]}.{d[7:10]}-{d[10:12]}'


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


def format_telefone_celular(value: str) -> str:
    """Normaliza celular BR: 062991827090, 62991827090, (62) 99182-7090 → (62) 99182-7090."""
    raw = str(value or '').strip()
    digits = only_digits(raw)
    if not digits:
        return raw
    if digits.startswith('55') and len(digits) >= 12:
        digits = digits[2:]
    while digits.startswith('0') and len(digits) > 10:
        digits = digits[1:]
    if len(digits) == 11:
        return f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
    if len(digits) == 10:
        return f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
    return raw


def parse_city_uf(value: str) -> tuple[str, str]:
    match = re.match(r'^(.+?)\s+([A-Za-z]{2})$', value.strip())
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


def _apply_tipo_equipamento_inversor(values: dict) -> None:
    """Token {{TIPO_EQUIPAMENTO_INVERSOR}} — 'Micro-inversor' ou 'Inversor' para planta/memorial."""
    if values.get('TIPO_EQUIPAMENTO_INVERSOR'):
        return
    from string_calculations import label_tipo_equipamento_inversor

    mps_raw = numeric_value(values.get('MODULOS_POR_STRING') or '')
    mps = int(float(mps_raw)) if mps_raw else None
    tipo = values.get('TIPO_INVERSOR')
    topo = None
    t_upper = (tipo or '').upper()
    if t_upper in ('MICRO', 'MICROINVERSOR', 'MICRO-INVERSOR'):
        topo = 'micro'
    elif t_upper in ('STRING', 'CENTRAL', 'STRING/MPPT', 'HIBRIDO', 'HÍBRIDO'):
        topo = 'string'
    values['TIPO_EQUIPAMENTO_INVERSOR'] = label_tipo_equipamento_inversor(tipo, topo, mps)


def _apply_dc_string_analysis(values: dict) -> None:
    """Deriva tokens de strings CC e textos de proteção para o memorial."""
    qtd_mod = numeric_value(values.get('QTD_MODULOS'))
    qtd_inv = numeric_value(values.get('QTD_INVERSORES'))
    if not qtd_mod or not qtd_inv:
        return

    modules = [{
        'quantidade': int(float(qtd_mod)),
        'voc': values.get('TENSAO_CIRCUITO_ABERTO'),
        'isc': values.get('CORRENTE_CURTO_CIRCUITO'),
        'vmpp': values.get('TENSAO_MAX_POTENCIA'),
        'impp': values.get('CORRENTE_MAX_POTENCIA'),
    }]
    inverters = [{
        'quantidade': int(float(qtd_inv)),
        'num_mppt': values.get('QTD_ENTRADAS_MPPT_INVERSOR') or values.get('NUM_MPPT'),
        'mppt_min': values.get('TENSAO_MPPT_MIN_INVERSOR'),
        'mppt_max': values.get('TENSAO_MPPT_MAX_INVERSOR'),
        'corrente_max_saida_ca': values.get('CORRENTE_MAX_SAIDA_CA_INVERSOR'),
        'tipo_inversor': values.get('TIPO_INVERSOR'),
    }]
    technical = {
        'tipo_inversor': values.get('TIPO_INVERSOR'),
        'num_mppt': values.get('NUM_MPPT') or values.get('QTD_ENTRADAS_MPPT_INVERSOR'),
        'modulos_por_string': values.get('MODULOS_POR_STRING'),
        'strings_por_mppt': values.get('STRINGS_POR_MPPT'),
        'micros_por_grupo_ca': values.get('MICROS_POR_GRUPO_CA'),
    }

    from string_calculations import analyze_dc_strings

    dc = analyze_dc_strings(modules, inverters, technical)
    values.setdefault('CONFIGURACAO_STRINGS_CC', dc.get('configuracao_strings_text', ''))
    values.setdefault('PROTECAO_CC_DESCRICAO', dc.get('protecao_cc_text', ''))
    values.setdefault('PROTECAO_CA_DESCRICAO', dc.get('protecao_ca_text', ''))
    if dc.get('strings_count'):
        values.setdefault('QTD_STRINGS_INVERSOR', str(dc['strings_count']))
    if dc.get('isc_design_a'):
        values.setdefault(
            'CORRENTE_DEMANDADA_CABO_CC',
            f"{int(round(dc['isc_design_a']))} A",
        )
    topo = dc.get('topology', '')
    if topo == 'micro':
        values.setdefault('DESCRICAO_TIPO_INVERSOR', 'microinversores monofásicos')
        values.setdefault('TIPO_INVERSOR', 'MICRO')
    elif topo == 'string':
        values.setdefault('DESCRICAO_TIPO_INVERSOR', 'inversores string')
        values.setdefault('TIPO_INVERSOR', 'STRING')
    from string_calculations import label_tipo_equipamento_inversor

    mps_raw = numeric_value(values.get('MODULOS_POR_STRING') or dc.get('modules_per_string') or '')
    mps = int(float(mps_raw)) if mps_raw else None
    values.setdefault(
        'TIPO_EQUIPAMENTO_INVERSOR',
        label_tipo_equipamento_inversor(
            values.get('TIPO_INVERSOR'),
            topo or None,
            mps,
        ),
    )


def load_defaults(path: Path) -> dict:
    from config_loader import load_project_defaults
    return load_project_defaults(path)


def format_thd_dht(value) -> str:
    """Formata THD/DHT do inversor para o memorial (ex.: <3%)."""
    if value in (None, ''):
        return '<3%'
    text = str(value).strip()
    if text.startswith('<'):
        return text if '%' in text else f'{text}%'
    try:
        cleaned = re.sub(r'[^\d.,]', '', text).replace(',', '.')
        n = float(cleaned)
        if n <= 3:
            return '<3%'
        return f'≤{n:g}%'
    except (ValueError, TypeError):
        return text if '%' in text else f'{text}%'


def format_tensao_atendimento(value) -> str:
    """Normaliza tensão para memorial — ex.: 220V → 220 V (evita 220VV)."""
    if value in (None, ''):
        return ''
    text = re.sub(r'(?i)\s*V+\s*$', '', str(value).strip()).strip()
    return f'{text} V' if text else ''


def tensao_nominal_numero(value) -> str:
    """Parte numérica da tensão (sem V) — para {{TENSAO_NOMINAL}} V no template."""
    if value in (None, ''):
        return ''
    return re.sub(r'(?i)\s*V+\s*$', '', str(value).strip()).strip()


def vn_fase_neutro(value, default: float = 220.0) -> float:
    """VN fase-neutro (220 V em GO) — PD e corrente de microinversores trifásicos."""
    if value in (None, ''):
        return default
    nums = [float(n) for n in re.findall(r'\d{2,3}', str(value))]
    return min(nums) if nums else default


# Área unitária típica de módulo FV (m²) — memorial + NT.00020-05 quando não informada
DEFAULT_AREA_MODULO_M2 = 2.5
DEFAULT_NUMERO_ENDERECO = 'S/N'


def ensure_numero_endereco(values: dict[str, str]) -> None:
    """Endereço sem número explícito → S/N (padrão Equatorial)."""
    if not str(values.get('ENDERECO') or values.get('LOGRADOURO') or '').strip():
        return
    if not str(values.get('NUMERO') or '').strip():
        values['NUMERO'] = DEFAULT_NUMERO_ENDERECO


def _parse_tipo_ligacao_from_text(text: str) -> str | None:
    v = normalize_label(text)
    if 'trifas' in v or re.search(r'\btri\b', v):
        return 'TRIFASICO'
    if 'bifas' in v or re.search(r'\bbi\b', v):
        return 'BIFASICO'
    if 'monofas' in v or re.search(r'\bmono\b', v):
        return 'MONOFASICO'
    return None


def _parse_tensao_atendimento_from_text(text: str, tipo_ligacao: str | None = None) -> str | None:
    raw = str(text or '')
    v = raw.upper().replace(' ', '')
    if '220/380' in v or ('220' in v and '380' in v):
        return '220/380V'
    tipo = (tipo_ligacao or _parse_tipo_ligacao_from_text(raw) or '').upper()
    if '380' in v and tipo == 'TRIFASICO':
        return '220/380V'
    if '127' in v:
        return '127V'
    if '220' in v or '380' in v:
        return '220V'
    return None


def _extract_disjuntor_a(value: str) -> str | None:
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*a\b', str(value or ''), re.I)
    if match:
        return match.group(1).replace(',', '.')
    digits = re.sub(r'[^\d.,]', '', str(value or ''))
    return digits or None


def apply_ligacao_existente(values: dict[str, str]) -> None:
    """Ligação Existente / Padrão de Conexão — TRI, 380 V, B1 residencial."""
    raw = values.get('LIGACAO_EXISTENTE') or values.get('PADRAO_CONEXAO') or ''
    if not raw:
        return
    tipo = _parse_tipo_ligacao_from_text(raw)
    if tipo:
        values.setdefault('TIPO_LIGACAO', tipo)
    tensao = _parse_tensao_atendimento_from_text(raw, tipo)
    if tensao:
        values.setdefault('TENSAO_ATENDIMENTO', tensao)
    if re.search(r'\bb1\b', raw, re.I):
        values.setdefault('CLASSE', 'Residencial')


def normalize_disjuntor_entrada(values: dict[str, str]) -> None:
    raw = values.get('DISJUNTOR_ENTRADA')
    if not raw:
        return
    tipo = _parse_tipo_ligacao_from_text(raw)
    if tipo:
        values.setdefault('TIPO_LIGACAO', tipo)
    cleaned = _extract_disjuntor_a(raw)
    if cleaned:
        values['DISJUNTOR_ENTRADA'] = cleaned

_AMPACITY_MM2_A: dict[str, int] = {
    '4': 35, '6': 45, '10': 55, '16': 70, '25': 95, '35': 120,
}


def capacidade_conducao_a(bitola: str) -> str:
    match = re.search(r'(\d+)', str(bitola or '4'))
    key = match.group(1) if match else '4'
    return f"{_AMPACITY_MM2_A.get(key, 35)} A"


def capacidade_conducao_tabela_cc(bitola: str) -> str:
    match = re.search(r'(\d+)', str(bitola or '4'))
    key = match.group(1) if match else '4'
    amps = _AMPACITY_MM2_A.get(key, 35)
    return f'~{amps} A (em condição padrão: 30°C, livre no ar)'


def capacidade_conducao_tabela_ca(bitola: str) -> str:
    match = re.search(r'(\d+)', str(bitola or '4'))
    key = match.group(1) if match else '4'
    amps = _AMPACITY_MM2_A.get(key, 35)
    return f'~{amps} A (30°C, livre no ar)'


def _memorial_num(value: float, decimals: int = 2) -> str:
    """Formata número para memorial (vírgula decimal)."""
    if decimals <= 0:
        return str(int(round(value)))
    fmt = f'{{:.{decimals}f}}'.format(value)
    return fmt.rstrip('0').rstrip('.').replace('.', ',')


def _apply_secao_54_pd_tokens(
    values: dict[str, str],
    *,
    system_type: str,
    v_ln: float,
    v_ll: float,
    uf: str | None,
) -> None:
    """Tokens narrativos da seção 5.4 — PD (GO: mono e trifásico)."""
    from normas_loader import calc_pd_kva_kw

    uf_k = (uf or 'GO').upper()[:2]
    idg_txt = numeric_value(values.get('CORRENTE_ENTRADA') or values.get('DISJUNTOR_ENTRADA') or '')
    if not idg_txt:
        try:
            from normas_loader import get_padrao_entrada

            padrao = get_padrao_entrada(uf_k, values.get('TIPO_LIGACAO'))
            if padrao and padrao.get('disjuntor_a'):
                idg_txt = str(padrao['disjuntor_a'])
                values.setdefault('DISJUNTOR_ENTRADA', idg_txt)
                values.setdefault('CORRENTE_ENTRADA', idg_txt)
        except ImportError:
            pass
    fp_txt = numeric_value(values.get('FATOR_POTENCIA') or '0.92')
    if not idg_txt or not fp_txt:
        return

    idg = float(idg_txt)
    fp = float(fp_txt)

    kva, kw = calc_pd_kva_kw(uf_k, values.get('TIPO_LIGACAO'), idg, fp)
    pd_w = kw * 1000

    if system_type == 'trifasico' and uf_k == 'GO':
        values.setdefault('FORMULA_PD', 'P = √3 × V_FF × IDG × FP')
        values.setdefault(
            'TEXTO_PD_PARAMETROS',
            f'• V_FN (Tensão fase-neutro): {_memorial_num(v_ln, 0)} V\n'
            f'• V_FF (Tensão fase-fase): {_memorial_num(v_ll, 0)} V\n'
            f'• IDG (Corrente de linha / disjuntor geral): {_memorial_num(idg, 0)} A\n'
            f'• FP (Fator de Potência): {_memorial_num(fp, 2)}\n'
            f'• Sistema trifásico equilibrado',
        )
        values.setdefault(
            'CALCULO_PD',
            f'PD = √3 × {_memorial_num(v_ll, 0)} × {_memorial_num(idg, 0)} × '
            f'{_memorial_num(fp, 2)} = {_memorial_num(pd_w, 0)} W '
            f'({_memorial_num(kw, 2)} kW)',
        )
    else:
        values.setdefault('FORMULA_PD', 'P = V × IDG × FP')
        values.setdefault(
            'TEXTO_PD_PARAMETROS',
            f'• V (Tensão Nominal): {_memorial_num(v_ln, 0)} V fase/neutro\n'
            f'• IDG (Corrente do Disjuntor Geral): {_memorial_num(idg, 0)} A\n'
            f'• FP (Fator de Potência): {_memorial_num(fp, 2)}',
        )
        values.setdefault(
            'CALCULO_PD',
            f'PD = {_memorial_num(v_ln, 0)} × {_memorial_num(idg, 0)} × '
            f'{_memorial_num(fp, 2)} = {_memorial_num(pd_w, 0)} W '
            f'({_memorial_num(kw, 2)} kW)',
        )

    values.setdefault('POTENCIA_DISP_KVA', _memorial_num(kva, 2))
    values.setdefault('POTENCIA_DISP_KW', _memorial_num(kw, 2))
    values.setdefault('POTENCIA_DISPONIBILIZADA', _memorial_num(kw, 2))
    values.setdefault('POTENCIA_DISPONIBILIZADA_FORMATADA', f"{_memorial_num(kw, 2)} kW")
    values.setdefault('POTENCIA_DISP_KW_W', _memorial_num(pd_w, 0))


def _recommend_qdca_breaker(i_sys: float, bitola_ca: str | None = None) -> int:
    """Disjuntor QDCA: comercial ≥ corrente de projeto, respeitando ampacidade do cabo."""
    from nbr5410_calculations import STANDARD_BREAKERS_A, standard_breaker_rating

    disj = standard_breaker_rating(i_sys)
    if bitola_ca:
        match = re.search(r'(\d+)', str(bitola_ca))
        if match:
            amp = _AMPACITY_MM2_A.get(match.group(1), 999)
            if disj > amp:
                for rating in reversed(STANDARD_BREAKERS_A):
                    if rating <= amp and rating >= i_sys:
                        return rating
    return disj


def build_values(raw: dict[str, str], defaults: dict) -> dict[str, str]:
    values: dict[str, str] = dict(raw)
    if values.get('TABELA_DEMANDA'):
        values['TABELA_DEMANDA'] = values['TABELA_DEMANDA'].replace(' {{NL}} ', '\n')
    if values.get('TEXTO_VALOR_PAGAMENTO_CONTRATO'):
        values['TEXTO_VALOR_PAGAMENTO_CONTRATO'] = values[
            'TEXTO_VALOR_PAGAMENTO_CONTRATO'
        ].replace(' {{NL}} ', '\n')
    if values.get('TABELA_DEMANDA_JSON'):
        values['__DEMAND_TABLE_JSON__'] = values.pop('TABELA_DEMANDA_JSON')

    apply_ligacao_existente(values)
    normalize_disjuntor_entrada(values)

    if 'CPF' in values:
        values['CPF'] = format_cpf(values['CPF'])
    if 'CEP' in values:
        values['CEP'] = format_cep(values['CEP'])
    if values.get('TELEFONE_CELULAR'):
        values['TELEFONE_CELULAR'] = format_telefone_celular(values['TELEFONE_CELULAR'])
    if values.get('CONTA_CONTRATO'):
        uc_raw = values['CONTA_CONTRATO']
        digits = normalize_conta_contrato(uc_raw)
        values['CONTA_CONTRATO_DIGITOS'] = digits
        values['CONTA_CONTRATO'] = digits
        if digits:
            values.setdefault('CONTA_CONTRATO_FORMATADA', format_conta_contrato(uc_raw))
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
    ensure_numero_endereco(values)
    values.setdefault('COMPLEMENTO', '')
    values.setdefault('TELEFONE_FIXO', '')

    procurador = defaults.get('procurador', {})
    tecnico = defaults.get('responsavel_tecnico', {})
    procuracao = defaults.get('procuracao', {})
    cabos = defaults.get('cabos', {})
    modulos_cfg = defaults.get('modulos', {})
    area_modulo_default = float(modulos_cfg.get('area_modulo_m2', DEFAULT_AREA_MODULO_M2))
    testemunhas = defaults.get('testemunhas', {})
    pagamento = defaults.get('pagamento_integrador', {})

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
    values.setdefault('OBJETO_PROCURACAO', procuracao.get('objeto', 'Energia Fotovoltaica'))
    values.setdefault('CIDADE_DOCUMENTO', values.get('CIDADE', procuracao.get('cidade_documento', '')))
    if values.get('CIDADE_DOCUMENTO') and not values.get('UF'):
        values.setdefault('UF', procuracao.get('uf_documento', 'GO'))
    values.setdefault('DATA_DOCUMENTO', procuracao.get('data_documento', ''))
    values.setdefault('NUMERO_CONTRATO', procuracao.get('numero_contrato', ''))

    values.setdefault('NOME_TESTEMUNHA_1', testemunhas.get('nome_1', ''))
    values.setdefault('NOME_TESTEMUNHA_2', testemunhas.get('nome_2', ''))
    values.setdefault('CPF_TESTEMUNHA_1', testemunhas.get('cpf_1', ''))
    values.setdefault('CPF_TESTEMUNHA_2', testemunhas.get('cpf_2', ''))

    values.setdefault('FORMA_PAGAMENTO', pagamento.get('forma_pagamento', ''))
    values.setdefault('BANCO', pagamento.get('banco', ''))
    values.setdefault('AGENCIA', pagamento.get('agencia', ''))
    values.setdefault('CONTA', pagamento.get('conta', ''))
    values.setdefault('CNPJ_INTEGRADOR', pagamento.get('cnpj_integrador', ''))
    values.setdefault('PIX_INTEGRADOR', pagamento.get('pix_integrador', ''))
    values.setdefault('NOME_INTEGRADOR', pagamento.get('nome_integrador', ''))
    values.setdefault('NOME_CONTRATANTE', values.get('NOME_CLIENTE', ''))
    _integ_addr: list[str] = []
    for part in (
        procurador.get('endereco'),
        procurador.get('bairro'),
        f"{procurador.get('cidade', '')}/{procurador.get('uf', '')}".strip('/'),
        procurador.get('cep'),
    ):
        if part and str(part).strip():
            _integ_addr.append(str(part).strip())
    if _integ_addr:
        values.setdefault('ENDERECO_INTEGRADOR', ', '.join(_integ_addr))
    values.setdefault('TELEFONE_INTEGRADOR', procurador.get('telefone', ''))
    values.setdefault('EMAIL_INTEGRADOR', procurador.get('email', ''))
    if not values.get('DATA_DOCUMENTO'):
        values['DATA_DOCUMENTO'] = datetime.now().strftime('%d/%m/%Y')
    if values.get('DATA_DOCUMENTO'):
        values.setdefault('DATA_DOCUMENTO_EXTENSO', date_extended(values.get('DATA_DOCUMENTO')))
        values.setdefault('DATA', values['DATA_DOCUMENTO'])
    if values.get('DATA_DOCUMENTO') and not values.get('DATA_OPERACAO'):
        values['DATA_OPERACAO'] = values['DATA_DOCUMENTO']

    # Campos derivados para Memorial Descritivo
    values.setdefault('ESTADO_CONCESSAO', values.get('UF', 'GO'))
    if values.get('ENDERECO') or values.get('LOGRADOURO'):
        endereco = values.get('ENDERECO') or values.get('LOGRADOURO', '')
        numero = values.get('NUMERO', '')
        if numero and numero not in endereco:
            endereco = f'{endereco}, Nº {numero}'
        values.setdefault('ENDERECO_COMPLETO', endereco)
    else:
        values.setdefault('ENDERECO_COMPLETO', values.get('ENDERECO', ''))

    # NT.00020-05 — endereço UC (logradouro + nº + complemento + bairro)
    addr_uc: list[str] = []
    base = values.get('ENDERECO') or values.get('LOGRADOURO') or ''
    if base:
        addr_uc.append(base)
    num = str(values.get('NUMERO') or '').strip()
    if num and num not in base:
        addr_uc.append(num if num.upper().startswith('N') else f'Nº {num}')
    comp = str(values.get('COMPLEMENTO') or '').strip()
    if comp:
        addr_uc.append(comp)
    bairro = str(values.get('BAIRRO') or '').strip()
    if bairro:
        addr_uc.append(bairro)
    if addr_uc:
        values.setdefault('ENDERECO_UC', ', '.join(addr_uc))

    # NT.00020-05 — RG + órgão emissor (+ UF se houver)
    rg_parts = [str(values.get('RG') or '').strip()]
    org = str(values.get('ORGAO_EMISSOR_RG') or '').strip()
    uf_rg = str(values.get('UF_RG') or '').strip()
    if org:
        rg_parts.append(org)
    if uf_rg and uf_rg not in org:
        rg_parts.append(uf_rg)
    rg_full = ' '.join(p for p in rg_parts if p)
    if rg_full:
        values.setdefault('RG_COMPLETO', rg_full)
    values.setdefault('POTENCIA_INVERSOR_UNITARIO', values.get('POTENCIA_INVERSOR', ''))

    # Eficiência módulo — garantir token mesmo com rótulo alternativo ou valor só no form
    if not values.get('EFICIENCIA_MODULO'):
        for alt in ('EFICIENCIA_MODULO', 'EFICIENCIA', 'RENDIMENTO_MODULO'):
            if values.get(alt):
                values['EFICIENCIA_MODULO'] = values[alt]
                break
    if values.get('EFICIENCIA_MODULO'):
        ef = numeric_value(values['EFICIENCIA_MODULO']) or str(values['EFICIENCIA_MODULO']).replace('%', '').strip()
        values['EFICIENCIA_MODULO'] = ef

    values.setdefault('NUM_POSTE', 'ilégível')

    thd_src = values.get('THD_CORRENTE_INVERSOR') or values.get('DHT')
    thd_fmt = format_thd_dht(thd_src or '3')
    values['THD_CORRENTE_INVERSOR'] = thd_fmt
    values['DHT'] = thd_fmt

    from coordinate_utils import enrich_coordinate_tokens
    enrich_coordinate_tokens(values)
    values.setdefault('FUSO_UTM', values.get('FUSO_UTM', '22S'))

    if values.get('DISJUNTOR_ENTRADA') and not values.get('CORRENTE_ENTRADA'):
        values['CORRENTE_ENTRADA'] = values['DISJUNTOR_ENTRADA']
    if values.get('DISJUNTOR_ENTRADA'):
        disj_pad = str(values['DISJUNTOR_ENTRADA']).strip().upper().removesuffix('A').strip()
        values.setdefault('DISJUNTOR_CA_PADRAO_A', disj_pad)
        values.setdefault('TEXTO_DISJUNTOR_CA_PADRAO', f'Disjuntor {disj_pad}A')
    if values.get('DISJUNTOR_ENTRADA') and not values.get('CORRENTE_NOMINAL_DISJUNTOR'):
        values.setdefault('CORRENTE_NOMINAL_DISJUNTOR', values['DISJUNTOR_ENTRADA'])
    if values.get('NUM_POLOS_DISJUNTOR') and not values.get('DESCRICAO_POLOS_DISJUNTOR'):
        num_polos = str(values['NUM_POLOS_DISJUNTOR'])
        desc_map = {'1': 'Unipolar', '2': 'Bipolar', '3': 'Tripolar', '4': 'Tetrapolar'}
        values.setdefault('DESCRICAO_POLOS_DISJUNTOR', desc_map.get(num_polos, f'{num_polos} polos'))
    if values.get('TENSAO_MPPT_MIN_INVERSOR') and values.get('TENSAO_MPPT_MAX_INVERSOR'):
        values.setdefault(
            'FAIXA_TENSAO_MPPT_INVERSOR',
            f"{values['TENSAO_MPPT_MIN_INVERSOR']}V - {values['TENSAO_MPPT_MAX_INVERSOR']}V",
        )
        values.setdefault('FAIXA_TENSAO_INVERSOR', values['FAIXA_TENSAO_MPPT_INVERSOR'])
    if values.get('QTD_ENTRADAS_MPPT_INVERSOR') and not values.get('QTD_STRINGS_INVERSOR'):
        values.setdefault('QTD_STRINGS_INVERSOR', values['QTD_ENTRADAS_MPPT_INVERSOR'])
    if values.get('EFICIENCIA_MAX_INVERSOR') and not values.get('RENDIMENTO'):
        values.setdefault('RENDIMENTO', values['EFICIENCIA_MAX_INVERSOR'])

    # Formatações específicas do Memorial
    if values.get('TENSAO_ATENDIMENTO'):
        ta_raw = values['TENSAO_ATENDIMENTO']
        values.setdefault('TENSAO_ATENDIMENTO_FORMATADA', format_tensao_atendimento(ta_raw))
        values.setdefault('TENSAO_NOMINAL', tensao_nominal_numero(ta_raw))

    if values.get('POTENCIA_DISPONIBILIZADA'):
        values.setdefault('POTENCIA_DISPONIBILIZADA_FORMATADA', f"{values['POTENCIA_DISPONIBILIZADA']} kW")

    # Data do documento - Mês e Ano
    if values.get('DATA_DOCUMENTO'):
        parsed_document_date = parse_date(values['DATA_DOCUMENTO'])
        if parsed_document_date:
            values.setdefault('MES_DOCUMENTO', MONTHS_PT[parsed_document_date.month])
            values.setdefault('ANO_DOCUMENTO', str(parsed_document_date.year))

    # Tipo de Ligação → NF (PD), condutores e disjuntor de entrada
    from grid_voltage import resolve_ac_voltage, resolve_ligacao_config, map_inverter_fase

    ligacao = resolve_ligacao_config(values.get('TIPO_LIGACAO'))
    values.setdefault('NUM_FASES', str(ligacao['num_fases']))
    values.setdefault('TIPO_REDE', ligacao['tipo_rede'])
    values.setdefault('QTD_CONDUTORES_FASE', ligacao['qtd_condutores_fase'])
    values.setdefault('QTD_CONDUTORES_NEUTRO', ligacao['qtd_condutores_neutro'])
    values.setdefault('NUM_POLOS_DISJUNTOR', ligacao['num_polos_disjuntor'])
    values.setdefault('DESCRICAO_POLOS_DISJUNTOR', ligacao['descricao_polos'])
    values.setdefault('DESCRICAO_CONEXAO_INVERSORES', ligacao['descricao_conexao_inversores'])
    values.setdefault('DESCRICAO_DISJUNTOR_PADRAO', ligacao['descricao_disjuntor_padrao'])

    volt = resolve_ac_voltage(
        values.get('UF'),
        values.get('TIPO_LIGACAO'),
        values.get('TENSAO_ATENDIMENTO'),
    )
    v_ln = int(volt['voltage_ln_v'])
    v_ll = int(volt['voltage_ll_v'])
    values.setdefault('TENSAO_FASE_NEUTRO', str(v_ln))
    values.setdefault('TENSAO_ENTRE_FASES', str(v_ll))
    ta_raw = values.get('TENSAO_ATENDIMENTO') or ''
    ta_dual = '/' in re.sub(r'(?i)\s*V+\s*$', '', str(ta_raw)).strip()
    if volt['system_type'] == 'trifasico' and not ta_dual:
        ta_fmt = f'{v_ln}/{v_ll} V'
    else:
        ta_fmt = format_tensao_atendimento(
            values.get('TENSAO_ATENDIMENTO_FORMATADA') or ta_raw
        )
        if not ta_fmt:
            ta_fmt = f'{v_ln}/{v_ll} V' if volt['system_type'] == 'trifasico' else f'{v_ln} V'
    values['TENSAO_ATENDIMENTO_FORMATADA'] = ta_fmt
    values.setdefault('TENSAO_NOMINAL_DISJUNTOR', ta_fmt)
    values['TENSAO_NOMINAL'] = str(v_ln)
    if volt['system_type'] == 'trifasico':
        base = re.sub(r'\s*V\s*$', '', ta_fmt, flags=re.I).strip()
        if '/' not in base:
            base = f'{v_ln}/{v_ll}'
        values.setdefault(
            'DESCRICAO_TENSAO_ATENDIMENTO',
            f'{base} V ({v_ln} V fase-neutro, {v_ll} V entre fases)',
        )
    else:
        values.setdefault('DESCRICAO_TENSAO_ATENDIMENTO', f'{v_ln} V')

    _apply_dc_string_analysis(values)

    # Cabos — CC inversor 4 mm², CA inversor 6 mm², CA padrão entrada 10 mm²
    values.setdefault('BITOLA_CABO_CC', cabos.get('bitola_cc', '4 mm²'))
    values.setdefault('BITOLA_CABO_CA', cabos.get('bitola_ca_inversor', '6 mm²'))
    values.setdefault('BITOLA_CABO_PADRAO', cabos.get('bitola_ca_padrao', '10 mm²'))
    values.setdefault('CAPACIDADE_CABO_CC', capacidade_conducao_a(values['BITOLA_CABO_CC']))
    values.setdefault('CAPACIDADE_CABO_CA', capacidade_conducao_a(values['BITOLA_CABO_CA']))
    values.setdefault('CAPACIDADE_CABO_PADRAO', capacidade_conducao_a(values['BITOLA_CABO_PADRAO']))
    values.setdefault('CAPACIDADE_TABELA_CABO_CC', capacidade_conducao_tabela_cc(values['BITOLA_CABO_CC']))
    values.setdefault('CAPACIDADE_TABELA_CABO_CA', capacidade_conducao_tabela_ca(values['BITOLA_CABO_CA']))
    cc_dem = numeric_value(values.get('CORRENTE_MAX_CC_INVERSOR') or values.get('CORRENTE_DEMANDADA_CABO_CC'))
    if cc_dem:
        values.setdefault('CORRENTE_DEMANDADA_CABO_CC', f"{int(float(cc_dem))} A")
    else:
        values.setdefault('CORRENTE_DEMANDADA_CABO_CC', '15 A')

    # Campos de inversor já existentes no sistema
    values.setdefault('FAIXA_TENSAO_INVERSOR', values.get('FAIXA_TENSAO_INVERSOR', ''))
    values.setdefault('FAIXA_FREQUENCIA_INVERSOR', '59,9 - 60,1 Hz')

    # Faixas de tensão específicas do inversor
    if values.get('TENSAO_MIN_CA_INVERSOR') and values.get('TENSAO_MAX_CA_INVERSOR'):
        values.setdefault('FAIXA_TENSAO_CA_INVERSOR',
                         f"{values['TENSAO_MIN_CA_INVERSOR']}V - {values['TENSAO_MAX_CA_INVERSOR']}V")

    if values.get('TENSAO_MPPT_MIN_INVERSOR') and values.get('TENSAO_MPPT_MAX_INVERSOR'):
        values.setdefault('FAIXA_TENSAO_MPPT_INVERSOR',
                         f"{values['TENSAO_MPPT_MIN_INVERSOR']}V - {values['TENSAO_MPPT_MAX_INVERSOR']}V")

    # Campos de disjuntor - descrição dos polos
    if values.get('NUM_POLOS_DISJUNTOR'):
        num_polos = values['NUM_POLOS_DISJUNTOR']
        if num_polos == '1':
            values.setdefault('DESCRICAO_POLOS_DISJUNTOR', 'Unipolar')
        elif num_polos == '2':
            values.setdefault('DESCRICAO_POLOS_DISJUNTOR', 'Bipolar')
        elif num_polos == '3':
            values.setdefault('DESCRICAO_POLOS_DISJUNTOR', 'Tripolar')
        elif num_polos == '4':
            values.setdefault('DESCRICAO_POLOS_DISJUNTOR', 'Tetrapolar')

    # Derived values used by the main Equatorial workbook. They are only
    # calculated when the necessary equipment data is present; otherwise the
    # field remains pending for technical confirmation.
    if not values.get('AREA_MODULO'):
        if values.get('COMPRIMENTO_MODULO') and values.get('LARGURA_MODULO'):
            try:
                values['AREA_MODULO'] = (
                    f"{float(values['COMPRIMENTO_MODULO']) * float(values['LARGURA_MODULO']):g}"
                )
            except (TypeError, ValueError):
                values['AREA_MODULO'] = f'{area_modulo_default:g}'
        else:
            values['AREA_MODULO'] = f'{area_modulo_default:g}'

    try:
        qtd_modulos = float(values.get('QTD_MODULOS', ''))
        potencia_modulo = float(values.get('POTENCIA_MODULO', ''))
        potencia_modulos = qtd_modulos * potencia_modulo / 1000
        values.setdefault('POTENCIA_TOTAL_INSTALADA', f'{potencia_modulos:g}')
        if not values.get('AREA_ARRANJO'):
            area_u = float(values.get('AREA_MODULO') or area_modulo_default)
            values['AREA_ARRANJO'] = f'{qtd_modulos * area_u:g}'
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
            values.setdefault('POTENCIA_GERADOR', f'{potencia_modulos:g}')
        else:
            values.setdefault('POTENCIA_GERACAO', f'{potencia_inversores:g}')
            values.setdefault('POTENCIA_GERADOR', f'{potencia_inversores:g}')
    except (TypeError, ValueError):
        pass

    # Calculate the available power only when all source values are provided.
    try:
        corrente_text = numeric_value(
            values.get('CORRENTE_ENTRADA') or values.get('DISJUNTOR_ENTRADA') or ''
        )
        fp_text = numeric_value(values.get('FATOR_POTENCIA') or '0.92')
        if corrente_text and fp_text:
            _apply_secao_54_pd_tokens(
                values,
                system_type=volt['system_type'],
                v_ln=float(v_ln),
                v_ll=float(v_ll),
                uf=values.get('UF'),
            )
    except (TypeError, ValueError):
        pass

    # Convenient aliases used by the main Equatorial workbook.
    values.setdefault('TIPO_FONTE', 'SOLAR FOTOVOLTAICA')
    values.setdefault('MODALIDADE_COMPENSACAO', 'AUTOCONSUMO LOCAL')
    values.setdefault('ARMAZENAMENTO', 'NÃO')

    # Memorial — tokens derivados (campos +...+ convertidos)
    if values.get('POTENCIA_DISP_KW') and not values.get('POTENCIA_DISP_KW_W'):
        try:
            kw_disp = float(str(values['POTENCIA_DISP_KW']).replace(',', '.'))
            values.setdefault('POTENCIA_DISP_KW_W', _memorial_num(kw_disp * 1000, 0))
        except (TypeError, ValueError):
            pass

    values.setdefault('CLASSE', values.get('CLASSE', 'Residencial'))

    try:
        import math

        pot_kw = float(str(
            values.get('POTENCIA_GERACAO') or values.get('POTENCIA_INVERSOR_TOTAL') or 0
        ).replace(',', '.'))
        v_ln_calc = float(v_ln)
        v_ll_calc = float(v_ll)
        system_type = ligacao['system_type']
        qtd_inv = max(1, int(float(numeric_value(values.get('QTD_INVERSORES') or '1') or 1)))
        tipo_inv = (values.get('TIPO_INVERSOR') or '').upper()
        is_micro = 'MICRO' in tipo_inv
        inv_fase = map_inverter_fase(values.get('FASE_CA'))
        inv_trifasico = inv_fase == 'trifasico' and not is_micro
        curva = values.get('CURVA_ATUACAO_DISJUNTOR') or values.get('disjuntor_curva') or 'C'
        pot_w = pot_kw * 1000
        pot_inv_w = pot_w / qtd_inv

        if pot_kw > 0 and v_ln_calc > 0:
            if system_type == 'trifasico' and is_micro:
                i_sys = pot_w / v_ln_calc
                i_inv = pot_inv_w / v_ln_calc
                formula = (
                    f'I = {_memorial_num(pot_w, 0)} W ÷ {_memorial_num(v_ln_calc, 0)} V = '
                    f'{_memorial_num(i_sys, 2)} A'
                )
                inv_note = (
                    f'I_inversor = {_memorial_num(i_inv, 2)} A por inversor '
                    f'(microinversor monofásico — corrente por equipamento)'
                )
                tensao_saida_txt = (
                    f'{v_ln_calc:g} V (microinversores monofásicos, '
                    f'{ligacao["descricao_conexao_inversores"]})'
                )
            elif system_type == 'trifasico' and inv_trifasico:
                fp_inv = float(numeric_value(values.get('FATOR_POTENCIA_INVERSOR') or '0.99') or 0.99)
                i_sys = pot_w / (v_ll_calc * math.sqrt(3) * fp_inv)
                formula = (
                    f'I = {_memorial_num(pot_kw, 1)} kW / ({_memorial_num(v_ll_calc, 0)} V × √3 × '
                    f'{_memorial_num(fp_inv, 2)}) = {_memorial_num(i_sys, 2)} A'
                )
                inv_note = (
                    f'I_inversor = {_memorial_num(i_sys, 2)} A / {qtd_inv} = '
                    f'{_memorial_num(i_sys / qtd_inv, 2)} A (inversor string trifásico balanceado)'
                )
                tensao_saida_txt = f'{v_ln_calc:g}/{v_ll_calc:g} V'
            elif system_type == 'trifasico':
                i_sys = pot_w / v_ln_calc
                formula = (
                    f'I = {_memorial_num(pot_w, 0)} W ÷ {_memorial_num(v_ln_calc, 0)} V = '
                    f'{_memorial_num(i_sys, 2)} A'
                )
                inv_note = (
                    f'I_inversor = {_memorial_num(i_sys, 2)} A / {qtd_inv} = '
                    f'{_memorial_num(i_sys / qtd_inv, 2)} A '
                    f'(inversor monofásico em 1 fase da rede trifásica)'
                )
                tensao_saida_txt = (
                    f'{v_ln_calc:g} V (inversores string, conectados em fases distintas do '
                    f'sistema trifásico para balanceamento de carga)'
                )
            elif system_type == 'bifasico':
                fp_inv = float(numeric_value(values.get('FATOR_POTENCIA_INVERSOR') or '0.99') or 0.99)
                i_sys = pot_w / (v_ln_calc * fp_inv)
                formula = (
                    f'I = {_memorial_num(pot_kw, 1)} kW / ({_memorial_num(v_ln_calc, 0)} V × '
                    f'{_memorial_num(fp_inv, 2)}) = {_memorial_num(i_sys, 2)} A'
                )
                inv_note = (
                    f'I_inversor = {_memorial_num(i_sys, 2)} A / {qtd_inv} = '
                    f'{_memorial_num(i_sys / qtd_inv, 2)} A (fases distintas — balanceamento bifásico)'
                )
                tensao_saida_txt = f'{v_ln_calc:g} V'
            else:
                fp_inv = float(numeric_value(values.get('FATOR_POTENCIA_INVERSOR') or '0.99') or 0.99)
                i_sys = pot_w / (v_ln_calc * fp_inv)
                formula = (
                    f'I = {_memorial_num(pot_kw, 1)} kW / ({_memorial_num(v_ln_calc, 0)} V × '
                    f'{_memorial_num(fp_inv, 2)}) = {_memorial_num(i_sys, 2)} A'
                )
                inv_note = (
                    f'I_inversor = {_memorial_num(i_sys, 2)} A / {qtd_inv} = '
                    f'{_memorial_num(i_sys / qtd_inv, 2)} A (inversores em paralelo na mesma fase)'
                )
                tensao_saida_txt = f'{v_ln_calc:g} V'
            i_inv = i_sys / qtd_inv if not (system_type == 'trifasico' and is_micro) else pot_inv_w / v_ln_calc
            i_max_ca = float(numeric_value(values.get('CORRENTE_MAX_SAIDA_CA_INVERSOR') or '0') or 0)
            i_max_total = i_max_ca * qtd_inv if i_max_ca else i_sys

            values.setdefault('TENSAO_SAIDA_INVERSOR', tensao_saida_txt)
            values.setdefault('CALCULO_CORRENTE_SISTEMA', formula)
            values.setdefault('CALCULO_CORRENTE_INVERSOR', inv_note)
            values.setdefault(
                'CALCULO_CORRENTE_INVERSORES_TOTAL',
                f'Corrente total dos {qtd_inv} inversores: {i_max_total:.2f} A',
            )
            if i_max_ca:
                bitola_ca = values.get('BITOLA_CABO_CA', '—')
                values.setdefault(
                    'CALCULO_IMAX_CA',
                    f'Imáx-ca (inversor) = {i_max_ca:g} A × {qtd_inv} = {i_max_total:.1f} A → Cabo {bitola_ca}',
                )
            values.setdefault(
                'CALCULO_CORRENTE_CA',
                f'{i_max_ca:g} A × {qtd_inv} = {i_max_total:.1f} A' if i_max_ca else f'{i_sys:.2f} A',
            )

            bitola_ca = values.get('BITOLA_CABO_CA', '6 mm²')
            disj_rec = _recommend_qdca_breaker(i_sys, bitola_ca)
            values.setdefault('DISJUNTOR_CA_INVERSOR_A', str(disj_rec))
            values.setdefault('TEXTO_DISJUNTOR_CA_INVERSOR', f'Disjuntor {disj_rec}A')
            values.setdefault(
                'DISJUNTOR_RECOMENDADO_QDCA',
                f'Disjuntor recomendado: {disj_rec} A (Curva {curva}) — dimensionado conforme '
                f'corrente de projeto ({_memorial_num(i_sys, 2)} A), compatível com cabo {bitola_ca} '
                f'e padronizado para disjuntor comercial imediato.',
            )
            values.setdefault(
                'COMPARATIVO_CORRENTE_DISJUNTOR',
                f'• Corrente total: {_memorial_num(i_sys, 2)} A vs. disjuntor de {disj_rec} A',
            )
            margem = (1 - i_sys / disj_rec) * 100 if disj_rec else 0
            values.setdefault(
                'MARGEM_SEGURANCA_DISJUNTOR',
                f'• Margem de segurança: {_memorial_num(margem, 1)}% '
                f'({_memorial_num(i_sys, 2)} A vs. {disj_rec} A)',
            )
            values.setdefault('CORRENTE_DEMANDADA_CABO_CA', f"{int(round(i_sys))} A")
    except (TypeError, ValueError):
        pass

    if not values.get('CORRENTE_DEMANDADA_CABO_CA'):
        ca_dem = numeric_value(values.get('CORRENTE_INVERSOR') or values.get('CORRENTE_MAX_SAIDA_CA_INVERSOR'))
        if ca_dem:
            values['CORRENTE_DEMANDADA_CABO_CA'] = f"{int(float(ca_dem))} A"
        else:
            values.setdefault('CORRENTE_DEMANDADA_CABO_CA', '20 A')

    tipo_inv = (values.get('TIPO_INVERSOR') or '').lower()
    if 'micro' in tipo_inv:
        values.setdefault('DESCRICAO_TIPO_INVERSOR', 'microinversores monofásicos')
    else:
        values.setdefault('DESCRICAO_TIPO_INVERSOR', 'inversores')

    _apply_tipo_equipamento_inversor(values)

    tipo_rede = values.get('TIPO_REDE', '')
    q_fase = values.get('QTD_CONDUTORES_FASE', values.get('NUM_FASES', ''))
    q_neutro = values.get('QTD_CONDUTORES_NEUTRO', '1')
    if tipo_rede and q_fase:
        try:
            total_cond = int(q_fase) + int(q_neutro or 0)
            values.setdefault(
                'DESCRICAO_CIRCUITO_PADRAO',
                f'Configuração: Circuito {tipo_rede.lower()} a {total_cond} condutores '
                f'({q_fase} fases + {q_neutro} neutro).',
            )
        except (TypeError, ValueError):
            pass

    values.setdefault('FIGURA_LOCALIZACAO', '[Inserir figura / print do mapa da localização]')

    from caixa_medicao import enrich_caixa_medicao_values
    enrich_caixa_medicao_values(values)

    # Formulário NT.00020-05 e memorial — tokens com default explícito
    values.setdefault('DT_EXP', values.get('VALIDADE_CNH') or '05/06/2023')
    if not values.get('VALIDADE_CNH'):
        values['VALIDADE_CNH'] = values['DT_EXP']

    # Campos opcionais — default vazio (memorial + NT.00020-05)
    for _tk in (
        'NOME_TESTEMUNHA_1', 'CPF_TESTEMUNHA_1',
        'NOME_TESTEMUNHA_2', 'CPF_TESTEMUNHA_2',
    ):
        values.setdefault(_tk, '')
    values['POTENCIA_MAX_INJETAVEL'] = ''
    values['TELEFONE_FIXO'] = ''
    _valor_inv = str(values.get('VALOR_INVESTIMENTO') or '').strip()
    _forma_pag = str(values.get('FORMA_PAGAMENTO') or '').strip()
    values['VALOR_INVESTIMENTO'] = ''
    if not str(values.get('TEXTO_VALOR_PAGAMENTO_CONTRATO') or '').strip():
        _pag_lines: list[str] = []
        if _valor_inv:
            _pag_lines.append(
                f"O investimento objeto deste contrato é de R$ {_valor_inv}."
            )
        if _forma_pag:
            _pag_lines.append(_forma_pag)
        if _pag_lines:
            values['TEXTO_VALOR_PAGAMENTO_CONTRATO'] = '\n'.join(_pag_lines)

    # Memorial L~409 — tabela DPS, linha "Corrente Nominal [A]" (In do DPS, tip. 32 A)
    if not values.get('CORRENTE_PROTECAO_CA'):
        idg = numeric_value(values.get('DISJUNTOR_ENTRADA') or values.get('CORRENTE_ENTRADA') or '40')
        values['CORRENTE_PROTECAO_CA'] = str(int(min(float(idg or 40), 32)))

    return values


def token_replacer(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = normalize_token(match.group(1))
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
        key = normalize_token(match.group(1))
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


def _paragraph_text(paragraph) -> str:
    return ''.join(paragraph.xpath('.//w:t/text()', namespaces=NS_W))


def _insert_demand_table_at_token(root, values: dict[str, str]) -> bool:
    """Substitui parágrafo {{TABELA_DEMANDA}} por tabela Word real quando há JSON estruturado."""
    from demand_table_docx import build_demand_table_elements, parse_demand_table_payload

    payload = values.pop('__DEMAND_TABLE_JSON__', None)
    demand_data = parse_demand_table_payload(payload)
    if not demand_data:
        return False

    token = '{{TABELA_DEMANDA}}'
    for paragraph in root.xpath('.//w:p', namespaces=NS_W):
        if token not in _paragraph_text(paragraph):
            continue
        parent = paragraph.getparent()
        if parent is None:
            continue
        idx = parent.index(paragraph)
        parent.remove(paragraph)
        for offset, element in enumerate(build_demand_table_elements(demand_data)):
            parent.insert(idx + offset, element)
        values['TABELA_DEMANDA'] = ''
        return True
    return False


def fill_docx(source: Path, destination: Path, values: dict[str, str]) -> set[str]:
    unresolved: set[str] = set()
    doc_values = dict(values)
    with ZipFile(source, 'r') as source_zip, ZipFile(destination, 'w', ZIP_DEFLATED) as target_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                try:
                    root = etree.fromstring(data)
                    if item.filename == 'word/document.xml':
                        _insert_demand_table_at_token(root, doc_values)
                    for paragraph in root.xpath('.//w:p', namespaces=NS_W):
                        replace_tokens_in_text_nodes(paragraph.xpath('.//w:t', namespaces=NS_W), doc_values)
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
    if path.name.startswith('~$'):
        return tokens
    try:
        with ZipFile(path, 'r') as archive:
            for name in archive.namelist():
                if name.startswith('word/') and name.endswith('.xml'):
                    tokens.update(TOKEN_RE.findall(archive.read(name).decode('utf-8', errors='ignore')))
    except Exception:
        return set()
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


def _find_worksheet_cell(root, ref: str):
    for cell in root.findall(f'.//{{{S_NS}}}c'):
        if cell.get('r') == ref:
            return cell
    return None


def _worksheet_cell_text(cell) -> str:
    if cell is None:
        return ''
    if cell.get('t') == 'inlineStr':
        return ''.join(cell.xpath('.//s:t/text()', namespaces=NS_S)).strip()
    value_node = cell.find(f'{{{S_NS}}}v')
    if value_node is not None and value_node.text is not None:
        return str(value_node.text).strip()
    return ''


def _worksheet_cell_float(root, ref: str) -> float | None:
    cell = _find_worksheet_cell(root, ref)
    if cell is None:
        return None
    text = _worksheet_cell_text(cell)
    if not text or text.startswith('{{'):
        return None
    parsed = numeric_value(text)
    if parsed is None:
        return None
    try:
        return float(parsed)
    except (TypeError, ValueError):
        return None


def _set_formula_cached_value(cell, value: float | None) -> None:
    if cell is None or cell.find(f'{{{S_NS}}}f') is None:
        return
    cache = cell.find(f'{{{S_NS}}}v')
    if cache is None:
        cache = etree.SubElement(cell, f'{{{S_NS}}}v')
    cache.text = '' if value is None else f'{value:g}'


def _sum_range(root, col_start: str, col_end: str, row_start: int, row_end: int) -> float:
    cols = [chr(c) for c in range(ord(col_start), ord(col_end) + 1)]
    total = 0.0
    found = False
    for row in range(row_start, row_end + 1):
        for col in cols:
            val = _worksheet_cell_float(root, f'{col}{row}')
            if val is not None:
                total += val
                found = True
    return total if found else 0.0


def _recalc_guia0_formulas(root) -> dict[str, float]:
    """Atualiza cache (<v>) das fórmulas da GUIA 0 (módulos/inversores)."""
    derived: dict[str, float] = {}
    k_total = 0.0
    k_any = False
    for row in range(7, 17):
        pot_w = _worksheet_cell_float(root, f'D{row}')
        qtd = _worksheet_cell_float(root, f'H{row}')
        k_cell = _find_worksheet_cell(root, f'K{row}')
        if pot_w is not None and qtd is not None:
            kwp = pot_w * qtd / 1000.0
            _set_formula_cached_value(k_cell, kwp)
            k_total += kwp
            k_any = True
        else:
            _set_formula_cached_value(k_cell, None)

    if k_any:
        derived['K17'] = k_total
        _set_formula_cached_value(_find_worksheet_cell(root, 'K17'), k_total)
    else:
        _set_formula_cached_value(_find_worksheet_cell(root, 'K17'), None)

    h_total = _sum_range(root, 'H', 'J', 7, 16)
    _set_formula_cached_value(_find_worksheet_cell(root, 'H17'), h_total or None)
    if h_total:
        derived['H17'] = h_total

    p_total = _sum_range(root, 'P', 'S', 7, 16)
    _set_formula_cached_value(_find_worksheet_cell(root, 'P17'), p_total or None)
    if p_total:
        derived['P17'] = p_total

    l_total = _sum_range(root, 'L', 'O', 22, 51)
    _set_formula_cached_value(_find_worksheet_cell(root, 'L52'), l_total or None)
    if l_total:
        derived['L52'] = l_total

    return derived


def _worksheet_cell_resolved(cell, shared_strings: list[str]) -> str:
    if cell is None:
        return ''
    shared = cell_value_from_shared(cell, shared_strings)
    if shared is not None:
        return shared.strip()
    if cell.get('t') == 'inlineStr':
        return ''.join(cell.xpath('.//s:t/text()', namespaces=NS_S)).strip()
    value_node = cell.find(f'{{{S_NS}}}v')
    if value_node is not None and value_node.text is not None:
        return str(value_node.text).strip()
    return ''


def _worksheet_cell_resolved_float(root, ref: str, shared_strings: list[str]) -> float | None:
    text = _worksheet_cell_resolved(_find_worksheet_cell(root, ref), shared_strings)
    if not text or text.startswith('{{'):
        return None
    parsed = numeric_value(text)
    if parsed is None:
        return None
    try:
        return float(parsed)
    except (TypeError, ValueError):
        return None


def _recalc_pd_uc_guia1(root, shared_strings: list[str], values: dict[str, str]) -> None:
    """
    Atualiza cache de AB29 — Potência Disponibilizada (PD) para a UC.
    Fórmula nativa do Excel depende de Q15 (UF), T27, AC27 e P29; após tokens,
    recalculamos via normas GO para o valor aparecer sem F9 manual.
    """
    uf = _worksheet_cell_resolved(_find_worksheet_cell(root, 'Q15'), shared_strings)
    if not uf or uf.startswith('{{'):
        uf = str(values.get('UF') or '').strip()
    tipo = _worksheet_cell_resolved(_find_worksheet_cell(root, 'T27'), shared_strings)
    if not tipo or tipo.startswith('{{'):
        tipo = str(values.get('TIPO_LIGACAO') or '').strip()
    disj = _worksheet_cell_resolved_float(root, 'P29', shared_strings)
    if disj is None:
        parsed = numeric_value(values.get('DISJUNTOR_ENTRADA') or '')
        disj = float(parsed) if parsed else None
    if not uf or not tipo or disj is None:
        return
    try:
        import math

        from normas_loader import calc_pd_max_kw

        pd = calc_pd_max_kw(uf, tipo, disj)
        if pd is None:
            return
        pd_out = float(math.floor(pd + 1e-9))
        _set_formula_cached_value(_find_worksheet_cell(root, 'AB29'), pd_out)
    except Exception:
        pass


def _recalc_guia1_formulas(root, guia0: dict[str, float]) -> None:
    """Atualiza Potência Geração do Orçamento / PGT (GUIA 1)."""
    fonte = _worksheet_cell_text(_find_worksheet_cell(root, 'G49')).upper()
    k17 = guia0.get('K17', 0.0)
    l52 = guia0.get('L52', 0.0)

    ac53 = None
    if fonte == 'SOLAR FOTOVOLTAICA' and (k17 or l52):
        if k17 and l52:
            ac53 = min(k17, l52)
        else:
            ac53 = k17 or l52
    _set_formula_cached_value(_find_worksheet_cell(root, 'AC53'), ac53)

    ac21 = _worksheet_cell_float(root, 'AC21')
    if ac53 is not None:
        ac55 = (ac21 or 0.0) + ac53
        _set_formula_cached_value(_find_worksheet_cell(root, 'AC55'), ac55)


def _patch_workbook_calc_pr(data: bytes) -> bytes:
    """Garante recálculo ao abrir no Excel sem quebrar XML (ex.: calcPr auto-fechado)."""
    if b'fullCalcOnLoad' in data:
        return data
    root = etree.fromstring(data)
    calc_pr = root.find(f'{{{S_NS}}}calcPr')
    if calc_pr is not None:
        calc_pr.set('fullCalcOnLoad', '1')
        calc_pr.set('calcMode', 'auto')
    else:
        calc_pr = etree.Element(f'{{{S_NS}}}calcPr')
        calc_pr.set('calcMode', 'auto')
        calc_pr.set('fullCalcOnLoad', '1')
        sheets = root.find(f'{{{S_NS}}}sheets')
        if sheets is not None:
            root.insert(list(root).index(sheets), calc_pr)
        else:
            root.append(calc_pr)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def _workbook_needs_xlsx_package(source: Path, destination: Path) -> bool:
    """XLT(X) salvo como .xlsx exige ContentType de planilha, não de template."""
    return source.suffix.lower() == '.xltx' or destination.suffix.lower() == '.xlsx'


def _patch_workbook_package_bytes(filename: str, data: bytes, *, as_xlsx: bool) -> bytes:
    if filename == '[Content_Types].xml':
        text = data.decode('utf-8')
        # Remover referência ao calcChain.xml para evitar erros ao abrir no Excel
        text = re.sub(
            r'<Override\s+PartName="/xl/calcChain\.xml"[^>]*/>',
            '',
            text,
        )
        if as_xlsx:
            text = text.replace(
                'application/vnd.openxmlformats-officedocument.spreadsheetml.template.main+xml',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
            )
        return text.encode('utf-8')
    return data


def fill_workbook(source: Path, destination: Path, values: dict[str, str]) -> set[str]:
    unresolved: set[str] = set()
    as_xlsx = _workbook_needs_xlsx_package(source, destination)
    guia0_derived: dict[str, float] = {}
    with ZipFile(source, 'r') as source_zip, ZipFile(destination, 'w', ZIP_DEFLATED) as target_zip:
        has_shared_strings = 'xl/sharedStrings.xml' in source_zip.namelist()
        shared_strings: list[str] = []
        if has_shared_strings:
            shared_root = etree.fromstring(source_zip.read('xl/sharedStrings.xml'))
            shared_strings = [shared_string_text(si) for si in shared_root.findall(f'{{{S_NS}}}si')]
        else:
            shared_root = etree.Element(
                f'{{{S_NS}}}sst',
                count='0',
                uniqueCount='0',
            )

        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            # Remover calcChain.xml para evitar erros ao abrir no Excel
            if item.filename == 'xl/calcChain.xml':
                continue
            if item.filename == 'xl/sharedStrings.xml':
                if has_shared_strings:
                    data = etree.tostring(shared_root, xml_declaration=True, encoding='UTF-8', standalone=True)
                else:
                    continue
            elif item.filename.startswith('xl/worksheets/') and item.filename.endswith('.xml'):
                try:
                    data = transform_worksheet(
                        data,
                        shared_strings,
                        shared_root,
                        values,
                        unresolved,
                        sheet_path=item.filename,
                        guia0_derived=guia0_derived,
                    )
                except etree.XMLSyntaxError:
                    pass
            elif item.filename == 'xl/workbook.xml':
                data = _patch_workbook_calc_pr(data)
            data = _patch_workbook_package_bytes(item.filename, data, as_xlsx=as_xlsx)
            target_zip.writestr(item, data)

    return unresolved


def _trim_guia0_inverter_rows(root, values: dict[str, str]) -> None:
    """Mantém só QTD_INVERSORES linhas preenchidas na GUIA 0 (evita SUM inflado)."""
    try:
        qtd = int(float(numeric_value(values.get('QTD_INVERSORES') or '1') or 1))
    except (TypeError, ValueError):
        qtd = 1
    first_row, last_row = 22, 31
    qtd = max(1, min(qtd, last_row - first_row + 1))
    inv_cols = {'D', 'H', 'L', 'P', 'T', 'W', 'Z', 'AC'}
    for cell in root.findall(f'.//{{{S_NS}}}c'):
        ref = cell.get('r') or ''
        match = re.match(r'([A-Z]+)(\d+)', ref)
        if not match:
            continue
        col, row = match.group(1), int(match.group(2))
        if col in inv_cols and first_row + qtd <= row <= last_row:
            formula = cell.find(f'{{{S_NS}}}f')
            if formula is not None:
                cell.remove(formula)
            set_numeric_cell(cell, '')


def transform_worksheet(
    data: bytes,
    shared_strings: list[str],
    shared_root,
    values: dict[str, str],
    unresolved: set[str],
    *,
    sheet_path: str = '',
    guia0_derived: dict[str, float] | None = None,
) -> bytes:
    root = etree.fromstring(data)
    shared_items = shared_root.findall(f'{{{S_NS}}}si')
    for cell in root.findall(f'.//{{{S_NS}}}c'):
        current = cell_value_from_shared(cell, shared_strings)
        if current is not None:
            token_match = re.fullmatch(r'\{\{([A-Za-z0-9_]+)\}\}', current.strip())
            if token_match:
                key = normalize_token(token_match.group(1))
                if key in values:
                    raw = values[key]
                    if key in NUMERIC_KEYS:
                        num = numeric_value(raw)
                        if num is not None:
                            set_numeric_cell(cell, num)
                        elif key in OPTIONAL_KEYS or str(raw or '').strip() == '':
                            set_numeric_cell(cell, '')
                        else:
                            value_node = cell.find(f'{{{S_NS}}}v')
                            if value_node is not None:
                                set_shared_string(shared_items[int(value_node.text)], str(raw))
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
            inline_text = ''.join(
                (node.text or '') for node in cell.xpath('.//s:t', namespaces=NS_S)
            )
            token_match = re.fullmatch(r'\{\{([A-Za-z0-9_]+)\}\}', inline_text.strip())
            if token_match:
                key = normalize_token(token_match.group(1))
                if key in values:
                    raw = values[key]
                    if key in NUMERIC_KEYS:
                        num = numeric_value(raw)
                        if num is not None:
                            set_numeric_cell(cell, str(num))
                        else:
                            set_numeric_cell(cell, '')
                    else:
                        nodes = cell.xpath('.//s:t', namespaces=NS_S)
                        if nodes:
                            nodes[0].text = str(raw)
                            for node in nodes[1:]:
                                node.text = ''
                else:
                    unresolved.add(key)
            else:
                for text_node in cell.xpath('.//s:t', namespaces=NS_S):
                    if text_node.text:
                        text_node.text = token_replacer(text_node.text, values)
    if sheet_path.endswith('sheet2.xml'):
        _trim_guia0_inverter_rows(root, values)
        derived = _recalc_guia0_formulas(root)
        if guia0_derived is not None:
            guia0_derived.update(derived)
    elif sheet_path.endswith('sheet3.xml'):
        if guia0_derived is not None:
            _recalc_guia1_formulas(root, guia0_derived)
        _recalc_pd_uc_guia1(root, shared_strings, values)
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
    for template in iter_document_templates(args.templates_dir):
        destination = args.output_dir / template.name
        if template.suffix.lower() == '.xltx':
            destination = destination.with_suffix('.xlsx')
        if template.suffix.lower() == '.docx':
            if 'memorial' in template.name.lower():
                from caixa_medicao import enrich_caixa_medicao_values

                values.setdefault(
                    'FIGURA_LOCALIZACAO',
                    '[Inserir figura / print do mapa da localização]',
                )
                enrich_caixa_medicao_values(values)
            unresolved = fill_docx(template, destination, values)
            if 'memorial' in template.name.lower():
                from figura_localizacao import try_embed_figura_localizacao
                from caixa_medicao import try_embed_caixa_medicao

                ok_mapa, msg_mapa = try_embed_figura_localizacao(destination, values, args.output_dir)
                report_lines.append(msg_mapa)
                if ok_mapa:
                    unresolved.discard('FIGURA_LOCALIZACAO')
                ok_caixa, msg_caixa = try_embed_caixa_medicao(destination, values)
                report_lines.append(msg_caixa)
                if ok_caixa:
                    unresolved.discard('FIGURA_CAIXA')
                    unresolved.discard('figura_caixa')
                    unresolved.discard('TEXTO_CAIXA')
                    unresolved.discard('Texto_caixa')
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

    try:
        from autocad_tokens import write_autocad_tokens_file
        from autocad_fill import generate_planta_cad

        tok_path = write_autocad_tokens_file(args.output_dir, values)
        if tok_path:
            print(f'Tokens AutoCAD: {tok_path.resolve()}')

        planta_path, planta_pending, planta_fmt = generate_planta_cad(args.output_dir, values)
        if planta_path:
            print(f'Planta CAD ({planta_fmt.upper()}): {planta_path.resolve()}')
            if planta_fmt == 'dxf':
                print('AVISO: ODA File Converter indisponível — entregue planta.dxf (salvar como DWG no AutoCAD).')
            if planta_pending:
                pend = ', '.join(sorted(planta_pending))
                print(f'AVISO: tokens CAD sem valor: {pend}')
    except Exception as exc:
        print(f'AVISO: exportação AutoCAD não concluída: {exc}')

    print(f'Documentos gerados em: {args.output_dir.resolve()}')
    print(f'Relatório: {report_path.resolve()}')
    if all_unresolved:
        print('ATENÇÃO: existem marcadores pendentes. Consulte o relatório.')


if __name__ == '__main__':
    main()

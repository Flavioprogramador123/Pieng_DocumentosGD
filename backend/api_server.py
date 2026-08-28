"""
API Server para Automação de Documentos Equatorial
Backend Flask que conecta o frontend React ao gerador de documentos Python
"""

from pathlib import Path
import os

# Carregar .env ANTES de importar módulos que leem chaves de API
from load_secrets import load_local_env, redact_secrets

load_local_env()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import tempfile
import shutil
from datetime import datetime
import subprocess
import sys
import re

from form_mapper import normalize_form_payload
from equipment_enrichment import (
    enrich_equipment_lists,
    gemini_available,
    verify_gemini_connection,
    friendly_gemini_error,
    ollama_available,
    ai_available,
    gemini_last_error,
)
from gerar_documentos import preview_token_mapping
from system_calculations import calculate_technical_parameters
from residential_defaults import apply_residential_defaults, iso_to_br, today_br
from cep_lookup import lookup_address_by_cep, lookup_cep_by_address, enrich_client_address
from catalog_db import (
    delete_row,
    init_db,
    list_table,
    lookup_inverter,
    lookup_module,
    lookup_padrao,
    upsert_row,
)
from patch_memorial_demand import patch_memorial_template
from grid_voltage import suggest_tensao_atendimento
from yaml_loader import export_form_to_yaml, import_yaml_project, read_template

app = Flask(__name__)

# SEGURANÇA: Configuração do Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# CORS: Apenas origem do frontend local
CORS(app, origins=['http://localhost:5173', 'http://127.0.0.1:5173'])

# Diretórios
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
TEMPLATES_DIR = ROOT_DIR / 'templates'
CONFIG_FILE = BASE_DIR / 'config_padrao.json'
OUTPUT_BASE_DIR = ROOT_DIR / 'saida' / 'web_generated'

# Garantir que diretório de saída existe
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

init_db()
patch_memorial_template(TEMPLATES_DIR / 'MEMORIAL_DESCRITIVO_marcadores.docx')


def _safe_error_message(exc):
    """Mensagem de erro segura para o cliente (sem chaves nem stack trace)."""
    return redact_secrets(str(exc))


def create_txt_data(data):
    """
    Converte dados do formulário web para formato TXT esperado pelo gerador
    Mapeia TODOS os campos do frontend para os tokens do gerar_documentos.py
    """
    data = normalize_form_payload(data)
    data = apply_residential_defaults(data)
    lines = []

    # === DADOS DO CLIENTE ===
    cliente = data.get('cliente', {})

    if cliente.get('nome'):
        lines.append(f"Nome: {cliente['nome']}")
    if cliente.get('cpf'):
        lines.append(f"CPF: {cliente['cpf']}")
    if cliente.get('rg'):
        lines.append(f"RG: {cliente['rg']}")
    if cliente.get('data_nascimento'):
        lines.append(f"Data de Nascimento: {cliente['data_nascimento']}")
    if cliente.get('telefone'):
        lines.append(f"Telefone Celular: {cliente['telefone']}")
    if cliente.get('email'):
        lines.append(f"E-mail: {cliente['email']}")

    # Endereço completo
    if cliente.get('endereco_completo'):
        lines.append(f"Endereço Completo: {cliente['endereco_completo']}")

    # Endereço fragmentado
    if cliente.get('logradouro'):
        lines.append(f"Endereço: {cliente['logradouro']}")
    if cliente.get('numero'):
        lines.append(f"Número: {cliente['numero']}")
    if cliente.get('complemento'):
        lines.append(f"Complemento: {cliente['complemento']}")
    if cliente.get('bairro'):
        lines.append(f"Bairro: {cliente['bairro']}")
    if cliente.get('cidade'):
        lines.append(f"Cidade: {cliente['cidade']}")
    if cliente.get('uf'):
        lines.append(f"UF: {cliente['uf']}")
    if cliente.get('cep'):
        lines.append(f"CEP: {cliente['cep']}")

    # === UNIDADE CONSUMIDORA ===
    uc = data.get('unidade_consumidora', {})

    if uc.get('numero'):
        lines.append(f"Unidade Consumidora (UC): {uc['numero']}")
    if uc.get('classe'):
        lines.append(f"Classe: {uc['classe']}")
    if uc.get('tipo_ligacao'):
        lines.append(f"Tipo de Ligação: {uc['tipo_ligacao']}")
    if uc.get('tensao_atendimento'):
        lines.append(f"Tensão de Atendimento (V): {uc['tensao_atendimento']}")
    if uc.get('disjuntor_entrada'):
        lines.append(f"Disjuntor de Entrada (A): {uc['disjuntor_entrada']}")
    if uc.get('num_poste'):
        lines.append(f"Nº Poste/Transformador: {uc['num_poste']}")
    if uc.get('modalidade_compensacao'):
        lines.append(f"Modalidade de Compensação: {uc['modalidade_compensacao']}")

    # === COORDENADAS ===
    if uc.get('coordenada_utm_x'):
        lines.append(f"Coordenada UTM X: {uc['coordenada_utm_x']}")
    if uc.get('coordenada_utm_y'):
        lines.append(f"Coordenada UTM Y: {uc['coordenada_utm_y']}")
    if uc.get('fuso_utm'):
        lines.append(f"Fuso UTM: {uc['fuso_utm']}")

    # === MÓDULOS FOTOVOLTAICOS ===
    modulos = data.get('modulos', [])
    if modulos:
        lines.append("\n# MÓDULOS FOTOVOLTAICOS")

        total_modulos = sum(int(m.get('quantidade', 0)) for m in modulos if m.get('quantidade'))
        lines.append(f"Quantidade de Módulos: {total_modulos}")

        # Pegar dados do primeiro módulo como referência
        primeiro = modulos[0]
        if primeiro.get('fabricante'):
            lines.append(f"Fabricante dos Módulos: {primeiro['fabricante']}")
        if primeiro.get('modelo'):
            lines.append(f"Modelo dos Módulos: {primeiro['modelo']}")
        if primeiro.get('potencia'):
            lines.append(f"Potência Unitária dos Módulos (Wp): {primeiro['potencia']}")
        if primeiro.get('voc'):
            lines.append(f"Tensão de Circuito Aberto (Voc) [V]: {primeiro['voc']}")
        if primeiro.get('isc'):
            lines.append(f"Corrente de Curto Circuito (Isc) [A]: {primeiro['isc']}")
        if primeiro.get('vmpp'):
            lines.append(f"Tensão de Máxima Potência (Vpmp) [V]: {primeiro['vmpp']}")
        if primeiro.get('impp'):
            lines.append(f"Corrente de Máxima Potência (Ipmp) [A]: {primeiro['impp']}")
        if primeiro.get('eficiencia'):
            lines.append(f"Eficiência do Módulo (%): {primeiro['eficiencia']}")

    # === INVERSORES ===
    inversores = data.get('inversores', [])
    if inversores:
        lines.append("\n# INVERSORES")

        total_inversores = sum(int(i.get('quantidade', 0)) for i in inversores if i.get('quantidade'))
        lines.append(f"Quantidade de Inversores: {total_inversores}")

        # Pegar dados do primeiro inversor como referência
        primeiro = inversores[0]
        if primeiro.get('fabricante'):
            lines.append(f"Fabricante dos Inversores: {primeiro['fabricante']}")
        if primeiro.get('modelo'):
            lines.append(f"Modelo dos Inversores: {primeiro['modelo']}")
        if primeiro.get('potencia'):
            # IMPORTANTE: O formulário envia em kW, manter em kW
            lines.append(f"Potência Nominal dos Inversores (kW): {primeiro['potencia']}")
        if primeiro.get('tensao_nominal'):
            lines.append(f"Tensão Nominal CA (V): {primeiro['tensao_nominal']}")
        if primeiro.get('corrente_nominal'):
            lines.append(f"Corrente Nominal dos Inversores (A): {primeiro['corrente_nominal']}")
        if primeiro.get('mppt_min'):
            lines.append(f"Mínima Tensão MPPT (V): {primeiro['mppt_min']}")
        if primeiro.get('mppt_max'):
            lines.append(f"Máxima Tensão MPPT (V): {primeiro['mppt_max']}")
        if primeiro.get('eficiencia'):
            lines.append(f"Eficiência Máxima do Inversor (%): {primeiro['eficiencia']}")

    # === DADOS TÉCNICOS ===
    tecnicos = data.get('dados_tecnicos', {})

    if tecnicos.get('area_arranjo'):
        lines.append(f"Área dos Arranjos (m²): {tecnicos['area_arranjo']}")
    if tecnicos.get('tipo_fonte'):
        lines.append(f"Tipo de Fonte: {tecnicos['tipo_fonte']}")
    if tecnicos.get('data_operacao'):
        lines.append(f"Data Prevista de Operação: {tecnicos['data_operacao']}")
    if tecnicos.get('demanda_alvo_kw'):
        lines.append(f"Demanda Alvo da Unidade (kW): {tecnicos['demanda_alvo_kw']}")
    if tecnicos.get('tabela_demanda_text'):
        escaped = str(tecnicos['tabela_demanda_text']).replace('\n', ' {{NL}} ')
        lines.append(f"Tabela de Demanda: {escaped}")

    # Cabos e proteções
    if tecnicos.get('bitola_cabo_cc'):
        lines.append(f"Bitola do Cabo CC: {tecnicos['bitola_cabo_cc']}")
    if tecnicos.get('bitola_cabo_ca'):
        lines.append(f"Bitola do Cabo CA: {tecnicos['bitola_cabo_ca']}")
    if tecnicos.get('bitola_cabo_padrao'):
        lines.append(f"Bitola Cabo Padrão: {tecnicos['bitola_cabo_padrao']}")
    if tecnicos.get('tipo_arranjo'):
        lines.append(f"Tipo de Arranjo: {tecnicos['tipo_arranjo']}")
    if tecnicos.get('dps_cc'):
        lines.append(f"DPS CC: {tecnicos['dps_cc']}")
    if tecnicos.get('dps_ca'):
        lines.append(f"DPS CA: {tecnicos['dps_ca']}")
    if tecnicos.get('aterramento'):
        lines.append(f"Aterramento: {tecnicos['aterramento']}")
    if tecnicos.get('disjuntor_curva'):
        lines.append(f"Curva do Disjuntor: {tecnicos['disjuntor_curva']}")
    if tecnicos.get('dr_tipo'):
        lines.append(f"DR: {tecnicos['dr_tipo']}")
    elif tecnicos.get('dr_sensibilidade_ma'):
        lines.append(f"Sensibilidade DR (mA): {tecnicos['dr_sensibilidade_ma']}")

    # Data do documento (assinatura) — padrão: dia da geração; usuário pode alterar no formulário
    doc_date = tecnicos.get('data_documento') or cliente.get('data_documento')
    if doc_date:
        lines.append(f"\nData do Documento: {iso_to_br(doc_date) or doc_date}")
    else:
        lines.append(f"\nData do Documento: {today_br()}")
    cidade_doc = cliente.get('cidade') or 'Anápolis'
    lines.append(f"Cidade do Documento: {cidade_doc}")

    return '\n'.join(lines)


def _map_ai_json_to_nested(ai_data):
    """Mapeia JSON extraído pela IA para estrutura aninhada do formulário."""
    parsed = {
        'cliente': {},
        'unidade_consumidora': {},
        'modulos': [],
        'inversores': [],
        'dados_tecnicos': {},
    }
    if not isinstance(ai_data, dict):
        return parsed

    field_map = {
        'nome': 'nome', 'cpf': 'cpf', 'rg': 'rg',
        'data_nascimento': 'data_nascimento', 'validade_cnh': 'validade_cnh',
        'telefone': 'telefone', 'email': 'email',
        'endereco_completo': 'endereco_completo', 'logradouro': 'logradouro',
        'numero': 'numero', 'complemento': 'complemento', 'bairro': 'bairro',
        'cidade': 'cidade', 'uf': 'uf', 'cep': 'cep',
    }
    for src, dst in field_map.items():
        if ai_data.get(src):
            parsed['cliente'][dst] = ai_data[src]

    uc = ai_data.get('uc') or ai_data.get('unidade_consumidora')
    if uc:
        parsed['unidade_consumidora']['numero'] = uc
    if ai_data.get('tensao'):
        parsed['unidade_consumidora']['tensao_atendimento'] = ai_data['tensao']
    if ai_data.get('classe'):
        parsed['unidade_consumidora']['classe'] = ai_data['classe']
    if ai_data.get('tipo_ligacao'):
        parsed['unidade_consumidora']['tipo_ligacao'] = ai_data['tipo_ligacao']

    for mod in ai_data.get('modulos', []) or []:
        parsed['modulos'].append({
            'quantidade': mod.get('quantidade'),
            'fabricante': mod.get('fabricante'),
            'modelo': mod.get('modelo'),
            'potencia': mod.get('potencia'),
            'voc': mod.get('voc'),
            'isc': mod.get('isc'),
            'vmpp': mod.get('vmpp'),
            'impp': mod.get('impp'),
            'eficiencia': mod.get('eficiencia'),
        })

    for inv in ai_data.get('inversores', []) or []:
        parsed['inversores'].append({
            'quantidade': inv.get('quantidade'),
            'fabricante': inv.get('fabricante'),
            'modelo': inv.get('modelo'),
            'potencia': inv.get('potencia'),
        })

    return parsed


def _call_ai_for_text_extraction(text):
    """Tenta Ollama, depois Gemini, para extrair dados do TXT."""
    prompt = f"""Extraia as informações do texto abaixo e retorne APENAS um JSON válido:

{text}

Formato esperado:
{{
  "nome": "...",
  "cpf": "...",
  "rg": "...",
  "data_nascimento": "...",
  "validade_cnh": "...",
  "telefone": "...",
  "email": "...",
  "endereco_completo": "...",
  "logradouro": "...",
  "numero": "...",
  "bairro": "...",
  "cidade": "...",
  "uf": "...",
  "cep": "...",
  "uc": "...",
  "tensao": "...",
  "classe": "...",
  "tipo_ligacao": "...",
  "modulos": [{{"quantidade": 0, "fabricante": "...", "modelo": "...", "potencia": 0}}],
  "inversores": [{{"quantidade": 0, "fabricante": "...", "modelo": "...", "potencia": 0}}]
}}"""

    from equipment_enrichment import _call_ollama, _call_gemini, _extract_json

    for source, caller in (
        ('ollama', lambda: _call_ollama(prompt, timeout=90)),
        ('gemini', lambda: _call_gemini(prompt, timeout=60, use_search=False)),
    ):
        ai_text = caller()
        ai_data = _extract_json(ai_text)
        if ai_data and ai_data.get('nome'):
            return _map_ai_json_to_nested(ai_data), source
    return None, None


def parse_text_with_ai(text):
    """
    Analisa texto usando IA local (Ollama) ou parser regex
    Retorna dados estruturados para popular o formulário
    """
    parsed_data = {
        'cliente': {},
        'unidade_consumidora': {},
        'modulos': [],
        'inversores': [],
        'dados_tecnicos': {}
    }

    # Tentar IA (Ollama → Gemini)
    ai_result, source = _call_ai_for_text_extraction(text)
    if ai_result:
        return ai_result, source

    # Parser local baseado em regex (sempre funciona)
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Separar label: valor
        if ':' not in line:
            continue

        parts = line.split(':', 1)
        label = parts[0].strip().lower()
        value = parts[1].strip()

        if not value:
            continue

        # === CLIENTE ===
        if 'nome' in label and 'unidade' not in label:
            parsed_data['cliente']['nome'] = value
        elif 'cpf' in label:
            # Limpar CPF (remover texto extra)
            cpf_match = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', value)
            if cpf_match:
                parsed_data['cliente']['cpf'] = cpf_match.group(1)
        elif 'rg' in label:
            parsed_data['cliente']['rg'] = value
        elif 'validade' in label and 'cnh' in label:
            parsed_data['cliente']['validade_cnh'] = value
        elif 'nascimento' in label:
            parsed_data['cliente']['data_nascimento'] = value
        elif 'telefone' in label or 'celular' in label:
            parsed_data['cliente']['telefone'] = value
        elif 'email' in label or 'e-mail' in label:
            parsed_data['cliente']['email'] = value

        # === ENDEREÇO ===
        elif 'endere' in label and 'completo' in label:
            endereco_completo = value
            parsed_data['cliente']['endereco_completo'] = endereco_completo

            # Fragmentar endereço
            # Extrair quadra (Q. F)
            match_q = re.search(r'Q\.?\s*([A-Z0-9/\-]+)', endereco_completo, re.I)
            if match_q:
                parsed_data['cliente']['complemento'] = f"Q. {match_q.group(1)}"

            # Extrair lote (L. 5/6)
            match_l = re.search(r'L\.?\s*([A-Z0-9/\-]+)', endereco_completo, re.I)
            if match_l:
                comp = parsed_data['cliente'].get('complemento', '')
                if comp:
                    parsed_data['cliente']['complemento'] = f"{comp}, L. {match_l.group(1)}"
                else:
                    parsed_data['cliente']['complemento'] = f"L. {match_l.group(1)}"

            # Extrair logradouro (parte antes de Q. ou L.)
            logr_match = re.search(r'^([^,]+)', endereco_completo)
            if logr_match:
                logradouro = logr_match.group(1).strip()
                # Remover Q. e L. do logradouro se estiverem lá
                logradouro = re.sub(r',?\s*Q\.?\s*[A-Z0-9/\-]+', '', logradouro, flags=re.I)
                logradouro = re.sub(r',?\s*L\.?\s*[A-Z0-9/\-]+', '', logradouro, flags=re.I)
                parsed_data['cliente']['logradouro'] = logradouro.strip(' ,')

            # Extrair bairro (parte após última vírgula)
            bairro_match = re.search(r',\s*([^,]+)$', endereco_completo)
            if bairro_match:
                bairro = bairro_match.group(1).strip()
                # Limpar Q. e L. do bairro
                bairro = re.sub(r'Q\.?\s*[A-Z0-9/\-]+', '', bairro, flags=re.I)
                bairro = re.sub(r'L\.?\s*[A-Z0-9/\-]+', '', bairro, flags=re.I)
                parsed_data['cliente']['bairro'] = bairro.strip(' ,')

        elif 'cidade' in label and '/' in value:
            cidade, uf = value.split('/')
            parsed_data['cliente']['cidade'] = cidade.strip()
            parsed_data['cliente']['uf'] = uf.strip()
        elif 'cidade' in label:
            parsed_data['cliente']['cidade'] = value
        elif 'uf' in label and len(value) <= 2:
            parsed_data['cliente']['uf'] = value.upper()
        elif 'cep' in label:
            parsed_data['cliente']['cep'] = value

        # === UNIDADE CONSUMIDORA ===
        elif 'unidade consumidora' in label or label == 'uc':
            uc_match = re.search(r'(\d{10,})', value)
            if uc_match:
                parsed_data['unidade_consumidora']['numero'] = uc_match.group(1)
                parsed_data['unidade_consumidora']['numero_uc'] = uc_match.group(1)
        elif 'tensao' in label or 'tensão' in label:
            parsed_data['unidade_consumidora']['tensao_atendimento'] = value
        elif 'tipo de ligacao' in label or 'tipo de ligação' in label:
            parsed_data['unidade_consumidora']['tipo_ligacao'] = value
        elif 'modalidade' in label:
            parsed_data['unidade_consumidora']['modalidade_compensacao'] = value
        elif 'coordenada utm x' in label:
            parsed_data['unidade_consumidora']['coordenada_utm_x'] = value
        elif 'coordenada utm y' in label:
            parsed_data['unidade_consumidora']['coordenada_utm_y'] = value

        # === MÓDULOS ===
        elif 'quantidade de m' in label and 'dulo' in label:
            if not parsed_data['modulos']:
                parsed_data['modulos'].append({})
            parsed_data['modulos'][0]['quantidade'] = value
        elif 'fabricante dos m' in label or 'fabricante do m' in label:
            if not parsed_data['modulos']:
                parsed_data['modulos'].append({})
            parsed_data['modulos'][0]['fabricante'] = value
        elif 'modelo dos m' in label or 'modelo do m' in label:
            if not parsed_data['modulos']:
                parsed_data['modulos'].append({})
            parsed_data['modulos'][0]['modelo'] = value
        elif 'pot' in label and 'm' in label and ('wp' in label or 'w)' in label):
            if not parsed_data['modulos']:
                parsed_data['modulos'].append({})
            parsed_data['modulos'][0]['potencia'] = value

        # === INVERSORES ===
        elif 'quantidade de inversor' in label:
            if not parsed_data['inversores']:
                parsed_data['inversores'].append({})
            parsed_data['inversores'][0]['quantidade'] = value
        elif 'fabricante dos inversor' in label or 'fabricante do inversor' in label:
            if not parsed_data['inversores']:
                parsed_data['inversores'].append({})
            parsed_data['inversores'][0]['fabricante'] = value
        elif 'modelo dos inversor' in label or 'modelo do inversor' in label:
            if not parsed_data['inversores']:
                parsed_data['inversores'].append({})
            parsed_data['inversores'][0]['modelo'] = value
        elif 'pot' in label and 'inversor' in label and 'kw' in label:
            if not parsed_data['inversores']:
                parsed_data['inversores'].append({})
            parsed_data['inversores'][0]['potencia'] = value

        # === CABOS ===
        elif 'bitola' in label and 'cc' in label:
            match = re.search(r'(\d+)\s*mm', value)
            if match:
                parsed_data['dados_tecnicos']['bitola_cabo_cc'] = match.group(1)
        elif 'bitola' in label and 'ca' in label:
            match = re.search(r'(\d+)\s*mm', value)
            if match:
                parsed_data['dados_tecnicos']['bitola_cabo_ca'] = match.group(1)

    # Garantir estrutura mínima
    if not parsed_data['modulos']:
        parsed_data['modulos'] = [{}]
    if not parsed_data['inversores']:
        parsed_data['inversores'] = [{}]

    return parsed_data, 'parser_local'


@app.route('/api/yaml/template', methods=['GET'])
def yaml_template():
    try:
        return jsonify({'success': True, 'content': read_template()})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 404


@app.route('/api/import-yaml', methods=['POST'])
def import_yaml():
    try:
        payload = request.json or {}
        content = payload.get('yaml') or payload.get('content') or ''
        if not str(content).strip():
            return jsonify({'success': False, 'error': 'YAML vazio'}), 400
        result = import_yaml_project(content)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/export-yaml', methods=['POST'])
def export_yaml():
    try:
        data = request.json or {}
        yaml_text = export_form_to_yaml(data)
        return jsonify({'success': True, 'yaml': yaml_text})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/<table_name>', methods=['GET'])
def catalog_list(table_name):
    try:
        return jsonify({'success': True, 'rows': list_table(table_name)})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/<table_name>', methods=['POST'])
def catalog_upsert(table_name):
    try:
        data = request.json or {}
        row = upsert_row(table_name, data)
        return jsonify({'success': True, 'row': row})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/<table_name>/<int:row_id>', methods=['DELETE'])
def catalog_delete(table_name, row_id):
    try:
        ok = delete_row(table_name, row_id)
        if not ok:
            return jsonify({'success': False, 'error': 'Registro não encontrado'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/lookup', methods=['POST'])
def catalog_lookup():
    try:
        data = request.json or {}
        kind = data.get('type', 'module')
        fab = data.get('fabricante', '')
        mod = data.get('modelo', data.get('model', ''))
        if kind == 'inverter':
            row = lookup_inverter(fab, mod)
        elif kind == 'padrao':
            row = lookup_padrao(data.get('uf', ''), data.get('tipo_ligacao', ''))
        else:
            row = lookup_module(fab, mod)
        return jsonify({'success': True, 'found': bool(row), 'row': row})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/grid-voltage/suggest', methods=['POST'])
def grid_voltage_suggest():
    data = request.json or {}
    return jsonify({
        'success': True,
        'tensao_atendimento': suggest_tensao_atendimento(
            data.get('uf'),
            data.get('tipo_ligacao'),
        ),
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica se o servidor está funcionando"""
    return jsonify({
        'status': 'ok',
        'message': 'API Equatorial Automation está funcionando',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/ai-status', methods=['GET'])
def ai_status():
    """Verifica status da IA (Ollama e Gemini)"""
    status = {
        'ollama': False,
        'gemini': gemini_available(),
        'model': None,
    }
    if status['gemini']:
        status['gemini_model'] = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
        # Não gasta cota a cada refresh da página — só verifica se ?verify=1
        if request.args.get('verify') == '1':
            ok, err = verify_gemini_connection(force=True)
            status['gemini_working'] = ok
            if not ok and err:
                status['gemini_error'] = err
        else:
            status['gemini_working'] = True
            status['gemini_verify'] = 'skipped'

    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            if models:
                status['ollama'] = True
                status['model'] = models[0].get('name', 'unknown')
    except Exception:
        pass

    if status['ollama']:
        status['primary'] = 'ollama'
    elif status['gemini']:
        status['primary'] = 'gemini'
    else:
        status['primary'] = 'none'

    return jsonify(status)


def _module_to_frontend(module):
    return {
        'quantity': module.get('quantidade', ''),
        'fabricante': module.get('fabricante', ''),
        'model': module.get('modelo', ''),
        'power': module.get('potencia', ''),
        'voc': module.get('voc', ''),
        'isc': module.get('isc', ''),
        'vmpp': module.get('vmpp', ''),
        'impp': module.get('impp', ''),
        'eficiencia': module.get('eficiencia', ''),
    }


def _inverter_to_frontend(inverter):
    return {
        'quantity': inverter.get('quantidade', ''),
        'fabricante': inverter.get('fabricante', ''),
        'model': inverter.get('modelo', ''),
        'power': inverter.get('potencia', ''),
        'tensao_nominal': inverter.get('tensao_nominal', ''),
        'corrente_nominal': inverter.get('corrente_nominal', ''),
        'mppt_min': inverter.get('mppt_min', ''),
        'mppt_max': inverter.get('mppt_max', ''),
        'num_mppt': inverter.get('num_mppt', ''),
        'tipo_inversor': inverter.get('tipo_inversor', ''),
        'eficiencia': inverter.get('eficiencia', ''),
    }


@app.route('/api/lookup-address', methods=['POST'])
def lookup_address():
    """CEP → endereço (ViaCEP) ou endereço → CEP (Nominatim / IA)."""
    try:
        payload = request.json or {}
        cep = payload.get('cep', '')
        logradouro = payload.get('logradouro', '')
        cidade = payload.get('cidade', '')
        uf = payload.get('uf', '')
        bairro = payload.get('bairro', '')

        found = None
        if cep and str(cep).strip():
            found = lookup_address_by_cep(cep)
        elif logradouro and cidade and uf:
            found = lookup_cep_by_address(logradouro, cidade, uf, bairro)

        if not found:
            return jsonify({
                'success': False,
                'error': 'Endereço ou CEP não encontrado.',
            }), 404

        return jsonify({
            'success': True,
            'address': found,
            'source': found.get('source'),
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': _safe_error_message(exc)}), 500


@app.route('/api/enrich-equipment', methods=['POST'])
def enrich_equipment():
    """Busca specs de módulos/inversores via Ollama ou Gemini"""
    try:
        payload = request.json or {}
        data = normalize_form_payload(payload)
        modulos, inversores, sources = enrich_equipment_lists(
            data.get('modulos', []),
            data.get('inversores', []),
            save_to_catalog=bool(payload.get('save_to_catalog', True)),
        )
        enriched = bool(sources)
        hint = None
        if not enriched:
            if not ai_available():
                hint = 'Modelo não está no catálogo local. Cadastre na aba Catálogo SQL ou configure Ollama/Gemini.'
            elif gemini_available() and gemini_last_error():
                hint = friendly_gemini_error()
            else:
                hint = 'IA não encontrou specs para este modelo ou os campos Voc/Isc já estavam preenchidos.'
        return jsonify({
            'success': True,
            'modules': [_module_to_frontend(m) for m in modulos],
            'inverters': [_inverter_to_frontend(i) for i in inversores],
            'sources': sources,
            'enriched': enriched,
            'hint': hint,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/analyze-text', methods=['POST'])
def analyze_text():
    """
    Analisa texto TXT usando IA ou parser local
    """
    try:
        data = request.json
        text = data.get('text', '')

        if not text:
            return jsonify({
                'success': False,
                'error': 'Texto vazio'
            }), 400

        # Analisar texto
        parsed_data, source = parse_text_with_ai(text)

        return jsonify({
            'success': True,
            'source': source,
            'data': parsed_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e),
        }), 500


@app.route('/api/calculate-system', methods=['POST'])
def calculate_system():
    """Calcula parâmetros técnicos completos + tabela de demanda opcional."""
    try:
        data = request.json or {}
        modules = data.get('modules') or []
        inverters = data.get('inverters') or []

        if not modules or not inverters:
            return jsonify({
                'success': False,
                'error': 'Módulos e inversores são obrigatórios',
            }), 400

        def _has_valid_equipment(items, qty_keys=('quantity', 'quantidade'), power_keys=('power', 'potencia')):
            for item in items:
                if not isinstance(item, dict):
                    continue
                qty = next((item.get(k) for k in qty_keys if item.get(k) not in (None, '')), None)
                pwr = next((item.get(k) for k in power_keys if item.get(k) not in (None, '')), None)
                if qty and pwr:
                    try:
                        if float(str(pwr).replace(',', '.')) > 0 and int(float(str(qty).replace(',', '.'))) > 0:
                            return True
                    except (TypeError, ValueError):
                        continue
            return False

        if not _has_valid_equipment(modules) or not _has_valid_equipment(inverters):
            return jsonify({
                'success': False,
                'error': 'Informe quantidade e potência (Wp/kW) em pelo menos um módulo e um inversor.',
            }), 400

        context = {
            'client': {},
            'technical': data.get('technical') or {},
            'demand_table_ai': data.get('demand_table_ai', False),
            'hsp': data.get('hsp'),
        }
        normalized = normalize_form_payload(data)
        cliente = normalized.get('cliente') or {}
        uc = normalized.get('unidade_consumidora') or {}
        tecnicos = normalized.get('dados_tecnicos') or {}
        context['client'] = {
            **cliente,
            'client_name': cliente.get('nome') or data.get('client_name'),
            'consumer_unit': uc.get('numero') or data.get('consumer_unit'),
            'classe': uc.get('classe') or data.get('classe'),
            'tensao_atendimento': uc.get('tensao_atendimento') or data.get('tensao_atendimento'),
            'tipo_ligacao': uc.get('tipo_ligacao') or data.get('tipo_ligacao'),
        }
        context['technical'] = {**tecnicos, **context['technical']}
        if data.get('demanda_alvo_kw') is not None:
            context['technical']['demanda_alvo_kw'] = data.get('demanda_alvo_kw')

        calculations = calculate_technical_parameters(modules, inverters, context)

        return jsonify({
            'success': True,
            'calculations': calculations,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e),
        }), 500


@app.route('/api/generate-demand-table', methods=['POST'])
def generate_demand_table_endpoint():
    """Gera apenas a tabela de demanda para memorial descritivo."""
    try:
        from demand_table import generate_demand_table

        data = request.json or {}
        target = float(data.get('demanda_alvo_kw') or data.get('target_kw', 0))
        if target <= 0:
            return jsonify({'success': False, 'error': 'Informe demanda-alvo em kW'}), 400

        client = data.get('client') or {}
        table = generate_demand_table(
            target_kw=target,
            classe=client.get('classe') or data.get('classe') or 'INDUSTRIAL',
            client_name=client.get('client_name') or data.get('client_name') or '',
            uc=client.get('consumer_unit') or data.get('consumer_unit') or '',
            notes=data.get('demanda_notas') or data.get('notes') or '',
            prefer_ai=bool(data.get('use_ai')),
        )
        return jsonify({'success': True, 'demand_table': table})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/preview-de-para', methods=['POST'])
def preview_de_para():
    """
    Pré-visualiza mapeamento DE/PARA: rótulo do formulário → {{TOKEN}} → valor.
    Permite conferir placeholders antes de gerar os documentos.
    """
    try:
        data = request.json or {}
        normalized = normalize_form_payload(data)
        txt_content = create_txt_data(normalized)
        preview = preview_token_mapping(txt_content, CONFIG_FILE, TEMPLATES_DIR)
        return jsonify({
            'success': True,
            'txt_preview': txt_content,
            **preview,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e),
        }), 500


@app.route('/api/fill-documents', methods=['POST'])
def fill_documents():
    """
    Endpoint para gerar documentos preenchidos
    """
    try:
        data = request.json

        # Extrair nome do cliente de diferentes estruturas possíveis
        client_name = None
        if data.get('cliente', {}).get('nome'):
            client_name = data['cliente']['nome']
        elif data.get('client_name'):
            client_name = data['client_name']

        # Extrair UC de diferentes estruturas possíveis
        consumer_unit = None
        if data.get('unidade_consumidora', {}).get('numero'):
            consumer_unit = data['unidade_consumidora']['numero']
        elif data.get('consumer_unit'):
            consumer_unit = data['consumer_unit']

        # Validar dados obrigatórios
        if not client_name:
            return jsonify({
                'success': False,
                'error': 'Nome do cliente é obrigatório'
            }), 400

        # Criar diretório único para este cliente
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        client_slug = client_name.replace(' ', '_').lower()[:30]
        output_dir = OUTPUT_BASE_DIR / f"{client_slug}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Normalizar payload plano do frontend → estrutura aninhada
        data = normalize_form_payload(data)

        cliente, cep_source = enrich_client_address(data.get('cliente', {}))
        data['cliente'] = cliente
        data = apply_residential_defaults(data)

        # Enriquecer specs de módulos/inversores se Voc/Isc/MPPT faltarem
        enrich_sources = []
        if data.get('enrich_specs', True):
            data['modulos'], data['inversores'], enrich_sources = enrich_equipment_lists(
                data.get('modulos', []),
                data.get('inversores', []),
                save_to_catalog=bool(data.get('save_to_catalog', True)),
            )

        # Criar arquivo TXT temporário
        txt_content = create_txt_data(data)
        txt_file = output_dir / 'dados_cliente.txt'
        txt_file.write_text(txt_content, encoding='utf-8')

        # Executar gerador de documentos
        python_exe = sys.executable
        cmd = [
            python_exe,
            str(BASE_DIR / 'gerar_documentos.py'),
            '--input', str(txt_file),
            '--templates-dir', str(TEMPLATES_DIR),
            '--output-dir', str(output_dir),
            '--config', str(CONFIG_FILE)
        ]

        # CORREÇÃO: Usar errors='replace' para lidar com encoding
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': redact_secrets(f'Erro ao gerar documentos: {result.stderr}')
            }), 500

        # Listar arquivos gerados e categorizar
        excel_file = None
        memorial_file = None
        procuracao_file = None
        other_files = []

        for file in output_dir.iterdir():
            if file.suffix in ['.docx', '.xlsx']:
                file_info = {
                    'name': file.name,
                    'size': file.stat().st_size,
                    'path': str(file),
                    'download_url': f"http://localhost:5000/api/download/{client_slug}_{timestamp}/{file.name}"
                }

                # Categorizar por tipo
                if file.suffix == '.xlsx':
                    excel_file = file_info
                elif 'memorial' in file.name.lower():
                    memorial_file = file_info
                elif 'procuracao' in file.name.lower() or 'procura' in file.name.lower():
                    procuracao_file = file_info
                else:
                    other_files.append(file_info)

        return jsonify({
            'success': True,
            'message': 'Documentos gerados com sucesso!',
            'output_directory': str(output_dir),
            'files': {
                'excel': excel_file,
                'memorial': memorial_file,
                'procuracao': procuracao_file,
                'outros': other_files
            },
            'txt_content': txt_content,
            'enrichment_sources': enrich_sources,
            'cep_source': cep_source,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e),
        }), 500


@app.route('/api/download/<path:filepath>', methods=['GET'])
def download_file(filepath):
    """
    Endpoint para download de arquivos gerados
    SEGURANÇA: Previne path traversal (../) e garante que arquivo está dentro de OUTPUT_BASE_DIR
    """
    try:
        # Resolver path completo e normalizar
        file_path = OUTPUT_BASE_DIR / filepath
        file_path = file_path.resolve()

        # SEGURANÇA: Verificar que o arquivo está dentro do diretório permitido
        if not str(file_path).startswith(str(OUTPUT_BASE_DIR.resolve())):
            return jsonify({
                'success': False,
                'error': 'Acesso negado: path inválido'
            }), 403

        # Verificar se arquivo existe
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        # Verificar se é um arquivo (não diretório)
        if not file_path.is_file():
            return jsonify({
                'success': False,
                'error': 'Path inválido: não é um arquivo'
            }), 400

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Erro ao baixar arquivo'
        }), 500


@app.route('/api/list-clients', methods=['GET'])
def list_clients():
    """
    Lista todos os clientes processados
    """
    try:
        clients = []

        for client_dir in OUTPUT_BASE_DIR.iterdir():
            if client_dir.is_dir():
                files = list(client_dir.glob('*.docx')) + list(client_dir.glob('*.xlsx'))
                clients.append({
                    'name': client_dir.name,
                    'date': datetime.fromtimestamp(client_dir.stat().st_mtime).isoformat(),
                    'files_count': len(files)
                })

        return jsonify({
            'success': True,
            'clients': sorted(clients, key=lambda x: x['date'], reverse=True)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e)
        }), 500


if __name__ == '__main__':
    # Verificar modo de desenvolvimento
    is_dev = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == '1'

    print("=" * 80)
    print("API Server - Automação Equatorial (Versão Unificada)")
    print("=" * 80)
    print(f"Modo: {'DESENVOLVIMENTO' if is_dev else 'PRODUÇÃO'}")
    print(f"Servidor: http://{'0.0.0.0' if is_dev else '127.0.0.1'}:5000")
    print(f"Frontend: http://localhost:5173")
    print(f"Diretório base: {BASE_DIR}")
    print(f"Templates: {TEMPLATES_DIR}")
    print(f"Saída: {OUTPUT_BASE_DIR}")
    print("\nEndpoints disponíveis:")
    print("  GET  /api/health          - Status do servidor")
    print("  GET  /api/ai-status       - Status da IA (Ollama/Gemini)")
    print("  POST /api/analyze-text    - Análise de texto com IA")
    print("  POST /api/enrich-equipment - Buscar specs módulos/inversores")
    print("  POST /api/calculate-system - Cálculos técnicos")
    print("  POST /api/preview-de-para  - Conferência DE/PARA (placeholders)")
    print("  POST /api/fill-documents  - Gerar documentos")
    print("  GET  /api/download/<path> - Download de arquivos")
    print("  GET  /api/list-clients    - Listar clientes")
    print("=" * 80)

    # SEGURANÇA: Em produção, não usar debug e bind apenas localhost
    app.run(
        debug=is_dev,
        host='0.0.0.0' if is_dev else '127.0.0.1',
        port=5000
    )

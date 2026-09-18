"""
API Server para Automação de Documentos Equatorial
Backend Flask que conecta o frontend React ao gerador de documentos Python
"""

from pathlib import Path
import os

# Carregar .env ANTES de importar módulos que leem chaves de API
from load_secrets import load_local_env, redact_secrets

load_local_env()

from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
import json
import tempfile
import shutil
from datetime import datetime
import subprocess
import sys
import re

from form_mapper import normalize_form_payload, pick_field
from equipment_enrichment import (
    enrich_equipment_lists,
    gemini_available,
    verify_gemini_connection,
    friendly_gemini_error,
    ollama_available,
    ai_available,
    gemini_last_error,
)
from gerar_documentos import format_thd_dht, preview_token_mapping
from system_calculations import calculate_technical_parameters
from residential_defaults import apply_residential_defaults, iso_to_br, today_br
from token_enrichment import enrich_normalized_payload
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
from output_paths import (
    get_output_base_dir,
    output_config_status,
    folder_name_from_contract,
    save_local_output_dir,
    resolve_client_file,
    open_path_in_os,
)
from equipment_validation import validate_modules_inverters

app = Flask(__name__)

# SEGURANÇA: Configuração do Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# CORS: Apenas origem do frontend local (cookies de sessão)
CORS(app, origins=[
    'http://localhost:5173', 'http://127.0.0.1:5173',
    'http://localhost:5174', 'http://127.0.0.1:5174',
], supports_credentials=True)

from auth_routes import register_auth
register_auth(app)

# Diretórios
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
TEMPLATES_DIR = ROOT_DIR / 'templates'
CONFIG_FILE = BASE_DIR / 'config_padrao.json'

VIEWABLE_SUFFIXES = frozenset({'.png', '.jpg', '.jpeg', '.gif', '.webp', '.txt'})

VIEW_MIME = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.txt': 'text/plain; charset=utf-8',
}


def _file_actions(folder_name: str, file_name: str, suffix: str) -> dict:
    view_url = None
    if suffix in VIEWABLE_SUFFIXES:
        from urllib.parse import quote
        view_url = f"/api/view/{quote(folder_name)}/{quote(file_name)}"
    return {
        'view_url': view_url,
        'can_view_web': view_url is not None,
        'can_open_app': True,
    }

init_db()
try:
    from import_modulos_yaml import import_modulos_yaml
    import_modulos_yaml()
except Exception:
    pass
try:
    from import_inversores_yaml import import_inversores_yaml
    import_inversores_yaml()
except Exception:
    pass
patch_memorial_template(TEMPLATES_DIR / 'MEMORIAL_DESCRITIVO_marcadores.docx')
try:
    from patch_memorial_inversor_text import patch_memorial_inversor_text
    patch_memorial_inversor_text(TEMPLATES_DIR / 'MEMORIAL_DESCRITIVO_marcadores.docx')
except Exception:
    pass


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
    data = enrich_normalized_payload(data)
    lines = []

    # === DADOS DO CLIENTE ===
    cliente = data.get('cliente', {})

    if cliente.get('nome'):
        lines.append(f"Nome: {cliente['nome']}")
    if cliente.get('cpf'):
        lines.append(f"CPF: {cliente['cpf']}")
    if cliente.get('rg'):
        lines.append(f"RG: {cliente['rg']}")
    if cliente.get('nome_representante'):
        lines.append(f"Nome do Representante: {cliente['nome_representante']}")
    if cliente.get('cpf_representante'):
        lines.append(f"CPF do Representante: {cliente['cpf_representante']}")
    if cliente.get('rg_representante'):
        lines.append(f"RG do Representante: {cliente['rg_representante']}")
    if cliente.get('data_nascimento'):
        lines.append(f"Data de Nascimento: {cliente['data_nascimento']}")
    validade_cnh = cliente.get('validade_cnh') or '05/06/2023'
    lines.append(f"Validade CNH: {validade_cnh}")
    lines.append(f"Data Expedição: {validade_cnh}")
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
        numero = str(cliente.get('numero') or '').strip() or 'S/N'
        lines.append(f"Número: {numero}")
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
    num_poste = pick_field(uc, 'num_poste') or 'ilegível'
    lines.append(f"Nº Poste/Transformador: {num_poste}")
    if uc.get('modalidade_compensacao'):
        lines.append(f"Modalidade de Compensação: {uc['modalidade_compensacao']}")

    # === COORDENADAS ===
    if uc.get('coordenada_utm_x'):
        lines.append(f"Coordenada UTM X: {uc['coordenada_utm_x']}")
    if uc.get('coordenada_utm_y'):
        lines.append(f"Coordenada UTM Y: {uc['coordenada_utm_y']}")
    if uc.get('fuso_utm'):
        lines.append(f"Fuso UTM: {uc['fuso_utm']}")

    tec = data.get('dados_tecnicos', {})
    if tec.get('latitude'):
        lines.append(f"Latitude: {tec['latitude']}")
    if tec.get('longitude'):
        lines.append(f"Longitude: {tec['longitude']}")
    coord_raw = tec.get('coordenadas_raw') or uc.get('coordenadas_raw')
    if coord_raw:
        lines.append(f"Coordenadas: {coord_raw}")

    figura_zoom = tec.get('figura_map_zoom') or data.get('figura_map_zoom')
    if figura_zoom not in (None, '', 'auto'):
        lines.append(f"Zoom Figura Localização: {figura_zoom}")

    # === MÓDULOS FOTOVOLTAICOS ===
    modulos = data.get('modulos', [])
    if modulos:
        lines.append("\n# MÓDULOS FOTOVOLTAICOS")

        total_modulos = sum(
            int(pick_field(m, 'quantidade', 'quantity') or 0)
            for m in modulos
            if pick_field(m, 'quantidade', 'quantity')
        )
        lines.append(f"Quantidade de Módulos: {total_modulos}")

        primeiro = modulos[0]
        if pick_field(primeiro, 'fabricante'):
            lines.append(f"Fabricante dos Módulos: {pick_field(primeiro, 'fabricante')}")
        if pick_field(primeiro, 'modelo', 'model'):
            lines.append(f"Modelo dos Módulos: {pick_field(primeiro, 'modelo', 'model')}")
        if pick_field(primeiro, 'potencia', 'power'):
            lines.append(f"Potência Unitária dos Módulos (Wp): {pick_field(primeiro, 'potencia', 'power')}")
        if pick_field(primeiro, 'voc'):
            lines.append(f"Tensão de Circuito Aberto (Voc) [V]: {pick_field(primeiro, 'voc')}")
        if pick_field(primeiro, 'isc'):
            lines.append(f"Corrente de Curto Circuito (Isc) [A]: {pick_field(primeiro, 'isc')}")
        if pick_field(primeiro, 'vmpp'):
            lines.append(f"Tensão de Máxima Potência (Vpmp) [V]: {pick_field(primeiro, 'vmpp')}")
        if pick_field(primeiro, 'impp'):
            lines.append(f"Corrente de Máxima Potência (Ipmp) [A]: {pick_field(primeiro, 'impp')}")
        ef_mod = pick_field(primeiro, 'eficiencia', 'efficiency')
        if ef_mod is not None:
            lines.append(f"Eficiência do Módulo (%): {ef_mod}")
        if pick_field(primeiro, 'comprimento_m'):
            lines.append(f"Comprimento do Módulo (m): {pick_field(primeiro, 'comprimento_m')}")
        if pick_field(primeiro, 'largura_m'):
            lines.append(f"Largura do Módulo (m): {pick_field(primeiro, 'largura_m')}")
        area_mod = pick_field(primeiro, 'area_modulo')
        comp_m = pick_field(primeiro, 'comprimento_m')
        larg_m = pick_field(primeiro, 'largura_m')
        if not area_mod and comp_m and larg_m:
            try:
                area_mod = float(comp_m) * float(larg_m)
            except (TypeError, ValueError):
                area_mod = None
        if not area_mod:
            area_mod = 2.5
        lines.append(f"Área do Módulo (m²): {area_mod}")
        if total_modulos:
            try:
                lines.append(f"Área dos Arranjos (m²): {total_modulos * float(area_mod):g}")
            except (TypeError, ValueError):
                pass
        if pick_field(primeiro, 'peso_kg'):
            lines.append(f"Peso do Módulo (kg): {pick_field(primeiro, 'peso_kg')}")
        pot_ref = pick_field(primeiro, 'potencia', 'power')
        if total_modulos and pot_ref:
            try:
                pot_total = total_modulos * float(pot_ref) / 1000
                lines.append(f"Potência Total Instalada (kW): {pot_total:g}")
            except (TypeError, ValueError):
                pass

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
        if primeiro.get('potencia_max_cc_kw'):
            lines.append(f"Máxima Potência na Entrada CC (kW): {primeiro['potencia_max_cc_kw']}")
        if primeiro.get('tensao_max_cc'):
            lines.append(f"Máxima Tensão CC (V): {primeiro['tensao_max_cc']}")
        if primeiro.get('corrente_max_cc'):
            lines.append(f"Máxima Corrente CC (A): {primeiro['corrente_max_cc']}")
        if primeiro.get('tensao_partida_cc'):
            lines.append(f"Tensão CC de Partida (V): {primeiro['tensao_partida_cc']}")
        if primeiro.get('qtd_strings_max') or primeiro.get('qtd_entradas_mppt'):
            lines.append(f"Quantidade de Strings: {primeiro.get('qtd_strings_max') or primeiro.get('qtd_entradas_mppt')}")
        if primeiro.get('num_mppt') or primeiro.get('qtd_entradas_mppt'):
            lines.append(f"Quantidade de Entradas MPPT: {primeiro.get('qtd_entradas_mppt') or primeiro.get('num_mppt')}")
        if primeiro.get('potencia_nominal_ca_kw') or primeiro.get('potencia'):
            lines.append(f"Potência Nominal CA (kW): {primeiro.get('potencia_nominal_ca_kw') or primeiro['potencia']}")
        if primeiro.get('potencia_max_saida_ca_kw'):
            lines.append(f"Máxima Potência na Saída CA (kW): {primeiro['potencia_max_saida_ca_kw']}")
        if primeiro.get('corrente_max_saida_ca'):
            lines.append(f"Máxima Corrente na Saída CA (A): {primeiro['corrente_max_saida_ca']}")
        if primeiro.get('frequencia_hz'):
            lines.append(f"Frequência Nominal (Hz): {primeiro['frequencia_hz']}")
        if primeiro.get('tensao_max_ca') and primeiro.get('tensao_min_ca'):
            lines.append(f"Máxima Tensão CA (V): {primeiro['tensao_max_ca']}")
            lines.append(f"Mínima Tensão CA (V): {primeiro['tensao_min_ca']}")
            lines.append(f"Faixa de Tensão dos Inversores (V): {primeiro['tensao_min_ca']}-{primeiro['tensao_max_ca']}")
        thd_raw = pick_field(primeiro, 'thd_pct', 'thd', 'dht')
        thd_fmt = format_thd_dht(thd_raw or '3')
        lines.append(f"THD de Corrente (%): {thd_fmt}")
        lines.append(f"DHT de Corrente (%): {thd_fmt}")
        if primeiro.get('fator_potencia'):
            lines.append(f"Fator de Potência do Inversor: {primeiro['fator_potencia']}")
        if primeiro.get('tipo_inversor'):
            lines.append(f"Tipo de Conexão do Inversor: {primeiro['tipo_inversor']}")

    # === DADOS TÉCNICOS ===
    tecnicos = data.get('dados_tecnicos', {})
    contrato = data.get('contrato') or {}

    def contrato_val(key):
        val = contrato.get(key)
        if val not in (None, ''):
            return val
        return tecnicos.get(key)

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
    if tecnicos.get('tabela_demanda_json'):
        lines.append(f"Tabela de Demanda JSON: {tecnicos['tabela_demanda_json']}")

    # === CONTRATO (ModeloContrato.docx) ===
    lines.append("\n# CONTRATO")
    if contrato_val('numero_contrato'):
        lines.append(f"Número do Contrato: {contrato_val('numero_contrato')}")
    if contrato_val('texto_valor_pagamento_contrato'):
        escaped = str(contrato_val('texto_valor_pagamento_contrato')).replace('\n', ' {{NL}} ')
        lines.append(f"Texto Valor Pagamento Contrato: {escaped}")

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
        lines.append(f"Curva de Atuação: {tecnicos['disjuntor_curva']}")
    if tecnicos.get('disjuntor_polos'):
        lines.append(f"Número de Polos do Disjuntor: {tecnicos['disjuntor_polos']}")
    if tecnicos.get('disjuntor_tensao_nominal'):
        lines.append(f"Tensão Nominal do Disjuntor (V): {tecnicos['disjuntor_tensao_nominal']}")
    if tecnicos.get('disjuntor_corrente_nominal') or uc.get('disjuntor_entrada'):
        lines.append(f"Corrente Nominal do Disjuntor (A): {tecnicos.get('disjuntor_corrente_nominal') or uc.get('disjuntor_entrada')}")
    if tecnicos.get('disjuntor_frequencia'):
        lines.append(f"Frequência do Disjuntor (Hz): {tecnicos['disjuntor_frequencia']}")
    if tecnicos.get('disjuntor_capacidade_ka'):
        lines.append(f"Capacidade Máxima de Interrupção (kA): {tecnicos['disjuntor_capacidade_ka']}")
    if tecnicos.get('disjuntor_elemento'):
        lines.append(f"Elemento de Proteção do Disjuntor: {tecnicos['disjuntor_elemento']}")
    if tecnicos.get('disjuntor_acionamento'):
        lines.append(f"Acionamento do Disjuntor: {tecnicos['disjuntor_acionamento']}")
    if tecnicos.get('dps_tipo'):
        lines.append(f"Tipo DPS: {tecnicos['dps_tipo']}")
    if tecnicos.get('dps_classe'):
        lines.append(f"Classe DPS: {tecnicos['dps_classe']}")
    if tecnicos.get('dps_tensao_v'):
        lines.append(f"Tensão DPS (V): {tecnicos['dps_tensao_v']}")
    if tecnicos.get('dps_corrente_nominal_ka'):
        lines.append(f"Corrente Nominal DPS (kA): {tecnicos['dps_corrente_nominal_ka']}")
    if tecnicos.get('dps_corrente_maxima_ka'):
        lines.append(f"Corrente Máxima DPS (kA): {tecnicos['dps_corrente_maxima_ka']}")
    if tecnicos.get('fator_potencia'):
        lines.append(f"Fator de Potência: {tecnicos['fator_potencia']}")
    if uc.get('disjuntor_entrada'):
        lines.append(f"Corrente de Entrada: {uc['disjuntor_entrada']}")
    if tecnicos.get('armazenamento'):
        lines.append(f"Armazenamento (se houver): {tecnicos['armazenamento']}")
    if tecnicos.get('dr_tipo'):
        lines.append(f"DR: {tecnicos['dr_tipo']}")
    elif tecnicos.get('dr_sensibilidade_ma'):
        lines.append(f"Sensibilidade DR (mA): {tecnicos['dr_sensibilidade_ma']}")

    if tecnicos.get('tipo_inversor'):
        lines.append(f"Tipo de Inversor (topologia): {tecnicos['tipo_inversor']}")
    if tecnicos.get('num_mppt'):
        lines.append(f"Quantidade de Entradas MPPT: {tecnicos['num_mppt']}")
    if tecnicos.get('modulos_por_string'):
        lines.append(f"Módulos por String: {tecnicos['modulos_por_string']}")
    if tecnicos.get('strings_por_mppt'):
        lines.append(f"Strings em Paralelo por MPPT: {tecnicos['strings_por_mppt']}")
    if tecnicos.get('micros_por_grupo_ca'):
        lines.append(f"Microinversores por Grupo CA: {tecnicos['micros_por_grupo_ca']}")
    if tecnicos.get('qdca_micros_fase_a'):
        lines.append(f"QDCA Micros Fase A: {tecnicos['qdca_micros_fase_a']}")
    if tecnicos.get('qdca_micros_fase_b'):
        lines.append(f"QDCA Micros Fase B: {tecnicos['qdca_micros_fase_b']}")
    if tecnicos.get('qdca_micros_fase_c'):
        lines.append(f"QDCA Micros Fase C: {tecnicos['qdca_micros_fase_c']}")
    if tecnicos.get('qdca_disj_fase_a'):
        lines.append(f"QDCA Disjuntor Fase A (A): {tecnicos['qdca_disj_fase_a']}")
    if tecnicos.get('qdca_disj_fase_b'):
        lines.append(f"QDCA Disjuntor Fase B (A): {tecnicos['qdca_disj_fase_b']}")
    if tecnicos.get('qdca_disj_fase_c'):
        lines.append(f"QDCA Disjuntor Fase C (A): {tecnicos['qdca_disj_fase_c']}")
    if tecnicos.get('qdca_corrente_proj_fase_a'):
        lines.append(f"QDCA I Projeto Fase A (A): {tecnicos['qdca_corrente_proj_fase_a']}")
    if tecnicos.get('qdca_corrente_proj_fase_b'):
        lines.append(f"QDCA I Projeto Fase B (A): {tecnicos['qdca_corrente_proj_fase_b']}")
    if tecnicos.get('qdca_corrente_proj_fase_c'):
        lines.append(f"QDCA I Projeto Fase C (A): {tecnicos['qdca_corrente_proj_fase_c']}")
    if tecnicos.get('qdca_corrente_proj'):
        lines.append(f"QDCA Corrente Projeto (A): {tecnicos['qdca_corrente_proj']}")
    if tecnicos.get('qdca_tem_disj_acoplamento'):
        lines.append(f"QDCA Tem Disj. Acoplamento: {tecnicos['qdca_tem_disj_acoplamento']}")
    if tecnicos.get('qdca_disjuntor_geral'):
        lines.append(f"QDCA Disj. Geral (A): {tecnicos['qdca_disjuntor_geral']}")
    if tecnicos.get('qdca_bitola_tronco'):
        lines.append(f"QDCA Bitola Tronco (mm²): {tecnicos['qdca_bitola_tronco']}")
    if tecnicos.get('qdca_disjuntor_ca'):
        lines.append(f"QDCA Disjuntor CA Inversor (A): {tecnicos['qdca_disjuntor_ca']}")
    if tecnicos.get('qdca_num_dps'):
        lines.append(f"Quantidade DPS QDCA: {tecnicos['qdca_num_dps']}")
    if tecnicos.get('qdca_observacoes'):
        lines.append(f"Observações QDCA: {tecnicos['qdca_observacoes']}")
    if tecnicos.get('qdca_bitola_ca'):
        lines.append(f"QDCA Bitola Cabo CA: {tecnicos['qdca_bitola_ca']}")
    for fase in ('a', 'b', 'c'):
        bit = tecnicos.get(f'qdca_bitola_fase_{fase}')
        if bit:
            lines.append(f"QDCA Bitola Cabo CA Fase {fase.upper()}: {bit}")

    # Data do documento (assinatura) — padrão: dia da geração; usuário pode alterar no formulário
    doc_date = contrato_val('data_documento') or cliente.get('data_documento')
    if doc_date:
        lines.append(f"\nData do Documento: {iso_to_br(doc_date) or doc_date}")
    else:
        lines.append(f"\nData do Documento: {today_br()}")
    cidade_doc = contrato_val('cidade_documento') or cliente.get('cidade') or 'Anápolis'
    lines.append(f"Cidade do Documento: {cidade_doc}")

    if not any('DHT de Corrente' in line for line in lines):
        thd_fmt = format_thd_dht('3')
        lines.append(f"THD de Corrente (%): {thd_fmt}")
        lines.append(f"DHT de Corrente (%): {thd_fmt}")

    # Overrides editados na aba Cálculos (token → valor final no memorial)
    overrides = data.get('token_overrides') or data.get('calculation_token_overrides') or {}
    if isinstance(overrides, dict) and overrides:
        lines.append('\n# OVERRIDES CÁLCULOS (editados pelo usuário)')
        for token, value in overrides.items():
            tok = str(token or '').strip()
            if not tok or value is None:
                continue
            val = str(value).strip()
            if not val:
                continue
            lines.append(f'{tok}: {val}')

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
    if ai_data.get('disjuntor_entrada') or ai_data.get('disjuntor'):
        parsed['unidade_consumidora']['disjuntor_entrada'] = ai_data.get('disjuntor_entrada') or ai_data.get('disjuntor')
    if ai_data.get('num_poste'):
        parsed['unidade_consumidora']['num_poste'] = ai_data['num_poste']
    if ai_data.get('demanda_alvo_kw') or ai_data.get('demanda_kw') or ai_data.get('demanda'):
        val = ai_data.get('demanda_alvo_kw') or ai_data.get('demanda_kw') or ai_data.get('demanda')
        parsed['dados_tecnicos']['demanda_alvo_kw'] = val
    if ai_data.get('bitola_cabo_cc'):
        parsed['dados_tecnicos']['bitola_cabo_cc'] = ai_data['bitola_cabo_cc']
    if ai_data.get('bitola_cabo_ca'):
        parsed['dados_tecnicos']['bitola_cabo_ca'] = ai_data['bitola_cabo_ca']
    if ai_data.get('bitola_cabo_padrao'):
        parsed['dados_tecnicos']['bitola_cabo_padrao'] = ai_data['bitola_cabo_padrao']

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
    from normas_enrichment import ai_extraction_prompt_suffix

    normas_ctx = ai_extraction_prompt_suffix()
    prompt = f"""Extraia as informações do texto abaixo e retorne APENAS um JSON válido.

CONTEXTO NORMATIVO (Equatorial Goiás):
{normas_ctx}

TEXTO:
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
  "uf": "GO",
  "cep": "...",
  "uc": "...",
  "tensao": "220V",
  "classe": "RESIDENCIAL",
  "tipo_ligacao": "MONOFASICO",
  "disjuntor_entrada": 40,
  "demanda_alvo_kw": 6,
  "num_poste": "ilegível",
  "bitola_cabo_cc": "4 mm²",
  "bitola_cabo_ca": "6 mm²",
  "bitola_cabo_padrao": "10 mm²",
  "modulos": [{{"quantidade": 0, "fabricante": "...", "modelo": "...", "potencia": 0, "voc": 0, "isc": 0}}],
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
        elif 'telefone' in label or 'celular' in label or label.strip() == 'fone' or label.startswith('fone '):
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
        elif 'ligacao existente' in label or 'ligação existente' in label:
            parsed_data['unidade_consumidora']['ligacao_existente'] = value
            if re.search(r'\btrif\b|\btrifas', value, re.I):
                parsed_data['unidade_consumidora']['tipo_ligacao'] = 'TRIFASICO'
            elif re.search(r'\bbif\b|\bbifas', value, re.I):
                parsed_data['unidade_consumidora']['tipo_ligacao'] = 'BIFASICO'
            elif re.search(r'\bmono\b|\bmonofas', value, re.I):
                parsed_data['unidade_consumidora']['tipo_ligacao'] = 'MONOFASICO'
            if '380' in value and (
                parsed_data['unidade_consumidora'].get('tipo_ligacao') == 'TRIFASICO'
                or re.search(r'\btri\b', value, re.I)
            ):
                parsed_data['unidade_consumidora']['tensao_atendimento'] = '380V'
            elif '220' in value and '380' in value:
                parsed_data['unidade_consumidora']['tensao_atendimento'] = '380V'
            if re.search(r'\bb1\b', value, re.I):
                parsed_data['unidade_consumidora']['classe'] = 'Residencial'
        elif 'tipo de ligacao' in label or 'tipo de ligação' in label:
            parsed_data['unidade_consumidora']['tipo_ligacao'] = value
        elif 'disjuntor' in label and (
            'protecao' in label or 'proteção' in label or 'prote' in label
            or 'entrada' in label or 'geral' in label or label.endswith(' ac')
        ):
            match = re.search(r'(\d+(?:[.,]\d+)?)\s*a\b', value, re.I)
            if match:
                parsed_data['unidade_consumidora']['disjuntor_entrada'] = match.group(1).replace(',', '.')
            if re.search(r'\btrif\b|\btrifas', value, re.I):
                parsed_data['unidade_consumidora']['tipo_ligacao'] = 'TRIFASICO'
        elif 'modalidade' in label:
            parsed_data['unidade_consumidora']['modalidade_compensacao'] = value
        elif 'coordenada utm x' in label:
            parsed_data['unidade_consumidora']['coordenada_utm_x'] = value
        elif 'coordenada utm y' in label:
            parsed_data['unidade_consumidora']['coordenada_utm_y'] = value
        elif label.startswith('coordenada') and 'utm' not in label:
            parsed_data.setdefault('dados_tecnicos', {})
            parsed_data['dados_tecnicos']['coordenadas_raw'] = value
            parsed_data['unidade_consumidora']['coordenadas_raw'] = value
        elif label in ('latitude', 'lat'):
            parsed_data.setdefault('dados_tecnicos', {})
            parsed_data['dados_tecnicos']['latitude'] = value
        elif label in ('longitude', 'lng', 'long'):
            parsed_data.setdefault('dados_tecnicos', {})
            parsed_data['dados_tecnicos']['longitude'] = value
        elif 'fuso utm' in label:
            parsed_data['unidade_consumidora']['fuso_utm'] = value

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
        data = request.get_json(silent=True) or {}
        row = upsert_row(table_name, data)
        return jsonify({'success': True, 'row': row})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
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


@app.route('/api/catalog/import-modulos-yaml', methods=['POST'])
def catalog_import_modulos_yaml():
    """Importa dados/modulos_solares.yaml ou YAML colado ({ yaml: "..." })."""
    try:
        from import_modulos_yaml import (
            import_modulos_yaml,
            import_modulos_yaml_text,
            resolve_yaml_path,
        )
        payload = request.get_json(silent=True) or {}
        yaml_text = (payload.get('yaml') or payload.get('content') or '').strip()
        if yaml_text:
            result = import_modulos_yaml_text(
                yaml_text,
                save_file=bool(payload.get('save_file', True)),
            )
        else:
            path = payload.get('path')
            yaml_path = Path(path) if path else None
            result = import_modulos_yaml(yaml_path)
        return jsonify({
            **result,
            'yaml_path': result.get('saved_path')
            or result.get('source')
            or (str(resolve_yaml_path()) if resolve_yaml_path() else None),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/modulos-yaml-info', methods=['GET'])
def catalog_modulos_yaml_info():
    try:
        from import_modulos_yaml import load_yaml_modulos, resolve_yaml_path
        path = resolve_yaml_path()
        if not path:
            return jsonify({'success': False, 'error': 'YAML de módulos não encontrado'}), 404
        rows = load_yaml_modulos(path)
        return jsonify({
            'success': True,
            'path': str(path),
            'count': len(rows),
            'preview': rows[:5],
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/import-inversores-yaml', methods=['POST'])
def catalog_import_inversores_yaml():
    """Importa dados/inversores.yaml ou YAML colado ({ yaml: "..." })."""
    try:
        from import_inversores_yaml import (
            import_inversores_yaml,
            import_inversores_yaml_text,
            resolve_yaml_path,
        )
        payload = request.get_json(silent=True) or {}
        yaml_text = (payload.get('yaml') or payload.get('content') or '').strip()
        if yaml_text:
            result = import_inversores_yaml_text(
                yaml_text,
                save_file=bool(payload.get('save_file', True)),
            )
        else:
            path = payload.get('path')
            yaml_path = Path(path) if path else None
            result = import_inversores_yaml(yaml_path)
        return jsonify({
            **result,
            'yaml_path': result.get('saved_path')
            or result.get('source')
            or (str(resolve_yaml_path()) if resolve_yaml_path() else None),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 400


@app.route('/api/catalog/inversores-yaml-info', methods=['GET'])
def catalog_inversores_yaml_info():
    try:
        from import_inversores_yaml import load_yaml_inversores, resolve_yaml_path
        path = resolve_yaml_path()
        if not path:
            return jsonify({'success': False, 'error': 'YAML de inversores não encontrado'}), 404
        rows = load_yaml_inversores(path)
        return jsonify({
            'success': True,
            'path': str(path),
            'count': len(rows),
            'preview': rows[:5],
        })
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
            row = lookup_inverter(
                fab, mod,
                data.get('potencia_kw') or data.get('potencia') or data.get('power'),
            )
        elif kind == 'padrao':
            row = lookup_padrao(data.get('uf', ''), data.get('tipo_ligacao', ''))
        else:
            row = lookup_module(
                fab, mod,
                data.get('potencia_wp') or data.get('potencia') or data.get('power'),
            )
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
        'timestamp': datetime.now().isoformat(),
        'capabilities': {
            'output_open': True,
            'output_config': True,
            'planta_dwg': True,
        },
    })


@app.route('/api/system/requirements', methods=['GET'])
def system_requirements():
    """Dependências opcionais do sistema (ex.: ODA File Converter para planta.dwg)."""
    from dxf_to_dwg import get_oda_status

    oda = get_oda_status()
    install_bat = ROOT_DIR / 'INSTALAR_ODA.bat'
    return jsonify({
        'success': True,
        'oda': {
            **oda,
            'install_script_available': install_bat.is_file(),
            'install_script_path': str(install_bat) if install_bat.is_file() else None,
        },
    })


@app.route('/api/system/oda/launch-installer', methods=['POST'])
def launch_oda_installer():
    """Inicia INSTALAR_ODA.bat (Windows) — o usuário confirma elevação UAC."""
    if os.name != 'nt':
        return jsonify({
            'success': False,
            'error': 'Instalação automática do ODA disponível apenas no Windows.',
        }), 400

    install_bat = ROOT_DIR / 'INSTALAR_ODA.bat'
    if not install_bat.is_file():
        return jsonify({
            'success': False,
            'error': 'INSTALAR_ODA.bat não encontrado na pasta do projeto.',
        }), 404

    try:
        subprocess.Popen(
            ['cmd', '/c', 'start', '', str(install_bat)],
            cwd=str(ROOT_DIR),
            shell=False,
        )
    except OSError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500

    return jsonify({
        'success': True,
        'message': (
            'Instalador do ODA File Converter iniciado. '
            'Confirme a permissão de administrador (UAC) e aguarde a conclusão.'
        ),
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


@app.route('/api/normas', methods=['GET'])
def get_normas():
    """Retorna normas Equatorial GO (padrão entrada, cabos, demanda) para UI/IA."""
    try:
        from normas_loader import (
            calc_pd_max_kw,
            lookup_ramal_conexao,
            resolve_entrada_uc,
            load_normas,
            suggest_demanda_alvo_kw,
        )

        uf = request.args.get('uf', 'GO')
        tipo = request.args.get('tipo_ligacao', 'MONOFASICO')
        classe = request.args.get('classe', 'RESIDENCIAL')
        carga_kw = request.args.get('carga_kw') or request.args.get('demanda_alvo_kw')
        carga_f = None
        if carga_kw not in (None, ''):
            try:
                carga_f = float(str(carga_kw).replace(',', '.'))
            except (TypeError, ValueError):
                pass
        padrao = resolve_entrada_uc(uf, tipo, classe, carga_kw=carga_f)
        disj = padrao.get('disjuntor_a') if padrao else 40
        ramal_faixa = lookup_ramal_conexao(tipo, carga_f) if carga_f is not None else None
        return jsonify({
            'success': True,
            'meta': (load_normas() or {}).get('meta'),
            'padrao_entrada': padrao,
            'ramal_faixa': ramal_faixa,
            'pd_max_kw': calc_pd_max_kw(uf, tipo, disj),
            'demanda_alvo_sugerida_kw': suggest_demanda_alvo_kw(
                uf=uf, tipo_ligacao=tipo, disjuntor_a=disj, classe=classe,
            ),
            'tabela_cabos': (load_normas() or {}).get('tabela_cabos'),
            'tokens_guia': (load_normas() or {}).get('tokens_guia'),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


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
        'thd_pct': inverter.get('thd_pct', ''),
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


@app.route('/api/coordinates/resolve', methods=['POST'])
def resolve_coordinates_api():
    """Converte UTM WGS84 ↔ graus decimais (mesma lógica do gerador de documentos)."""
    try:
        from coordinate_utils import resolve_coordinates

        payload = request.json or {}
        resolved = resolve_coordinates(
            utm_x=payload.get('coordenada_utm_x') or payload.get('utm_x'),
            utm_y=payload.get('coordenada_utm_y') or payload.get('utm_y'),
            fuso_utm=payload.get('fuso_utm'),
            latitude=payload.get('latitude'),
            longitude=payload.get('longitude'),
            raw_text=payload.get('coordenadas_raw') or payload.get('raw_text'),
        )
        if not resolved:
            return jsonify({
                'success': False,
                'error': 'Informe coordenadas UTM, graus decimais ou texto do Google Earth.',
            }), 400

        coords = {
            'coordenada_utm_x': resolved.get('coordenada_utm_x') or resolved.get('COORDENADA_UTM_X'),
            'coordenada_utm_y': resolved.get('coordenada_utm_y') or resolved.get('COORDENADA_UTM_Y'),
            'fuso_utm': resolved.get('fuso_utm') or resolved.get('FUSO_UTM'),
            'latitude': resolved.get('latitude') or resolved.get('LATITUDE'),
            'longitude': resolved.get('longitude') or resolved.get('LONGITUDE'),
        }
        return jsonify({'success': True, 'coordinates': coords})
    except Exception as exc:
        return jsonify({'success': False, 'error': _safe_error_message(exc)}), 500


@app.route('/api/figura-localizacao/preview', methods=['POST'])
def figura_localizacao_preview():
    """Pré-visualiza mapa de localização e sugere zoom (16 rural / 17 urbano)."""
    try:
        import base64
        from io import BytesIO

        from coordinate_utils import resolve_coordinates
        from figura_localizacao import (
            _nominatim_reverse,
            _resolve_zoom_for_location,
            _reverse_geocode_label_from_nominatim,
            build_map_tiles,
        )

        payload = request.json or {}
        data = normalize_form_payload(payload)
        tec = data.get('dados_tecnicos') or {}
        uc = data.get('unidade_consumidora') or {}

        resolved = resolve_coordinates(
            utm_x=uc.get('coordenada_utm_x') or tec.get('coordenada_utm_x'),
            utm_y=uc.get('coordenada_utm_y') or tec.get('coordenada_utm_y'),
            fuso_utm=uc.get('fuso_utm') or tec.get('fuso_utm'),
            latitude=tec.get('latitude'),
            longitude=tec.get('longitude'),
            raw_text=tec.get('coordenadas_raw') or uc.get('coordenadas_raw'),
        )
        if not resolved:
            return jsonify({
                'success': False,
                'error': 'Informe coordenadas para visualizar o mapa.',
            }), 400

        lat = float(str(resolved.get('latitude')).replace(',', '.'))
        lon = float(str(resolved.get('longitude')).replace(',', '.'))

        zoom_raw = payload.get('figura_map_zoom') or tec.get('figura_map_zoom')
        zoom_fixed = None
        if zoom_raw not in (None, '', 'auto'):
            try:
                zoom_fixed = int(str(zoom_raw).strip())
                if not (10 <= zoom_fixed <= 20):
                    zoom_fixed = None
            except ValueError:
                zoom_fixed = None

        nominatim_data = _nominatim_reverse(lat, lon)
        suggested = _resolve_zoom_for_location(lat, lon, nominatim_data=nominatim_data)
        zoom_used = zoom_fixed if zoom_fixed is not None else suggested
        place_label = _reverse_geocode_label_from_nominatim(nominatim_data)

        img = build_map_tiles(lat, lon, zoom=zoom_used, place_label=place_label)
        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)

        return jsonify({
            'success': True,
            'suggested_zoom': suggested,
            'zoom_used': zoom_used,
            'place_label': place_label,
            'image_base64': base64.b64encode(buf.getvalue()).decode('ascii'),
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
            catalog_only=bool(payload.get('catalog_only', False)),
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
    Analisa texto TXT usando IA ou parser local.
    NOVO: Enriquece automaticamente com catálogo SQLite (busca inteligente).
    """
    try:
        data = request.json
        text = data.get('text', '')

        if not text:
            return jsonify({
                'success': False,
                'error': 'Texto vazio'
            }), 400

        # 1. Analisar texto (parser ou IA)
        parsed_data, source = parse_text_with_ai(text)

        # 2. Normalizar payload
        normalized = normalize_form_payload(parsed_data)

        # 3. ENRIQUECER COM CATÁLOGO SQLITE (busca inteligente 3 camadas!)
        enriched = enrich_normalized_payload(normalized)

        return jsonify({
            'success': True,
            'source': source,
            'data': enriched,
            'catalog_enriched': True,
            'normas_applied': bool((enriched.get('dados_tecnicos') or {}).get('normas_fonte')),
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

        equipment_error = validate_modules_inverters(modules, inverters)
        if equipment_error:
            return jsonify({
                'success': False,
                'error': equipment_error,
            }), 400

        # Catálogo SQLite — sem IA e sem aproximar potência (ex.: 544 W ≠ 620 W)
        modules, inverters, enrich_sources = enrich_equipment_lists(
            modules, inverters, catalog_only=True,
        )
        normalized_pre = normalize_form_payload(data)
        enriched_pre = enrich_normalized_payload({
            'modulos': modules,
            'inversores': inverters,
            'cliente': normalized_pre.get('cliente') or {},
            'unidade_consumidora': normalized_pre.get('unidade_consumidora') or {},
            'dados_tecnicos': normalized_pre.get('dados_tecnicos') or {},
        })
        modules = enriched_pre.get('modulos') or modules
        inverters = enriched_pre.get('inversores') or inverters

        context = {
            'client': {},
            'technical': data.get('technical') or {},
            'demand_table_ai': data.get('demand_table_ai', False),
            'hsp': data.get('hsp'),
        }
        normalized = normalized_pre
        cliente = normalized.get('cliente') or {}
        uc = normalized.get('unidade_consumidora') or {}
        tecnicos = normalized.get('dados_tecnicos') or {}
        web_client = data.get('client') or {}
        context['client'] = {
            **cliente,
            **web_client,
            'client_name': cliente.get('nome') or web_client.get('client_name') or data.get('client_name'),
            'consumer_unit': uc.get('numero') or web_client.get('consumer_unit') or data.get('consumer_unit'),
            'classe': uc.get('classe') or web_client.get('classe') or data.get('classe') or 'RESIDENCIAL',
            'tensao_atendimento': (
                uc.get('tensao_atendimento')
                or web_client.get('tensao_atendimento')
                or data.get('tensao_atendimento')
            ),
            'tipo_ligacao': (
                uc.get('tipo_ligacao')
                or web_client.get('tipo_ligacao')
                or data.get('tipo_ligacao')
            ),
        }
        context['technical'] = {**tecnicos, **context['technical']}
        if data.get('demanda_alvo_kw') is not None:
            context['technical']['demanda_alvo_kw'] = data.get('demanda_alvo_kw')
        if data.get('demanda_modelo_id'):
            context['technical']['demanda_modelo_id'] = data.get('demanda_modelo_id')
        elif context['technical'].get('demanda_modelo_id'):
            pass

        calculations = calculate_technical_parameters(modules, inverters, context)

        return jsonify({
            'success': True,
            'calculations': calculations,
            'modules': [_module_to_frontend(m) for m in modules],
            'inverters': [_inverter_to_frontend(i) for i in inverters],
            'enrichment_sources': enrich_sources,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': _safe_error_message(e),
        }), 500


@app.route('/api/demanda-modelos', methods=['GET'])
def list_demanda_modelos():
    """Lista modelos prontos de tabela de demanda (NTC-04)."""
    try:
        from demand_presets import list_models, load_catalog
        return jsonify({
            'success': True,
            'meta': load_catalog().get('meta'),
            'modelos': list_models(),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/demanda-modelos/<modelo_id>/gerar', methods=['POST'])
def gerar_demanda_modelo(modelo_id):
    """Gera tabela de demanda a partir de um modelo JSON."""
    try:
        from demand_presets import apply_model_to_payload, generate_from_model

        data = request.json or {}
        client = data.get('client') or {}
        target_raw = data.get('demanda_alvo_kw') or data.get('target_kw')
        target = float(str(target_raw).replace(',', '.')) if target_raw not in (None, '') else None

        table = generate_from_model(
            modelo_id,
            client_name=client.get('client_name') or data.get('client_name') or '',
            uc=client.get('consumer_unit') or data.get('consumer_unit') or '',
            target_kw=target,
            notes=data.get('demanda_notas') or data.get('notes') or '',
        )

        payload_patch = {}
        if data.get('apply_form'):
            normalized = normalize_form_payload({
                'client': client,
                'technical': data.get('technical') or {},
                'clientData': client,
                'technicalData': data.get('technical') or {},
            })
            apply_model_to_payload(normalized, modelo_id)
            payload_patch = {
                'classe': normalized.get('unidade_consumidora', {}).get('classe'),
                'tipo_ligacao': normalized.get('unidade_consumidora', {}).get('tipo_ligacao'),
                'tensao_atendimento': normalized.get('unidade_consumidora', {}).get('tensao_atendimento'),
                'disjuntor_entrada': normalized.get('unidade_consumidora', {}).get('disjuntor_entrada'),
                'demanda_alvo_kw': normalized.get('dados_tecnicos', {}).get('demanda_alvo_kw'),
            }

        return jsonify({
            'success': True,
            'demand_table': table,
            'form_patch': payload_patch,
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/generate-demand-table', methods=['POST'])
def generate_demand_table_endpoint():
    """Gera apenas a tabela de demanda para memorial descritivo."""
    try:
        from demand_table import generate_demand_table

        data = request.json or {}
        modelo_id = data.get('demanda_modelo_id') or data.get('modelo_id')

        if modelo_id:
            from demand_presets import generate_from_model
            target_raw = data.get('demanda_alvo_kw') or data.get('target_kw')
            target = float(str(target_raw).replace(',', '.')) if target_raw not in (None, '') else None
            client = data.get('client') or {}
            table = generate_from_model(
                modelo_id,
                client_name=client.get('client_name') or data.get('client_name') or '',
                uc=client.get('consumer_unit') or data.get('consumer_unit') or '',
                target_kw=target,
                notes=data.get('demanda_notas') or data.get('notes') or '',
            )
            return jsonify({'success': True, 'demand_table': table})

        target = float(data.get('demanda_alvo_kw') or data.get('target_kw', 0))
        if target <= 0:
            return jsonify({'success': False, 'error': 'Informe demanda-alvo em kW'}), 400

        client = data.get('client') or {}
        table = generate_demand_table(
            target_kw=target,
            classe=client.get('classe') or data.get('classe') or 'RESIDENCIAL',
            client_name=client.get('client_name') or data.get('client_name') or '',
            uc=client.get('consumer_unit') or data.get('consumer_unit') or '',
            notes=data.get('demanda_notas') or data.get('notes') or '',
            prefer_ai=bool(data.get('use_ai')),
        )
        return jsonify({'success': True, 'demand_table': table})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/export-calculations', methods=['POST'])
def export_calculations_endpoint():
    """
    Exporta cálculos técnicos em JSON, CSV e TXT.
    Retorna URLs para download dos arquivos gerados.
    """
    try:
        from export_calculations import export_all_formats
        from system_calculations import calculate_technical_parameters

        data = request.json or {}
        modules = data.get('modules') or data.get('modulos') or []
        inverters = data.get('inverters') or data.get('inversores') or []
        context = {
            'client': data.get('client') or data.get('cliente') or {},
            'technical': data.get('technical') or data.get('dados_tecnicos') or {},
            'hsp': data.get('hsp'),
            'demand_table_ai': data.get('demand_table_ai', False),
        }

        calc_result = calculate_technical_parameters(modules, inverters, context)

        # Gerar nome único baseado em timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        client_name = context['client'].get('nome') or context['client'].get('client_name') or 'cliente'
        # Sanitizar nome do cliente para usar em arquivo
        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '' for c in client_name)[:30]
        base_name = f'calculos_{safe_name}_{timestamp}'

        output_base, _output_warn = get_output_base_dir()
        output_dir = output_base / base_name
        paths = export_all_formats(calc_result, output_dir, 'relatorio_calculos')

        return jsonify({
            'success': True,
            'files': {
                'json': f'/api/download/{base_name}/relatorio_calculos.json',
                'csv': f'/api/download/{base_name}/relatorio_calculos.csv',
                'txt': f'/api/download/{base_name}/relatorio_calculos.txt',
            },
            'calculations': calc_result,
        })
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


@app.route('/api/output-config', methods=['GET', 'POST'])
def output_config():
    """Pasta de saída dos documentos (Google Drive / disco local / fallback)."""
    try:
        if request.method == 'POST':
            if session.get('role') != 'master':
                return jsonify({'success': False, 'error': 'Somente administrador pode alterar a pasta de saída.'}), 403
            data = request.get_json(silent=True) or {}
            raw_path = (data.get('client_output_dir') or '').strip()
            save_local_output_dir(raw_path)
            status = output_config_status()
            return jsonify({
                'success': True,
                'message': 'Pasta de saída atualizada.' if raw_path else 'Override local removido — usando .env ou padrão.',
                **status,
            })

        return jsonify({'success': True, **output_config_status()})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/app-settings', methods=['GET', 'POST'])
def app_settings_endpoint():
    """Parâmetros globais: HSP, geração, mapa de localização (app_settings.local.json)."""
    try:
        from app_settings import load_app_settings, save_app_settings, reset_app_settings

        if request.method == 'POST':
            if session.get('role') != 'master':
                return jsonify({'success': False, 'error': 'Somente administrador pode alterar configurações.'}), 403
            data = request.get_json(silent=True) or {}
            if data.get('reset'):
                settings = reset_app_settings()
            else:
                patch = data.get('settings') if isinstance(data.get('settings'), dict) else data
                settings = save_app_settings(patch)
            return jsonify({'success': True, 'settings': settings, 'message': 'Configurações salvas.'})

        return jsonify({'success': True, 'settings': load_app_settings()})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/output/open-folder', methods=['POST'])
def open_output_folder():
    """Abre a pasta do cliente (ou base) no Explorer/Finder."""
    try:
        data = request.get_json(silent=True) or {}
        folder_name = (data.get('folder_name') or '').strip()
        output_base, _ = get_output_base_dir()
        target = output_base / folder_name if folder_name else output_base
        target = target.resolve()
        if not str(target).startswith(str(output_base.resolve())):
            return jsonify({'success': False, 'error': 'Pasta inválida'}), 403
        if folder_name and not target.is_dir():
            return jsonify({'success': False, 'error': 'Pasta do cliente não encontrada'}), 404
        if not folder_name:
            target.mkdir(parents=True, exist_ok=True)
        open_path_in_os(target)
        return jsonify({'success': True, 'path': str(target)})
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/output/open-file', methods=['POST'])
def open_output_file():
    """Abre arquivo gerado no aplicativo padrão (Word, Excel, AutoCAD…)."""
    try:
        data = request.get_json(silent=True) or {}
        folder_name = (data.get('folder_name') or '').strip()
        file_name = (data.get('file_name') or '').strip()
        if not folder_name or not file_name:
            return jsonify({'success': False, 'error': 'folder_name e file_name são obrigatórios'}), 400
        output_base, _ = get_output_base_dir()
        file_path = resolve_client_file(output_base, folder_name, file_name)
        open_path_in_os(file_path)
        return jsonify({'success': True, 'path': str(file_path)})
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/fill-documents', methods=['POST'])
def fill_documents():
    """
    Endpoint para gerar documentos preenchidos
    """
    try:
        data = request.json or {}

        # Normalizar payload plano do frontend → estrutura aninhada
        data = normalize_form_payload(data)

        # Extrair nome do cliente
        client_name = (
            data.get('cliente', {}).get('nome')
            or data.get('client_name')
        )

        # Número do contrato = nome da pasta (ex.: 80, 122-2026)
        numero_contrato = (
            data.get('contrato', {}).get('numero_contrato')
            or data.get('contract', {}).get('numero_contrato')
            or data.get('numero_contrato')
        )

        # Extrair UC (opcional)
        consumer_unit = (
            data.get('unidade_consumidora', {}).get('numero')
            or data.get('consumer_unit')
        )

        if not client_name:
            return jsonify({
                'success': False,
                'error': 'Nome do cliente é obrigatório'
            }), 400

        if not (numero_contrato or '').strip():
            return jsonify({
                'success': False,
                'error': 'Número do contrato é obrigatório — a pasta de saída usa esse número (ex.: 80, 122/2026).'
            }), 400

        try:
            folder_name = folder_name_from_contract(numero_contrato, client_name)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

        output_base, output_warning = get_output_base_dir()
        output_dir = output_base / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)

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
        contrato_file = None
        planta_file = None
        other_files = []

        for file in output_dir.iterdir():
            if not file.is_file():
                continue
            suffix = file.suffix.lower()
            if suffix not in ('.docx', '.xlsx', '.dxf', '.dwg', '.png', '.txt'):
                continue
            file_info = {
                'name': file.name,
                'size': file.stat().st_size,
                'path': str(file),
                'download_url': f"/api/download/{folder_name}/{file.name}",
                **_file_actions(folder_name, file.name, suffix),
            }

            if suffix == '.xlsx':
                excel_file = file_info
            elif suffix == '.dwg' and file.name.lower() == 'planta.dwg':
                planta_file = file_info
            elif suffix == '.dxf' and file.name.lower() == 'planta.dxf' and not planta_file:
                planta_file = file_info
            elif suffix == '.docx' and 'memorial' in file.name.lower():
                memorial_file = file_info
            elif suffix == '.docx' and ('procuracao' in file.name.lower() or 'procura' in file.name.lower()):
                procuracao_file = file_info
            elif suffix == '.docx' and file.name.lower() == 'modelocontrato.docx':
                contrato_file = file_info
            elif suffix == '.docx':
                other_files.append(file_info)
            elif file.name.lower() in (
                'figura_localizacao.png',
                'tokens_autocad.txt',
                'relatorio_preenchimento.txt',
            ):
                other_files.append(file_info)

        return jsonify({
            'success': True,
            'message': 'Documentos gerados com sucesso!',
            'output_directory': str(output_dir),
            'output_base': str(output_base),
            'folder_name': folder_name,
            'numero_contrato': numero_contrato.strip(),
            'output_warning': output_warning,
            'files': {
                'excel': excel_file,
                'memorial': memorial_file,
                'procuracao': procuracao_file,
                'contrato': contrato_file,
                'planta': planta_file,
                'outros': other_files
            },
            'planta_format': (
                'dwg' if planta_file and planta_file['name'].lower().endswith('.dwg')
                else 'dxf' if planta_file else None
            ),
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
    SEGURANÇA: Previne path traversal (../) e garante que arquivo está dentro da pasta de saída configurada
    """
    try:
        output_base, _ = get_output_base_dir()
        output_base = output_base.resolve()
        # Resolver path completo e normalizar
        file_path = (output_base / filepath).resolve()

        # SEGURANÇA: Verificar que o arquivo está dentro do diretório permitido
        if not str(file_path).startswith(str(output_base)):
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


@app.route('/api/view/<folder_name>/<file_name>', methods=['GET'])
def view_file(folder_name, file_name):
    """Visualiza arquivo no navegador (PNG, TXT)."""
    try:
        from urllib.parse import unquote
        folder_name = unquote(folder_name)
        file_name = unquote(file_name)
        suffix = Path(file_name).suffix.lower()
        if suffix not in VIEWABLE_SUFFIXES:
            return jsonify({'success': False, 'error': 'Tipo de arquivo não suportado para visualização web'}), 400

        output_base, _ = get_output_base_dir()
        file_path = resolve_client_file(output_base, folder_name, file_name)
        return send_file(
            file_path,
            as_attachment=False,
            mimetype=VIEW_MIME.get(suffix, 'application/octet-stream'),
            download_name=file_path.name,
        )
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except Exception:
        return jsonify({'success': False, 'error': 'Erro ao abrir arquivo'}), 500


@app.route('/api/list-clients', methods=['GET'])
def list_clients():
    """
    Lista todos os clientes processados
    """
    try:
        clients = []
        output_base, _ = get_output_base_dir()

        for client_dir in output_base.iterdir():
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


@app.route('/api/catalog/search-modules', methods=['POST'])
def search_modules_endpoint():
    """
    Busca fuzzy de módulos fotovoltaicos no catálogo SQLite.
    
    POST body:
    {
        "query": "termo de busca",
        "fabricante": "filtro por fabricante",
        "potencia_min": 400,
        "potencia_max": 600,
        "limit": 10
    }
    
    Returns:
    {
        "success": true,
        "results": [...],
        "count": 5
    }
    """
    try:
        from catalog_db import search_modules_fuzzy
        
        data = request.json or {}
        query = data.get('query', '')
        fabricante = data.get('fabricante', '')
        potencia_min = data.get('potencia_min', 0)
        potencia_max = data.get('potencia_max', 999999)
        limit = data.get('limit', 10)
        
        results = search_modules_fuzzy(
            query=query,
            fabricante=fabricante,
            potencia_min=potencia_min,
            potencia_max=potencia_max,
            limit=limit,
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/catalog/search-inverters', methods=['POST'])
def search_inverters_endpoint():
    """
    Busca fuzzy de inversores no catálogo SQLite.
    
    POST body:
    {
        "query": "termo de busca",
        "fabricante": "filtro por fabricante",
        "potencia_min": 5,
        "potencia_max": 15,
        "tipo_inversor": "micro",
        "limit": 10
    }
    
    Returns:
    {
        "success": true,
        "results": [...],
        "count": 5
    }
    """
    try:
        from catalog_db import search_inverters_fuzzy
        
        data = request.json or {}
        query = data.get('query', '')
        fabricante = data.get('fabricante', '')
        potencia_min = data.get('potencia_min', 0)
        potencia_max = data.get('potencia_max', 999999)
        tipo_inversor = data.get('tipo_inversor', '')
        limit = data.get('limit', 10)
        
        results = search_inverters_fuzzy(
            query=query,
            fabricante=fabricante,
            potencia_min=potencia_min,
            potencia_max=potencia_max,
            tipo_inversor=tipo_inversor,
            limit=limit,
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/catalog/find-module', methods=['POST'])
def find_module_endpoint():
    """
    Busca inteligente de módulo com estratégia de 3 camadas.
    
    POST body:
    {
        "fabricante": "Canadian Solar",
        "modelo": "CS3W-400P",
        "potencia_wp": 400
    }
    
    Returns:
    {
        "success": true,
        "found": true,
        "module": {...},
        "match_type": "exact" | "power_exact" | "power_tolerance"
    }
    """
    try:
        from catalog_db import find_module_by_name_or_power
        
        data = request.json or {}
        fabricante = data.get('fabricante', '')
        modelo = data.get('modelo', '')
        potencia_wp = data.get('potencia_wp', 0)
        
        module = find_module_by_name_or_power(
            fabricante=fabricante,
            modelo=modelo,
            potencia_wp=potencia_wp,
        )
        
        # Determinar tipo de match
        match_type = None
        if module:
            if modelo and module.get('modelo', '').lower() in modelo.lower():
                match_type = 'exact'
            elif potencia_wp and module.get('potencia_wp') == potencia_wp:
                match_type = 'power_exact'
            else:
                match_type = 'power_tolerance'
        
        return jsonify({
            'success': True,
            'found': bool(module),
            'module': module,
            'match_type': match_type,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


@app.route('/api/catalog/find-inverter', methods=['POST'])
def find_inverter_endpoint():
    """
    Busca inteligente de inversor com estratégia de 3 camadas.
    
    POST body:
    {
        "fabricante": "Deye",
        "modelo": "SUN-6K-SG04LP3-EU",
        "potencia_kw": 6
    }
    
    Returns:
    {
        "success": true,
        "found": true,
        "inverter": {...},
        "match_type": "exact" | "power_exact" | "power_tolerance"
    }
    """
    try:
        from catalog_db import find_inverter_by_name_or_power
        
        data = request.json or {}
        fabricante = data.get('fabricante', '')
        modelo = data.get('modelo', '')
        potencia_kw = data.get('potencia_kw', 0)
        
        inverter = find_inverter_by_name_or_power(
            fabricante=fabricante,
            modelo=modelo,
            potencia_kw=potencia_kw,
        )
        
        # Determinar tipo de match
        match_type = None
        if inverter:
            if modelo and inverter.get('modelo', '').lower() in modelo.lower():
                match_type = 'exact'
            elif potencia_kw and inverter.get('potencia_kw') == potencia_kw:
                match_type = 'power_exact'
            else:
                match_type = 'power_tolerance'
        
        return jsonify({
            'success': True,
            'found': bool(inverter),
            'inverter': inverter,
            'match_type': match_type,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': _safe_error_message(e)}), 500


if __name__ == '__main__':
    is_dev = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == '1'

    print("=" * 80)
    print("API Server - Automação Equatorial (Versão Unificada)")
    print("=" * 80)
    print(f"Modo: {'DESENVOLVIMENTO' if is_dev else 'PRODUÇÃO'}")
    print(f"Servidor: http://{'0.0.0.0' if is_dev else '127.0.0.1'}:5000")
    print(f"Frontend: http://localhost:5173")
    print(f"Diretório base: {BASE_DIR}")
    print(f"Templates: {TEMPLATES_DIR}")
    out_base, out_warn = get_output_base_dir()
    print(f"Saída: {out_base}")
    if out_warn:
        print(f"  AVISO: {out_warn}")
    print("\nEndpoints disponíveis:")
    print("  GET  /api/health          - Status do servidor")
    print("  POST /api/auth/login       - Login (sessão)")
    print("  GET  /api/auth/me          - Usuário logado")
    print("  POST /api/auth/users       - Criar usuário (master)")
    print("  GET  /api/ai-status       - Status da IA (Ollama/Gemini)")
    print("  POST /api/analyze-text    - Análise de texto com IA")
    print("  POST /api/enrich-equipment - Buscar specs módulos/inversores")
    print("  POST /api/calculate-system - Cálculos técnicos")
    print("  POST /api/preview-de-para  - Conferência DE/PARA (placeholders)")
    print("  POST /api/fill-documents  - Gerar documentos")
    print("  GET  /api/download/<path> - Download de arquivos")
    print("  GET  /api/list-clients    - Listar clientes")
    print("=" * 80)

    app.run(
        debug=is_dev,
        use_reloader=False,
        host='0.0.0.0' if is_dev else '127.0.0.1',
        port=5000,
    )

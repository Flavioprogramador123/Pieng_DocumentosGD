"""
API Server para Automação de Documentos Equatorial
Backend Flask que conecta o frontend React ao gerador de documentos Python
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import json
import tempfile
import shutil
from datetime import datetime
import subprocess
import sys
import re
import os

app = Flask(__name__)

# SEGURANÇA: Configuração do Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# CORS: Apenas origem do frontend local
CORS(app, origins=['http://localhost:5173', 'http://127.0.0.1:5173'])

# Diretórios
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'templates'
CONFIG_FILE = BASE_DIR / 'config_padrao.json'
OUTPUT_BASE_DIR = BASE_DIR / 'saida' / 'web_generated'

# Garantir que diretório de saída existe
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)


def calculate_technical_parameters(modules, inverters):
    """
    Calcula parâmetros técnicos do sistema fotovoltaico
    IMPORTANTE: Módulos em W (Wp), Inversores em kW
    """
    # Potência total dos módulos (em Watts)
    total_module_power_w = sum(
        int(m.get('quantidade', m.get('quantity', 0))) * float(m.get('potencia', m.get('power', 0)))
        for m in modules if m.get('quantidade') or m.get('quantity')
    )
    total_module_power_kw = total_module_power_w / 1000

    # Potência total dos inversores (já em kW)
    total_inverter_power_kw = sum(
        int(i.get('quantidade', i.get('quantity', 0))) * float(i.get('potencia', i.get('power', 0)))
        for i in inverters if i.get('quantidade') or i.get('quantity')
    )

    # Geração mensal estimada
    # HSP Goiás: 5.2 h/dia (pode ser ajustado por UF)
    # Eficiência: 80% (conservador - inclui perdas de cabeamento, sujeira, temperatura)
    # Dias/mês: 30.4 (média anual)
    hsp_goias = 5.2
    efficiency = 0.80
    days_per_month = 30.4
    estimated_monthly_generation = total_module_power_kw * hsp_goias * efficiency * days_per_month

    # Recomendação de cabo baseada na potência
    if total_module_power_kw <= 5:
        cable_section_cc = "6mm²"
        cable_section_ca = "10mm²"
    elif total_module_power_kw <= 10:
        cable_section_cc = "10mm²"
        cable_section_ca = "16mm²"
    elif total_module_power_kw <= 20:
        cable_section_cc = "16mm²"
        cable_section_ca = "25mm²"
    else:
        cable_section_cc = "25mm²"
        cable_section_ca = "35mm²"

    # Disjuntor recomendado (baseado na corrente AC)
    # Assumindo tensão 220V bifásica como padrão
    corrente_ac = (total_inverter_power_kw * 1000) / 220
    disjuntor_recomendado = int(corrente_ac * 1.25)  # 25% de margem

    # Economia estimada
    tarifa_kwh = 1.10  # R$/kWh Goiás 2025 (estimativa)
    economia_mensal = estimated_monthly_generation * tarifa_kwh

    # Relação módulo/inversor (ideal entre 1.1 e 1.3)
    relacao_modulo_inversor = total_module_power_kw / total_inverter_power_kw if total_inverter_power_kw > 0 else 0

    return {
        'total_module_power_kw': round(total_module_power_kw, 2),
        'total_inverter_power_kw': round(total_inverter_power_kw, 2),
        'estimated_monthly_generation': round(estimated_monthly_generation, 0),
        'cable_section_cc': cable_section_cc,
        'cable_section_ca': cable_section_ca,
        'disjuntor_recomendado': disjuntor_recomendado,
        'relacao_modulo_inversor': round(relacao_modulo_inversor, 2),
        'economia_mensal_estimada': round(economia_mensal, 2),
        # Compatibilidade com frontend antigo
        'cable_section_recommendation': f"{cable_section_cc} CC / {cable_section_ca} CA",
        'power_summary': {
            'total_module_power': total_module_power_kw,
            'total_inverter_power': total_inverter_power_kw,
            'ratio': round(relacao_modulo_inversor, 2)
        },
        'generation': {
            'monthly_kwh': round(estimated_monthly_generation, 0),
            'daily_kwh': round(estimated_monthly_generation / 30.4, 1)
        },
        'compatibility': {
            'status': 'OK' if 1.1 <= relacao_modulo_inversor <= 1.3 else 'ATENÇÃO',
            'message': 'Relação módulo/inversor adequada' if 1.1 <= relacao_modulo_inversor <= 1.3 else 'Relação fora do ideal (1.1-1.3)'
        }
    }


def create_txt_data(data):
    """
    Converte dados do formulário web para formato TXT esperado pelo gerador
    Mapeia TODOS os campos do frontend para os tokens do gerar_documentos.py
    """
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

    # === DADOS TÉCNICOS ===
    tecnicos = data.get('dados_tecnicos', {})

    if tecnicos.get('area_arranjo'):
        lines.append(f"Área dos Arranjos (m²): {tecnicos['area_arranjo']}")
    if tecnicos.get('tipo_fonte'):
        lines.append(f"Tipo de Fonte: {tecnicos['tipo_fonte']}")
    if tecnicos.get('data_operacao'):
        lines.append(f"Data Prevista de Operação: {tecnicos['data_operacao']}")

    # Cabos e proteções
    if tecnicos.get('bitola_cabo_cc'):
        lines.append(f"Bitola do Cabo CC: {tecnicos['bitola_cabo_cc']}")
    if tecnicos.get('bitola_cabo_ca'):
        lines.append(f"Bitola do Cabo CA: {tecnicos['bitola_cabo_ca']}")
    if tecnicos.get('dps_cc'):
        lines.append(f"DPS CC: {tecnicos['dps_cc']}")
    if tecnicos.get('dps_ca'):
        lines.append(f"DPS CA: {tecnicos['dps_ca']}")
    if tecnicos.get('aterramento'):
        lines.append(f"Aterramento: {tecnicos['aterramento']}")
    if tecnicos.get('disjuntor_curva'):
        lines.append(f"Curva do Disjuntor: {tecnicos['disjuntor_curva']}")

    # Data do documento
    hoje = datetime.now()
    lines.append(f"\nData do Documento: {hoje.strftime('%d/%m/%Y')}")
    lines.append(f"Cidade do Documento: {cliente.get('cidade', 'Anápolis')}")

    return '\n'.join(lines)


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

    # Tentar Ollama primeiro (se disponível)
    try:
        import requests
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'deepseek-r1:8b',
                'prompt': f"""Extraia as informações do texto abaixo e retorne APENAS um JSON válido:

{text}

Formato esperado:
{{
  "nome": "...",
  "cpf": "...",
  "rg": "...",
  "data_nascimento": "...",
  "telefone": "...",
  "email": "...",
  "endereco_completo": "...",
  "logradouro": "...",
  "numero": "...",
  "bairro": "...",
  "cidade": "...",
  "uf": "...",
  "uc": "...",
  "tensao": "...",
  "modulos": [{{"quantidade": ..., "fabricante": "...", "modelo": "...", "potencia": ...}}],
  "inversores": [{{"quantidade": ..., "fabricante": "...", "modelo": "...", "potencia": ...}}]
}}""",
                'stream': False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            ai_text = result.get('response', '')
            # Tentar extrair JSON da resposta
            json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group(0))
                # Mapear dados da IA para estrutura esperada
                if ai_data.get('nome'):
                    parsed_data['cliente']['nome'] = ai_data['nome']
                # ... (continuar mapeamento)
                return parsed_data, 'ollama'
    except:
        pass  # Fallback para parser regex

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
        elif 'rg' in label or 'cnh' in label:
            parsed_data['cliente']['rg'] = value
        elif 'nascimento' in label or 'validade' in label:
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
            # Extrair apenas números
            uc_match = re.search(r'(\d{10,})', value)
            if uc_match:
                parsed_data['unidade_consumidora']['numero'] = uc_match.group(1)
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
    """Verifica status da IA (Ollama)"""
    status = {
        'ollama': False,
        'model': None
    }

    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            if models:
                status['ollama'] = True
                status['model'] = models[0].get('name', 'unknown')
    except:
        pass

    return jsonify(status)


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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500


@app.route('/api/calculate-system', methods=['POST'])
def calculate_system():
    """
    Endpoint para calcular parâmetros técnicos do sistema
    """
    try:
        data = request.json
        modules = data.get('modules', [])
        inverters = data.get('inverters', [])

        if not modules or not inverters:
            return jsonify({
                'success': False,
                'error': 'Módulos e inversores são obrigatórios'
            }), 400

        calculations = calculate_technical_parameters(modules, inverters)

        return jsonify({
            'success': True,
            'calculations': calculations
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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
                'error': f'Erro ao gerar documentos: {result.stderr}'
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
            'txt_content': txt_content
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
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
            'error': str(e)
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
    print("  GET  /api/ai-status       - Status da IA (Ollama)")
    print("  POST /api/analyze-text    - Análise de texto com IA")
    print("  POST /api/calculate-system - Cálculos técnicos")
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

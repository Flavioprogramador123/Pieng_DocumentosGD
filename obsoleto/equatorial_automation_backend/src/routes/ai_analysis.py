from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import requests
import json
import os

ai_bp = Blueprint('ai', __name__)

# Configuração de APIs
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:8b"

# Fallback para Gemini se Ollama não estiver disponível
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

def query_ollama(prompt, text):
    """Query Ollama local API"""
    try:
        full_prompt = f"{prompt}\n\nTexto para analisar:\n{text}\n\nResponda APENAS com um JSON válido, sem explicações adicionais."

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "temperature": 0.1,
            "format": "json"
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=180)

        if response.status_code == 200:
            result = response.json()
            return result.get('response', '{}')
        else:
            return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def query_gemini(prompt, text):
    """Query Gemini API (fallback)"""
    try:
        if not GEMINI_API_KEY:
            return None

        full_prompt = f"{prompt}\n\nTexto para analisar:\n{text}\n\nResponda APENAS com um JSON válido."

        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048
            }
        }

        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            # Limpar markdown se houver
            text = text.replace('```json', '').replace('```', '').strip()
            return text
        else:
            return None
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

@ai_bp.route('/analyze-text', methods=['POST'])
@cross_origin()
def analyze_text():
    """
    Endpoint para análise inteligente de texto usando IA
    Usa Ollama (local) como primeira opção, Gemini como fallback
    """
    try:
        data = request.json
        text = data.get('text', '')

        if not text:
            return jsonify({'error': 'Texto vazio'}), 400

        print(f"Usando parser local (IA desabilitada temporariamente)")
        print(f"Tamanho do texto: {len(text)} caracteres")

        # Usar parser local melhorado
        import re

        parsed_data = {
            "cliente": {},
            "unidade_consumidora": {},
            "modulos": [],
            "inversores": [],
            "dados_tecnicos": {}
        }

        # Extrair dados linha por linha
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if not value:
                continue

            # Cliente
            if 'nome' in key and 'pai' not in key and 'mãe' not in key:
                parsed_data['cliente']['nome'] = value
            elif 'cpf' in key:
                parsed_data['cliente']['cpf'] = value.split('/')[0].strip()
            elif 'rg' in key:
                parsed_data['cliente']['rg'] = value
            elif 'nascimento' in key:
                parsed_data['cliente']['data_nascimento'] = value
            elif 'telefone' in key:
                parsed_data['cliente']['telefone'] = value
            elif 'mail' in key:
                parsed_data['cliente']['email'] = value
            elif 'cep' in key:
                parsed_data['cliente']['cep'] = value

            # Endereço completo
            elif 'endereço' in key or 'endereco' in key:
                endereco_completo = value
                parsed_data['cliente']['endereco_completo'] = endereco_completo

                # Fragmentar endereço
                # Extrair quadra
                match_q = re.search(r'Q\.?\s*([A-Z0-9/\-]+)', endereco_completo, re.I)
                if match_q:
                    parsed_data['cliente']['complemento'] = f"Q. {match_q.group(1)}"

                # Extrair lote
                match_l = re.search(r'L\.?\s*([A-Z0-9/\-]+)', endereco_completo, re.I)
                if match_l:
                    if parsed_data['cliente'].get('complemento'):
                        parsed_data['cliente']['complemento'] += f", L. {match_l.group(1)}"
                    else:
                        parsed_data['cliente']['complemento'] = f"L. {match_l.group(1)}"

                # Extrair logradouro e bairro
                partes = [p.strip() for p in endereco_completo.split(',')]
                if len(partes) >= 1:
                    parsed_data['cliente']['logradouro'] = partes[0]
                if len(partes) >= 2:
                    # Último item geralmente é o bairro
                    parsed_data['cliente']['bairro'] = partes[-1]

            elif 'cidade' in key or 'município' in key:
                if '/' in value:
                    cidade, uf = value.split('/')
                    parsed_data['cliente']['cidade'] = cidade.strip()
                    parsed_data['cliente']['uf'] = uf.strip()
                else:
                    parsed_data['cliente']['cidade'] = value

            # UC
            elif 'unidade consumidora' in key or key == 'uc':
                parsed_data['unidade_consumidora']['numero_uc'] = value

            # Tensão e conexão
            elif 'padrão' in key or 'conexão' in key or 'conexao' in key:
                parsed_data['unidade_consumidora']['tensao_atendimento'] = value
                if 'trifásico' in value.lower() or 'trifasico' in value.lower() or '380' in value:
                    parsed_data['unidade_consumidora']['tipo_ligacao'] = 'TRIFASICO'
                elif 'bifásico' in value.lower() or 'bifasico' in value.lower():
                    parsed_data['unidade_consumidora']['tipo_ligacao'] = 'BIFASICO'
                else:
                    parsed_data['unidade_consumidora']['tipo_ligacao'] = 'MONOFASICO'

            # Disjuntor
            elif 'disjuntor' in key and 'ac' in key:
                match = re.search(r'(\d+)\s*A', value)
                if match:
                    parsed_data['unidade_consumidora']['disjuntor_entrada'] = match.group(1)

            # Módulos
            elif 'módulos' in key or 'módulos fotovoltaicos' in key or 'modulos' in key:
                match_qty = re.search(r'(\d+)\s*unidades?', value)
                match_power = re.search(r'(\d+)\s*W', value)

                fabricantes = ['RENEPV', 'JINKO', 'CANADIAN', 'TRINA', 'JA SOLAR', 'LONGI']
                fabricante = ''
                for fab in fabricantes:
                    if fab in value.upper():
                        fabricante = fab
                        break

                parsed_data['modulos'].append({
                    'quantidade': match_qty.group(1) if match_qty else '',
                    'fabricante': fabricante,
                    'modelo': value,
                    'potencia': match_power.group(1) if match_power else ''
                })

            # Inversores
            elif 'inversor' in key or 'microinversor' in key:
                match_qty = re.search(r'(\d+)\s*unidades?', value)
                match_power = re.search(r'(\d+(?:\.\d+)?)\s*kW', value, re.I)

                fabricantes = ['DEYE', 'GROWATT', 'FRONIUS', 'SOFAR', 'HUAWEI']
                fabricante = ''
                for fab in fabricantes:
                    if fab in value.upper():
                        fabricante = fab
                        break

                parsed_data['inversores'].append({
                    'quantidade': match_qty.group(1) if match_qty else '',
                    'fabricante': fabricante,
                    'modelo': value,
                    'potencia': match_power.group(1) if match_power else ''
                })

            # Cabeamento
            elif 'cabeamento' in key and 'ac' in key:
                match = re.search(r'(\d+)\s*mm', value)
                if match:
                    parsed_data['dados_tecnicos']['bitola_cabo_ca'] = match.group(1)

        # Garantir estrutura mínima
        if not parsed_data['modulos']:
            parsed_data['modulos'] = [{}]
        if not parsed_data['inversores']:
            parsed_data['inversores'] = [{}]

        source = "parser_local"

        return jsonify({
            'success': True,
            'source': source,
            'data': parsed_data
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in analyze_text: {error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500

@ai_bp.route('/ai-status', methods=['GET'])
@cross_origin()
def ai_status():
    """Verifica status das APIs de IA"""
    status = {
        'ollama': False,
        'gemini': False,
        'available_models': []
    }

    # Verificar Ollama
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            status['ollama'] = True
            models = response.json().get('models', [])
            status['available_models'] = [m['name'] for m in models]
    except:
        pass

    # Verificar Gemini
    if GEMINI_API_KEY:
        status['gemini'] = True

    status['primary'] = 'ollama' if status['ollama'] else ('gemini' if status['gemini'] else 'none')

    return jsonify(status)

@ai_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

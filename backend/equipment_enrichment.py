"""
Enriquecimento de especificações de módulos e inversores via Ollama ou Gemini.
Usado quando Voc/Isc/MPPT não foram informados no formulário.
"""

import json
import os
import re

import requests

from load_secrets import redact_secrets
from catalog_db import (
    catalog_inverter_to_specs,
    catalog_module_to_specs,
    lookup_inverter,
    lookup_module,
    save_inverter_from_form,
    save_module_from_form,
)

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'deepseek-r1:8b')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')


def _gemini_api_key():
    return os.environ.get('GEMINI_API_KEY', '').strip()


def gemini_available():
    return bool(_gemini_api_key())


def ollama_available():
    try:
        response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2)
        if response.status_code == 200:
            return bool(response.json().get('models'))
    except Exception:
        pass
    return False


def ai_available():
    return ollama_available() or gemini_available()


def _extract_json(text):
    if not text:
        return None
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _call_ollama(prompt, timeout=60):
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False},
            timeout=timeout,
        )
        if response.status_code == 200:
            return response.json().get('response', '')
    except Exception:
        pass
    return None


_LAST_GEMINI_ERROR = None


def _call_gemini(prompt, timeout=45, use_search=True):
    global _LAST_GEMINI_ERROR
    api_key = _gemini_api_key()
    if not api_key:
        return None
    url = (
        f'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{GEMINI_MODEL}:generateContent'
    )
    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json',
    }
    body = {'contents': [{'parts': [{'text': prompt}]}]}
    if use_search:
        body['tools'] = [{'google_search': {}}]
    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout)
        if response.status_code != 200 and use_search:
            body.pop('tools', None)
            response = requests.post(url, json=body, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                return ''.join(p.get('text', '') for p in parts)
        else:
            err = response.json().get('error', {}) if response.text else {}
            _LAST_GEMINI_ERROR = err.get('message') or f'HTTP {response.status_code}'
            if response.status_code in (429, 403):
                return None
    except Exception as exc:
        _LAST_GEMINI_ERROR = str(exc)
    return None


def gemini_last_error():
    return _LAST_GEMINI_ERROR


def is_gemini_quota_error(message: str | None = None) -> bool:
    text = (message or _LAST_GEMINI_ERROR or '').lower()
    return any(k in text for k in ('quota', 'rate limit', 'rate-limit', '429', 'resource_exhausted'))


def friendly_gemini_error(message: str | None = None) -> str:
    if is_gemini_quota_error(message):
        return (
            'Cota da API Gemini esgotada (tier gratuito do AI Studio, ~20 req/dia para modelos preview). '
            'Use o Catálogo SQL para specs sem IA, ou vincule cobrança ao projeto da chave em '
            'aistudio.google.com/apikey. Créditos do Google Cloud só contam se forem do mesmo projeto da chave AIza.'
        )
    return redact_secrets(message or _LAST_GEMINI_ERROR or 'Erro desconhecido na API Gemini')


_VERIFY_CACHE: dict = {'at': 0.0, 'ok': None, 'err': None}
_VERIFY_TTL_SEC = 600


def verify_gemini_connection(force: bool = False):
    """Testa se a chave Gemini responde (sem expor a chave). Cache 10 min."""
    import time
    if not gemini_available():
        return False, 'GEMINI_API_KEY não configurada'
    now = time.time()
    if (
        not force
        and _VERIFY_CACHE['ok'] is not None
        and now - _VERIFY_CACHE['at'] < _VERIFY_TTL_SEC
    ):
        return _VERIFY_CACHE['ok'], _VERIFY_CACHE['err']
    text = _call_gemini('Responda apenas: OK', timeout=15, use_search=False)
    if text:
        _VERIFY_CACHE.update({'at': now, 'ok': True, 'err': None})
        return True, None
    err = friendly_gemini_error()
    _VERIFY_CACHE.update({'at': now, 'ok': False, 'err': err})
    return False, err


def _query_specs(prompt):
    if not ai_available():
        return {}, 'none'
    callers = []
    if ollama_available():
        callers.append(('ollama', lambda p: _call_ollama(p)))
    if gemini_available():
        callers.append(('gemini', lambda p: _call_gemini(p, use_search=True)))
    for source, caller in callers:
        text = caller(prompt)
        parsed = _extract_json(text)
        if parsed and isinstance(parsed, dict):
            return parsed, source
    return {}, 'none'


def _module_prompt(fabricante, modelo, potencia):
    return f"""Busque na internet ou em fichas técnicas oficiais as especificações elétricas
do painel solar fotovoltaico abaixo. Retorne APENAS um JSON válido, sem markdown:

Fabricante: {fabricante or 'desconhecido'}
Modelo: {modelo}
Potência nominal (Wp): {potencia or 'desconhecida'}

{{
  "voc": <tensão circuito aberto Voc em V, número>,
  "isc": <corrente curto-circuito Isc em A, número>,
  "vmpp": <tensão máxima potência Vmpp em V, número>,
  "impp": <corrente máxima potência Impp em A, número>,
  "eficiencia": <eficiência %, número>
}}"""


def _inverter_prompt(fabricante, modelo, potencia_kw):
    return f"""Busque na internet ou em fichas técnicas oficiais as especificações elétricas
do inversor solar abaixo. Retorne APENAS um JSON válido, sem markdown:

Fabricante: {fabricante or 'desconhecido'}
Modelo: {modelo}
Potência nominal (kW): {potencia_kw or 'desconhecida'}

{{
  "tensao_nominal": <tensão nominal CA em V, número>,
  "corrente_nominal": <corrente nominal CA em A, número>,
  "mppt_min": <tensão MPPT mínima em V, número>,
  "mppt_max": <tensão MPPT máxima em V, número>,
  "eficiencia": <eficiência máxima %, número>
}}"""


def _needs_module_enrichment(module):
    modelo = module.get('modelo') or module.get('model')
    return bool(modelo) and not all(module.get(k) for k in ('voc', 'isc', 'vmpp', 'impp'))


def _needs_inverter_enrichment(inverter):
    modelo = inverter.get('modelo') or inverter.get('model')
    return bool(modelo) and not all(inverter.get(k) for k in ('mppt_min', 'mppt_max'))


def _merge_specs(target, specs, fields):
    for field in fields:
        if not target.get(field) and specs.get(field) not in (None, ''):
            target[field] = specs[field]


def enrich_module_specs(fabricante, modelo, potencia=None, catalog_only=False):
    """
    Busca especificações de módulo:
    1. Catálogo SQLite (match exato — sem aproximar potência)
    2. IA (Ollama/Gemini) — só se catalog_only=False
    """
    from catalog_db import find_module_by_name_or_power

    row = find_module_by_name_or_power(
        fabricante=fabricante or '',
        modelo=modelo or '',
        potencia_wp=potencia or 0,
    )

    if row:
        return catalog_module_to_specs(row), 'catalog'

    if catalog_only:
        return {}, 'none'

    specs, source = _query_specs(_module_prompt(fabricante, modelo, potencia))
    return specs, source


def enrich_inverter_specs(fabricante, modelo, potencia_kw=None, catalog_only=False):
    """
    Busca especificações de inversor:
    1. Catálogo SQLite (match exato)
    2. IA — só se catalog_only=False
    """
    from catalog_db import find_inverter_by_name_or_power

    row = find_inverter_by_name_or_power(
        fabricante=fabricante or '',
        modelo=modelo or '',
        potencia_kw=potencia_kw or 0,
    )

    if row:
        return catalog_inverter_to_specs(row), 'catalog'

    if catalog_only:
        return {}, 'none'

    specs, source = _query_specs(_inverter_prompt(fabricante, modelo, potencia_kw))
    return specs, source


def enrich_equipment_lists(modulos, inversores, save_to_catalog=False, catalog_only=False):
    """
    Preenche lacunas em modulos[] e inversores[] quando modelo está informado.
    Consulta catálogo SQLite; IA só se catalog_only=False (botão Enriquecer com IA).
    """
    sources = []
    enriched_modulos = []
    for mod in modulos or []:
        item = dict(mod)
        if _needs_module_enrichment(item):
            specs, source = enrich_module_specs(
                item.get('fabricante'),
                item.get('modelo') or item.get('model'),
                item.get('potencia') or item.get('power'),
                catalog_only=catalog_only,
            )
            if source != 'none':
                sources.append(f'modulo:{source}')
            _merge_specs(item, specs, ('voc', 'isc', 'vmpp', 'impp', 'eficiencia'))
            if save_to_catalog and source not in ('none', 'catalog'):
                save_module_from_form(
                    item.get('fabricante'),
                    item.get('modelo') or item.get('model'),
                    item,
                )
        enriched_modulos.append(item)

    enriched_inversores = []
    for inv in inversores or []:
        item = dict(inv)
        if _needs_inverter_enrichment(item):
            specs, source = enrich_inverter_specs(
                item.get('fabricante'),
                item.get('modelo') or item.get('model'),
                item.get('potencia') or item.get('power'),
                catalog_only=catalog_only,
            )
            if source != 'none':
                sources.append(f'inversor:{source}')
            _merge_specs(
                item,
                specs,
                ('tensao_nominal', 'corrente_nominal', 'mppt_min', 'mppt_max', 'eficiencia', 'num_mppt', 'tipo_inversor'),
            )
            if save_to_catalog and source not in ('none', 'catalog'):
                save_inverter_from_form(
                    item.get('fabricante'),
                    item.get('modelo') or item.get('model'),
                    item,
                )
        enriched_inversores.append(item)

    return enriched_modulos, enriched_inversores, list(dict.fromkeys(sources))

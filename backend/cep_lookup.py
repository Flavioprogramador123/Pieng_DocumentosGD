"""
Consulta CEP via ViaCEP e busca CEP por endereço (IA / Nominatim).
"""

from __future__ import annotations

import re

import requests

from equipment_enrichment import _query_specs, ai_available

VIACEP_URL = 'https://viacep.com.br/ws/{cep}/json/'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'


def _only_digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def _format_cep(digits: str) -> str:
    if len(digits) == 8:
        return f'{digits[:5]}-{digits[5:]}'
    return digits


def lookup_address_by_cep(cep: str) -> dict | None:
    """CEP → logradouro, bairro, cidade, UF."""
    digits = _only_digits(cep)
    if len(digits) != 8:
        return None
    try:
        response = requests.get(VIACEP_URL.format(cep=digits), timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        if data.get('erro'):
            return None
        return {
            'cep': _format_cep(digits),
            'logradouro': data.get('logradouro') or '',
            'bairro': data.get('bairro') or '',
            'cidade': data.get('localidade') or '',
            'uf': data.get('uf') or '',
            'complemento': data.get('complemento') or '',
            'source': 'viacep',
        }
    except Exception:
        return None


def _nominatim_cep(logradouro: str, cidade: str, uf: str) -> str | None:
    try:
        params = {
            'street': logradouro,
            'city': cidade,
            'state': uf,
            'country': 'Brazil',
            'format': 'json',
            'limit': 1,
        }
        headers = {'User-Agent': 'AutomacaoEquatorial/1.0'}
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=12)
        if response.status_code != 200:
            return None
        items = response.json()
        if not items:
            return None
        postcode = items[0].get('address', {}).get('postcode') or items[0].get('display_name', '')
        match = re.search(r'\b(\d{5}-?\d{3})\b', str(postcode))
        if match:
            return _format_cep(_only_digits(match.group(1)))
    except Exception:
        pass
    return None


def _ai_cep_prompt(logradouro: str, cidade: str, uf: str, bairro: str = '') -> str:
    return f"""Encontre o CEP correto no Brasil para o endereço:
Logradouro: {logradouro}
Bairro: {bairro or 'não informado'}
Cidade: {cidade}
UF: {uf}

Retorne APENAS JSON: {{"cep": "00000-000"}}"""


def lookup_cep_by_address(logradouro: str, cidade: str, uf: str, bairro: str = '') -> dict | None:
    """Endereço → CEP (Nominatim, depois IA)."""
    if not logradouro or not cidade or not uf:
        return None

    cep = _nominatim_cep(logradouro, cidade, uf.upper())
    if cep:
        result = lookup_address_by_cep(cep) or {}
        result.update({'cep': cep, 'source': 'nominatim'})
        return result

    if ai_available():
        specs, source = _query_specs(_ai_cep_prompt(logradouro, cidade, uf, bairro))
        if specs and specs.get('cep'):
            cep_val = _format_cep(_only_digits(str(specs['cep'])))
            enriched = lookup_address_by_cep(cep_val) or {}
            enriched.update({'cep': cep_val, 'source': f'ai:{source}'})
            return enriched

    return None


def enrich_client_address(cliente: dict) -> tuple[dict, str | None]:
    """
    Completa CEP ou endereço faltante. Retorna (cliente_atualizado, fonte).
    """
    updated = dict(cliente or {})
    source = None

    cep = updated.get('cep', '')
    logradouro = updated.get('logradouro', '')
    cidade = updated.get('cidade', '')
    uf = updated.get('uf', '')
    bairro = updated.get('bairro', '')

    if _only_digits(cep) and (not logradouro or not cidade):
        found = lookup_address_by_cep(cep)
        if found:
            for key in ('logradouro', 'bairro', 'cidade', 'uf', 'complemento', 'cep'):
                if found.get(key) and not str(updated.get(key, '')).strip():
                    updated[key] = found[key]
            source = found.get('source', 'viacep')

    elif not _only_digits(cep) and logradouro and cidade and uf:
        found = lookup_cep_by_address(logradouro, cidade, uf, bairro)
        if found:
            for key in ('logradouro', 'bairro', 'cidade', 'uf', 'complemento', 'cep'):
                if found.get(key):
                    if not str(updated.get(key, '')).strip() or key == 'cep':
                        updated[key] = found[key]
            source = found.get('source')

    return updated, source

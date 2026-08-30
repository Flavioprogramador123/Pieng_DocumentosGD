"""
Catálogo de modelos prontos para tabela de demanda (NTC-04).
Fonte: dados/demanda_modelos.json
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from demand_table import _normalize_load, generate_demand_table

CATALOG_PATH = Path(__file__).resolve().parent.parent / 'dados' / 'demanda_modelos.json'


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        return {'meta': {}, 'modelos': []}
    return json.loads(CATALOG_PATH.read_text(encoding='utf-8'))


def list_models() -> list[dict[str, Any]]:
    """Lista resumida para UI (sem array completo de cargas)."""
    out = []
    for m in load_catalog().get('modelos') or []:
        out.append({
            'id': m.get('id'),
            'nome': m.get('nome'),
            'descricao': m.get('descricao'),
            'classe': m.get('classe'),
            'tipo_ligacao': m.get('tipo_ligacao'),
            'tensao_atendimento': m.get('tensao_atendimento'),
            'disjuntor_entrada_a': m.get('disjuntor_entrada_a'),
            'demanda_alvo_kw': m.get('demanda_alvo_kw'),
            'notas': m.get('notas'),
            'qtd_cargas': len(m.get('cargas') or []),
        })
    return out


def get_model(model_id: str) -> dict[str, Any] | None:
    mid = (model_id or '').strip().lower()
    for m in load_catalog().get('modelos') or []:
        if (m.get('id') or '').lower() == mid:
            return dict(m)
    return None


def model_base_loads(model: dict[str, Any]) -> list[dict]:
    return [_normalize_load(row) for row in (model.get('cargas') or []) if row.get('descricao')]


def apply_model_to_payload(normalized: dict[str, Any], model_id: str) -> dict[str, Any] | None:
    """Preenche UC/dados técnicos conforme o modelo (sem sobrescrever valor já informado)."""
    model = get_model(model_id)
    if not model:
        return None

    uc = normalized.setdefault('unidade_consumidora', {})
    tec = normalized.setdefault('dados_tecnicos', {})
    cliente = normalized.setdefault('cliente', {})

    def _empty(val: Any) -> bool:
        return val is None or str(val).strip() == ''

    if _empty(uc.get('classe')):
        uc['classe'] = model.get('classe')
    if _empty(uc.get('tipo_ligacao')):
        uc['tipo_ligacao'] = model.get('tipo_ligacao')
    if _empty(uc.get('tensao_atendimento')):
        uc['tensao_atendimento'] = model.get('tensao_atendimento')
    if _empty(uc.get('disjuntor_entrada')) and model.get('disjuntor_entrada_a'):
        uc['disjuntor_entrada'] = str(model['disjuntor_entrada_a'])
    if _empty(tec.get('demanda_alvo_kw')) and model.get('demanda_alvo_kw'):
        kw = model['demanda_alvo_kw']
        tec['demanda_alvo_kw'] = str(kw).replace('.', ',')
    if _empty(tec.get('demanda_notas')) and model.get('notas'):
        tec['demanda_notas'] = model['notas']
    tec['demanda_modelo_id'] = model.get('id')
    if _empty(cliente.get('uf')):
        cliente['uf'] = 'GO'
    return model


def generate_from_model(
    model_id: str,
    *,
    client_name: str = '',
    uc: str = '',
    target_kw: float | None = None,
    notes: str = '',
) -> dict[str, Any]:
    model = get_model(model_id)
    if not model:
        raise ValueError(f'Modelo de demanda não encontrado: {model_id}')

    alvo = float(target_kw if target_kw is not None else model.get('demanda_alvo_kw') or 0)
    if alvo <= 0:
        raise ValueError('Demanda-alvo inválida para o modelo')

    loads = model_base_loads(model)
    if not loads:
        raise ValueError(f'Modelo {model_id} sem cargas definidas')

    table = generate_demand_table(
        target_kw=alvo,
        classe=model.get('classe') or 'RESIDENCIAL',
        client_name=client_name,
        uc=uc,
        notes=notes or model.get('notas') or '',
        base_loads=loads,
        modelo_id=model.get('id'),
    )
    table['modelo_id'] = model.get('id')
    table['modelo_nome'] = model.get('nome')
    table['tipo_ligacao'] = model.get('tipo_ligacao')
    table['tensao_atendimento'] = model.get('tensao_atendimento')
    table['disjuntor_entrada_a'] = model.get('disjuntor_entrada_a')
    return table

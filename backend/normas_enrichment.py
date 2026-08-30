"""
Enriquecimento pós-TXT com normas Equatorial GO — tokens, cabos, demanda.
"""

from __future__ import annotations

from typing import Any

from normas_loader import (
    apply_normas_to_payload,
    build_ai_context,
    calc_pd_max_kw,
    get_hsp,
    get_padrao_entrada,
    load_normas,
)


def apply_normas_enrichment(normalized: dict[str, Any]) -> dict[str, Any]:
    """
    Aplica normas GO ao payload: padrão entrada, cabos, demanda-alvo, metadados.
    Chamado após parse TXT e antes/durante enrich_normalized_payload.
    """
    if not load_normas():
        return normalized

    apply_normas_to_payload(normalized)

    cliente = normalized.get('cliente') or {}
    uc = normalized.get('unidade_consumidora') or {}
    tec = normalized.setdefault('dados_tecnicos', {})

    padrao = get_padrao_entrada(
        cliente.get('uf'),
        uc.get('tipo_ligacao'),
        uc.get('classe'),
    )
    if padrao:
        try:
            idg = float(str(uc.get('disjuntor_entrada') or padrao.get('disjuntor_a')))
            pd = calc_pd_max_kw(cliente.get('uf'), uc.get('tipo_ligacao'), idg)
            if pd:
                tec['demanda_fornecida_max_kw'] = pd
        except (TypeError, ValueError):
            pass

    tec.setdefault('hsp_referencia', get_hsp(cliente.get('uf')))
    return normalized


def ai_extraction_prompt_suffix() -> str:
    return build_ai_context('extracao')


def ai_demand_prompt_suffix() -> str:
    return build_ai_context('demanda')

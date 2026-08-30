"""
Gera planta CAD na pasta do cliente com tokens {{TOKEN}} já preenchidos.

Fluxo: ezdxf preenche planta.dxf → ODA File Converter gera planta.dwg (entrega).
Se ODA indisponível, mantém planta.dxf (fallback).

Template: templates/projeto_Modelo.dxf (exporte o DWG quando atualizar o template).
"""

from __future__ import annotations

import re
from pathlib import Path

import ezdxf

from autocad_tokens import enrich_autocad_values
from figura_localizacao import FIGURA_TOKEN

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DXF = ROOT / 'templates' / 'projeto_Modelo.dxf'
PLANTA_DXF = 'planta.dxf'
PLANTA_DWG = 'planta.dwg'

PLAIN_TOKEN_RE = re.compile(r'\{\{([A-Z0-9_]+)\}\}', re.IGNORECASE)
ESCAPED_TOKEN_RE = re.compile(r'\\?\{\\?\{([A-Z0-9_]+)\\?\}\\?\}', re.IGNORECASE)


def _token_keys_in_text(text: str) -> set[str]:
    keys: set[str] = set()
    for pattern in (PLAIN_TOKEN_RE, ESCAPED_TOKEN_RE):
        for match in pattern.finditer(text or ''):
            keys.add(match.group(1).upper())
    return keys


def replace_tokens_in_text(
    text: str,
    values: dict[str, str],
    *,
    keep_figura_marker: bool = True,
) -> str:
    enriched = enrich_autocad_values(values)

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).upper()
        if keep_figura_marker and key == FIGURA_TOKEN:
            return match.group(0)
        val = enriched.get(key, '')
        if val is None or not str(val).strip():
            return match.group(0)
        return str(val).replace('\r', ' ').replace('\n', ' ')

    text = PLAIN_TOKEN_RE.sub(repl, text or '')
    text = ESCAPED_TOKEN_RE.sub(repl, text or '')
    return text


def _iter_unique_text_entities(doc: ezdxf.document.Drawing):
    seen: set[str] = set()
    for layout in doc.layouts:
        for entity in layout:
            if entity.dxftype() not in ('TEXT', 'MTEXT'):
                continue
            handle = entity.dxf.handle
            if handle in seen:
                continue
            seen.add(handle)
            yield entity
    for block in doc.blocks:
        for entity in block:
            if entity.dxftype() not in ('TEXT', 'MTEXT'):
                continue
            handle = entity.dxf.handle
            if handle in seen:
                continue
            seen.add(handle)
            yield entity


def _entity_text(entity) -> str:
    if entity.dxftype() == 'TEXT':
        return entity.dxf.text
    return entity.text


def _set_entity_text(entity, text: str) -> None:
    if entity.dxftype() == 'TEXT':
        entity.dxf.text = text
    else:
        entity.text = text


def fill_dxf_document(doc: ezdxf.document.Drawing, values: dict[str, str]) -> set[str]:
    """Substitui tokens em TEXT/MTEXT. Retorna tokens ainda sem valor."""
    pending: set[str] = set()
    updated = 0
    for entity in _iter_unique_text_entities(doc):
        old_text = _entity_text(entity)
        keys = _token_keys_in_text(old_text)
        if not keys:
            continue
        new_text = replace_tokens_in_text(old_text, values, keep_figura_marker=True)
        for key in keys:
            if key == FIGURA_TOKEN:
                continue
            enriched = enrich_autocad_values(values)
            if not str(enriched.get(key, '') or '').strip():
                pending.add(key)
        if new_text != old_text:
            _set_entity_text(entity, new_text)
            updated += 1
    if updated == 0 and not pending:
        pending.update(_scan_pending_tokens(doc, values))
    return pending


def _scan_pending_tokens(doc: ezdxf.document.Drawing, values: dict[str, str]) -> set[str]:
    pending: set[str] = set()
    enriched = enrich_autocad_values(values)
    for entity in _iter_unique_text_entities(doc):
        for key in _token_keys_in_text(_entity_text(entity)):
            if key == FIGURA_TOKEN:
                continue
            if not str(enriched.get(key, '') or '').strip():
                pending.add(key)
    return pending


def generate_planta_dxf(output_dir: Path, values: dict[str, str]) -> tuple[Path | None, set[str]]:
    """
    Gera output_dir/planta.dxf com dados do cliente (intermediário ezdxf).
    Retorna (caminho, tokens_sem_valor).
    """
    if not TEMPLATE_DXF.is_file():
        return None, set()

    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / PLANTA_DXF

    doc = ezdxf.readfile(TEMPLATE_DXF)
    pending = fill_dxf_document(doc, values)
    doc.saveas(dest)
    return dest, pending


def generate_planta_cad(output_dir: Path, values: dict[str, str]) -> tuple[Path | None, set[str], str]:
    """
    Gera planta CAD para entrega ao cliente.
    Retorna (caminho, tokens_sem_valor, formato: 'dwg' | 'dxf').
    """
    dxf_path, pending = generate_planta_dxf(output_dir, values)
    if not dxf_path:
        return None, pending, 'dxf'

    dwg_path = output_dir / PLANTA_DWG
    try:
        from dxf_to_dwg import convert_dxf_to_dwg

        if convert_dxf_to_dwg(dxf_path, dwg_path):
            try:
                dxf_path.unlink()
            except OSError:
                pass
            return dwg_path, pending, 'dwg'
    except Exception:
        pass

    return dxf_path, pending, 'dxf'

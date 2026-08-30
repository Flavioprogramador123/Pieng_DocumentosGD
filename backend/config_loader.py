"""
Carrega config_padrao.json + config_padrao.local.json (gitignored) + variáveis .env.
Mantém operação local: dados reais ficam em config_padrao.local.json ou .env.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

_ENV_PROCURADOR = {
    'nome': 'PROCURADOR_NOME',
    'cpf': 'PROCURADOR_CPF',
    'rg': 'PROCURADOR_RG',
    'orgao_emissor_rg': 'PROCURADOR_ORGAO_RG',
    'uf_rg': 'PROCURADOR_UF_RG',
    'registro_profissional': 'PROCURADOR_REGISTRO',
    'titulo_profissional': 'PROCURADOR_TITULO',
    'endereco': 'PROCURADOR_ENDERECO',
    'bairro': 'PROCURADOR_BAIRRO',
    'cidade': 'PROCURADOR_CIDADE',
    'uf': 'PROCURADOR_UF',
    'cep': 'PROCURADOR_CEP',
    'telefone': 'PROCURADOR_TELEFONE',
    'email': 'PROCURADOR_EMAIL',
}

_ENV_TECNICO = {
    'nome': 'TECNICO_NOME',
    'titulo_profissional': 'TECNICO_TITULO',
    'registro_profissional': 'TECNICO_REGISTRO',
    'uf_registro': 'TECNICO_UF_REGISTRO',
    'endereco': 'TECNICO_ENDERECO',
    'bairro': 'TECNICO_BAIRRO',
    'cidade': 'TECNICO_CIDADE',
    'uf': 'TECNICO_UF',
    'cep': 'TECNICO_CEP',
    'telefone': 'TECNICO_TELEFONE',
    'email': 'TECNICO_EMAIL',
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _apply_env_section(section: dict, mapping: dict[str, str]) -> None:
    for field, env_key in mapping.items():
        val = os.environ.get(env_key, '').strip()
        if val:
            section[field] = val


def _apply_env_overrides(config: dict) -> dict:
    out = deepcopy(config)
    out.setdefault('procurador', {})
    out.setdefault('responsavel_tecnico', {})
    _apply_env_section(out['procurador'], _ENV_PROCURADOR)
    _apply_env_section(out['responsavel_tecnico'], _ENV_TECNICO)
    return out


def resolve_config_paths(config_path: Path | None = None) -> tuple[Path, Path]:
    base = config_path or (BASE_DIR / 'config_padrao.json')
    local = base.parent / 'config_padrao.local.json'
    return base, local


def load_project_defaults(config_path: Path | None = None) -> dict[str, Any]:
    """Base (repo) ← local (gitignored) ← .env (PROCURADOR_*, TECNICO_*)."""
    from load_secrets import load_local_env

    load_local_env()
    base_path, local_path = resolve_config_paths(config_path)

    if not base_path.is_file():
        return _apply_env_overrides({})

    config = json.loads(base_path.read_text(encoding='utf-8'))
    if local_path.is_file():
        local = json.loads(local_path.read_text(encoding='utf-8'))
        config = _deep_merge(config, local)

    return _apply_env_overrides(config)

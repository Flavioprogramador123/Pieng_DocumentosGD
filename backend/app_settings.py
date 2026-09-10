"""
Configurações editáveis pela UI (app_settings.local.json — gitignored).

Padrões em config_padrao.json → seção "app".
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from config_loader import _deep_merge, load_project_defaults

BASE_DIR = Path(__file__).resolve().parent
APP_SETTINGS_LOCAL = BASE_DIR / 'app_settings.local.json'

# Padrões embutidos se config_padrao.json não tiver seção app
_BUILTIN_DEFAULTS: dict[str, Any] = {
    'geracao': {
        'hsp_por_uf': {'GO': 5.30, 'MA': 5.20, 'PI': 5.20, 'PA': 5.00, 'DEFAULT': 5.30},
        'eficiencia_sistema': 0.80,
        'dias_por_mes': 30.4,
        'tarifa_kwh': 1.10,
        'formula_descricao': 'E_mês (kWh) = P_kWp × HSP (h/dia) × η × dias/mês',
    },
    'figura_localizacao': {
        'zoom_padrao': 18,
        'zoom_modo': 'fixo',
        'tile_provider': 'osmde',
        'tiles_radius': 2,
    },
}


def _load_local_overrides() -> dict[str, Any]:
    if not APP_SETTINGS_LOCAL.is_file():
        return {}
    try:
        data = json.loads(APP_SETTINGS_LOCAL.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _base_defaults() -> dict[str, Any]:
    project = load_project_defaults()
    app = project.get('app') if isinstance(project.get('app'), dict) else {}
    return _deep_merge(deepcopy(_BUILTIN_DEFAULTS), app)


def load_app_settings() -> dict[str, Any]:
    """Defaults do repo + config_padrao.local + app_settings.local.json."""
    merged = _base_defaults()
    local_app = _load_local_overrides()
    if local_app:
        merged = _deep_merge(merged, local_app)
    return merged


def save_app_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Persiste override local (merge parcial) e espelha no Google Drive se disponível."""
    current = load_app_settings()
    merged = _deep_merge(current, updates)
    APP_SETTINGS_LOCAL.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    try:
        from local_secrets_sync import push_secrets_to_drive
        push_secrets_to_drive()
    except Exception:
        pass
    return merged


def reset_app_settings() -> dict[str, Any]:
    if APP_SETTINGS_LOCAL.is_file():
        APP_SETTINGS_LOCAL.unlink()
    return load_app_settings()


def get_hsp_for_uf(uf: str | None = None) -> float:
    cfg = load_app_settings().get('geracao') or {}
    por_uf = cfg.get('hsp_por_uf') or {}
    uf_k = (uf or 'GO').upper()[:2]
    val = por_uf.get(uf_k) or por_uf.get('DEFAULT') or 5.30
    try:
        return float(val)
    except (TypeError, ValueError):
        return 5.30


def get_generation_params(uf: str | None = None) -> dict[str, Any]:
    cfg = load_app_settings().get('geracao') or {}
    hsp = get_hsp_for_uf(uf)
    try:
        eta = float(cfg.get('eficiencia_sistema') or 0.80)
    except (TypeError, ValueError):
        eta = 0.80
    try:
        dias = float(cfg.get('dias_por_mes') or 30.4)
    except (TypeError, ValueError):
        dias = 30.4
    try:
        tarifa = float(cfg.get('tarifa_kwh') or 1.10)
    except (TypeError, ValueError):
        tarifa = 1.10
    formula = str(cfg.get('formula_descricao') or _BUILTIN_DEFAULTS['geracao']['formula_descricao'])
    return {
        'hsp': hsp,
        'eficiencia_sistema': eta,
        'dias_por_mes': dias,
        'tarifa_kwh': tarifa,
        'formula_descricao': formula,
    }


def compute_monthly_generation_kwh(power_kwp: float, uf: str | None = None) -> dict[str, Any]:
    """Calcula geração mensal e devolve fórmula expandida para exibição."""
    p = get_generation_params(uf)
    hsp, eta, dias = p['hsp'], p['eficiencia_sistema'], p['dias_por_mes']
    monthly = power_kwp * hsp * eta * dias
    detail = (
        f"{p['formula_descricao']} → "
        f"{power_kwp:g} × {hsp:g} × {eta:g} × {dias:g} = {monthly:.0f} kWh/mês"
    )
    return {
        'monthly_kwh': monthly,
        'annual_kwh': monthly * 12,
        'daily_kwh': monthly / dias if dias else 0,
        'hsp': hsp,
        'eficiencia': eta,
        'dias_por_mes': dias,
        'tarifa_kwh': p['tarifa_kwh'],
        'formula_descricao': p['formula_descricao'],
        'formula_expanded': detail,
    }


def get_figura_settings() -> dict[str, Any]:
    fig = load_app_settings().get('figura_localizacao') or {}
    try:
        zoom = int(fig.get('zoom_padrao') or 18)
    except (TypeError, ValueError):
        zoom = 18
    zoom = max(10, min(20, zoom))
    modo = str(fig.get('zoom_modo') or 'fixo').lower()
    provider = str(fig.get('tile_provider') or 'osmde').lower()
    try:
        radius = int(fig.get('tiles_radius') or 2)
    except (TypeError, ValueError):
        radius = 2
    return {
        'zoom_padrao': zoom,
        'zoom_modo': modo,
        'tile_provider': provider,
        'tiles_radius': max(1, min(4, radius)),
    }


def resolve_figura_zoom(user_zoom: int | None = None) -> int | None:
    """
    None = automático urbano/rural (só se zoom_modo == 'auto').
    Inteiro = zoom fixo (padrão 18).
    """
    fig = get_figura_settings()
    if user_zoom is not None:
        return user_zoom
    if fig['zoom_modo'] == 'auto':
        return None
    return fig['zoom_padrao']

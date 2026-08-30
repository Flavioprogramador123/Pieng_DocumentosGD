"""
Destino dos documentos gerados (LGPD — dados pessoais fora do repositório git).

Configure CLIENT_OUTPUT_DIR no .env para apontar ao Google Drive sincronizado.
Ex.: I:/Meu Drive/Pieng Soluções Energéticas/pieng/2. Clientes Aprovados/80 a 100
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent


def default_output_base() -> Path:
    return (ROOT_DIR / 'saida' / 'web_generated').resolve()


def get_client_output_dir_env() -> str:
    return os.environ.get('CLIENT_OUTPUT_DIR', '').strip().strip('"').strip("'")


def get_output_base_dir() -> tuple[Path, str | None]:
    """
    Retorna (pasta_base, aviso).
    Se CLIENT_OUTPUT_DIR não estiver acessível, usa saida/web_generated local.
    """
    custom = get_client_output_dir_env()
    if not custom:
        path = default_output_base()
        path.mkdir(parents=True, exist_ok=True)
        return path, None

    path = Path(custom).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise OSError('caminho não é uma pasta')
        return path.resolve(), None
    except OSError as exc:
        fallback = default_output_base()
        fallback.mkdir(parents=True, exist_ok=True)
        warning = (
            f'Pasta CLIENT_OUTPUT_DIR indisponível ({exc}). '
            f'Usando fallback local: {fallback}'
        )
        logger.warning(warning)
        return fallback, warning


def output_config_status() -> dict:
    custom = get_client_output_dir_env()
    base, warning = get_output_base_dir()
    return {
        'configured': bool(custom),
        'path': str(base),
        'using_fallback': bool(warning),
        'warning': warning,
        'folder_naming': 'numero_contrato + primeiro e segundo nome',
        'lgpd_note': (
            'Documentos contêm dados pessoais (LGPD). '
            'Mantenha fora do GitHub e com acesso restrito no Google Drive.'
        ),
    }


def _sanitize_path_segment(text: str) -> str:
    safe = (text or '').strip()
    for ch in '\\/:*?"<>|':
        safe = safe.replace(ch, '-')
    return safe.strip(' .')


def client_first_two_names(client_name: str) -> str:
    """Primeiro e segundo nome para localização rápida na pasta."""
    parts = [p for p in (client_name or '').split() if p.strip()]
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    return f'{parts[0]} {parts[1]}'


def folder_name_from_contract(numero_contrato: str, client_name: str = '') -> str:
    """
    Nome da pasta = número do contrato + primeiro e segundo nome.
    Ex.: 80 + João Silva Costa → 80 - João Silva
         122/2026 + Maria Santos → 122-2026 - Maria Santos
    """
    raw_num = (numero_contrato or '').strip()
    if not raw_num:
        raise ValueError('Número do contrato é obrigatório para nomear a pasta de saída.')

    num = _sanitize_path_segment(raw_num.replace('/', '-'))
    if not num:
        raise ValueError('Número do contrato inválido para nome de pasta.')

    short_name = _sanitize_path_segment(client_first_two_names(client_name))
    if short_name:
        folder = f'{num} - {short_name}'
    else:
        folder = num

    return folder[:120]

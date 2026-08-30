"""
Destino dos documentos gerados (LGPD — dados pessoais fora do repositório git).

Configure CLIENT_OUTPUT_DIR no .env para apontar ao Google Drive sincronizado.
Ex.: I:/Meu Drive/Pieng Soluções Energéticas/pieng/2. Clientes Aprovados/80 a 100
"""

from __future__ import annotations

import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
OUTPUT_CONFIG_LOCAL = BASE_DIR / 'output_config.local.json'

DEFAULT_RELATIVE = Path('saida') / 'web_generated'


def default_output_base() -> Path:
    return (ROOT_DIR / DEFAULT_RELATIVE).resolve()


def get_client_output_dir_env() -> str:
    return os.environ.get('CLIENT_OUTPUT_DIR', '').strip().strip('"').strip("'")


def _load_local_output_config() -> dict:
    if not OUTPUT_CONFIG_LOCAL.is_file():
        return {}
    try:
        data = json.loads(OUTPUT_CONFIG_LOCAL.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_local_output_dir_setting() -> str:
    return str(_load_local_output_config().get('client_output_dir') or '').strip()


def save_local_output_dir(path: str) -> None:
    """Persiste pasta de saída escolhida na UI (gitignored). path vazio remove override."""
    cleaned = (path or '').strip().strip('"').strip("'")
    if cleaned:
        payload = {'client_output_dir': cleaned}
        OUTPUT_CONFIG_LOCAL.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    elif OUTPUT_CONFIG_LOCAL.is_file():
        OUTPUT_CONFIG_LOCAL.unlink()


def _try_output_path(raw: str, source: str) -> tuple[Path, str | None, str] | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise OSError('caminho não é uma pasta')
        return path.resolve(), None, source
    except OSError as exc:
        return None, str(exc), source


def get_output_base_dir() -> tuple[Path, str | None]:
    """
    Retorna (pasta_base, aviso).
    Prioridade: output_config.local.json > CLIENT_OUTPUT_DIR (.env) > saida/web_generated.
    """
    errors: list[str] = []
    local = get_local_output_dir_setting()
    env = get_client_output_dir_env()

    for raw, label in ((local, 'pasta local'), (env, 'CLIENT_OUTPUT_DIR')):
        if not raw:
            continue
        tried = _try_output_path(raw, label)
        if tried and tried[1] is None:
            return tried[0], None
        if tried and tried[1]:
            errors.append(f'{label} ({raw}): {tried[1]}')

    fallback = default_output_base()
    fallback.mkdir(parents=True, exist_ok=True)
    if errors:
        detail = '; '.join(errors)
        warning = f'Pasta configurada indisponível ({detail}). Usando fallback local: {fallback}'
        logger.warning(warning)
        return fallback, warning
    return fallback, None


def output_config_status() -> dict:
    local = get_local_output_dir_setting()
    env = get_client_output_dir_env()
    base, warning = get_output_base_dir()
    if local:
        source = 'local'
    elif env:
        source = 'env'
    else:
        source = 'default'
    return {
        'configured': bool(local or env),
        'path': str(base),
        'effective_path': str(base),
        'local_path': local or None,
        'env_path': env or None,
        'default_path': str(default_output_base()),
        'source': source,
        'using_fallback': bool(warning),
        'warning': warning,
        'folder_naming': 'numero_contrato + primeiro e segundo nome',
        'lgpd_note': (
            'Documentos contêm dados pessoais (LGPD). '
            'Mantenha fora do GitHub e com acesso restrito no Google Drive.'
        ),
    }


def resolve_client_file(output_base: Path, folder_name: str, file_name: str) -> Path:
    """Resolve arquivo dentro da pasta de saída (anti path traversal)."""
    base = output_base.resolve()
    folder = _sanitize_path_segment(folder_name)
    name = Path(file_name).name
    if not folder or not name or name != file_name:
        raise ValueError('Caminho de arquivo inválido')
    file_path = (base / folder / name).resolve()
    if not str(file_path).startswith(str(base)):
        raise ValueError('Acesso negado')
    if not file_path.is_file():
        raise FileNotFoundError('Arquivo não encontrado')
    return file_path


def open_path_in_os(path: Path) -> None:
    """Abre pasta ou arquivo com o aplicativo padrão do sistema."""
    import subprocess
    import sys

    target = str(path.resolve())
    if sys.platform == 'win32':
        os.startfile(target)  # noqa: S606
        return
    if sys.platform == 'darwin':
        subprocess.Popen(['open', target], close_fds=True)
        return
    subprocess.Popen(['xdg-open', target], close_fds=True)


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

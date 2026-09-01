"""
Sincroniza configs sigilosas entre Google Drive (Desktop) e arquivos locais gitignored.

Estrutura no Drive (pasta config/):
  shared/config_padrao.local.json
  shared/app_settings.local.json
  shared/backend.env
  machines/{NOME_PC}/output_config.local.json
  data/users.json

Prioridade do caminho do Drive:
  1. SECRETS_DRIVE_DIR (.env ou variável de ambiente)
  2. backend/secrets_drive.local.json → secrets_drive_dir
  3. Auto: {letra}:/Meu Drive/Pieng Soluções Energéticas/pieng/Automacao_Equatorial/config
"""

from __future__ import annotations

import json
import os
import shutil
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / 'data'

SECRETS_DRIVE_LOCAL = BASE_DIR / 'secrets_drive.local.json'
SECRETS_DRIVE_EXAMPLE = BASE_DIR / 'secrets_drive.local.json.example'

RELATIVE_DRIVE_SUFFIX = Path('Pieng Soluções Energéticas') / 'pieng' / 'Automacao_Equatorial' / 'config'

SHARED_FILES = {
    'config_padrao.local.json': BASE_DIR / 'config_padrao.local.json',
    'app_settings.local.json': BASE_DIR / 'app_settings.local.json',
    'backend.env': BASE_DIR / '.env',
}

DATA_FILES = {
    'users.json': DATA_DIR / 'users.json',
    'trusted_devices.json': DATA_DIR / 'trusted_devices.json',
}


def _machine_name() -> str:
    env = os.environ.get('SECRETS_MACHINE_NAME', '').strip()
    if env:
        return env
    return (os.environ.get('COMPUTERNAME') or socket.gethostname() or 'default').strip()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _find_meu_drive_roots() -> list[Path]:
    roots: list[Path] = []
    for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        candidate = Path(f'{letter}:') / 'Meu Drive'
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def resolve_secrets_drive_dir() -> Path | None:
    raw = os.environ.get('SECRETS_DRIVE_DIR', '').strip().strip('"').strip("'")
    if raw:
        path = Path(raw).expanduser()
        if path.is_dir():
            return path.resolve()

    local_cfg = _read_json(SECRETS_DRIVE_LOCAL)
    cfg_path = str(local_cfg.get('secrets_drive_dir') or '').strip()
    if cfg_path:
        path = Path(cfg_path).expanduser()
        if path.is_dir():
            return path.resolve()

    for root in _find_meu_drive_roots():
        candidate = root / RELATIVE_DRIVE_SUFFIX
        if candidate.is_dir():
            return candidate.resolve()
        # Pasta ainda não criada — retorna caminho alvo no primeiro Drive encontrado
        return candidate.resolve()

    return None


def _ensure_drive_tree(drive_dir: Path) -> None:
    (drive_dir / 'shared').mkdir(parents=True, exist_ok=True)
    (drive_dir / 'machines' / _machine_name()).mkdir(parents=True, exist_ok=True)
    (drive_dir / 'data').mkdir(parents=True, exist_ok=True)


def _drive_shared(drive_dir: Path, name: str) -> Path:
    return drive_dir / 'shared' / name


def _drive_machine_output(drive_dir: Path) -> Path:
    return drive_dir / 'machines' / _machine_name() / 'output_config.local.json'


def _drive_data(drive_dir: Path, name: str) -> Path:
    return drive_dir / 'data' / name


@dataclass
class SyncAction:
    name: str
    direction: str
    local: Path
    remote: Path
    ok: bool
    detail: str


def _copy_if_needed(src: Path, dst: Path, *, prefer: str) -> SyncAction:
    """
    prefer: 'newer' | 'source' | 'dest'
    """
    name = dst.name
    if not src.is_file():
        return SyncAction(name, prefer, dst, src, False, 'origem ausente')
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.is_file():
        shutil.copy2(src, dst)
        return SyncAction(name, prefer, dst, src, True, 'copiado (destino não existia)')

    src_m = src.stat().st_mtime
    dst_m = dst.stat().st_mtime
    if prefer == 'source' or (prefer == 'newer' and src_m >= dst_m):
        shutil.copy2(src, dst)
        return SyncAction(name, prefer, dst, src, True, 'atualizado')
    return SyncAction(name, prefer, dst, src, True, 'mantido (destino mais recente)')


def pull_secrets_from_drive() -> dict[str, Any]:
    drive_dir = resolve_secrets_drive_dir()
    if drive_dir is None:
        return {
            'success': False,
            'error': 'Google Drive não encontrado. Monte o Drive ou defina SECRETS_DRIVE_DIR.',
            'actions': [],
        }

    if not drive_dir.is_dir():
        return {
            'success': True,
            'skipped': True,
            'message': f'Pasta de config no Drive ainda não existe: {drive_dir}',
            'drive_dir': str(drive_dir),
            'actions': [],
        }

    actions: list[SyncAction] = []

    for remote_name, local_path in SHARED_FILES.items():
        remote = _drive_shared(drive_dir, remote_name)
        actions.append(_copy_if_needed(remote, local_path, prefer='newer'))

    out_local = BASE_DIR / 'output_config.local.json'
    out_remote = _drive_machine_output(drive_dir)
    actions.append(_copy_if_needed(out_remote, out_local, prefer='newer'))

    shared_out = _drive_shared(drive_dir, 'output_config.local.json')
    if not out_local.is_file() and shared_out.is_file():
        actions.append(_copy_if_needed(shared_out, out_local, prefer='source'))

    for remote_name, local_path in DATA_FILES.items():
        remote = _drive_data(drive_dir, remote_name)
        actions.append(_copy_if_needed(remote, local_path, prefer='newer'))

    return {
        'success': True,
        'drive_dir': str(drive_dir),
        'machine': _machine_name(),
        'actions': [
            {**a.__dict__, 'local': str(a.local), 'remote': str(a.remote)}
            for a in actions
        ],
    }


def push_secrets_to_drive() -> dict[str, Any]:
    drive_dir = resolve_secrets_drive_dir()
    if drive_dir is None:
        return {
            'success': False,
            'error': 'Google Drive não encontrado. Monte o Drive ou defina SECRETS_DRIVE_DIR.',
            'actions': [],
        }

    _ensure_drive_tree(drive_dir)
    actions: list[SyncAction] = []

    for remote_name, local_path in SHARED_FILES.items():
        if not local_path.is_file():
            continue
        remote = _drive_shared(drive_dir, remote_name)
        actions.append(_copy_if_needed(local_path, remote, prefer='source'))

    out_local = BASE_DIR / 'output_config.local.json'
    if out_local.is_file():
        remote = _drive_machine_output(drive_dir)
        actions.append(_copy_if_needed(out_local, remote, prefer='source'))

    for remote_name, local_path in DATA_FILES.items():
        if not local_path.is_file():
            continue
        remote = _drive_data(drive_dir, remote_name)
        actions.append(_copy_if_needed(local_path, remote, prefer='source'))

    readme = drive_dir / 'LEIA-ME.txt'
    if not readme.is_file():
        readme.write_text(
            'Configs sigilosas da Automação Equatorial (PIENG).\n'
            'Não compartilhar publicamente. Sincronizado via local_secrets_sync.py.\n'
            f'Última estrutura criada: {datetime.now().isoformat(timespec="seconds")}\n',
            encoding='utf-8',
        )

    copied = sum(
        1 for a in actions
        if a.ok and ('copiado' in a.detail or 'atualizado' in a.detail)
    )
    return {
        'success': True,
        'drive_dir': str(drive_dir),
        'machine': _machine_name(),
        'uploaded': copied,
        'actions': [
            {**a.__dict__, 'local': str(a.local), 'remote': str(a.remote)}
            for a in actions
        ],
    }


def secrets_sync_status() -> dict[str, Any]:
    drive_dir = resolve_secrets_drive_dir()
    local_present = {
        name: path.is_file()
        for name, path in {**SHARED_FILES, 'output_config.local.json': BASE_DIR / 'output_config.local.json'}.items()
    }
    remote_present = {}
    if drive_dir and drive_dir.is_dir():
        for name in SHARED_FILES:
            remote_present[name] = _drive_shared(drive_dir, name).is_file()
        remote_present['output_config.local.json'] = _drive_machine_output(drive_dir).is_file()

    return {
        'drive_dir': str(drive_dir) if drive_dir else None,
        'drive_mounted': drive_dir is not None and drive_dir.parent.parent.parent.parent.exists() if drive_dir else False,
        'machine': _machine_name(),
        'local': local_present,
        'remote': remote_present,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sync configs sigilosas com Google Drive')
    parser.add_argument('action', choices=('pull', 'push', 'status'))
    args = parser.parse_args()

    if args.action == 'pull':
        result = pull_secrets_from_drive()
    elif args.action == 'push':
        result = push_secrets_to_drive()
    else:
        result = secrets_sync_status()

    print(json.dumps(result, ensure_ascii=False, indent=2))

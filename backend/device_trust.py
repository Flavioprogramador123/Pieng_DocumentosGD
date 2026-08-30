"""
Dispositivos confiáveis e verificação por e-mail (login master em máquina nova).
"""

from __future__ import annotations

import json
import os
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
TRUSTED_FILE = ROOT_DIR / 'data' / 'trusted_devices.json'
PENDING_FILE = ROOT_DIR / 'data' / 'pending_device_verifications.json'

MASTER_VERIFY_EMAIL = os.environ.get('MASTER_VERIFY_EMAIL', 'solarlassis@gmail.com').strip()
APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5173').strip().rstrip('/')
DEVICE_VERIFY_MINUTES = int(os.environ.get('DEVICE_VERIFY_MINUTES', '20') or '20')
DEVICE_VERIFY_ENABLED = os.environ.get('AUTH_DEVICE_VERIFY', '1').strip().lower() not in ('0', 'false', 'no')


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _load_json(path: Path, default: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else default
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def device_verify_enabled() -> bool:
    return DEVICE_VERIFY_ENABLED


def is_device_trusted(username: str, device_id: str) -> bool:
    device_id = (device_id or '').strip()
    if not device_id:
        return False
    store = _load_json(TRUSTED_FILE, {'users': {}})
    trusted = store.get('users', {}).get(username, [])
    return device_id in trusted


def trust_device(username: str, device_id: str) -> None:
    device_id = (device_id or '').strip()
    if not device_id:
        return
    store = _load_json(TRUSTED_FILE, {'users': {}})
    users = store.setdefault('users', {})
    devices = list(users.get(username, []))
    if device_id not in devices:
        devices.append(device_id)
    users[username] = devices[-20:]
    _save_json(TRUSTED_FILE, store)


def _cleanup_pending(store: dict) -> dict:
    now = _now()
    pending = store.get('pending', {})
    kept = {}
    for token, item in pending.items():
        try:
            exp = datetime.fromisoformat(item['expires_at'])
        except (KeyError, ValueError, TypeError):
            continue
        if exp > now:
            kept[token] = item
    store['pending'] = kept
    return store


def create_device_verification(
    *,
    username: str,
    device_id: str,
    user_agent: str = '',
    ip_hint: str = '',
) -> tuple[dict | None, str | None]:
    device_id = (device_id or '').strip()
    if not device_id:
        return None, 'Identificador do dispositivo ausente.'

    code = f'{random.randint(0, 999999):06d}'
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(minutes=DEVICE_VERIFY_MINUTES)

    store = _cleanup_pending(_load_json(PENDING_FILE, {'pending': {}}))
    store['pending'][token] = {
        'username': username,
        'device_id': device_id,
        'code': code,
        'created_at': _now_iso(),
        'expires_at': expires.replace(microsecond=0).isoformat(),
        'user_agent': (user_agent or '')[:300],
        'ip_hint': (ip_hint or '')[:80],
    }
    _save_json(PENDING_FILE, store)

    confirm_url = f'{APP_BASE_URL}/?confirm_device={token}'

    return {
        'token': token,
        'code': code,
        'confirm_url': confirm_url,
        'expires_at': expires.replace(microsecond=0).isoformat(),
        'email_to': MASTER_VERIFY_EMAIL,
    }, None


def get_pending_verification(token: str, device_id: str) -> tuple[dict | None, str | None]:
    """Retorna verificação pendente se token e dispositivo conferem."""
    token = (token or '').strip()
    device_id = (device_id or '').strip()
    if not token or not device_id:
        return None, 'Sessão de verificação inválida. Faça login novamente.'

    store = _cleanup_pending(_load_json(PENDING_FILE, {'pending': {}}))
    item = store.get('pending', {}).get(token)
    if not item:
        _save_json(PENDING_FILE, store)
        return None, 'Verificação expirada. Faça login novamente.'

    if item.get('device_id') != device_id:
        return None, 'Este navegador não corresponde ao login iniciado.'

    try:
        exp = datetime.fromisoformat(item['expires_at'])
    except (KeyError, ValueError, TypeError):
        return None, 'Verificação inválida.'

    if exp <= _now():
        del store['pending'][token]
        _save_json(PENDING_FILE, store)
        return None, 'Verificação expirada. Faça login novamente.'

    confirm_url = f'{APP_BASE_URL}/?confirm_device={token}'
    return {
        'token': token,
        'username': item['username'],
        'device_id': device_id,
        'code': item['code'],
        'confirm_url': confirm_url,
        'expires_at': item['expires_at'],
        'email_to': MASTER_VERIFY_EMAIL,
    }, None


def confirm_device_verification(
    *,
    token: str,
    device_id: str,
    code: str | None = None,
) -> tuple[dict | None, str | None]:
    token = (token or '').strip()
    device_id = (device_id or '').strip()
    if not token or not device_id:
        return None, 'Token ou dispositivo inválido.'

    store = _cleanup_pending(_load_json(PENDING_FILE, {'pending': {}}))
    item = store.get('pending', {}).get(token)
    if not item:
        _save_json(PENDING_FILE, store)
        return None, 'Link ou código expirado. Faça login novamente.'

    if item.get('device_id') != device_id:
        return None, 'Este link não corresponde ao navegador atual. Abra no mesmo computador em que tentou entrar.'

    if code is not None and str(code).strip() != str(item.get('code', '')).strip():
        return None, 'Código incorreto.'

    try:
        exp = datetime.fromisoformat(item['expires_at'])
    except (KeyError, ValueError, TypeError):
        return None, 'Verificação inválida.'

    if exp <= _now():
        del store['pending'][token]
        _save_json(PENDING_FILE, store)
        return None, 'Link ou código expirado. Faça login novamente.'

    username = item['username']
    trust_device(username, device_id)
    del store['pending'][token]
    _save_json(PENDING_FILE, store)

    return {'username': username, 'role': 'master'}, None

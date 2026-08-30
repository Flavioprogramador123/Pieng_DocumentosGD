"""
Autenticação local: master via hash em variável de ambiente + usuários secundários em data/users.json.
A senha master nunca é armazenada em disco — apenas MASTER_PASSWORD_HASH no .env (gitignored).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
USERS_FILE = ROOT_DIR / 'data' / 'users.json'

MASTER_USERNAME = os.environ.get('MASTER_USERNAME', 'pieng').strip().lower()
MASTER_PASSWORD_HASH = os.environ.get('MASTER_PASSWORD_HASH', '').strip()

USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{2,31}$')


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_store() -> dict:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.is_file():
        return {'users': {}}
    try:
        data = json.loads(USERS_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'users': {}}
    if not isinstance(data, dict):
        return {'users': {}}
    data.setdefault('users', {})
    return data


def _save_store(data: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def normalize_username(username: str) -> str:
    return (username or '').strip().lower()


def validate_username(username: str) -> str | None:
    u = normalize_username(username)
    if not u:
        return 'Informe o usuário.'
    if u == MASTER_USERNAME:
        return 'Este nome é reservado ao administrador master.'
    if not USERNAME_RE.match(u):
        return 'Usuário inválido: use 3–32 caracteres (letras minúsculas, números, . _ -).'
    return None


def validate_password(password: str, *, min_len: int = 8) -> str | None:
    if not password or len(password) < min_len:
        return f'Senha deve ter pelo menos {min_len} caracteres.'
    return None


def master_configured() -> bool:
    return bool(MASTER_PASSWORD_HASH)


def is_master_username(username: str) -> bool:
    return normalize_username(username) == MASTER_USERNAME


def authenticate(username: str, password: str) -> dict | None:
    """Retorna {username, role} se credenciais válidas."""
    user = normalize_username(username)
    if not user or not password:
        return None

    if is_master_username(user):
        if not master_configured():
            return None
        if check_password_hash(MASTER_PASSWORD_HASH, password):
            return {'username': MASTER_USERNAME, 'role': 'master'}
        return None

    store = _load_store()
    record = store['users'].get(user)
    if not record or not record.get('active', True):
        return None
    pwhash = record.get('password_hash') or ''
    if pwhash and check_password_hash(pwhash, password):
        return {'username': user, 'role': 'user'}
    return None


def list_secondary_users() -> list[dict]:
    store = _load_store()
    rows = []
    for username, record in sorted(store['users'].items()):
        rows.append({
            'username': username,
            'role': 'user',
            'active': bool(record.get('active', True)),
            'created_at': record.get('created_at'),
            'created_by': record.get('created_by'),
        })
    return rows


def create_secondary_user(username: str, password: str, *, created_by: str) -> tuple[dict | None, str | None]:
    err = validate_username(username) or validate_password(password)
    if err:
        return None, err

    user = normalize_username(username)
    store = _load_store()
    if user in store['users']:
        return None, 'Usuário já existe.'

    store['users'][user] = {
        'password_hash': generate_password_hash(password),
        'role': 'user',
        'active': True,
        'created_at': _now_iso(),
        'created_by': created_by,
    }
    _save_store(store)
    return {'username': user, 'role': 'user', 'active': True}, None


def set_secondary_user_active(username: str, active: bool) -> tuple[bool, str | None]:
    user = normalize_username(username)
    if is_master_username(user):
        return False, 'Não é possível alterar o usuário master.'
    store = _load_store()
    if user not in store['users']:
        return False, 'Usuário não encontrado.'
    store['users'][user]['active'] = bool(active)
    store['users'][user]['updated_at'] = _now_iso()
    _save_store(store)
    return True, None


def delete_secondary_user(username: str) -> tuple[bool, str | None]:
    user = normalize_username(username)
    if is_master_username(user):
        return False, 'Não é possível excluir o usuário master.'
    store = _load_store()
    if user not in store['users']:
        return False, 'Usuário não encontrado.'
    del store['users'][user]
    _save_store(store)
    return True, None


def reset_secondary_password(username: str, new_password: str) -> tuple[bool, str | None]:
    user = normalize_username(username)
    if is_master_username(user):
        return False, 'Altere a senha master no arquivo .env (MASTER_PASSWORD_HASH).'
    err = validate_password(new_password)
    if err:
        return False, err
    store = _load_store()
    if user not in store['users']:
        return False, 'Usuário não encontrado.'
    store['users'][user]['password_hash'] = generate_password_hash(new_password)
    store['users'][user]['updated_at'] = _now_iso()
    _save_store(store)
    return True, None

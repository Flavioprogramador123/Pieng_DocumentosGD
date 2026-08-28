"""
Carrega variáveis sensíveis de arquivos .env locais (nunca commitados).
Deve ser importado antes de módulos que leem GEMINI_API_KEY etc.
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

SENSITIVE_ENV_KEYS = frozenset({
    'GEMINI_API_KEY',
    'SECRET_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
})


def load_local_env():
    """Lê .env da raiz do projeto e de backend/ (sem sobrescrever variáveis já definidas)."""
    for env_path in (ROOT_DIR / '.env', BASE_DIR / '.env'):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)


def redact_secrets(text):
    """Remove valores de chaves sensíveis de strings (logs, erros)."""
    if not text:
        return text
    result = str(text)
    for key in SENSITIVE_ENV_KEYS:
        val = os.environ.get(key, '')
        if val and len(val) > 4:
            result = result.replace(val, '***REDACTED***')
    # Padrões comuns de chave em URL ou JSON
    result = re.sub(
        r'(key=|api[_-]?key["\']?\s*[:=]\s*["\']?)[^\s&"\'}]+',
        r'\1***REDACTED***',
        result,
        flags=re.IGNORECASE,
    )
    return result

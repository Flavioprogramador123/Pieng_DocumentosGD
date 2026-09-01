"""
Caixa de medição no memorial — figura + texto conforme TIPO_LIGACAO.

Assets: templates/assets/caixa_medicao/{monofasica|polifasica}/
Tokens: {{FIGURA_CAIXA}}, {{TEXTO_CAIXA}} (aceita minúsculas no template)
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from docx_media import insert_image_at_placeholders

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / 'templates' / 'assets' / 'caixa_medicao'

VARIANTS = {
    'monofasica': ASSETS_DIR / 'monofasica',
    'polifasica': ASSETS_DIR / 'polifasica',
}

FIGURA_TOKEN = 'FIGURA_CAIXA'
TEXTO_TOKEN = 'TEXTO_CAIXA'
FIGURA_PLACEHOLDER = '[Figura caixa de medição]'

FIGURA_PLACEHOLDERS = (
    '{{FIGURA_CAIXA}}',
    '{{figura_caixa}}',
    FIGURA_TOKEN,
    FIGURA_PLACEHOLDER,
)


def _is_polifasico(tipo_ligacao: str | None) -> bool:
    t = (tipo_ligacao or '').upper()
    if 'MONO' in t:
        return False
    if 'TRIF' in t or 'BIF' in t or 'POLI' in t:
        return True
    return False


def resolve_caixa_variant(tipo_ligacao: str | None) -> str:
    return 'polifasica' if _is_polifasico(tipo_ligacao) else 'monofasica'


def resolve_caixa_assets(tipo_ligacao: str | None) -> dict[str, Path]:
    folder = VARIANTS[resolve_caixa_variant(tipo_ligacao)]
    imagem = folder / 'figura.png'
    if not imagem.is_file():
        imagem = folder / 'figura.jpg'
    return {
        'variante': folder.name,
        'imagem': imagem,
        'texto': folder / 'texto.txt',
    }


@lru_cache(maxsize=4)
def _load_text_cached(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_file():
        return ''
    raw = path.read_text(encoding='utf-8-sig').strip()
    return re.sub(r'[ \t]+', ' ', raw).strip()


def load_caixa_texto(path: Path) -> str:
    return _load_text_cached(str(path.resolve()))


def enrich_caixa_medicao_values(values: dict[str, str]) -> None:
    assets = resolve_caixa_assets(values.get('TIPO_LIGACAO'))
    texto = load_caixa_texto(assets['texto'])
    if texto:
        values[TEXTO_TOKEN] = texto
    else:
        values.setdefault(TEXTO_TOKEN, '')
    values.setdefault(FIGURA_TOKEN, FIGURA_PLACEHOLDER)


def try_embed_caixa_medicao(memorial_docx: Path, values: dict[str, str]) -> tuple[bool, str]:
    assets = resolve_caixa_assets(values.get('TIPO_LIGACAO'))
    imagem = assets['imagem']
    if not imagem.is_file():
        return False, (
            f'Figura da caixa de medição não encontrada em {imagem} '
            f'(variante {assets["variante"]}).'
        )
    ok = insert_image_at_placeholders(
        memorial_docx,
        imagem,
        FIGURA_PLACEHOLDERS,
        width_cm=12.0,
    )
    if ok:
        return True, f'Figura da caixa de medição inserida ({assets["variante"]}).'
    return False, (
        'Figura da caixa não inserida — marcador {{figura_caixa}} / '
        '[Figura caixa de medição] ausente no memorial.'
    )

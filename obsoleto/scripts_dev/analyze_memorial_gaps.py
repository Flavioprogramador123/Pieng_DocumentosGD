"""Analisa tokens vazios no memorial a partir do YAML padrão + catálogo."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_server import create_txt_data
from gerar_documentos import discover_tokens_docx, preview_token_mapping
from token_enrichment import enrich_normalized_payload
from yaml_loader import import_yaml_project
from residential_defaults import apply_residential_defaults

MEMORIAL = 'MEMORIAL_DESCRITIVO_marcadores.docx'


def main() -> None:
    templates = ROOT / 'templates'
    config = Path(__file__).resolve().parent / 'config_padrao.json'
    yaml_text = (ROOT / 'dados' / 'projeto_padrao.yaml').read_text(encoding='utf-8')

    imp = import_yaml_project(yaml_text)
    norm = imp['normalized']
    # Campos mínimos do cliente (simula preenchimento manual)
    norm['cliente'].update({
        'nome': 'Maria Silva Teste',
        'cpf': '123.456.789-00',
        'logradouro': 'Rua Teste',
        'numero': '100',
        'bairro': 'Centro',
        'cidade': 'Anápolis',
        'uf': 'GO',
        'cep': '75000-000',
    })
    norm['unidade_consumidora']['numero'] = '704.212.012-65'
    norm['dados_tecnicos']['area_arranjo'] = '28'
    norm['dados_tecnicos']['demanda_alvo_kw'] = '4.5'
    norm = apply_residential_defaults(norm)
    norm = enrich_normalized_payload(norm)
    flat = norm
    txt = create_txt_data(flat)
    preview = preview_token_mapping(txt, config, templates)

    mem_tokens = sorted(discover_tokens_docx(templates / MEMORIAL))
    missing = preview['unresolved_by_template'].get(MEMORIAL, [])
    values = preview['values']

    print(f'=== {MEMORIAL}: {len(mem_tokens)} tokens, {len(missing)} vazios ===\n')
    for token in missing:
        in_txt = token in {m['token'] for m in preview['mappings']}
        print(f'  {token}  (no TXT: {"sim" if in_txt else "nao"})')

    out = ROOT / 'dados' / 'memorial_tokens_pendentes.json'
    out.write_text(
        json.dumps({
            'memorial': MEMORIAL,
            'total_tokens': len(mem_tokens),
            'missing_count': len(missing),
            'missing_tokens': missing,
            'filled_tokens': [t for t in mem_tokens if t not in missing],
            'stats': preview['stats'],
        }, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f'\nRelatório salvo: {out}')


if __name__ == '__main__':
    main()

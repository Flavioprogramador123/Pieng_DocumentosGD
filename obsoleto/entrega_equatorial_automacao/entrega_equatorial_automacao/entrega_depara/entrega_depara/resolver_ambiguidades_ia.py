from __future__ import annotations

import argparse
import json
from pathlib import Path

from openai import OpenAI

from gerar_documentos import LABEL_ALIASES, normalize_alias_key

SCHEMA = {
    'type': 'object',
    'properties': {
        'mappings': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'label_original': {'type': 'string'},
                    'chave_sugerida': {'type': 'string'},
                    'confianca': {'type': 'number'},
                    'motivo': {'type': 'string'},
                },
                'required': ['label_original', 'chave_sugerida', 'confianca', 'motivo'],
                'additionalProperties': False,
            },
        }
    },
    'required': ['mappings'],
    'additionalProperties': False,
}


def unknown_labels(path: Path) -> list[str]:
    known = {normalize_alias_key(key) for key in LABEL_ALIASES}
    labels = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if ':' not in line:
            continue
        label = line.split(':', 1)[0].strip().lstrip('-*').strip()
        if label and normalize_alias_key(label) not in known:
            labels.append(label)
    return sorted(set(labels))


def main() -> None:
    parser = argparse.ArgumentParser(description='Sugere mapeamentos De/Para para chaves desconhecidas.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('sugestoes_depara_ia.json'))
    args = parser.parse_args()

    labels = unknown_labels(args.input)
    if not labels:
        args.output.write_text(json.dumps({'mappings': []}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Nenhuma chave desconhecida. Resultado: {args.output}')
        return

    allowed = sorted(set(LABEL_ALIASES.values()))
    client = OpenAI()
    response = client.chat.completions.create(
        model='gpt-5-mini',
        messages=[
            {
                'role': 'system',
                'content': (
                    'Você é um classificador de chaves de documentos elétricos. '
                    'Sugira apenas chaves da lista permitida. Nunca invente uma chave. '
                    'Se não houver correspondência segura, use DESCONHECIDA e confiança 0. '
                    'Não extraia nem altere valores; analise somente os nomes das chaves.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps({'chaves_desconhecidas': labels, 'chaves_permitidas': allowed}, ensure_ascii=False),
            },
        ],
        max_completion_tokens=2000,
        response_format={
            'type': 'json_schema',
            'json_schema': {'name': 'depara_suggestions', 'strict': True, 'schema': SCHEMA},
        },
    )
    result = json.loads(response.choices[0].message.content)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Sugestões gravadas em: {args.output}')
    print('As sugestões devem ser revisadas antes de serem adicionadas ao depara_chaves.json.')


if __name__ == '__main__':
    main()

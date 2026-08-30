"""
Gera preview NBR do memorial (fora do fluxo de produção):
  1. Formata backup PRE_NBR → MEMORIAL_DESCRITIVO_marcadores_NBR.docx
  2. Preenche exemplo → MEMORIAL_DESCRITIVO_exemplo_preenchido.docx
  3. Relatório de tokens pendentes

Não altera templates/MEMORIAL_DESCRITIVO_marcadores.docx oficial.

Uso (na raiz do repo):
  backend\\.venv\\Scripts\\python.exe obsoleto\\memorial_nbr_preview\\generate_memorial_nbr_preview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE))

from format_memorial_nbr import format_memorial_docx
from gerar_documentos import build_values, fill_docx, load_defaults, parse_txt

OUT_DIR = HERE / 'preview_output'
BACKUP = ROOT / 'obsoleto' / 'templates_backup' / 'MEMORIAL_DESCRITIVO_marcadores_PRE_NBR.docx'
EXAMPLE_TXT = HERE / 'dados_exemplo_memorial.txt'
TEMPLATE_NBR = OUT_DIR / 'MEMORIAL_DESCRITIVO_marcadores_NBR.docx'
EXAMPLE_OUT = OUT_DIR / 'MEMORIAL_DESCRITIVO_exemplo_preenchido.docx'
REPORT = OUT_DIR / 'relatorio_preenchimento_exemplo.txt'


def main() -> None:
    if not BACKUP.is_file():
        raise SystemExit(f'Backup não encontrado: {BACKUP}')
    if not EXAMPLE_TXT.is_file():
        raise SystemExit(f'Dados exemplo não encontrados: {EXAMPLE_TXT}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print('1/3 Formatando template NBR...')
    format_memorial_docx(BACKUP, TEMPLATE_NBR)

    print('2/3 Preenchendo exemplo...')
    raw = parse_txt(EXAMPLE_TXT)
    config = BACKEND / 'config_padrao.json'
    values = build_values(raw, load_defaults(config))
    unresolved = fill_docx(TEMPLATE_NBR, EXAMPLE_OUT, values)

    print('3/3 Relatório...')
    lines = [
        'PREVIEW MEMORIAL NBR — Automação Equatorial',
        f'Entrada: {EXAMPLE_TXT.name}',
        f'Template formatado: {TEMPLATE_NBR.name}',
        f'Saída preenchida: {EXAMPLE_OUT.name}',
        '',
        'Restaurar original:',
        '  Copy-Item obsoleto\\templates_backup\\MEMORIAL_DESCRITIVO_marcadores_PRE_NBR.docx '
        'templates\\MEMORIAL_DESCRITIVO_marcadores.docx -Force',
        '',
        'Valores principais:',
        f"  NOME_CLIENTE: {values.get('NOME_CLIENTE', '—')}",
        f"  QTD_MODULOS: {values.get('QTD_MODULOS', '—')}",
        f"  POTENCIA_TOTAL_INSTALADA: {values.get('POTENCIA_TOTAL_INSTALADA', '—')} kW",
        f"  QTD_INVERSORES: {values.get('QTD_INVERSORES', '—')}",
        f"  TIPO_EQUIPAMENTO_INVERSOR: {values.get('TIPO_EQUIPAMENTO_INVERSOR', '—')}",
        f"  DISJUNTOR_ENTRADA: {values.get('DISJUNTOR_ENTRADA', values.get('CORRENTE_ENTRADA', '—'))} A",
        f"  AREA_ARRANJO: {values.get('AREA_ARRANJO', '—')} m²",
        '',
        f'Tokens ainda no DOCX ({len(unresolved)}):',
    ]
    if unresolved:
        for t in sorted(unresolved):
            lines.append(f'  {{{{{t}}}}}')
    else:
        lines.append('  (nenhum)')

    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print('')
    print('Arquivos gerados em obsoleto/memorial_nbr_preview/preview_output/:')
    for p in (TEMPLATE_NBR, EXAMPLE_OUT, REPORT):
        print(f'  {p.relative_to(ROOT)}  ({p.stat().st_size:,} bytes)')
    print('')
    print('Abra MEMORIAL_DESCRITIVO_exemplo_preenchido.docx no Word e confirme layout/tabelas.')
    print(f'Tokens pendentes: {len(unresolved)} — ver {REPORT.name}')


if __name__ == '__main__':
    main()

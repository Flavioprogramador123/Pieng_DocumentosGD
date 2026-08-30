# Preview memorial NBR (arquivado)

Experimentos de formatação ABNT/NBR no memorial descritivo — **fora do fluxo de produção**.

Status em 30/08/2026: reprovado; o template oficial (`templates/MEMORIAL_DESCRITIVO_marcadores.docx`) permanece inalterado. Ajustes de layout serão feitos manualmente no Word.

## Conteúdo

| Item | Descrição |
|------|-----------|
| `format_memorial_nbr.py` | Aplica margens, fonte e tabelas NBR no DOCX |
| `generate_memorial_nbr_preview.py` | Gera preview preenchido + relatório de tokens |
| `dados_exemplo_memorial.txt` | Entrada De/Para para o exemplo |
| `preview_output/` | DOCX e relatório gerados (rascunho) |

Backup do memorial pré-NBR: `obsoleto/templates_backup/MEMORIAL_DESCRITIVO_marcadores_PRE_NBR.docx`

## Regenerar preview

```bat
cd C:\Users\flavi\projeto\Automacao_Equatorial01
backend\.venv\Scripts\python.exe obsoleto\memorial_nbr_preview\generate_memorial_nbr_preview.py
```

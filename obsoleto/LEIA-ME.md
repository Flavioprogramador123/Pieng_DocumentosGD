# Obsoleto — pode excluir depois de validar o sistema

Esta pasta guarda o que **não entra mais no fluxo ativo** após a reorganização de 28/08/2026.

Não apague ainda se quiser comparar um documento antigo. Quando o `iniciar.bat` gerar procuração, memorial e planilha corretamente, esta pasta inteira pode ser excluída.

## O que veio para cá

| Item | Motivo |
|------|--------|
| `equatorial_automation_backend/` | Flask antigo (python-docx, células de exemplo, CRUD /users) |
| `entrega_equatorial_automacao/` | Cópia aninhada 3 níveis; o código útil foi extraído para `backend/` e `templates/` |
| `templates_originais_sem_marcadores/` | Modelos oficiais sem `{{TOKEN}}` — o gerador usa os parametrizados |
| `venv/`, `node_modules/` da raiz | Ambiente e Express que não serviam o app |
| `scripts/`, `output/`, `saved_forms/`, `data_input/` | Saídas e scripts do backend antigo |
| `automacao-docs/` e manuais extras | Documentação duplicada/contraditória |
| Zips e `package.json` Express da raiz | Artefatos de entrega/cópia |

## Limpeza de 29/08/2026 (pré-GitHub)

| Pasta | Conteúdo |
|-------|----------|
| `scripts_dev/` | Patches pontuais (`patch_nt_formulario`, `patch_modelo_contrato_numero`, …), extratores de memorial, criadores de template, `requirements.txt` antigo |
| `scripts_testes/` | `test_catalog_search.py`, `test_enrichment.py` (testes manuais, não pytest) |
| `templates_backup/` | `.bak_*`, `_test_fill_nt.xlsx`, planilha Tokens-Revisao, `ModeloContrato_marcadores.docx`, texto de referência do contrato |
| `dados_analise/` | `debug_txt.txt`, análises de marcadores/tokens do memorial |
| `docs_memorial/` | `MEMORIAL_LEGENDA.md`, `MEMORIAL_TOKENS.md` (referência de desenvolvimento) |
| `diagnostico/` | `diagnostico.bat`, `diagnostico.sh` |
| `temp_figura_maps/` | Protótipo da figura de localização (integrado em `backend/figura_localizacao.py`) |
| `imagenscaixas/` | Assets antigos da caixa de medição (substituídos por `templates/assets/caixa_medicao/`) |

**Mantido no fluxo ativo:** `backend/patch_memorial_demand.py` (aplicado na subida da API), `export_calculations.py`, catálogo YAML, templates oficiais sem sufixo `.bak`.

O sistema ativo está na raiz: `backend/`, `equatorial_automation_frontend/`, `templates/`, `saida/`, `dados/`.

## Limpeza de 30/08/2026

| Pasta / item | Conteúdo |
|--------------|----------|
| `memorial_nbr_preview/` | Scripts e preview do memorial NBR (reprovado; não entra na geração oficial) |
| `templates_backup/` | Backups movidos de `templates/backup/` (incl. `MEMORIAL_*_PRE_NBR.docx`) |
| `scripts_dev/list_dwg_tokens.py` | Utilitário para listar tokens em DXF/DWG |
| `docs_checkpoints/` | Notas de checkpoint de desenvolvimento (`CHECKPOINT_2026-08-30_pre_mppt.md`) |

Removido da raiz: pasta `templates/backup/`, duplicatas em `.temp/` (cópias já existem em `docs/`), artefato `nul` do Windows.

Se ainda existir `.temp/memorial_nbr/` com arquivo aberto no Word, pode apagar manualmente após fechar o documento.

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

O sistema ativo está na raiz: `backend/`, `frontend/`, `templates/`, `saida/`, `dados/`.

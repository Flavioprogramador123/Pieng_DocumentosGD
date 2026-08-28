# Automação Equatorial — documentos de microgeração

Gera procuração, memorial descritivo e formulário NT.00020-05 a partir de um TXT ou do formulário web.

## Como iniciar

Na raiz do projeto, execute `iniciar.bat` (Windows) ou `iniciar.sh` (Linux/Mac).

- Backend: http://127.0.0.1:5000
- Frontend: http://localhost:5173

## Estrutura ativa

```
backend/                         API Flask + gerar_documentos.py
equatorial_automation_frontend/  Interface React
templates/                     Modelos oficiais com {{TOKEN}}
dados/                         TXT de exemplo
saida/                         Documentos gerados
obsoleto/                      Cópias antigas — pode excluir depois de validar
```

## Uso rápido

1. Abra http://localhost:5173
2. Cole o TXT do cliente na aba TXT e importe
3. Revise os campos (bairro às vezes não vem no texto)
4. Calcule e gere os documentos — os arquivos saem em `saida/web_generated/`

Pela linha de comando:

```bash
cd backend
.venv\Scripts\python gerar_documentos.py --input ..\dados\dados_modelo.txt --templates-dir ..\templates --output-dir ..\saida --config config_padrao.json
```

## Pastas que não usar

Tudo em `obsoleto/` ficou de fora do fluxo (backend Flask antigo, pastas aninhadas, templates sem marcadores, manuais duplicados). Leia `obsoleto/LEIA-ME.md` antes de apagar.

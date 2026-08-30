# Automação Equatorial — documentos de microgeração

Gera procuração, memorial, contrato, formulário NT.00020-05 e planta CAD a partir do formulário web ou TXT.

## Como iniciar

Na raiz do projeto, execute `iniciar.bat` (Windows) ou `start_all.bat`.

- Backend: http://127.0.0.1:5000
- Frontend: http://localhost:5173
- Login master: usuário `pieng` (senha via `MASTER_PASSWORD_HASH` no `backend/.env`)

## Estrutura ativa

```
backend/                         API Flask + gerar_documentos.py
equatorial_automation_frontend/  Interface React (login + formulário)
templates/                       Modelos oficiais com {{TOKEN}}
  NT.00020-05-...templates.xlsx  Formulário NT (listas suspensas pré-configuradas)
  autocad/                       LISP opcional + LEIA-ME
dados/                           TXT de exemplo + normas_equatorial_go.json
saida/web_generated/             Fallback local se Drive indisponível
obsoleto/                        Código e templates legados
```

## Uso rápido

1. Configure `backend/.env` (hash master, opcional: `CLIENT_OUTPUT_DIR`, SMTP).
2. Abra http://localhost:5173 e faça login.
3. Preencha o formulário (número do contrato obrigatório) → **Gerar documentos**.
4. Pasta do cliente: `{contrato} - {nome}\` no Drive ou `saida/web_generated/`.

**Saída típica por cliente:**

| Arquivo | Descrição |
|---------|-----------|
| Memorial / Procuração / Contrato | DOCX |
| NT.00020-05-...templates.xlsx | Excel (tokens + listas já escolhidas no template) |
| planta.dxf | AutoCAD com textos preenchidos |
| figura_localizacao.png | Mapa (colar na prancha com Win+Shift+S) |
| tokens_autocad.txt | Backup dos valores CAD |

Pela linha de comando:

```bash
cd backend
python gerar_documentos.py --input ..\dados\cliente_fabrica_doces.txt --templates-dir ..\templates --output-dir ..\saida\teste --config config_padrao.json
```

## Documentação Técnica

- **[CHANGELOG.md](CHANGELOG.md)** — Histórico de versões (último marco: **0.5.4**, 29/08/2026)
- **[AGENTS.md](AGENTS.md)** — Arquitetura e roadmap técnico
- **[templates/autocad/LEIA-ME.md](templates/autocad/LEIA-ME.md)** — Fluxo planta CAD
- **[docs/INTEGRACAO_CALCULOS_TEMPLATES.md](docs/INTEGRACAO_CALCULOS_TEMPLATES.md)** — Cálculos e tokens nos templates
- **[docs/NBR5410_CALCULOS_ELETRICOS.md](docs/NBR5410_CALCULOS_ELETRICOS.md)** — Cálculos elétricos NBR 5410
- **[docs/CATALOG_SEARCH.md](docs/CATALOG_SEARCH.md)** — Catálogo SQLite / busca fuzzy

## Recursos Principais

### Geração de Documentos
- Memorial Descritivo (DOCX)
- Procuração (DOCX)
- Contrato (DOCX)
- Formulário NT.00020-05 Anexo I (XLSX — template com dropdowns fixos)
- Planta CAD (DXF pré-preenchido)

### Autenticação e saída
- Login master + usuários secundários
- Confirmação de dispositivo novo por e-mail (ou código na tela em dev local)
- Pasta de saída no Google Drive (`CLIENT_OUTPUT_DIR`) — dados LGPD fora do git

### Cálculos Automáticos
- Dimensionamento de cabos CC/CA
- Análise de strings fotovoltaicas
- Compatibilidade módulo/inversor
- Geração estimada (mensal/anual)
- Tabela de levantamento de carga (demanda)

### ✅ Busca Inteligente de Equipamentos (v0.5.3)
- **3 camadas de busca**: exato → potência → tolerância (±5% módulos, ±10% inversores)
- **Prioridade SQLite**: 99% das consultas resolvidas localmente (sem API)
- **Fuzzy search**: encontra 'Canadian' mesmo digitando 'Canadan'
- **Economia**: reduz custo/latência em 99% vs API Gemini

### ✅ Inteligência Artificial
- Gemini 3.6 Flash como **último recurso** (apenas equipamentos novos)
- Enriquecimento automático de especificações técnicas
- Geração de tabela de demanda personalizada
- Respostas salvas no catálogo para reutilização

### ✅ Catálogo SQLite
- Módulos fotovoltaicos (JA Solar, Longi, Risen, Canadian, etc.)
- Inversores (Fronius, Sungrow, Huawei, DEYE, SAJ, Growatt)
- Padrão de entrada por UF/ligação
- **Busca fuzzy com pontuação de relevância**

## Pastas que não usar

Tudo em `obsoleto/` ficou de fora do fluxo (backend Flask antigo, pastas aninhadas, templates sem marcadores, manuais duplicados). Leia `obsoleto/LEIA-ME.md` antes de apagar.
# Pieng_DocumentosGD

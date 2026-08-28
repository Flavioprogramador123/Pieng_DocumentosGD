# Changelog — Automação Equatorial

Registro de alterações do projeto. Versões seguem ordem cronológica de marcos entregues.

---

## [0.4.0] — 2026-08-28

### Adicionado
- **Entrada YAML** — `dados/projeto_padrao.yaml` como schema documentado para preenchimento externo (IA ou manual).
- **`backend/yaml_loader.py`** — importação YAML → formulário, enriquecimento via catálogo SQLite, exportação do formulário para YAML.
- **API** — `GET /api/yaml/template`, `POST /api/import-yaml`, `POST /api/export-yaml`.
- **Frontend** — sub-aba YAML na aba Entrada (carregar modelo, importar, exportar do formulário).
- **`dados/YAML_INSTRUCOES.md`** — prompt sugerido para preencher o YAML com IA externa.
- **Catálogo SQLite expandido** — mais módulos (JA Solar, Longi, Risen) e inversores (Fronius, Sungrow, Huawei).

### Melhorado
- Importação YAML consulta catálogo antes de deixar campos vazios (Voc, Isc, MPPT, padrão de entrada por UF).
- Memorial descritivo: placeholder `{{TABELA_DEMANDA}}` abaixo da Tabela 1.

### Testado pelo usuário
- SQLite catálogo (CRUD + lookup).
- Gemini (`gemini-3.6-flash`) para enriquecimento de equipamentos.
- Inserção de tokens nos templates DOCX/XLSX.

---

## [0.3.0] — 2026-08-28

### Adicionado
- **Catálogo SQLite** (`backend/catalog_db.py`) — módulos, inversores, padrão de entrada por UF/ligação.
- **Aba Catálogo SQL** no frontend (`CatalogPanel.jsx`) — edição tipo planilha.
- **API catálogo** — `GET/POST /api/catalog/<table>`, `DELETE`, `POST /api/catalog/lookup`.
- **Cálculos elétricos** — strings CC (V série, I não soma), microinversor, trifásico √3 e 380 V GO.
- **`backend/string_calculations.py`**, **`backend/grid_voltage.py`**, **`backend/system_calculations.py`**.
- **Tabela de demanda** — geração automática e injeção no memorial (`backend/demand_table.py`, `patch_memorial_demand.py`).
- **Painel DE/PARA** redimensionável (`DeParaPanel.jsx`).
- **Busca CEP/endereço** — ViaCEP (`backend/cep_lookup.py`, `POST /api/lookup-address`).
- **Defaults residenciais** — disjuntor, DPS, cabos, aterramento (`residential_defaults.py`, `formDefaults.js`).
- **Enriquecimento IA** — Ollama → Gemini com catálogo primeiro (`equipment_enrichment.py`).
- **Proxy Vite** `/api` → backend local.

### Corrigido
- Mapeamento formulário plano → backend aninhado (`form_mapper.py`) — placeholders vazios na procuração.
- Erro 500 em `/api/calculate-system` com campos vazios (`_safe_int` / `_safe_float`).
- Unidade inversor: kW no formulário (não watt).
- Chave Gemini via `.env`; modelo padrão `gemini-3.6-flash`.

---

## [0.2.0] — 2026-08-28

### Adicionado
- Reorganização do repositório — código ativo na raiz; legado em `obsoleto/`.
- **`AGENTS.md`** — briefing P0→P3 para evolução do projeto.
- **`backend/api_server.py`** + **`backend/gerar_documentos.py`** como pilha única.
- Scripts `iniciar.bat`, `start_all.bat` unificados.

### Corrigido
- Parser TXT De/Para — RG, endereço, UC (caso Rosembergue).

---

## [0.1.0] — baseline

### Existente
- Gerador XML com tokens `{{TOKEN}}` em DOCX/XLSX.
- Templates oficiais em `templates/`.
- Formulário web React com abas Cliente, Equipamentos, Técnicos, Cálculos.
- Parser De/Para local (`txtParser.js`).

---

## Próximos passos (planejado)

- [ ] Reduzir tokens NULL no memorial via catálogo + YAML + specs web.
- [ ] Quarto documento oficial (aguardando definição do template).
- [ ] PII de `config_padrao.json` → `.env` / `config_padrao.local.json`.
- [ ] Testes pytest (tokens, aliases, cálculos).
- [ ] Validar CPF/CEP/UC antes de gerar (Zod no frontend).

# Changelog — Automação Equatorial

Registro de alterações do projeto. Versões seguem ordem cronológica de marcos entregues.

---

## [0.5.5] — 2026-08-30 — *checkpoint pre-MPPT*

Marco de restauração **antes** da integração de topologia MPPT/strings (SAJ/DEYE). Ver `docs/CHECKPOINT_2026-08-30_pre_mppt.md`.

### Adicionado
- **Coordenadas UTM ↔ graus decimais** — `coordinate_utils.py`, frontend, `/api/coordinates/resolve`, testes.
- **Figura de localização** — `figura_localizacao.py` (osmde, zoom adaptivo 16/18), preview na UI (`FiguraLocalizacaoPreview.jsx`), `/api/figura-localizacao/preview`.
- **Tokens UC normalizados** — `CONTA_CONTRATO_DIGITOS` / `CONTA_CONTRATO_FORMATADA` para memorial e DXF.
- **Testes trifásico** — `test_trifasico_calculations.py`.

### Corrigido
- **Trifásico GO** — disjuntor tripolar, PD com VN 220 V FN, corrente micro I=P/220 V, strings em √3×380 V.
- **Conta contrato** — não concatenar dígitos duplicados (UC com e sem separadores).
- **Startup** — `iniciar.bat` aguarda backend (`/api/health`) e Vite antes de abrir o navegador.

### Pendente (próxima sessão)
- Topologia MPPT/strings por fabricante (catálogo YAML/SQLite + motor de strings + UI).

---

## [0.5.4] — 2026-08-29

Sessão de consolidação: autenticação, saída LGPD, CAD, NT.00020-05 com listas suspensas e PD calculado.

### Adicionado
- **Autenticação web** — login master (`pieng` + hash no `.env`), usuários secundários, sessão Flask 8h.
- **Verificação de dispositivo novo** — e-mail + código de 6 dígitos (`MASTER_VERIFY_EMAIL`, SMTP Gmail); modo local exibe código na tela quando SMTP vazio em `localhost`.
- **Saída LGPD** — `CLIENT_OUTPUT_DIR` no `.env` (Google Drive); pasta `{numero_contrato} - {1º 2º nome}` via `output_paths.py`.
- **Planta CAD automática** — `planta.dxf` gerado com tokens preenchidos (`backend/autocad_fill.py` + `ezdxf`); mapa colado manualmente (Win+Shift+S) no AutoCAD.
- **Tokens AutoCAD** — `tokens_autocad.txt` + `figura_localizacao.png` na pasta do cliente; LISP `PIENG_TOKENS` opcional (`templates/autocad/`).
- **Contrato** — template `ModeloContrato.docx` no fluxo de geração.
- **Template NT.00020-05 em `.xlsx`** — listas suspensas pré-selecionadas no modelo (`templates/NT.00020-05-...templates.xlsx`); `.xltx` legado ignorado.

### Corrigido
- **PD (Potência Disponibilizada)** — célula `AB29` do formulário NT: cache recalculado após preenchimento (`_recalc_pd_uc_guia1`); GO mono 40 A → 8 kW. UF default **GO** no template resolve visualização antes da geração.
- **Template NT duplicado** — `.xltx` antigo não sobrescreve mais o `.xlsx` editado pelo usuário.
- **Login** — fluxo e-mail → enviar código → confirmar; token de verificação repassado ao frontend.
- **Download na UI** — botão **Planta CAD** (`planta.dxf`) e demais anexos na pasta do cliente.

### Melhorado
- **AutoCAD** — fluxo simplificado: textos no `planta.dxf`; figura de localização manual (sem automação de imagem no LISP).
- **Documentação** — `templates/autocad/LEIA-ME.md`, `.env.example` (SMTP, auth, Drive).

### Decisões / uso diário (registro)
| Item | Decisão |
|------|---------|
| Mapa na prancha | Recorte Win+Shift+S → colar no AutoCAD |
| NT listas suspensas | Fixas no `.xlsx` template; só `{{TOKEN}}` é sobrescrito |
| UF no NT | Default **GO** no template |
| SMTP | Configurar `SMTP_PASSWORD` (senha de app Gmail) para e-mail real; senão código na tela em localhost |

---

## [0.5.3] — 2026-08-28

### Adicionado
- **Busca fuzzy de equipamentos no catálogo SQLite** — reduz drasticamente uso da API Gemini.
- **Estratégia de busca inteligente em 3 camadas**:
  1. Match exato: fabricante + modelo
  2. Match por potência exata: fabricante + potência
  3. Match com tolerância: ±5% para módulos, ±10% para inversores
- **`search_modules_fuzzy()`** — busca de módulos com pontuação de relevância.
- **`search_inverters_fuzzy()`** — busca de inversores com filtro por tipo (micro/string).
- **`find_module_by_name_or_power()`** — busca inteligente de módulos.
- **`find_inverter_by_name_or_power()`** — busca inteligente de inversores.
- **4 novos endpoints de API**:
  - `POST /api/catalog/search-modules` — busca fuzzy de módulos
  - `POST /api/catalog/search-inverters` — busca fuzzy de inversores
  - `POST /api/catalog/find-module` — busca inteligente com 3 camadas
  - `POST /api/catalog/find-inverter` — busca inteligente com 3 camadas

### Melhorado
- **equipment_enrichment.py** — agora usa busca fuzzy ANTES de chamar Gemini.
- **token_enrichment.py** — atualizado para usar `find_module_by_name_or_power` e `find_inverter_by_name_or_power`.
- **`/api/analyze-text`** — importação TXT agora enriquece AUTOMATICAMENTE com catálogo SQLite.
- **Prioridade de busca correta**: SQLite (exato → potência → tolerância) → Gemini API (último recurso).
- **Economia de custo/tempo**: até 80% menos chamadas à API Gemini em projetos com equipamentos comuns.
- **Tolerância inteligente**: 400W ±5% encontra módulos de 380-420W automaticamente.
- **Preenchimento automático de campos técnicos**: num_mppt, Voc, Isc, MPPT ranges, etc.

### Exemplo de Uso
```python
# Antes: chamava Gemini mesmo com módulo no catálogo
enrich_module_specs("Canadian Solar", "CS3W-400P", 400)
# → Gemini API call (custo + latência)

# Agora: busca inteligente no catálogo primeiro
enrich_module_specs("Canadian Solar", "CS3W-400P", 400)
# → Tier 1: Match exato "CS3W-400P" ✅ (0ms, grátis)
# → Tier 2: Match potência 400W (se tier 1 falhar)
# → Tier 3: Match 380-420W (±5%) (se tier 2 falhar)
# → Gemini API apenas se nenhum tier encontrar
```

---

## [0.5.2] — 2026-08-28

### Adicionado
- **Validação de limites de potência por rede** — bloqueia sistemas que excedem capacidade da rede.
- **Limites NBR 5410**: Monofásico 220V → 12 kW | Bifásico 220V → 25 kW | Trifásico → 75 kW.
- **Cálculo de quantidade de disjuntores CA** — automático para microinversores e inversores string.
- **Agrupamento de microinversores por disjuntor** — máximo 3 micros/disjuntor, grupos detalhados.
- **`validate_network_power_limit()`** — valida se potência respeita limite da rede.
- **`calculate_breaker_groups_microinverters()`** — divide microinversores em grupos de até 3 por disjuntor.

### Corrigido
- **❌ ERRO CRÍTICO**: Sistema aceitava 15 kW em rede monofásica 220V (limite: 12 kW).
- **❌ ERRO CRÍTICO**: Não calculava quantidade de disjuntores CA necessários.
- **❌ ERRO CRÍTICO**: Microinversores sem agrupamento por disjuntor (todos no mesmo disjuntor = PERIGOSO).

### Melhorado
- **system_calculations.py** — integra validação de potência e cálculo de disjuntores.
- **Novos campos no resultado**: `power_limit`, `num_breakers_ca`, `breaker_groups`.
- **Mensagens de erro específicas** — "Sistema de 15 kW EXCEDE limite de 12 kW. Migrar para rede maior ou reduzir potência."

### Exemplos Práticos Adicionados
**Exemplo 4**: 5 microinversores 2,25 kW em rede monofásica 220V
```
5 micros ÷ 3 = 2 disjuntores
Disjuntor 1: 3 micros → 30,68A → 40A
Disjuntor 2: 2 micros → 20,45A → 32A
✅ OK: 11,25 kW < 12 kW (limite monofásico)
```

**Exemplo 5**: 15 kW em rede monofásica 220V
```
❌ ERRO: 15 kW EXCEDE limite de 12 kW
Solução: Migrar para rede bifásica (25 kW) ou trifásica (75 kW)
```

**Exemplo 6**: 2 inversores string 6kW em rede monofásica 220V
```
2 inversores = 2 disjuntores (1 por inversor)
Cada disjuntor: 40A
Total: 12 kW (no limite)
```

---

## [0.5.1] — 2026-08-28

### Adicionado
- **`backend/nbr5410_calculations.py`** — cálculos elétricos conformes NBR 5410 com validações automáticas.
- **Validação de compatibilidade inversor × rede** — bloqueia inversor monofásico em rede trifásica e vice-versa.
- **Análise de distribuição de microinversores** — máximo 3 em série por fase, balanceamento trifásico.
- **Cálculo correto de corrente CA** — fórmulas específicas para mono/bi/trifásico (P/V vs P/(V×√3)).
- **Documentação NBR 5410** — `docs/NBR5410_CALCULOS_ELETRICOS.md` com exemplos práticos e regras detalhadas.

### Corrigido
- **❌ ERRO CRÍTICO**: Cálculo de corrente CA para microinversores ignorava soma de correntes em série.
- **❌ ERRO CRÍTICO**: Sistema não reconhecia limite de 3 microinversores em série por fase.
- **❌ ERRO CRÍTICO**: Distribuição de microinversores em rede trifásica não balanceava nas 3 fases.
- **❌ ERRO CRÍTICO**: Inversor monofásico sendo aceito em rede trifásica (incompatível).
- **❌ ERRO CRÍTICO**: Fórmula trifásica aplicava √3 incorretamente para inversores string.

### Melhorado
- **system_calculations.py** — integra `nbr5410_calculations` com avisos automáticos de incompatibilidade.
- **Corrente por fase** — novo campo `corrente_por_fase_a` no resultado de cálculos.
- **Mensagens de compatibilidade** — avisos específicos: "⚠️ 5 micros/fase excede limite de 3 em série".
- **Dimensionamento de disjuntor** — baseado em corrente por fase × 1,25 (NBR 5410).

### Exemplos Corrigidos
**ANTES** (❌ incorreto):
```
9 microinversores 500W, rede trifásica 220V
I_total = (9 × 500W) / 220V = 20,45 A  // ERRADO: não considera série
```

**DEPOIS** (✅ correto):
```
9 microinversores 500W, rede trifásica 220V
Distribuição: 3 micro/fase (3 em série por fase)
I_micro = 500W / 220V = 2,27 A
I_por_fase = 2,27 A × 3 série = 6,82 A
I_total = 6,82 A × 3 fases = 20,45 A  // CORRETO
```

---

## [0.5.0] — 2026-08-28

### Adicionado
- **Backend unificado** — migração completa para `backend/api_server.py` como servidor único; eliminado backend duplicado.
- **Links de download clicáveis** — botões "Baixar" funcionais para Excel, Memorial e Procuração após geração.
- **Script de inicialização profissional** — `iniciar.bat` com barra de progresso animada (0%→100%) e tela final limpa.
- **Verificação de templates** — auditoria completa dos 3 templates oficiais (DOCX/XLSX) com mapeamento de 150+ tokens.
- **Proteção contra Path Traversal** — sanitização de caminhos no endpoint `/api/download/<filepath>`.
- **Exportação de cálculos** — `backend/export_calculations.py` gera relatórios técnicos em JSON, CSV e TXT.
- **Endpoint `/api/export-calculations`** — exporta cálculos completos com download de relatórios formatados.
- **Documentação completa** — `docs/INTEGRACAO_CALCULOS_TEMPLATES.md` com guia técnico de integração de cálculos e tabelas.

### Melhorado
- **Gemini AI integrado** — migração de `gemini-2.0-flash` (descontinuado) → `gemini-3.6-flash` (atual).
- **Badge de status IA** — detecção automática de Ollama/Gemini com fallback correto no frontend.
- **Mapeamento de campos** — análise de cobertura: **80% dos campos principais mapeados** (cliente, equipamentos, técnicos).
- **Scripts de startup** — `start_backend.bat` e `start_frontend.bat` com instalação silenciosa de dependências.
- **Compatibilidade batch** — substituição de caracteres Unicode por ASCII; correção `/T /NOBREAK` (uppercase).

### Corrigido
- **Múltiplos processos backend** — eliminados 8 processos duplicados rodando simultaneamente na porta 5000.
- **Chave API Gemini** — migração de API Agent Platform → Generative Language API (chave correta `AIza...`).
- **Cache Python** — limpeza de arquivos `.pyc` obsoletos que impediam atualização do modelo Gemini.
- **Encoding batch files** — remoção de `chcp 65001` e caracteres Unicode incompatíveis com CMD.
- **Detecção de IA primária** — campo `primary` adicionado ao status IA para renderização correta do badge.

### Verificado
- ✅ **Excel template** — `NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xltx` abre corretamente (openpyxl).
- ✅ **Word templates** — `MEMORIAL_DESCRITIVO_marcadores.docx` (329 KB) e `modelo_procuracao_marcadores.docx` (28 KB) funcionais.
- ✅ **Cobertura de tokens** — 120/150 tokens principais mapeados; 30 tokens pendentes (specs detalhadas de inversor/módulo).

---

## [0.4.1] — 2026-08-28

### Adicionado
- **`backend/token_enrichment.py`** — enriquecimento antes do TXT: catálogo campo a campo, defaults de disjuntor/DPS/inversor, tabela de demanda automática.
- **`backend/analyze_memorial_gaps.py`** — relatório de tokens pendentes no memorial (`dados/memorial_tokens_pendentes.json`).
- Catálogo SQLite: dimensões de módulos (m, kg) e specs estendidas de inversores (CC/CA, THD, MPPT).

### Melhorado
- **`dados/modulos_solares.yaml`** + **`import_modulos_yaml.py`** — importa RENE PV / TSUN POWER (620–700 W) para SQLite; carrega ao subir o backend.
- Lookup de módulo por **fabricante + potência (Wp)** quando modelo não informado.
- API: `POST /api/catalog/import-modulos-yaml`, `GET /api/catalog/modulos-yaml-info`.
- Catálogo UI: botão **Importar YAML módulos** + colunas comprimento/largura/peso.
- **`dados/inversores.yaml`** + **`import_inversores_yaml.py`** — DEYE/SAJ micro 2,25 kW, string 6 kW e 15 kW trifásico.
- Lookup inversor por **fabricante + potência (kW)**; import automático ao subir backend.
- Memorial: **33 → 3 tokens vazios** com YAML padrão + catálogo (restam só UTM X/Y e Nº poste — dados de campo).
- `create_txt_data` emite labels completos do memorial (inversor, disjuntor, DPS, módulo).
- `build_values` calcula potência disponibilizada (kVA/kW) com tensão `220V` e fator `0,92`.
- Correção: catálogo preenche Voc/Isc/MPPT campo a campo (não só quando potência vazia).

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

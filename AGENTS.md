# Instruções para a IA — melhoria da Automação Equatorial

Este arquivo é o briefing obrigatório antes de alterar o projeto. Foi gerado a partir da análise de 28/08/2026. Siga a ordem P0 → P1 → P2 → P3. Não comece por catálogo, AutoCAD, ART/TRT ou APIs da ANEEL.

Responda e implemente em **português**.

---

## O que este projeto é

Sistema local para preencher documentos de microgeração distribuída da Equatorial Energia (PRODIST 3):

1. Procuração (DOCX)
2. Memorial técnico descritivo (DOCX)
3. Formulário NT.00020-05 (XLSX)
4. Quarto documento oficial — **planta CAD** (`planta.dxf` + ajuste manual no AutoCAD); ART/diagrama formal ainda fora se necessário

Entrada: formulário web e/ou arquivo TXT `Campo: valor`. Saída: DOCX/XLSX/DXF na pasta do cliente (Drive ou `saida/`).

---

## O que NÃO reescrever

Estas peças já estão corretas. Melhore por volta delas; não recrie do zero.

| Peça | Onde | Por quê |
|------|------|---------|
| Gerador XML | `backend/gerar_documentos.py` | Preenche DOCX/XLSX no XML (`{{TOKEN}}`), aliases De/Para, normaliza CPF/CEP/RG, gera `relatorio_preenchimento.txt` |
| Templates com marcadores | `templates/modelo_procuracao_marcadores.docx`, `MEMORIAL_DESCRITIVO_marcadores.docx`, `NT.00020-05-...templates.xlsx`, `ModeloContrato.docx` | Documentos oficiais parametrizados; NT usa `.xlsx` com listas suspensas fixas no modelo |
| Parser De/Para (JS) | `equatorial_automation_frontend/src/utils/txtParser.js` | Dezenas de rótulos mapeados; caminho confiável sem IA |
| Formulário web (campos) | `equatorial_automation_frontend/src/App.jsx` | Já coleta Voc, Isc, coordenadas, DPS, cabos, aterramento — o buraco é não enviar isso ao gerador |

IA (Ollama/Gemini) é **opcional**. O parser De/Para é o caminho padrão. Não torne a geração dependente de LLM.

---

## Estrutura atual (reorganizada em 28/08/2026)

Há **um** backend ativo: `backend/api_server.py` + `backend/gerar_documentos.py`.
`iniciar.bat` e `start_all.bat` sobem a mesma pilha.

```
backend/                         api_server.py, gerar_documentos.py, config_padrao.json
equatorial_automation_frontend/
templates/                     modelos com {{TOKEN}}
dados/                         TXT de exemplo
saida/                         documentos gerados
obsoleto/                      não usar — Flask antigo, pastas aninhadas, docs duplicadas
```

Não reative nada de `obsoleto/`. Não recrie o Flask antigo (`python-docx` / células C15).

### Incompatibilidade de contrato (ainda no código)

**Cálculos**

- Frontend faz `setCalculations(data)` e lê `data.power_summary`, `data.generation`, `data.compatibility`.
- `api_server.py` devolve `{ success, calculations: { total_module_power_kw, ... } }` — **sem** `power_summary`. A aba Cálculos quebra ou fica vazia.

**Documentos**

- Frontend espera `data.files.excel / memorial / procuracao` (objeto).
- `api_server.py` devolve `data.files` como **array** `{ name, size, download_url }`.
- A UI mostra um alert e caminhos; **não há botão de download**.

**Unidade do inversor (bug de engenharia)**

- Label no frontend: potência do inversor em **kW** (ex.: 2,25).
- Backend antigo trata como **watt**.
- `api_server.create_txt_data` faz `float(power) / 1000` assumindo watt.
- 8 × 2,25 kW deveria ser 18 kW. Se lido como 2,25 W, cabos, disjuntor e relação módulo/inversor saem errados.

**Perda de campos na web**

`api_server.create_txt_data()` só grava nome, CPF, endereço, UC, tensão, tipo de consumo, quantidade/modelo/potência de módulos e inversores.

**Não entram no TXT** (e portanto não preenchem o DOCX/XLSX): RG, nascimento, telefone, e-mail, logradouro/número/bairro/cidade/UF/CEP separados, Voc, Isc, Vmpp, Impp, eficiência, coordenadas UTM, fuso, poste, DPS, curva do disjuntor, bitolas, aterramento, área do arranjo, data de operação, fabricante.

O formulário já tem esses campos. O trabalho é **mapear para os tokens** de `LABEL_ALIASES` em `gerar_documentos.py`, não redesenhar a UI.

---

## Arquitetura alvo

Um backend, um frontend, um `templates/`, um `saida/`.

```
entrada (TXT | JSON | formulário)
        → mesmo schema de tokens
        → gerar_documentos.py (import Python, evitar subprocess se possível)
        → saida/<cliente_timestamp>/ + ZIP
        → /api/download sanitizado
```

- Flask antigo (`equatorial_automation_backend`) sai do fluxo da UI. Reaproveitar só `advanced_calculations.py` **depois** de corrigir unidades e usar Voc/Isc reais.
- Remover CRUD `/api/users` (scaffold sem autenticação, não faz parte do produto).
- Cálculos avançados: módulo importado, não segundo servidor.

---

## P0 — Unificar a pilha (fazer agora)

Critério de pronto: preencher o formulário completo, gerar os 3 arquivos oficiais iguais ao CLI, baixar ZIP, unidades kW/W corretas, um único `iniciar`.

1. **Escolher um backend:** FEITO — só `backend/api_server.py` + `gerar_documentos.py`. Não reativar `obsoleto/`.
2. **Alinhar o contrato JSON** com o frontend (ou ajustar o frontend ao contrato novo — uma fonte só):
   - `POST /api/calculate-system` → objeto de cálculos que a aba Cálculos já renderiza **ou** frontend lendo `data.calculations`.
   - `POST /api/fill-documents` → lista de arquivos com `download_url`.
   - `GET /api/download/...` usado por botões reais na UI.
3. **Mapear todos os campos** de `clientData`, `technicalData`, `modules[]`, `inverters[]` para o TXT/tokens (`LABEL_ALIASES`). Não descartar Voc/Isc/coordenadas/DPS/cabos.
4. **Padronizar unidades no backend, uma vez:**
   - Módulo: W (Wp)
   - Inversor: kW
   - Documentar no formulário e converter só num ponto.
5. **Download na UI:** um botão por arquivo + ZIP do pacote do cliente. Não mostrar só path local.
6. **Segurança mínima:**
   - `debug=False` fora de desenvolvimento
   - bind `127.0.0.1` (não `0.0.0.0` com debug)
   - `SECRET_KEY` via variável de ambiente
   - sanitizar `/api/download/<path>`: resolver o path e garantir que fica **dentro** de `saida/`; recusar `..`
   - não devolver `traceback` ao cliente
   - CORS só para a origem do frontend local

Arquivos principais P0:

- `equatorial_automation_frontend/src/App.jsx`
- `entrega_equatorial_automacao/.../api_server.py`
- `entrega_equatorial_automacao/.../gerar_documentos.py`
- `iniciar.bat`, `iniciar.sh`, `start_all.bat`, `start_backend.bat`

---

## P1 — Deixar confiável para protocolo (2–4 semanas)

Critério de pronto: um caminho de pastas, HSP por UF, 4º documento definido ou explicitamente fora de escopo, nenhum CPF real no git.

1. **Achatar o ninho** — FEITO (28/08/2026). Código morto está em `obsoleto/`.
2. **Um único script de start** apontando para a pilha certa. Remover `package.json` Express da raiz (`express` não é usado pelo produto).
3. **Cálculos com dados reais:**
   - Usar Voc, Isc, Vmpp, Impp, MPPT min/max do formulário — **não** Voc=45 V nem “10 módulos por string” inventados em `validate_system_compatibility`.
   - HSP (irradiação) por cidade/UF; hoje está 5,2 fixo, um arquivo diz Maranhão e outro Goiás.
   - Tensão e número de fases do cliente, não assumir 220 V monofásico sempre.
   - Não usar `dr_rating = max(30, corrente * 1.3)` em documento oficial (mistura A e mA).
   - Custo R$ 3,50/Wp e TIR por busca linear são estimativa grosseira — rotular como estimativa ou tirar do documento oficial.
4. **Quarto documento:** confirmar com o usuário qual é o 4º arquivo oficial (ART, declaração, diagrama, tabela de demanda). Parametrizar com `{{TOKEN}}` no mesmo gerador. Não inventar o template.
5. **PII fora do git:** `config_padrao.json` tem CPF, RG, telefone e e-mail reais do procurador. Mover para `.env` / `config_padrao.local.json`, gitignore, deixar placeholders no repo.
6. **Validar antes de gerar:** CPF/CNPJ, CEP, UC, nome, endereço, potências numéricas. Zod e react-hook-form já estão no `package.json` do frontend e não são usados.

---

## P2 — Qualidade de engenharia (1–2 meses)

1. Quebrar `App.jsx` (~1450 linhas) em abas/componentes.
2. Proxy Vite `/api` → backend; remover `http://localhost:5000` hardcoded. Hoje `vite.config.js` não tem proxy.
3. Testes: pytest no gerador (tokens, CPF, aliases) e nos cálculos; fixtures `cliente_001` / `dados_rosembergue`. Hoje **não há testes do projeto**.
4. Um `README.md` + um `QUICKSTART.md`. Arquivar os outros manuais contraditórios em `automacao-docs/` (caminhos `/home/ubuntu`, Python 3.10 vs 3.11, HSP divergente).
5. Remover dezenas de componentes shadcn não usados em `src/components/ui/`.
6. Mostrar `relatorio_preenchimento.txt` na UI (tokens que faltaram).
7. `requirements.txt` do backend antigo lista FastAPI, WeasyPrint, Playwright, matplotlib — não usados. Manter só o que o código importa. O backend antigo importa `flask_cors` e `flask_sqlalchemy` e o pin não lista esses pacotes.

---

## P3 — Expansão (só depois do núcleo estável)

Não começar por aqui.

- Catálogo de módulos/inversores (JSON ou SQLite) com autocomplete
- Lista de projetos na UI, reabrir, regenerar, lote (o CLI já gera lote em `saida/lote/`)
- Exportar PDF além de DOCX/XLSX
- Manter Ollama como extra; parser como padrão
- Área de conferência do responsável técnico / assinatura
- ART/TRT, AutoCAD, APIs ANEEL — documentação antiga promete isso; não bloqueia o uso diário

---

## Regras ao implementar

- Não criar segundo gerador. Estender `gerar_documentos.py`.
- Não preencher DOCX com `paragraph.text = ...` no fluxo oficial (quebra runs/formatação). Só XML/`{{TOKEN}}`.
- Não deixar `except: pass` em células Excel.
- Não commitar `.env`, `config_padrao.local.json`, `saida/`, `.venv`, `node_modules`.
- Não expandir escopo no meio do P0 (sem catálogo, sem IA obrigatória, sem redesign visual).
- Conferir o documento gerado contra o template oficial antes de declarar pronto.
- Se o usuário pedir “exploit/PoC” de path traversal: só o **fix** (sanitizar download).

---

## Referência rápida de arquivos

```
equatorial_automation_frontend/src/App.jsx          # UI
equatorial_automation_frontend/src/utils/txtParser.js
equatorial_automation_frontend/vite.config.js
backend/api_server.py
backend/gerar_documentos.py
backend/config_padrao.json                         # ainda contém PII — mover para local
templates/
dados/
saida/
iniciar.bat / start_all.bat                         # mesma pilha
obsoleto/                                           # não usar
```

Diagnóstico visual: canvas `roadmap-melhoria.canvas.tsx` no diretório de canvases do Cursor deste workspace.

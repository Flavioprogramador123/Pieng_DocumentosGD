# Checkpoint — 2026-08-30 (antes da integração MPPT/strings)

**Tag git sugerida para voltar:** commit deste checkpoint (`pre-mppt-integracao`)  
**Próximo trabalho planejado:** topologia MPPT/strings SAJ/DEYE no catálogo + `string_calculations.py`  
**Status deste checkpoint:** integração MPPT **ainda não iniciada** no código principal.

---

## Como restaurar

```bash
git log --oneline -5
git checkout <hash-deste-commit> -- .
# ou branch dedicada:
git checkout -b restore-pre-mppt <hash-deste-commit>
```

---

## Alterações incluídas neste marco

### Coordenadas (UTM ↔ graus decimais)
- `backend/coordinate_utils.py` — conversão WGS84/UTM
- `equatorial_automation_frontend/src/utils/coordinateUtils.js` — espelho frontend
- `App.jsx` — campo georreferenciado + sync on blur
- `txtParser.js` — lat/lon → UTM ao importar TXT
- `POST /api/coordinates/resolve`
- Testes: `coordinateUtils.test.js`, `txtParser.test.js`, `test_coordinate_utils.py`

### Trifásico (GO — 220 V FN, 380 V LL)
- `grid_voltage.py` — disjuntor tripolar
- `dados/normas_equatorial_go.json` — PD 63 A corrigido
- `gerar_documentos.py`, `nbr5410_calculations.py`, `system_calculations.py` — corrente micro I=P/220; strings √3×380
- `test_trifasico_calculations.py`

### UC / conta contrato (DXF)
- `normalize_conta_contrato()` / `format_conta_contrato()` em `gerar_documentos.py`
- Tokens: `CONTA_CONTRATO_DIGITOS`, `CONTA_CONTRATO_FORMATADA`
- `autocad_tokens.py` — normalização UC

### Figura de localização (memorial)
- `backend/figura_localizacao.py` — tiles osmde, zoom adaptivo (18 urbano / 16 rural ou OSM vazio)
- `FiguraLocalizacaoPreview.jsx` — preview + seletor zoom na UI
- `POST /api/figura-localizacao/preview`
- `FIGURA_MAP_ZOOM` / `FIGURA_MAP_TILE` em `.env.example`

### Startup
- `iniciar.bat` — prepara venv/npm, aguarda backend e frontend antes do browser
- `start_all.bat` — delega ao `iniciar.bat`

### Pesquisa MPPT (rascunho local — pasta `.temp/`, gitignored)
- `.temp/conhecimento_strings_mppt_saj_deye.md`
- `.temp/equipamentos_referencia.yaml`
- `.temp/exemplos_interacao_modulo_inversor.json`

---

## O que NÃO está neste checkpoint (próxima etapa)

- [ ] `strings_por_mppt` no `inversores.yaml` / SQLite
- [ ] Auto inteligente em `string_calculations.py` (topologia fabricante)
- [ ] Modelos 3K / 25K SAJ/DEYE no catálogo
- [ ] Módulos Risen 600/690 e TSUN 600 em `modulos_solares.yaml`
- [ ] Sugestão automática na UI ao escolher inversor do catálogo

---

## Regra de negócio confirmada (próxima integração)

| Faixa potência | Fase CA |
|----------------|---------|
| Até **10 kW** | Monofásico **220 V** |
| A partir de **12 kW** | Trifásico |

---

## Arquivos sensíveis — nunca commitados

`.env`, `config_padrao.local.json`, `saida/`, `data/catalog.db`, `.temp/`

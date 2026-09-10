# Changelog QDCA / Proteção CA — 2026-09-02

Registro detalhado para **reverter** alterações desta sessão, se necessário.

---

## Problema reportado

- **I projeto** nas fases A/B mostrava **38,35 A** (3 micros × 2,25 kW com ×1,25), mas disjuntor estava em **32 A** — inconsistência.
- Botões **Sugerir QDCA** / mudança de qtd micros **sobrescreviam** disjuntores e distribuição já preenchidos.
- **MPPT por inversor** não vinha como **4** por padrão para microinversores.

---

## Correções aplicadas (2026-09-02 — segunda rodada)

### Bug: Calcular sistema ignorava QDCA do formulário

**Causa:** `enrich_micro_layout_protection` substituía `phase_details` por `breaker_rows` sem os overrides do usuário. A tabela memorial usava 32 A, mas a aba Cálculos mostrava 40 A (calculado).

**Arquivos:**
- `backend/protection_hierarchy.py` — `breaker_rows` agora sincroniza disjuntor/bitola do formulário
- `backend/system_calculations.py` — aba Cálculos usa QDCA micro (32 A, 6 mm²) em vez de heurística da potência total (16 A, 16 mm², 80 A)

**Reverter:** restaurar `table['breaker_rows'] = rows` sem loop `synced_rows` em `protection_hierarchy.py`.

---

## Correções aplicadas (2026-09-02 — primeira rodada)

### 1. I projeto = corrente nominal (sem ×1,25)

| Arquivo | Mudança |
|---------|---------|
| `equatorial_automation_frontend/src/utils/qdcaLayout.js` | `estimatePhaseProjectCurrentA` e `estimateInverterProjectCurrentA` passam a retornar corrente **nominal** (P/V). O ×1,25 permanece só em `estimatePhaseBreakerA` para dimensionar disjuntor. |
| `backend/protection_hierarchy.py` | Tabela memorial usa `current_a` (nominal) como default de `corrente_projeto_a`; string idem com `current_nominal_a`. |

**Exemplo 8 micros, 2,25 kW, 220 V, fase com 3 micros:**
- Antes: I projeto = **38,35 A**
- Depois: I projeto = **30,68 A**; disjuntor sugerido = **40 A** (se campo vazio)

### 2. Não sobrescrever campos já preenchidos

| Arquivo | Mudança |
|---------|---------|
| `StringsQdcaSection.jsx` | `applyAutoQdca` usa `mergeSuggestedQdcaFields` (só preenche vazios). |
| `StringsQdcaSection.jsx` | `updatePhaseMicros` atualiza I projeto ao mudar qtd, mas **não altera disjuntor** se já preenchido. |
| `StringsQdcaSection.jsx` | `rebalancePhases` usa merge para disjuntores; correntes recalculadas (derivadas da nova distribuição). |

### 3. MPPT default 4 para micro

| Arquivo | Mudança |
|---------|---------|
| `StringsQdcaSection.jsx` | Ao selecionar tipo **MICRO**, define `num_mppt: '4'` se vazio ou ainda `'2'`. |
| `App.jsx` | Cálculo DC com topologia `micro` sugere `num_mppt: 4` quando campo vazio. |

---

## Como reverter cada ponto

### Reverter I projeto (voltar ×1,25 na coluna)

Em `qdcaLayout.js`, restaurar em `estimatePhaseProjectCurrentA`:

```javascript
const iProj = iMicro * q * 1.25
return iProj.toFixed(2).replace('.', ',')
```

Em `protection_hierarchy.py` linha ~259, trocar `row['current_a']` de volta para `row['current_design_a']`.

String (~307): `round(i_des, 2)` em vez de `round(i_nom, 2)`.

### Reverter merge (voltar a sobrescrever tudo)

Em `StringsQdcaSection.jsx` `applyAutoQdca`:

```javascript
setTechnicalData((prev) => ({ ...prev, ...patch }))
```

Em `updatePhaseMicros`, sempre setar `disjKey` com `estimatePhaseBreakerA`.

### Reverter MPPT default

Remover bloco `num_mppt: '4'` em `StringsQdcaSection.jsx` e lógica micro em `App.jsx`.

---

## Arquivos tocados nesta correção

```
equatorial_automation_frontend/src/utils/qdcaLayout.js
equatorial_automation_frontend/src/components/StringsQdcaSection.jsx
equatorial_automation_frontend/src/App.jsx
backend/protection_hierarchy.py
docs/CHANGELOG_QDCA_2026-09-02.md  (este arquivo)
CHANGELOG.md  (entrada resumida)
```

---

## Sessão anterior (contexto — já implementado antes desta correção)

Peças criadas/alteradas na sessão QDCA completa (para rollback maior):

| Peça | Arquivo |
|------|---------|
| Engine tabela proteção | `backend/protection_hierarchy.py` |
| Layout micro por disjuntor | `backend/qdca_layout.py` |
| Textos memorial corrente | `backend/memorial_current_text.py` |
| Tokens DOCX | `backend/gerar_documentos.py` |
| UI QDCA | `equatorial_automation_frontend/src/components/StringsQdcaSection.jsx` |
| Utils FE | `equatorial_automation_frontend/src/utils/qdcaLayout.js` |
| Defaults form | `equatorial_automation_frontend/src/utils/formDefaults.js` |
| Testes | `backend/test_protection_hierarchy.py`, `test_micro_qdca.py`, `test_memorial_current_text.py` |

Para desfazer a feature QDCA inteira: reverter commits que tocaram esses arquivos ou restaurar do checkpoint `0.5.6` em `CHANGELOG.md`.

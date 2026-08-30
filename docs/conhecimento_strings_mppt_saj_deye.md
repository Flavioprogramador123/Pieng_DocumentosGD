# Conhecimento — Strings CC / MPPT (SAJ & DEYE)

> **Status:** integrado parcialmente em `string_calculations.py`, `string_topology.py`, catálogo SQLite.  
> **Data:** 2026-08-30 (atualizado)  
> **Norma de referência:** **NT.00020.EQTL** (Equatorial — PRODIST Módulo 3)  
> **Fontes:** datasheets SAJ R6-S3, R6-T2, M2-S4; DEYE G06P3; módulos Risen/TSUN.

---

## 0. Micro-inversor × Inversor string (NT.00020.EQTL)

Esta distinção **não** depende da potência nominal em kW. Depende da **topologia CC** e do **tipo de equipamento**.

### Micro-inversor

| Aspecto | Característica |
|---------|----------------|
| Topologia CC | **1 módulo por entrada MPPT/string** |
| Instalação | Equipamento **junto ao módulo** (no telhado/estrutura) |
| Tensão CC | Próxima à do módulo (dezenas de V — ex. Vmpp ~35–50 V) |
| Corrente CC | ≈ **Isc / Impp do próprio módulo** (não soma strings longas) |
| Tensão máx. típica | Baixa (ex. Vdc máx ~60 V no SAJ M2) |
| CA | Até **3 micros em série** por disjuntor (correntes CA somam) |

### Inversor string / central

| Aspecto | Característica |
|---------|----------------|
| Topologia CC | **2 ou mais módulos em série por string** |
| Instalação | Inversor centralizado (parede/garagem); cabos CC longos |
| Tensão CC | **N × Vmpp / N × Voc** — pode **ultrapassar 1000 V CC** |
| Corrente CC | Isc da string (paralelos no MPPT somam corrente) |
| Risco / cuidados | Tensões CC elevadas exigem **proteção, seccionamento, aterramento e rotulagem** conforme NT.00020.EQTL |
| Token planta | `{{TIPO_EQUIPAMENTO_INVERSOR}}` → **Inversor** |

### Como o sistema classifica

1. **Campo `tipo_inversor`** no formulário/catálogo (`MICRO` vs `STRING`) — prioridade.
2. **`modulos_por_string` > 1** → sempre inversor string.
3. **Catálogo/datasheet:** `micros_max_disjuntor_ca`, Vdc máx ≤ ~80 V, modelo M2/micro.
4. **Não usar** potência kW como critério (ex.: SAJ 25 kW é string mesmo com poucos módulos).

---

## 1. O que o bloco da UI representa

O bloco **Strings CC / MPPT** (`modulos_por_string`, `strings_por_mppt`, `num_mppt`, `tipo_inversor`) define a **topologia elétrica CC real** do projeto:

| Grandeza | Em série | Em paralelo (mesmo MPPT) |
|----------|----------|---------------------------|
| Tensão (Voc, Vmpp) | **Soma** | Igual |
| Corrente (Isc, Impp) | Igual | **Soma** |

Isso alimenta:
- textos do memorial (`CONFIGURACAO_STRINGS_CC`, proteções CC/CA)
- corrente de projeto por MPPT (`Isc × strings_paralelo × 1,25`)
- validação Vmpp/Voc vs faixa MPPT do inversor
- dimensionamento de cabos e disjuntores

**Micro:** 1 módulo por entrada MPPT (equipamento no módulo); tensão/corrente CC ≈ do módulo; ver §0.

**String/central:** N ≥ 2 módulos em série por string; tensões CC elevadas (>1000 V possível); cuidados NT.00020.EQTL; ver §0.

---

## 2. Lacunas remanescentes (`string_calculations.py`)

1. ~~**Modo Auto** faz `ceil(qtd_módulos / (num_mppt × qtd_inversor))`~~ — parcialmente corrigido via `string_topology.py` + catálogo.
2. **`inversores.yaml`** — `strings_por_mppt` e Icc por MPPT já importados; validar todos os modelos.
3. **MPPT mistos** (DEYE 15K `2/1+2`) — modelados via `strings_por_mppt_json`.
4. **Classificação micro × string** — baseada em tipo de equipamento + módulos/string (NT.00020.EQTL), não em kW.

---

## 3. Inversores pesquisados (resumo datasheet)

### 3.1 SAJ monofásico string — série R6-S3

| Modelo | Pnom AC | Wp máx | MPPT | Strings/MPPT | Vmppt (V) | Vdc máx | Icc MPPT (A) |
|--------|---------|--------|------|--------------|-----------|---------|--------------|
| R6-3K-S3 | 3 kW | 4,5 kWp | **3** | **1/1/1** | 90–550 | 600 | 16 |
| R6-6K-S3 | 6 kW | 9 kWp | **3** | **1/1/1** | 90–550 | 600 | 16 |

**Uso típico residencial:**
- **3 kW:** 1 string única (6–8 módulos 550–600 W) ligada a **1 MPPT**; os outros MPPT podem ficar vazios.
- **6 kW:** **2 ou 3 strings** independentes (ex.: 12 módulos → 2×6 ou 3×4), **1 string por MPPT**, sem paralelo no mesmo MPPT.

### 3.2 SAJ trifásico string — R6-25K-T2-32

| Modelo | Pnom AC | Wp máx | MPPT | Strings/MPPT | Vmppt (V) | Vdc máx | Icc MPPT (A) |
|--------|---------|--------|------|--------------|-----------|---------|--------------|
| R6-25K-T2-32 | 25 kW | 37,5 kWp | **2** | **2/2** | 180–1000 | 1100 | 32 |

Até **4 strings** no inversor (2 por MPPT). Paralelo no mesmo MPPT **dobra Isc** — verificar limite 32 A.

### 3.3 SAJ micro — M2-2.25K-S4

| Parâmetro | Valor |
|-----------|-------|
| Pnom AC | 2,25 kW (2250 W) |
| Entradas MPPT | **4** (1 módulo/entrada) |
| Módulo recomendado | 400–700+ Wp |
| Vmppt | 35–50 V (manual EU) / 28–45 V (revenda BR) |
| Vdc máx | 60 V |
| Icc entrada | 20 A × 4 |
| Micros por ramal CA (10 AWG) | **máx. 3** unidades |

### 3.4 DEYE trifásico — SUN-xK-G06P3-EU-AM2

| Modelo | Pnom AC | Wp máx | MPPT | Strings/MPPT | Vmppt (V) | Vdc máx | Icc oper. (A) |
|--------|---------|--------|------|--------------|-----------|---------|---------------|
| SUN-3K-G06P3 | 3 kW | 4,5 kWp | **2** | **1+1** | 120–1000 | 1100 | 13+13 |
| SUN-6K-G06P3 | 6 kW | 9 kWp | **2** | **1+1** | 120–1000 | 1100 | 13+13 |
| SUN-15K-G06P3 | 15 kW | 22,5 kWp | **2** | **1+2** | 120–1000 | 1100 | 20+26 |
| SUN-25K-G06P3 | 25 kW | 37,5 kWp | **2** | **2+2** | 200–1000 | 1100 | 54+48 |

Notação `1+2` = MPPT-A com 1 string, MPPT-B com 2 strings em paralelo.

### 3.5 DEYE micro — SUN2000G4 / S2.25K-G4 (já no YAML)

Similar ao SAJ: 4 MPPT, 1 módulo/MPPT, ~2,25 kW CA.

---

## 4. Módulos de referência (600 Wp e 690 Wp)

### Risen RSM120-8-600BMDG (600 Wp PERC bifacial)

| Voc | Isc | Vmpp | Impp | Fusível série |
|-----|-----|------|------|---------------|
| 41,70 V | 18,26 A | 34,80 V | 17,25 A | 30 A |

### Risen RSM132-8-690BHDG (690 Wp HJT bifacial)

| Voc | Isc | Vmpp | Impp | Fusível série |
|-----|-----|------|------|---------------|
| 49,65 V | 17,66 A | 41,63 V | 16,60 A | 35 A |

### TSUN TS600S8E-132GANT (600 Wp N-Type) — alternativa BR

| Voc | Isc | Vmpp | Impp |
|-----|-----|------|------|
| 48,28 V | 15,84 A | 40,16 V | 14,94 A |

> **690 Wp TSUN:** linha comercial chega ~680 Wp (TS660–680S9); usar Risen 690 W ou TSUN 625 W como proxy até datasheet 690 W local.

---

## 5. Exemplos de interação módulo × inversor

### 5.1 Residencial 4,8 kWp — SAJ R6-3K-S3 + 8× Risen 600 W

| Item | Valor |
|------|-------|
| Topologia | 1 string, 8 módulos série, **1 MPPT usado** |
| Vmpp string | 8 × 34,8 = **278,4 V** ✓ (90–550) |
| Voc string (cold) | ~8 × 41,7 = **333,6 V** ✓ (< 600) |
| Isc string | **18,26 A** ⚠ **> 16 A** limite SAJ 3K |

**Conclusão:** Risen 600 W (Isc 18,26 A) **excede** Icc 16 A do R6-S3. Preferir TSUN 600 (Isc 15,84 A) ou validar com fabricante / usar inversor com Icc ≥ 18 A.

**UI sugerida:** `modulos_por_string=8`, `strings_por_mppt=1`, `num_mppt=3` (só 1 MPPT ocupado).

### 5.2 Residencial 7,2 kWp — SAJ R6-6K-S3 + 12× Risen 600 W

| Item | Valor |
|------|-------|
| Topologia | **2 strings × 6 módulos** (MPPT1 + MPPT2) ou 3×4 |
| Vmpp/string (6 s) | 208,8 V ✓ |
| Isc/string | 18,26 A ⚠ mesmo problema Icc |

Com **TSUN 600:** 2 strings × 6 mód = 7,2 kWp; Isc 15,84 A ✓.

**UI:** `modulos_por_string=6`, `strings_por_mppt=1`, `num_mppt=3`.

### 5.3 Comercial ~24,8 kWp — SAJ R6-25K-T2 + 36× Risen 690 W

| Item | Valor |
|------|-------|
| Topologia | 4 strings × 9 módulos; **2 strings/MPPT** |
| Vmpp/string | 9 × 41,63 = **374,7 V** ✓ |
| Voc string | 9 × 49,65 = **446,9 V** ✓ |
| Isc por MPPT (2 par.) | 2 × 17,66 = **35,32 A** ⚠ **> 32 A** |

**Conclusão:** 2 strings de 690 W em paralelo no mesmo MPPT estoura 32 A. Opções: 1 string/MPPT (9+9 módulos nos 2 MPPT = 18 mód), ou módulo com Isc menor, ou menos strings paralelas.

### 5.4 Micro — SAJ M2-2.25K-S4 + 4× Risen 690 W (1 equipamento)

| Item | Valor |
|------|-------|
| Topologia | 4 módulos, 1 por MPPT |
| Vmpp entrada | 41,63 V ✓ (35–50) |
| Impp | 16,6 A ✓ (< 20 A) |
| Pdc | 4 × 690 = 2,76 kWp → limitado a **2,25 kW** AC (clipping) |

**CA:** até 3 micros em série por disjuntor → corrente grupo ≈ 3 × 9,78 A ≈ 29,3 A.

### 5.5 DEYE SUN-6K-G06P3 + 12× TSUN 600 W

| Item | Valor |
|------|-------|
| Topologia | 2 strings × 6 módulos (**1+1** nos 2 MPPT) |
| Vmpp/string | 6 × 40,16 = 241 V ✓ |
| Isc/string | 15,84 A ✓ (< 13+13 por MPPT — OK) |

---

## 6. Proposta de adaptação ao sistema (após aprovação)

### 6.1 Catálogo (`dados/inversores.yaml` + SQLite)

Adicionar por inversor:

```yaml
entrada_cc:
  numero_mppts: 2
  strings_por_mppt: "1+1"      # ou [1,1] ou [2,2]
  strings_por_mppt_max: 2      # máx paralelo por MPPT
  corrente_entrada_cc_max_a_por_mppt: [13, 13]
  modulos_serie_min: 3           # opcional, do manual
  modulos_serie_max: 18        # calculado Voc/Vmppt
```

### 6.2 Motor de cálculo (`string_calculations.py`)

1. **Prioridade:** dados do catálogo > campos manuais UI > heurística Auto.
2. **Auto inteligente:** distribuir módulos em strings respeitando `strings_por_mppt` e limites Voc/Vmpp/Isc.
3. **Modos MPPT:** simples (1 str/MPPT), paralelo (2 str/MPPT), misto (array por MPPT).
4. **Alertas explícitos:** Icc MPPT, Voc cold (+ temperatura), clipping AC micro.

### 6.3 UI (`App.jsx`)

- Ao selecionar inversor no catálogo → preencher `num_mppt`, sugerir `modulos_por_string` e `strings_por_mppt`.
- Modo **Auto** mostra preview editável antes de gerar documentos.
- Exibir tabela: MPPT1..N → strings → módulos → Voc/Vmpp/Isc.

### 6.4 Import SQLite

Campos novos na tabela `inversores`: `strings_por_mppt`, `icc_mppt_a`, `topologia_mppt_json`.

---

## 7. Referências

- SAJ R6 3–10K S3 datasheet (3 MPPT, 1/1/1, Icc 16 A)
- SAJ R6-25K-T2-32 (2 MPPT, 2/2, Icc 32 A)
- SAJ M2-2.25K-S4 user manual EU
- DEYE SUN-(3–15)K-G06P3 datasheet (2/1+1, 2/1+2)
- DEYE SUN-(18–25)K-G06P3 (2/2+2)
- Risen RSM120-600 / RSM132-690 datasheets
- TSUN TS600S8E-132GANT spec BR

---

## 8. Arquivos relacionados nesta pasta

- `equipamentos_referencia.yaml` — dados estruturados para importação futura
- `exemplos_interacao_modulo_inversor.json` — casos numéricos para testes pytest

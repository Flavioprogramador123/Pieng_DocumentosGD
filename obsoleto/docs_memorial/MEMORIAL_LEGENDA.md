# Memorial descritivo — legenda de marcadores

Arquivo: `templates/MEMORIAL_DESCRITIVO_marcadores.docx`

## Convenção original (documento-base)

| Marcação | Significado | No gerador |
|----------|-------------|------------|
| `**texto**` | **Variável** — valor que vem do formulário/TXT/YAML | Deve virar `{{TOKEN}}` no template |
| `+ texto +` | **Campo calculado** — fórmula/engenharia, pode ir para temp e depois ao DOCX | Deve virar `{{TOKEN_CALCULADO}}` ou texto derivado em `build_values()` |

O gerador oficial (`backend/gerar_documentos.py`) só substitui **`{{NOME_DO_TOKEN}}`**.  
Marcadores `**` e `+...+` **não são preenchidos automaticamente** — são resíduos do documento-base antes da parametrização.

---

## Estado atual (28/08/2026 — patch aplicado)

| Tipo | Quantidade | Status |
|------|------------|--------|
| Tokens `{{...}}` no XML | **87** | ✅ Patch `patch_memorial_legado.py` aplicado |
| Marcadores `**` legados | **0** | ✅ Convertidos |
| Blocos `+...+` (cálculo) | **0** | ✅ Convertidos em tokens calculados |

Backup automático: `templates/MEMORIAL_DESCRITIVO_marcadores.docx.bak_*`

Lista extraída: `dados/memorial_linhas_marcadas.txt`  
JSON resumido: `dados/memorial_legenda_marcadores.json`

---

## Tokens oficiais já no template (65)

Estes **já estão corretos** — mapeados em `LABEL_ALIASES` / `create_txt_data()` / catálogo:

`ACIONAMENTO_DISJUNTOR`, `ANO_DOCUMENTO`, `BITOLA_CABO_CA`, `BITOLA_CABO_CC`, `BITOLA_CABO_PADRAO`, `CAPACIDADE_INT_DISJUNTOR`, `CIDADE`, `CONTA_CONTRATO`, `COORDENADA_UTM_X`, `COORDENADA_UTM_Y`, `CORRENTE_ENTRADA`, `CORRENTE_MAX_CC_INVERSOR`, `CORRENTE_MAX_SAIDA_CA_INVERSOR`, `CORRENTE_NOMINAL_DISJUNTOR`, `CPF`, `CURVA_ATUACAO_DISJUNTOR`, `DESCRICAO_POLOS_DISJUNTOR`, `EFICIENCIA_MAX_INVERSOR`, `ELEMENTO_PROTECAO_DISJUNTOR`, `ENDERECO_COMPLETO`, `ESTADO_CONCESSAO`, `FABRICANTE_INVERSOR`, `FABRICANTE_MODULO`, `FAIXA_FREQUENCIA_INVERSOR`, `FAIXA_TENSAO_CA_INVERSOR`, `FAIXA_TENSAO_INVERSOR`, `FAIXA_TENSAO_MPPT_INVERSOR`, `FATOR_POTENCIA`, `FATOR_POTENCIA_INVERSOR`, `FREQUENCIA_DISJUNTOR`, `FREQUENCIA_NOMINAL_INVERSOR`, `FUSO_UTM`, `MES_DOCUMENTO`, `MODELO_INVERSOR`, `NOME_CLIENTE`, `NOME_RESP_TECNICO`, `NUM_FASES`, `NUM_POLOS_DISJUNTOR`, `NUM_POSTE`, `POTENCIA_DISPONIBILIZADA_FORMATADA`, `POTENCIA_DISP_KVA`, `POTENCIA_DISP_KW`, `POTENCIA_GERACAO`, `POTENCIA_GERADOR`, `POTENCIA_INVERSOR_TOTAL`, `POTENCIA_INVERSOR_UNITARIO`, `POTENCIA_MAX_CC_INVERSOR`, `POTENCIA_MAX_SAIDA_CA_INVERSOR`, `POTENCIA_MODULO`, `QTD_CONDUTORES_FASE`, `QTD_CONDUTORES_NEUTRO`, `QTD_ENTRADAS_MPPT_INVERSOR`, `QTD_INVERSORES`, `QTD_MODULOS`, `REGISTRO_PROFISSIONAL`, `TABELA_DEMANDA`, `TENSAO_ATENDIMENTO_FORMATADA`, `TENSAO_MAX_CC_INVERSOR`, `TENSAO_NOMINAL`, `TENSAO_NOMINAL_CA_INVERSOR`, `TENSAO_NOMINAL_DISJUNTOR`, `THD_CORRENTE_INVERSOR`, `TIPO_REDE`, `TITULO_PROFISSIONAL`, `UF`

**Pendentes de dado de campo:** `COORDENADA_UTM_X`, `COORDENADA_UTM_Y`, `NUM_POSTE`

---

## Trechos `**` ainda não convertidos → DE/PARA

| Linha (aprox.) | Texto legado `**...**` | Token alvo | Origem do valor |
|----------------|------------------------|------------|-----------------|
| L0010 | `220/380 V` | `{{TENSAO_ATENDIMENTO_FORMATADA}}` | UC / catálogo padrão UF |
| L0010 | `AUTOCONSUMO LOCAL` | `{{MODALIDADE_COMPENSACAO}}` | UC (default em `build_values`) |
| L0186 | `Residencial` | `{{CLASSE_CONSUMO}}` | UC `classe` |
| L0253 | `4,50 kW` | `{{POTENCIA_INVERSOR_TOTAL}} kW` | qtd × potência inversor |
| L0259 | `63 A` (IDG) | `{{CORRENTE_ENTRADA}} A` | disjuntor entrada |
| L0260 | `3` (NF) | `{{NUM_FASES}}` | tipo ligação |
| L0262 | `63`, `3`, `38.253,6 W` | `{{CORRENTE_ENTRADA}}`, `{{NUM_FASES}}`, `{{POTENCIA_DISP_KW_W}}` | fórmula PD em `build_values` |
| L0266 | `220 V` | `{{TENSAO_NOMINAL}} V` | tensão atendimento |
| L0266 | `micro inversores monofásicos` | `{{DESCRICAO_TIPO_INVERSOR}}` | catálogo / `tipo_inversor` |
| L0332 | `49,8` | `{{TENSAO_CIRCUITO_ABERTO}}` | catálogo módulo (Voc) |
| L0334 | `14,5` | `{{CORRENTE_CURTO_CIRCUITO}}` | catálogo módulo (Isc) |
| L0336 | `41,0` | `{{TENSAO_MAX_POTENCIA}}` | catálogo módulo (Vmpp) |
| L0338 | `16,8` | `{{CORRENTE_MAX_POTENCIA}}` | catálogo módulo (Impp) |
| L0340 | `22,0` | dimensão módulo | `{{COMPRIMENTO_MODULO}}` ou similar |
| L0342 | `80` | peso módulo | `{{PESO_MODULO}}` |
| L0357 | `2` | `{{QTD_INVERSORES}}` | formulário |
| L0408 | `220` | `{{TENSAO_NOMINAL_DPS}}` ou CA | DPS / tensão |
| L0409 | `32` | `{{CORRENTE_PROTECAO_CA}}` | DPS tabela |
| L0447 | `14,98 A` | `{{CORRENTE_CURTO_CIRCUITO}} A` | Isc módulo |
| L0453 | `10 A x 2 = 20 A` | `{{CALCULO_CORRENTE_CA}}` | calculado |

Parágrafos de **proteção QDCA / margem / disjuntor 63 A** (L0267–L0317): texto misturado `**` + `+` — substituir por tokens calculados abaixo.

---

## Trechos `+...+` (cálculo) → DE/PARA

| Texto legado | Token calculado proposto | Onde calcular |
|--------------|--------------------------|---------------|
| `+ AQUI VAI COLOCAR O CALCULO CORRENTE DO SISTEMA +` | `{{CALCULO_CORRENTE_SISTEMA}}` | `system_calculations.corrente_ac_a` → texto formatado em `build_values` |
| `+ AQUI VAI COLOCAR O CALCULO CORRENTE POR INVEROSR +` | `{{CALCULO_CORRENTE_INVERSOR}}` | corrente AC ÷ `QTD_INVERSORES` |
| `+Figura tirado do maps da localização do imóvel+` | `{{FIGURA_LOCALIZACAO}}` | **Manual** — imagem inserida pelo RT (não automatizar) |
| `+Configuração: Circuito trifásico a 4 condutores...` | `{{DESCRICAO_CIRCUITO_PADRAO}}` | derivado de `TIPO_REDE` + `QTD_CONDUTORES_*` |

Outros textos de engenharia ainda hardcoded (sem `+` fechado):

- Margem de segurança 36,1% → `{{MARGEM_SEGURANCA_DISJUNTOR}}`
- Disjuntor recomendado 25 A → `{{DISJUNTOR_RECOMENDADO_QDCA}}`
- Imáx-ca × qtd inversores → `{{CALCULO_CORRENTE_INVERSORES_TOTAL}}`

Cálculos já existem em `backend/system_calculations.py` (`corrente_ac_a`, `disjuntor_recomendado_a`, bitolas). Falta **repassar para tokens** antes de gerar o DOCX.

---

## Fluxo alvo

```
Formulário / YAML / TXT
    → form_mapper + token_enrichment (catálogo)
    → system_calculations (temp: correntes, cabos, disjuntor)
    → build_values() merge tokens + calculados
    → gerar_documentos.py substitui {{TOKEN}} no DOCX
```

---

## Como revalidar marcadores

```bat
cd backend
.venv\Scripts\python.exe extrair_marcadores_memorial.py
.venv\Scripts\python.exe analyze_memorial_gaps.py
```

---

## Próximo passo técnico

1. Rodar `patch_memorial_legado.py` (quando criado) para trocar `**` e `+...+` restantes por `{{TOKEN}}`.
2. Estender `build_values()` com tokens calculados listados acima.
3. Conferir documento gerado em `saida/` contra este mapa.

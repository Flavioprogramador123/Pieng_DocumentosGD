# Memorial descritivo — cobertura de tokens

Gerado por `backend/analyze_memorial_gaps.py` (YAML padrão + catálogo Jinko/Growatt + demanda 4,5 kW).

## Resultado atual

| Métrica | Valor |
|---------|-------|
| Tokens no template | 65 |
| Preenchidos automaticamente | **62** |
| Pendentes (campo obrigatório no local) | **3** |

## Tokens que ainda precisam de dados de campo

| Token | Onde obter |
|-------|------------|
| `COORDENADA_UTM_X` | Levantamento topográfico / Google Earth Pro / app GPS |
| `COORDENADA_UTM_Y` | Idem |
| `NUM_POSTE` | Visita técnica / concessionária / projeto elétrico |

Preencha no formulário (aba Cliente / Dados Técnicos) ou no YAML:

```yaml
unidade_consumidora:
  num_poste: "123456"
  coordenada_utm_x: "654321,00"
  coordenada_utm_y: "8234567,00"
  fuso_utm: "22S"
```

## O que passa a ser preenchido automaticamente

- **Módulos:** Voc, Isc, Vmpp, Impp, eficiência, dimensões, peso, potência total (catálogo SQLite).
- **Inversores:** MPPT, CC/CA, THD, fator de potência, strings, eficiência (catálogo + defaults).
- **Padrão de entrada:** disjuntor, DPS, curva, bitola, DR (catálogo por UF/ligação).
- **Demanda:** Tabela 1 gerada quando `demanda_alvo_kw` está preenchido.
- **Derivados:** potência disponibilizada kVA/kW, tipo de rede, fases, endereço completo.

## Como revalidar

```bat
cd backend
.venv\Scripts\python.exe analyze_memorial_gaps.py
```

Consulte `dados/memorial_tokens_pendentes.json` para lista atualizada.

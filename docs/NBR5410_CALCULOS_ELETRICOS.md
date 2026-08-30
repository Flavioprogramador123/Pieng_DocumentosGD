# Cálculos Elétricos conforme NBR 5410

## Regras Implementadas no Sistema

Este documento detalha as correções implementadas nos cálculos elétricos do sistema para conformidade com a **NBR 5410** e estratégias corretas de distribuição de carga.

---

## 1. MICROINVERSORES — Regras Críticas

### 1.1 Limitação de Série

**REGRA**: Máximo **3 microinversores em SÉRIE** por fase.

**Motivo**: Limitação técnica de tensão acumulada e proteção contra sobretensão.

**Implementação**:
```python
if micros_per_phase > 3:
    warnings.append(
        f'⚠️  ATENÇÃO: {micros_per_phase} microinversores por fase excede '
        f'limite de 3 em série. Reconfigurar ou usar inversor string.'
    )
```

### 1.2 Soma de Correntes em Série

**REGRA**: Correntes CA **SOMAM** quando microinversores estão em série.

**Fórmula**:
```
I_fase = I_micro × quantidade_série
```

**Exemplo**:
- 3 microinversores de 500W em série, 220V
- I_micro = 500W / 220V = 2,27 A
- I_fase = 2,27 A × 3 = **6,82 A**

**Código**:
```python
i_micro = power_per_micro_w / voltage_v
i_per_phase = i_micro * num_devices  # Série: correntes somam
```

---

## 2. DISTRIBUIÇÃO EM REDE TRIFÁSICA

### 2.1 Balanceamento de Fases

**REGRA**: Em rede trifásica, distribuir microinversores nas **3 fases** de forma balanceada.

**Estratégia**:
```
micros_por_fase = TETO(total_microinversores / 3)
```

**Exemplo Real**:
- 9 microinversores de 500W em rede trifásica 220V
- Distribuição: **3 micro/fase** (9 ÷ 3 = 3)
- Cada fase: 3 em série
- Corrente por fase: 2,27 A × 3 = **6,82 A**
- Corrente total: 6,82 A × 3 fases = **20,45 A**

**Código**:
```python
micros_per_phase = math.ceil(num_devices / 3)

if system_type == 'trifasico':
    i_per_phase = i_micro * min(micros_per_phase, 3)
    i_total = i_per_phase * 3
```

### 2.2 Mais de 3 Microinversores por Fase

Se `micros_per_phase > 3`, o sistema cria **grupos em paralelo**:

**Exemplo**:
- 12 microinversores em rede trifásica
- Por fase: 12 ÷ 3 = **4 microinversores**
- Configuração: **3 em série + 1 em paralelo** (ou 2 grupos de 2)
- Aviso: ⚠️ Excede limite de 3 em série

**Código**:
```python
series_per_phase = 3
parallel_groups = math.ceil(micros_per_phase / 3)
i_per_phase = i_micro * series_per_phase * parallel_groups
```

---

## 3. INVERSORES STRING — Compatibilidade de Rede

### 3.1 Regra Crítica

**INVERSOR MONOFÁSICO** → **SOMENTE** rede monofásica
**INVERSOR TRIFÁSICO** → **SOMENTE** rede trifásica
**INVERSOR BIFÁSICO** → **SOMENTE** rede bifásica

### 3.2 Validação Automática

O sistema **BLOQUEIA** configurações incompatíveis:

**Exemplo de Erro**:
```
❌ ERRO: Inversor MONOFÁSICO não pode ser conectado em rede TRIFÁSICA.
Use inversor trifásico ou altere a rede para monofásica.
```

**Código**:
```python
if 'mono' in inverter_type and 'mono' not in network_type:
    return {
        'compatible': False,
        'status': 'ERRO',
        'message': 'Inversor MONOFÁSICO não pode conectar em rede TRIFÁSICA.'
    }
```

---

## 4. CÁLCULO DE CORRENTE CA — NBR 5410

### 4.1 Fórmulas por Tipo de Sistema

#### **Monofásico** (127V ou 220V)
```
I = P / V
```

**Exemplo**:
- P = 5000 W (5 kW)
- V = 220 V
- I = 5000 / 220 = **22,73 A**

#### **Bifásico** (220V entre fases)
```
I = P / V
I_por_fase = I / 2
```

**Exemplo**:
- P = 5000 W
- V = 220 V
- I_total = 5000 / 220 = 22,73 A
- I_por_fase = 22,73 / 2 = **11,36 A**

#### **Trifásico** (220V ou 380V linha-linha)
```
I = P / (V_LL × √3)
I_por_fase = I / 3
```

**Onde**:
- V_LL = tensão linha-linha (220V ou 380V)
- √3 ≈ 1,732

**Exemplo** (Goiás — 380V):
- P = 10.000 W (10 kW)
- V_LL = 380 V
- I_total = 10.000 / (380 × 1,732) = **15,19 A**
- I_por_fase = 15,19 / 3 = **5,06 A**

### 4.2 Implementação no Código

```python
def calculate_ac_current_nbr5410(power_kw, voltage_v, system_type, topology, num_devices):
    power_w = power_kw * 1000

    if topology == 'micro':
        # Lógica de microinversores (seção 1 e 2)
        ...
    else:  # String
        if system_type == 'trifasico':
            i_total = power_w / (voltage_v * math.sqrt(3))
            i_per_phase = i_total / 3
        elif system_type == 'bifasico':
            i_total = power_w / voltage_v
            i_per_phase = i_total / 2
        else:  # monofasico
            i_total = power_w / voltage_v
            i_per_phase = i_total

    return {
        'current_total_a': i_total,
        'current_per_phase_a': i_per_phase,
        'formula': ...,
        'distribution': ...,
    }
```

---

## 5. DIMENSIONAMENTO DE DISJUNTOR POR FASE

### 5.1 Fator de Segurança NBR 5410

**Regra**: Disjuntor deve suportar corrente nominal × fator de segurança **1,25**.

```
I_disjuntor = I_por_fase × 1,25
```

### 5.2 Valores Comerciais Padronizados

```python
[10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 150, 200, 250, 300] # Amperes
```

**Seleção**: Primeiro valor comercial **≥** I_disjuntor calculado.

**Exemplo**:
- I_por_fase = 45 A
- I_disjuntor = 45 × 1,25 = 56,25 A
- Valor comercial: **63 A**

### 5.3 Código

```python
def calculate_breaker_per_phase(current_per_phase_a, safety_factor=1.25):
    i_design = current_per_phase_a * safety_factor
    standard_breakers = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 150, 200, 250, 300]
    breaker_rated = next((b for b in standard_breakers if b >= i_design), 300)

    return {
        'current_design_a': round(i_design, 2),
        'breaker_rated_a': breaker_rated,
        'breaker_standard': f'{breaker_rated}A',
    }
```

---

## 6. EXEMPLOS PRÁTICOS

### Exemplo 1: 9 Microinversores 500W — Rede Trifásica 220V

**Dados**:
- 9 microinversores × 500W = 4,5 kW
- Rede: Trifásica 220V

**Distribuição**:
- 3 fases
- 9 ÷ 3 = **3 microinversores por fase**
- Configuração: **3 em série por fase** (máximo permitido)

**Cálculos**:
```
I_micro = 500W / 220V = 2,27 A
I_por_fase = 2,27 A × 3 = 6,82 A
I_total = 6,82 A × 3 fases = 20,45 A
```

**Disjuntor**:
```
I_disjuntor = 6,82 A × 1,25 = 8,53 A
Valor comercial: 10 A (por fase)
```

**Status**: ✅ OK — 3 microinversores em série está dentro do limite.

---

### Exemplo 2: Inversor String 10kW Trifásico — Rede Trifásica 380V (GO)

**Dados**:
- 1 inversor trifásico × 10 kW
- Rede: Trifásica 380V (Goiás)

**Cálculos**:
```
I_total = 10.000W / (380V × √3) = 10.000 / 657,7 = 15,19 A
I_por_fase = 15,19 A / 3 = 5,06 A (balanceado)
```

**Disjuntor**:
```
I_disjuntor = 15,19 A × 1,25 = 18,99 A
Valor comercial: 20 A (tripolar)
```

**Fórmula usada**: `I = P / (V × √3)`

**Status**: ✅ OK — Inversor trifásico compatível com rede trifásica.

---

### Exemplo 3: 15 Microinversores 500W — Rede Trifásica 220V ⚠️

**Dados**:
- 15 microinversores × 500W = 7,5 kW
- Rede: Trifásica 220V

**Distribuição**:
- 15 ÷ 3 = **5 microinversores por fase**
- **EXCEDE** limite de 3 em série!

**Configuração sugerida**:
- **Opção 1**: 3 em série + 2 grupos em paralelo por fase
- **Opção 2**: Substituir por inversor string 7,5 kW

**Cálculos**:
```
I_micro = 500W / 220V = 2,27 A
I_por_fase = 2,27 A × 5 = 11,36 A
```

**Aviso**:
```
⚠️  ATENÇÃO: 5 microinversores por fase excede limite de 3 em série.
Reconfigurar distribuição ou usar inversor string.
```

**Status**: ⚠️ ATENÇÃO — Requer reconfiguração.

---

### Exemplo 4: 5 Microinversores 2,25kW — Rede Monofásica 220V ✅

**Dados**:
- 5 microinversores × 2,25 kW = 11,25 kW
- Rede: Monofásica 220V (limite 12 kW)

**Validação de Potência**:
```
✅ OK: 11,25 kW está dentro do limite de 12 kW (rede monofásica 220V)
```

**Distribuição de Disjuntores**:
- Máximo 3 microinversores por disjuntor CA
- 5 micros ÷ 3 = **2 disjuntores necessários**

**Configuração**:
- **Disjuntor 1**: 3 microinversores em série
- **Disjuntor 2**: 2 microinversores em série

**Cálculos**:
```
I_micro = 2250W / 220V = 10,23 A

Disjuntor 1 (3 micros):
  I_grupo1 = 10,23 A × 3 = 30,68 A
  I_disjuntor1 = 30,68 A × 1,25 = 38,35 A
  Valor comercial: 40 A

Disjuntor 2 (2 micros):
  I_grupo2 = 10,23 A × 2 = 20,45 A
  I_disjuntor2 = 20,45 A × 1,25 = 25,57 A
  Valor comercial: 32 A
```

**Resumo**:
- 2 disjuntores CA: 1× 40A + 1× 32A
- Corrente total: 51,13 A (30,68 + 20,45)
- Status: ✅ OK

---

### Exemplo 5: 15 kW em Rede Monofásica 220V ❌

**Dados**:
- Sistema de 15 kW
- Rede: Monofásica 220V (limite 12 kW)

**Validação de Potência**:
```
❌ ERRO: Sistema de 15,0 kW EXCEDE o limite de 12 kW (rede monofásica 220V).
Excesso: 3,0 kW.
SOLUÇÃO: Migrar para rede de maior capacidade ou reduzir potência.
```

**Soluções**:
1. **Migrar para rede bifásica** (limite 25 kW) ✅
2. **Migrar para rede trifásica** (limite 75 kW) ✅
3. **Reduzir sistema para 12 kW** (remover 3 kW de equipamentos)

**Status**: ❌ ERRO — Sistema incompatível com a rede.

---

### Exemplo 6: 2 Inversores String 6kW — Rede Monofásica 220V ✅

**Dados**:
- 2 inversores monofásicos × 6 kW = 12 kW
- Rede: Monofásica 220V (limite 12 kW)

**Validação de Potência**:
```
✅ OK: 12,0 kW está dentro do limite de 12 kW (rede monofásica 220V)
```

**Quantidade de Disjuntores**:
- **REGRA**: 1 disjuntor CA por inversor string
- 2 inversores = **2 disjuntores CA**

**Cálculos**:
```
Inversor 1 (6 kW):
  I1 = 6000W / 220V = 27,27 A
  I_disjuntor1 = 27,27 A × 1,25 = 34,09 A
  Valor comercial: 40 A

Inversor 2 (6 kW):
  I2 = 6000W / 220V = 27,27 A
  I_disjuntor2 = 27,27 A × 1,25 = 34,09 A
  Valor comercial: 40 A
```

**Resumo**:
- 2 disjuntores CA: 2× 40A (1 por inversor)
- Corrente total: 54,55 A
- Status: ✅ OK

---

## 7. INTEGRAÇÃO NO SISTEMA

### 7.1 Módulo Principal

**Arquivo**: `backend/nbr5410_calculations.py`

**Funções Principais**:
- `calculate_ac_current_nbr5410()` — Cálculo de corrente CA
- `validate_inverter_network_compatibility()` — Validação inversor × rede
- `calculate_breaker_per_phase()` — Dimensionamento de disjuntor
- `analyze_microinverter_distribution()` — Análise de distribuição de micros

### 7.2 Integração em system_calculations.py

```python
from nbr5410_calculations import (
    calculate_ac_current_nbr5410,
    validate_inverter_network_compatibility,
    calculate_breaker_per_phase,
)

# Dentro de calculate_technical_parameters()
ac_current_result = calculate_ac_current_nbr5410(
    power_kw=total_inverter_power_kw,
    voltage_v=voltage,
    system_type=system_type,
    topology=topology,
    num_devices=num_inverters,
)

corrente_ac = ac_current_result['current_total_a']
corrente_por_fase = ac_current_result['current_per_phase_a']

breaker_result = calculate_breaker_per_phase(corrente_por_fase)
disjuntor_recomendado = breaker_result['breaker_rated_a']
```

### 7.3 Retorno da API

```json
{
  "corrente_ac_a": 15.19,
  "corrente_por_fase_a": 5.06,
  "ac_current_nbr5410": {
    "current_total_a": 15.19,
    "current_per_phase_a": 5.06,
    "formula": "I = P / (V × √3) = 10000W / (380V × 1.732)",
    "distribution": "Carga balanceada em 3 fases: 5.06 A por fase",
    "warnings": []
  },
  "network_compatibility": {
    "compatible": true,
    "status": "OK",
    "message": "✅ Inversor TRIFASICO compatível com rede TRIFASICO."
  },
  "disjuntor_recomendado_a": 20
}
```

---

## 8. AVISOS E VALIDAÇÕES AUTOMÁTICAS

### 8.1 Microinversores > 3 em Série

```
⚠️  ATENÇÃO: 5 microinversores por fase excede limite de 3 em série.
Configuração: 3 em série × 2 grupos em paralelo.
```

### 8.2 Inversor Monofásico em Rede Trifásica

```
❌ ERRO: Inversor MONOFÁSICO não pode ser conectado em rede TRIFÁSICA.
Use inversor trifásico ou altere a rede para monofásica.
```

### 8.3 Inversor Trifásico em Rede Monofásica

```
❌ ERRO: Inversor TRIFÁSICO requer rede trifásica.
Rede atual: MONOFASICO.
```

---

## 9. TESTES

### Executar Testes Unitários

```bash
cd backend
.venv/Scripts/python nbr5410_calculations.py
```

**Saída Esperada**:
```
================================================================================
TESTE 1: 9 microinversores 500W em rede trifásica 220V
================================================================================
Corrente total: 20.45 A
Corrente por fase: 6.82 A
Distribuição: 9 microinversores distribuídos em 3 fases (3 por fase, máx 3 em série).

================================================================================
TESTE 2: Inversor string 10kW trifásico em rede trifásica 380V (GO)
================================================================================
Corrente total: 15.19 A
Corrente por fase: 5.06 A
Fórmula: I = P / (V × √3) = 10000W / (380V × 1.732)

================================================================================
TESTE 3: Compatibilidade inversor monofásico em rede trifásica
================================================================================
❌ ERRO: Inversor MONOFÁSICO não pode conectar em rede TRIFÁSICA.
```

---

## 10. REFERÊNCIAS

- **NBR 5410**: Instalações elétricas de baixa tensão
- **NR10**: Segurança em instalações e serviços em eletricidade
- **ABNT NBR 16690**: Sistemas fotovoltaicos — Requisitos mínimos

---

**Última Atualização**: 2026-08-28 — v0.5.1
**Autor**: Sistema Automação Equatorial
**Módulo**: backend/nbr5410_calculations.py

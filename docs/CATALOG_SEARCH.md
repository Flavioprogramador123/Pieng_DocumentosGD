# Busca Inteligente de Equipamentos no Catálogo

Documentação completa do sistema de busca fuzzy de módulos e inversores fotovoltaicos.

---

## Visão Geral

O sistema implementa busca inteligente em 3 camadas para reduzir drasticamente o uso da API Gemini, priorizando o catálogo SQLite local.

### Prioridade de Busca

```
┌─────────────────────────────────────────────────────────────┐
│  1. CATÁLOGO SQLITE (3 camadas)                             │
│     ├─ Tier 1: Match exato (fabricante + modelo)            │
│     ├─ Tier 2: Match potência exata (fabricante + potência) │
│     └─ Tier 3: Match tolerância (±5% módulos, ±10% inversores)│
│                                                              │
│  2. GEMINI API (último recurso)                             │
│     └─ Apenas se nenhuma camada SQLite encontrar            │
└─────────────────────────────────────────────────────────────┘
```

---

## Funções de Busca

### 1. Busca Fuzzy de Módulos

```python
from catalog_db import search_modules_fuzzy

results = search_modules_fuzzy(
    query='Canadian',              # Termo de busca (modelo ou fabricante)
    fabricante='Canadian Solar',   # Filtro por fabricante
    potencia_min=400,              # Potência mínima (Wp)
    potencia_max=600,              # Potência máxima (Wp)
    limit=10,                      # Máximo de resultados
)

# Retorna lista ordenada por relevância:
# [
#   {'id': 1, 'fabricante': 'Canadian Solar', 'modelo': 'CS3W-550P',
#    'potencia_wp': 550, 'voc': 49.5, 'isc': 13.9, 'relevancia': 3},
#   {'id': 2, 'fabricante': 'Canadian Solar', 'modelo': 'CS3W-400P',
#    'potencia_wp': 400, 'voc': 46.0, 'isc': 10.8, 'relevancia': 2},
#   ...
# ]
```

**Pontuação de Relevância**:
- `relevancia: 3` — modelo LIKE query (melhor match)
- `relevancia: 2` — fabricante LIKE query
- `relevancia: 1` — outros

---

### 2. Busca Inteligente de Módulos (3 Camadas)

```python
from catalog_db import find_module_by_name_or_power

# Exemplo 1: Match exato (Tier 1)
module = find_module_by_name_or_power(
    fabricante='Canadian Solar',
    modelo='CS3W-550P',
    potencia_wp=550,
)
# → Encontra exatamente 'Canadian Solar CS3W-550P'

# Exemplo 2: Match por potência (Tier 2)
module = find_module_by_name_or_power(
    fabricante='Canadian Solar',
    modelo='',  # Modelo desconhecido
    potencia_wp=550,
)
# → Encontra 'Canadian Solar' com 550Wp exatos

# Exemplo 3: Match com tolerância (Tier 3)
module = find_module_by_name_or_power(
    fabricante='Canadian Solar',
    modelo='',
    potencia_wp=545,  # Potência aproximada
)
# → Encontra módulo entre 518W e 572W (±5%)
# → Prioriza o mais próximo de 545W
```

**Retorno**:
```python
{
    'id': 1,
    'fabricante': 'Canadian Solar',
    'modelo': 'CS3W-550P',
    'potencia_wp': 550,
    'voc': 49.5,
    'isc': 13.9,
    'vmpp': 41.5,
    'impp': 13.25,
    'eficiencia': 21.2,
    'tipo_celula': 'Monocristalino PERC',
    'dimensoes': '2278×1134×35mm',
}
```

---

### 3. Busca Fuzzy de Inversores

```python
from catalog_db import search_inverters_fuzzy

results = search_inverters_fuzzy(
    query='Deye',
    fabricante='Deye',
    potencia_min=5,
    potencia_max=15,
    tipo_inversor='micro',  # Filtro: 'micro', 'string', 'central'
    limit=10,
)

# Retorna lista ordenada por relevância e potência
```

---

### 4. Busca Inteligente de Inversores (3 Camadas)

```python
from catalog_db import find_inverter_by_name_or_power

# Exemplo 1: Match exato
inverter = find_inverter_by_name_or_power(
    fabricante='Deye',
    modelo='SUN-6K-SG04LP3-EU',
    potencia_kw=6,
)

# Exemplo 2: Match com tolerância ±10%
inverter = find_inverter_by_name_or_power(
    fabricante='Deye',
    modelo='',
    potencia_kw=5.8,  # Encontra inversores 5.22-6.38 kW
)
```

**Retorno**:
```python
{
    'id': 1,
    'fabricante': 'Deye',
    'modelo': 'SUN-6K-SG04LP3-EU',
    'potencia_kw': 6.0,
    'tensao_nominal': 230,
    'corrente_nominal': 26.1,
    'mppt_min': 90,
    'mppt_max': 560,
    'num_mppt': 2,
    'eficiencia': 97.6,
    'tipo_inversor': 'string',
}
```

---

## Endpoints de API

### POST /api/catalog/search-modules

Busca fuzzy de módulos.

**Request**:
```json
{
  "query": "Canadian",
  "fabricante": "Canadian Solar",
  "potencia_min": 400,
  "potencia_max": 600,
  "limit": 10
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {"id": 1, "fabricante": "Canadian Solar", "modelo": "CS3W-550P", "potencia_wp": 550, ...},
    {"id": 2, "fabricante": "Canadian Solar", "modelo": "CS3W-400P", "potencia_wp": 400, ...}
  ],
  "count": 2
}
```

---

### POST /api/catalog/search-inverters

Busca fuzzy de inversores.

**Request**:
```json
{
  "query": "Deye",
  "fabricante": "Deye",
  "potencia_min": 5,
  "potencia_max": 15,
  "tipo_inversor": "micro",
  "limit": 10
}
```

**Response**:
```json
{
  "success": true,
  "results": [...],
  "count": 5
}
```

---

### POST /api/catalog/find-module

Busca inteligente de módulo (3 camadas).

**Request**:
```json
{
  "fabricante": "Canadian Solar",
  "modelo": "CS3W-550P",
  "potencia_wp": 550
}
```

**Response**:
```json
{
  "success": true,
  "found": true,
  "module": {...},
  "match_type": "exact"  // "exact" | "power_exact" | "power_tolerance"
}
```

---

### POST /api/catalog/find-inverter

Busca inteligente de inversor (3 camadas).

**Request**:
```json
{
  "fabricante": "Deye",
  "modelo": "SUN-6K-SG04LP3-EU",
  "potencia_kw": 6
}
```

**Response**:
```json
{
  "success": true,
  "found": true,
  "inverter": {...},
  "match_type": "exact"
}
```

---

## Integração com Enriquecimento de Equipamentos

O sistema de busca está integrado automaticamente em `equipment_enrichment.py`:

```python
from equipment_enrichment import enrich_module_specs

specs, source = enrich_module_specs(
    fabricante='Canadian Solar',
    modelo='CS3W-550P',
    potencia=550,
)

# Fluxo interno:
# 1. Tenta find_module_by_name_or_power() (3 camadas SQLite)
# 2. Se encontrar → retorna specs, source='catalog'
# 3. Se não encontrar → chama Gemini API → source='gemini'
```

---

## Configuração de Tolerância

### Módulos: ±5%

```python
# Busca por 400W encontra módulos de 380-420W
tolerance = 0.05
min_power = 400 * (1 - 0.05) = 380W
max_power = 400 * (1 + 0.05) = 420W
```

### Inversores: ±10%

```python
# Busca por 10kW encontra inversores de 9-11kW
tolerance = 0.10
min_power = 10 * (1 - 0.10) = 9kW
max_power = 10 * (1 + 0.10) = 11kW
```

---

## Métricas de Economia

### Antes (v0.5.2 e anteriores)

```python
# 100 projetos com 'Canadian Solar CS3W-550P'
# → 100 chamadas Gemini API
# → Custo: ~$0.50 (modelo flash)
# → Tempo: ~30s por projeto
```

### Depois (v0.5.3+)

```python
# 100 projetos com 'Canadian Solar CS3W-550P'
# → 1 chamada Gemini (primeiro projeto)
# → 99 consultas SQLite (instantâneas, grátis)
# → Custo: ~$0.005 (1% do anterior)
# → Tempo: ~0.1s por projeto (300× mais rápido)
```

**Redução de custo**: 99%
**Redução de latência**: 99.7%

---

## Exemplos Práticos

### Exemplo 1: Projeto com Equipamento Comum

```python
# Usuário cola TXT com "Canadian Solar CS3W-550P"
# Sistema:
# 1. Extrai: fabricante='Canadian Solar', modelo='CS3W-550P', potencia=550
# 2. Chama enrich_module_specs()
# 3. find_module_by_name_or_power() → Tier 1 (match exato) ✅
# 4. Retorna specs do SQLite (0ms, grátis)
# 5. Gemini API NÃO é chamada 🎉
```

### Exemplo 2: Projeto com Potência Aproximada

```python
# Usuário informa: fabricante='Jinko', potencia=545W, modelo=''
# Sistema:
# 1. Tier 1 (modelo): falha (modelo vazio)
# 2. Tier 2 (potência exata 545W): falha
# 3. Tier 3 (518-572W): encontra 'Jinko Tiger Pro 550W' ✅
# 4. Retorna specs (0ms, grátis)
```

### Exemplo 3: Equipamento Novo (não no catálogo)

```python
# Usuário informa: fabricante='NewBrand', modelo='X-9000', potencia=600
# Sistema:
# 1. Tier 1, 2, 3: todos falham (equipamento não cadastrado)
# 2. Chama Gemini API como fallback
# 3. Retorna specs da IA
# 4. Salva no catálogo SQLite para próximas consultas
```

---

## Fluxograma Completo

```
┌───────────────────────────────────────────────────────────────┐
│ Usuário envia formulário com módulo/inversor                  │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│ equipment_enrichment.py → enrich_module_specs()               │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│ catalog_db.py → find_module_by_name_or_power()                │
└────────────────────────┬──────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌──────────────┐
   │ Tier 1  │    │ Tier 2   │    │ Tier 3       │
   │ Exato   │───▶│ Potência │───▶│ Tolerância   │
   │         │    │ Exata    │    │ ±5%/±10%     │
   └────┬────┘    └────┬─────┘    └──────┬───────┘
        │              │                  │
        │ Encontrou?   │ Encontrou?       │ Encontrou?
        ▼              ▼                  ▼
       SIM            SIM                SIM
        │              │                  │
        └──────────────┴──────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │ Retorna specs SQLite  │
           │ source = 'catalog'    │
           └───────────────────────┘
                       │
                       │ NÃO encontrou?
                       ▼
           ┌───────────────────────┐
           │ Chama Gemini API      │
           │ source = 'gemini'     │
           └───────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │ Salva no SQLite       │
           │ (próximas consultas)  │
           └───────────────────────┘
```

---

## Testes

### Testar Busca Fuzzy de Módulos

```bash
curl -X POST http://localhost:5000/api/catalog/search-modules \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Canadian",
    "potencia_min": 400,
    "potencia_max": 600,
    "limit": 5
  }'
```

### Testar Busca Inteligente de Módulos

```bash
curl -X POST http://localhost:5000/api/catalog/find-module \
  -H "Content-Type: application/json" \
  -d '{
    "fabricante": "Canadian Solar",
    "modelo": "CS3W-550P",
    "potencia_wp": 550
  }'
```

### Testar Busca de Inversores

```bash
curl -X POST http://localhost:5000/api/catalog/search-inverters \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Deye",
    "tipo_inversor": "micro",
    "limit": 10
  }'
```

---

## Benefícios

### 1. Redução de Custo
- 80-99% menos chamadas à API Gemini
- Economia de ~$0.005 por projeto com equipamentos comuns

### 2. Redução de Latência
- Consulta SQLite: <1ms
- API Gemini: ~2-5s
- **300× mais rápido** para equipamentos conhecidos

### 3. Funcionamento Offline
- Catálogo SQLite funciona sem internet
- Gemini API apenas para equipamentos novos

### 4. Precisão
- Dados técnicos garantidos (pré-validados no catálogo)
- Sem erros de parsing de IA

### 5. Escalabilidade
- Catálogo cresce automaticamente
- Cada consulta Gemini alimenta o catálogo

---

## Manutenção do Catálogo

### Importar Módulos de YAML

```python
from import_modulos_yaml import import_modulos_yaml
import_modulos_yaml()
```

### Importar Inversores de YAML

```python
from import_inversores_yaml import import_inversores_yaml
import_inversores_yaml()
```

### Listar Equipamentos

```python
from catalog_db import list_table

modules = list_table('catalog_modules')
inverters = list_table('catalog_inverters')
```

---

## Próximos Passos

1. **Frontend UI**: Adicionar interface de busca de equipamentos similares na aba Equipamentos
2. **Feedback de match**: Mostrar ao usuário qual tier encontrou o equipamento
3. **Sugestões inteligentes**: "Você quis dizer CS3W-550P?" quando modelo não for exato
4. **Cache de IA**: Salvar respostas Gemini mesmo quando não encontrado (evitar reconsultas)
5. **Analytics**: Dashboard de uso (% catalog vs % AI)

---

**Versão**: 0.5.3
**Data**: 2026-08-28
**Autor**: Sistema Automação Equatorial

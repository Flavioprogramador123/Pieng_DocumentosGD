# 🌐 Interface Web - Automação de Documentos Equatorial

Sistema completo com interface web para geração automatizada de documentos PRODIST 3 e Resolução ANEEL para sistemas fotovoltaicos.

---

## 📋 ÍNDICE
1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Instalação](#instalação)
4. [Como Usar](#como-usar)
5. [Arquitetura](#arquitetura)
6. [API Endpoints](#api-endpoints)
7. [Resolução de Problemas](#resolução-de-problemas)

---

## 🎯 VISÃO GERAL

### O que o sistema faz?
- ✅ Interface web moderna para entrada de dados
- ✅ Cálculos automáticos de potência e geração
- ✅ Geração de 3 documentos oficiais:
  1. Procuração
  2. Formulário de Solicitação
  3. Memorial Técnico Descritivo
- ✅ Download direto dos documentos gerados
- ✅ Preservação de formatação original

### Tecnologias Utilizadas
- **Frontend:** React 19 + Vite + Tailwind CSS + shadcn/ui
- **Backend:** Flask 3.1 + Python 3.10+
- **Processamento:** lxml + openpyxl (manipulação de Office XML)

---

## 💻 PRÉ-REQUISITOS

### Software Necessário:
1. **Python 3.10 ou superior**
   - Download: https://www.python.org/downloads/
   - ✅ Certifique-se de marcar "Add Python to PATH" durante instalação

2. **Node.js 18+ (com pnpm)**
   - Download: https://nodejs.org/
   - Instalar pnpm: `npm install -g pnpm`

3. **Git** (opcional, para clonar o repositório)
   - Download: https://git-scm.com/

### Verificar Instalações:
```bash
python --version  # Deve mostrar Python 3.10+
node --version    # Deve mostrar v18+
pnpm --version    # Deve mostrar versão do pnpm
```

---

## 🚀 INSTALAÇÃO

### Opção 1: Instalação Automática (Recomendado)

1. **Duplo clique em `start_all.bat`**
   - O script irá:
     - Ativar ambiente virtual Python
     - Instalar dependências do backend
     - Instalar dependências do frontend
     - Iniciar ambos os servidores

### Opção 2: Instalação Manual

#### Backend (API Flask)

```bash
# Navegar para pasta do backend
cd entrega_equatorial_automacao\entrega_equatorial_automacao\entrega_equatorial_automacao

# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements_api.txt
```

#### Frontend (React)

```bash
# Navegar para pasta do frontend
cd equatorial_automation_frontend

# Instalar dependências
pnpm install
```

---

## 📖 COMO USAR

### Iniciar o Sistema

#### Método 1: Tudo de uma vez
```bash
# Na raiz do projeto
start_all.bat
```
Isso irá abrir 2 janelas:
- **Backend API:** Porta 5000
- **Frontend:** Porta 5173

#### Método 2: Separadamente
```bash
# Terminal 1 - Backend
start_backend.bat

# Terminal 2 - Frontend (em outra janela)
start_frontend.bat
```

### Acessar a Interface

1. Abra o navegador em: **http://localhost:5173**

2. Preencha o formulário:
   - **Dados do Cliente** (obrigatórios):
     - Nome completo
     - Endereço completo
     - Unidade Consumidora (UC)
     - CPF (opcional)

   - **Dados Técnicos**:
     - Módulos: Quantidade, Modelo, Potência (W)
     - Inversores: Quantidade, Modelo, Potência (W)

   - **Configurações**:
     - Tensão da Rede (220V, 380V, 13.8kV)
     - Tipo de Consumo (Autoconsumo Local, etc.)

3. **Calcular Sistema** (opcional):
   - Clique em "Calcular Sistema"
   - Veja potência total, geração estimada, recomendação de cabos

4. **Gerar Documentos**:
   - Clique em "Gerar Todos os Documentos"
   - Aguarde o processamento (~5 segundos)
   - Veja a lista de documentos gerados
   - Clique em "Baixar" para fazer download

---

## 🏗️ ARQUITETURA

```
┌─────────────────────────────────────────────────────────────┐
│                    Navegador Web (Cliente)                  │
│                   http://localhost:5173                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ REST API (JSON)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend Flask API (Servidor)                   │
│                 http://localhost:5000                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Endpoints:                                           │  │
│  │  - POST /api/calculate-system   (Cálculos)         │  │
│  │  - POST /api/fill-documents     (Gerar docs)       │  │
│  │  - GET  /api/download/<file>    (Download)         │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Subprocess Python
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Gerador de Documentos (gerar_documentos.py)       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - Converte dados → formato TXT                      │  │
│  │ - Aplica defaults (config_padrao.json)             │  │
│  │ - Preenche templates com marcadores {{TOKEN}}      │  │
│  │ - Preserva formatação original                     │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Arquivos XML
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Templates (DOCX/XLSX)                   │
│  - modelo_procuracao_marcadores.docx                       │
│  - MEMORIAL_DESCRITIVO_marcadores.docx                     │
│  - NT.00020-05-Anexo-I-Formulario...templates.xltx        │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ Documentos Preenchidos
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Saída (saida/web_generated/)               │
│  cliente_nome_timestamp/                                    │
│    ├── modelo_procuracao_marcadores.docx                   │
│    ├── MEMORIAL_DESCRITIVO_marcadores.docx                 │
│    ├── NT.00020-05...templates.xlsx                        │
│    ├── relatorio_preenchimento.txt                         │
│    └── dados_cliente.txt                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 API ENDPOINTS

### 1. Health Check
```http
GET /api/health
```
**Resposta:**
```json
{
  "status": "ok",
  "message": "API Equatorial Automation está funcionando",
  "timestamp": "2026-08-28T00:00:00"
}
```

### 2. Calcular Sistema
```http
POST /api/calculate-system
Content-Type: application/json
```
**Corpo:**
```json
{
  "modules": [
    { "quantity": "10", "model": "CS3W-540P", "power": "540" }
  ],
  "inverters": [
    { "quantity": "1", "model": "MIN 5000TL-XH", "power": "5000" }
  ]
}
```
**Resposta:**
```json
{
  "success": true,
  "calculations": {
    "total_module_power_kw": 5.4,
    "total_inverter_power_kw": 5.0,
    "estimated_monthly_generation": 658,
    "cable_section_recommendation": "6mm² CC / 10mm² CA",
    "economia_mensal_estimada": 723.80
  }
}
```

### 3. Gerar Documentos
```http
POST /api/fill-documents
Content-Type: application/json
```
**Corpo:**
```json
{
  "client_name": "MARIA APARECIDA SANTOS",
  "client_cpf": "123.456.789-00",
  "client_address": "RUA DAS FLORES, N. 234, JARDIM AMÉRICA",
  "consumer_unit": "701.234.567-89",
  "grid_voltage": "220V",
  "consumption_type": "AUTOCONSUMO LOCAL",
  "modules": [...],
  "inverters": [...],
  "total_power": 5.4
}
```
**Resposta:**
```json
{
  "success": true,
  "message": "Documentos gerados com sucesso!",
  "files": [
    {
      "name": "modelo_procuracao_marcadores.docx",
      "size": 30628,
      "download_url": "/api/download/maria_aparecida_santos_20260828_120000/modelo_procuracao_marcadores.docx"
    },
    {
      "name": "MEMORIAL_DESCRITIVO_marcadores.docx",
      "size": 604503,
      "download_url": "/api/download/maria_aparecida_santos_20260828_120000/MEMORIAL_DESCRITIVO_marcadores.docx"
    },
    {
      "name": "NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xlsx",
      "size": 360448,
      "download_url": "/api/download/maria_aparecida_santos_20260828_120000/NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xlsx"
    }
  ]
}
```

### 4. Download de Arquivo
```http
GET /api/download/<client_folder>/<filename>
```
Retorna o arquivo binário para download.

---

## 🛠️ RESOLUÇÃO DE PROBLEMAS

### Backend não inicia

**Problema:** `ModuleNotFoundError: No module named 'flask'`

**Solução:**
```bash
cd entrega_equatorial_automacao\entrega_equatorial_automacao\entrega_equatorial_automacao
.venv\Scripts\activate
pip install -r requirements_api.txt
```

### Frontend não inicia

**Problema:** `pnpm: command not found`

**Solução:**
```bash
npm install -g pnpm
```

**Problema:** Erro ao instalar dependências

**Solução:**
```bash
cd equatorial_automation_frontend
rm -rf node_modules
rm pnpm-lock.yaml
pnpm install
```

### Erro CORS no navegador

**Problema:** `Access to fetch at 'http://localhost:5000' from origin 'http://localhost:5173' has been blocked by CORS policy`

**Solução:**
- Verifique se Flask-CORS está instalado
- Reinicie o backend
- Limpe cache do navegador (Ctrl+Shift+Delete)

### Documentos não são gerados

**Problema:** Erro ao gerar documentos

**Soluções:**
1. Verifique se os templates existem:
   ```
   templates/
     ├── modelo_procuracao_marcadores.docx
     ├── MEMORIAL_DESCRITIVO_marcadores.docx
     └── NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xltx
   ```

2. Verifique se `config_padrao.json` existe

3. Veja logs do backend para detalhes do erro

### Porta já em uso

**Problema:** `Address already in use: Port 5000` ou `Port 5173`

**Solução:**
```bash
# Windows - Matar processo na porta
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# Ou escolher outra porta
# Backend: Editar api_server.py, linha: app.run(port=5001)
# Frontend: Editar package.json, adicionar: "dev": "vite --port 5174"
```

---

## 📝 LOGS E DEBUG

### Ver logs do Backend:
Os logs aparecem diretamente no terminal onde `start_backend.bat` foi executado.

### Ver logs do Frontend:
Console do navegador (F12 → Console)

### Arquivos Gerados:
Todos os documentos ficam em:
```
entrega_equatorial_automacao/
  entrega_equatorial_automacao/
    entrega_equatorial_automacao/
      saida/
        web_generated/
          cliente_nome_timestamp/
            ├── *.docx
            ├── *.xlsx
            ├── dados_cliente.txt
            └── relatorio_preenchimento.txt
```

---

## 🎓 RECURSOS ADICIONAIS

### Documentação Original (CLI):
- [README.md](entrega_equatorial_automacao/entrega_equatorial_automacao/entrega_equatorial_automacao/README.md)
- [ENTREGA.md](entrega_equatorial_automacao/entrega_equatorial_automacao/entrega_equatorial_automacao/ENTREGA.md)

### Código Fonte:
- **Backend:** [api_server.py](entrega_equatorial_automacao/entrega_equatorial_automacao/entrega_equatorial_automacao/api_server.py)
- **Frontend:** [App.jsx](equatorial_automation_frontend/src/App.jsx)
- **Gerador:** [gerar_documentos.py](entrega_equatorial_automacao/entrega_equatorial_automacao/entrega_equatorial_automacao/gerar_documentos.py)

---

## 🆘 SUPORTE

Para problemas ou dúvidas:
1. Verifique a seção de [Resolução de Problemas](#resolução-de-problemas)
2. Consulte os logs do backend e frontend
3. Verifique se todos os pré-requisitos foram instalados
4. Entre em contato com o desenvolvedor

---

## 🔒 SEGURANÇA E PRIVACIDADE

- ✅ Todos os dados são processados **localmente**
- ✅ Nenhuma informação é enviada para internet
- ✅ Arquivos gerados ficam apenas no seu computador
- ✅ Dados técnicos devem ser conferidos antes do protocolo

---

## 📊 PERFORMANCE

- **Tempo médio de geração:** < 3 segundos
- **Taxa de preenchimento automático:** 91-93%
- **Documentos por execução:** 3
- **Tamanho médio dos documentos:** ~1 MB total

---

**Sistema desenvolvido para uso local no VS Code com interface web moderna.**

**Versão:** 1.0.0 | **Data:** Agosto 2026 | **Status:** ✅ Produção

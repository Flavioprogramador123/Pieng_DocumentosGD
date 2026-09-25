# 📦 PIENG - Instalação em Nova Máquina

Guia completo para instalar o sistema em um novo computador.

---

## 🎯 Requisitos do Sistema

### Hardware Mínimo
- **Processador**: Intel i3 ou equivalente
- **RAM**: 4GB (8GB recomendado)
- **Disco**: 5GB livres
- **Internet**: Para instalar dependências e Google Drive sync

### Software Necessário

1. **Windows 10/11** (64-bit)
2. **Python 3.11+** → https://www.python.org/downloads/
3. **Node.js 20+** → https://nodejs.org/
4. **Google Drive for Desktop** → https://www.google.com/drive/download/

---

## 🚀 Instalação Automática (Recomendado)

### Passo a Passo

1. **Clone ou copie o repositório** para o computador novo
   ```
   Exemplo: C:\Users\SeuNome\projeto\Automacao_Equatorial01
   ```

2. **Execute como Administrador**:
   - Clique com botão direito em `INSTALAR_NOVA_MAQUINA.bat`
   - Selecione "Executar como administrador"

3. **Aguarde a instalação** (5-10 minutos)
   - Instala pnpm automaticamente
   - Cria ambiente virtual Python
   - Instala todas as dependências
   - Inicializa banco de dados
   - Cria atalho na área de trabalho

4. **Configure os arquivos .env**:
   - Edite `.env` na raiz do projeto
   - Edite `backend\.env`
   - Adicione suas chaves (GEMINI_API_KEY, emails, etc.)

5. **Instale o Google Drive for Desktop**
   - Faça login com sua conta
   - Aguarde sincronização completa

6. **Pronto!** Use o atalho "PIENG - Automacao Equatorial" na área de trabalho

---

## 📝 Instalação Manual

Se preferir instalar manualmente:

### 1. Instalar Dependências

```bash
# Python
python --version  # Verifica se está instalado

# Node.js
node --version    # Verifica se está instalado

# pnpm (global)
npm install -g pnpm
```

### 2. Ambiente Virtual Python

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
deactivate
```

### 3. Dependências Node.js

```bash
cd equatorial_automation_frontend
pnpm install
```

### 4. Configuração

```bash
# Copie os arquivos de exemplo
copy .env.example .env
copy backend\.env.example backend\.env

# Edite os arquivos .env com suas configurações
notepad .env
notepad backend\.env
```

### 5. Banco de Dados

```bash
cd backend
.venv\Scripts\activate.bat
python -c "from catalog_db import init_db; init_db()"
deactivate
```

---

## 🎮 Como Usar

### Iniciar o Sistema

**Método 1 - Atalho (Mais Rápido)**:
- Duplo clique no atalho "PIENG - Automacao Equatorial" na área de trabalho

**Método 2 - Arquivo VBS**:
- Duplo clique em `PIENG.vbs` na pasta do projeto

**Método 3 - Arquivo BAT**:
- Duplo clique em `INICIAR_SISTEMA.bat`

### Fechar o Sistema

- Duplo clique em `FECHAR_SISTEMA.bat`

### Verificar Status

- Duplo clique em `VERIFICAR_SISTEMA.bat`

---

## ⚙️ Configuração de Inicialização Automática

Para que o sistema inicie automaticamente com o Windows:

### Opção 1 - Atalho na Pasta de Inicialização (Recomendado)

1. Pressione `Win + R`
2. Digite: `shell:startup`
3. Pressione Enter
4. Copie o arquivo `PIENG.vbs` para esta pasta
5. Pronto! Na próxima vez que ligar o PC, o sistema inicia automaticamente

### Opção 2 - Agendador de Tarefas (Avançado)

1. Abra o "Agendador de Tarefas" do Windows
2. Crie Nova Tarefa
3. Nome: "PIENG - Automacao Equatorial"
4. Gatilho: "Ao fazer logon"
5. Ação: Executar `C:\caminho\para\PIENG.vbs`
6. Marque: "Executar com privilégios mais altos"

---

## 📐 ODA File Converter (planta.dwg compacto)

Na **primeira execução** do sistema (após login), a interface verifica se o **ODA File Converter** está instalado.

| Com ODA | Sem ODA (fallback) |
|---------|-------------------|
| `planta.dwg` ~2 MB | `planta.dxf` ~25 MB |

**Instalar:**
- Pelo aviso na web: **Instalar ODA File Converter**
- Ou execute `INSTALAR_ODA.bat` (como administrador)
- Ou durante `INSTALAR_NOVA_MAQUINA.bat` (passo 8)

Download manual: https://www.opendesign.com/guestfiles/oda_file_converter

---

## 🔧 Solução de Problemas

### Sistema não abre

1. Execute `VERIFICAR_SISTEMA.bat`
2. Verifique se Python, Node.js e pnpm estão instalados
3. Verifique se as portas 5000 e 5180 não estão em uso

### "Python não encontrado"

- Instale Python 3.11+ de https://www.python.org/downloads/
- Marque a opção "Add Python to PATH" durante a instalação

### "Node.js não encontrado"

- Instale Node.js 20+ de https://nodejs.org/
- Reinicie o computador após a instalação

### "pnpm não encontrado"

```bash
npm install -g pnpm
```

### Google Drive não sincroniza

- Instale Google Drive for Desktop
- Faça login com sua conta
- Aguarde sincronização inicial completar

### Backend não inicia

1. Verifique os logs na janela minimizada
2. Verifique se o `.env` está configurado corretamente
3. Tente executar manualmente:
   ```bash
   cd backend
   .venv\Scripts\activate.bat
   python api_server.py
   ```

### Frontend não inicia

1. Verifique se `node_modules` existe em `equatorial_automation_frontend`
2. Se não existir, execute:
   ```bash
   cd equatorial_automation_frontend
   pnpm install
   ```

---

## 📊 Estrutura de Arquivos

```
Automacao_Equatorial01/
├── PIENG.vbs                    ← Iniciar (sem janela CMD)
├── INICIAR_SISTEMA.bat          ← Iniciar (com janela)
├── FECHAR_SISTEMA.bat           ← Encerrar sistema
├── VERIFICAR_SISTEMA.bat        ← Verificar status
├── INSTALAR_NOVA_MAQUINA.bat    ← Instalação automatizada
├── .env                         ← Configurações (EDITAR!)
├── backend/
│   ├── .env                     ← Configurações backend (EDITAR!)
│   ├── .venv/                   ← Ambiente virtual Python
│   └── api_server.py            ← Servidor Flask
├── equatorial_automation_frontend/
│   ├── node_modules/            ← Dependências Node.js
│   └── src/                     ← Código React
└── templates/                   ← Templates de documentos
```

---

## 🔐 Segurança

### Arquivos que NUNCA devem ir para o Git

- `.env` (chaves de API, senhas)
- `backend\.env` (configurações sensíveis)
- `data/users.json` (usuários e senhas)
- `data/*.db` (banco de dados)
- `saida/` (documentos com dados LGPD)

### Backup

O Google Drive for Desktop já faz backup automático dos arquivos gerados em:
```
I:\Meu Drive\Pieng Soluções Energéticas\pieng\2. Clientes Aprovados\80 a 100
```

---

## 📞 Suporte

Se encontrar problemas:

1. Execute `VERIFICAR_SISTEMA.bat` e anote os erros
2. Verifique os logs nas janelas minimizadas
3. Consulte a documentação no repositório GitHub

---

## 📄 Licença

Este sistema é de uso interno da PIENG. Não distribuir sem autorização.

---

**Versão**: 1.0
**Última atualização**: 2026-08-30

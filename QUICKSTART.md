# Início rápido

1. Python 3.10+ e Node.js 18+ (com pnpm).
2. Duplo clique em `iniciar.bat`.
3. Navegador em http://localhost:5173
4. Cole o TXT do cliente → Importar → revisar → Gerar documentos.

Se o backend não subir:

```bat
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements_api.txt
.venv\Scripts\python api_server.py
```

Se o frontend não subir:

```bat
cd equatorial_automation_frontend
pnpm install
pnpm run dev
```

Documentos gerados: `saida/web_generated/`

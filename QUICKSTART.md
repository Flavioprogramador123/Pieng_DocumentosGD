# Início rápido

1. Python 3.11+ e Node.js 18+ (pnpm).
2. Configure `backend/.env` — mínimo: `MASTER_PASSWORD_HASH` (gerar com `python bootstrap_master_hash.py`).
3. Duplo clique em `start_all.bat` ou `iniciar.bat`.
4. Navegador em http://localhost:5180 → login `pieng`.
5. Preencha o formulário ( **número do contrato** obrigatório ) → Gerar documentos.

**Dispositivo novo:** informe o e-mail cadastrado → Enviar código → Confirmar.  
Sem SMTP em localhost, o código aparece na tela (modo dev).

## Onde ficam os arquivos

| Config | Pasta |
|--------|--------|
| `CLIENT_OUTPUT_DIR` no `.env` | Google Drive (ex.: `…/80 a 100/80 - Nome Cliente/`) |
| Vazio / Drive indisponível | `saida/web_generated/{contrato} - {nome}/` |

## Por cliente (principais)

- DOCX: memorial, procuração, contrato
- XLSX: NT.00020-05 (template com listas já escolhidas)
- `planta.dxf` — abrir no AutoCAD; mapa: Win+Shift+S → colar
- `figura_localizacao.png`, `tokens_autocad.txt`, `relatorio_preenchimento.txt`

## Se não subir

**Backend:**

```bat
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements_api.txt
.venv\Scripts\python api_server.py
```

**Frontend:**

```bat
cd equatorial_automation_frontend
pnpm install
pnpm run dev
```

Versão atual documentada: **0.5.4** — ver [CHANGELOG.md](CHANGELOG.md).

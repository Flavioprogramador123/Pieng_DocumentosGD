#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " Sistema de Automacao Equatorial Energia"
echo "========================================"

if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python3 nao encontrado."
    exit 1
fi
if ! command -v node &> /dev/null; then
    echo "ERRO: Node.js nao encontrado."
    exit 1
fi

cd "$ROOT/backend"
if [ ! -x ".venv/bin/python" ]; then
    python3 -m venv .venv
    .venv/bin/python -m pip install -q -r requirements_api.txt
fi

echo "[1/2] Backend http://127.0.0.1:5000"
.venv/bin/python api_server.py &
BACKEND_PID=$!

echo "[2/2] Frontend http://localhost:5180"
cd "$ROOT/equatorial_automation_frontend"
if [ ! -d node_modules ]; then
    pnpm install
fi
pnpm run dev &
FRONTEND_PID=$!

cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Sistema parado."
    exit 0
}
trap cleanup SIGINT

echo "PIDs: backend=$BACKEND_PID frontend=$FRONTEND_PID"
echo "Ctrl+C para parar."
wait

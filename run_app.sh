#!/bin/bash

PORT=8501
APP_DIR="/home/karolinewac/tablab_abc"
PDF_DIR="$APP_DIR/pdfs_abc"
VENV_DIR="$APP_DIR/venv"

# Ativa a venv
source "$VENV_DIR/bin/activate"

# Limpa PDFs antigos
echo "🧹 Limpando PDFs antigos em $PDF_DIR..."
rm -rf "$PDF_DIR"/*

# Finaliza processo antigo na porta, se houver
PID=$(lsof -t -i:$PORT)
if [ ! -z "$PID" ]; then
  echo "🔴 Matando processo anterior na porta $PORT (PID: $PID)..."
  kill -9 $PID
  sleep 1
fi

# Inicia o app
echo "🚀 Iniciando app Streamlit na porta $PORT..."
cd "$APP_DIR"
python3 -m streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

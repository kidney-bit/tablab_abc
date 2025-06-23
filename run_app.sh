#!/bin/bash

PORT=8501
APP_DIR="/home/karolinewac/tablab_abc"
PDF_DIR="$APP_DIR/pdfs_abc"
VENV_PATH="$APP_DIR/venv/bin/activate"

echo "🧹 Limpando PDFs antigos em $PDF_DIR..."
rm -rf "$PDF_DIR"/*

echo "🧼 Matando processos anteriores na porta $PORT..."
PID=$(lsof -t -i:$PORT)
if [ ! -z "$PID" ]; then
  echo "🔴 Matando processo (PID: $PID)..."
  kill -9 $PID
  sleep 1
fi

echo "📦 Ativando ambiente virtual..."
source "$VENV_PATH"

echo "🚀 Iniciando app Streamlit na porta $PORT..."
python3 -m streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

#!/bin/bash

PORT=8501
PDF_DIR="/home/karolinewac/tablab_abc/pdfs_abc"

echo "🧹 Limpando PDFs antigos em $PDF_DIR..."
/usr/bin/rm -rf "$PDF_DIR"/*

PID=$(/usr/bin/lsof -t -i:$PORT)

if [ ! -z "$PID" ]; then
  echo "🔴 Matando processo anterior na porta $PORT (PID: $PID)..."
  /bin/kill -9 $PID
  sleep 1
fi

echo "🚀 Iniciando app Streamlit na porta $PORT..."
/home/karolinewac/tablab_abc/venv/bin/python3 -m streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

#!/bin/bash

PORT=8501
PID=$(lsof -t -i:$PORT)

if [ ! -z "$PID" ]; then
  echo "🔴 Matando processo anterior na porta $PORT (PID: $PID)..."
  kill -9 $PID
  sleep 1
fi

echo "🚀 Iniciando app Streamlit na porta $PORT..."
python3 -m streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

#!/bin/bash

PORT=8501
PDF_DIR="/home/karolinewac/tablab_abc/pdfs_abc"
PYTHON="/home/karolinewac/tablab_abc/venv/bin/python3"
STREAMLIT="/home/karolinewac/tablab_abc/venv/bin/streamlit"

echo "🧹 Limpando PDFs antigos em $PDF_DIR..."
/usr/bin/find "$PDF_DIR" -type f -delete

echo "🧼 Matando processos anteriores na porta $PORT..."
/usr/bin/lsof -t -i:$PORT | /usr/bin/xargs -r /bin/kill -9
/bin/sleep 1

echo "🚀 Iniciando app Streamlit na porta $PORT..."
"$PYTHON" -m streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

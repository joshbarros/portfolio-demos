#!/usr/bin/env bash
set -e
cd /app
if [ ! -f data/riverbend.duckdb ]; then
  python -m riverbend.cli seed
  (cd dbt && dbt build --profiles-dir .)
fi
streamlit run riverbend/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
exec python -m riverbend.scheduler

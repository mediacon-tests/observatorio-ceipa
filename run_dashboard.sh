#!/usr/bin/env bash
# Levanta el dashboard CEIPA en segundo plano (persistente al cerrar la terminal).
# Uso:  ./run_dashboard.sh          -> arranca
#       ./run_dashboard.sh stop     -> detiene

set -e
cd "$(dirname "$0")"

LOG=/tmp/ceipa_streamlit.log
PIDFILE=/tmp/ceipa_streamlit.pid

if [[ "$1" == "stop" ]]; then
    if [[ -f "$PIDFILE" ]]; then
        kill "$(cat "$PIDFILE")" 2>/dev/null || true
        rm -f "$PIDFILE"
        echo "Dashboard detenido."
    else
        pkill -f "streamlit run src/dashboard/app.py" 2>/dev/null || true
        echo "No había PID registrado; intenté pkill."
    fi
    exit 0
fi

# Ya corriendo?
if curl -sk http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    echo "Ya está corriendo en http://localhost:8501"
    exit 0
fi

setsid nohup .venv/bin/streamlit run src/dashboard/app.py \
    --server.headless true --server.port 8501 \
    </dev/null >"$LOG" 2>&1 &

echo $! > "$PIDFILE"
sleep 6

if curl -sk http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    echo "Dashboard levantado en  http://localhost:8501"
    echo "Logs: $LOG"
    echo "Para detener: ./run_dashboard.sh stop"
else
    echo "Falló al arrancar. Últimas líneas del log:"
    tail -20 "$LOG"
    exit 1
fi

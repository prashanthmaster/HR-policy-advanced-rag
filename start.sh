#!/usr/bin/env bash
# T-8.1/T-8.4: launched as the container's single CMD.
#
# Cloud Run gives the container exactly one external port, in $PORT
# (Cloud Run sets this automatically -- do not hardcode 8080 in gcloud
# config, only here as a local-dev fallback). FastAPI/uvicorn runs
# internally on a fixed port (8000) that nothing outside the container can
# reach; Streamlit is what actually binds $PORT and is what Cloud Run's
# public URL serves. streamlit_app.py talks to the FastAPI process over
# plain localhost HTTP (API_BASE_URL, defaulting to http://localhost:8000)
# -- both processes share one container's network namespace, so this
# works without any extra networking setup.
set -euo pipefail

PORT="${PORT:-8080}"
export API_BASE_URL="http://localhost:8000"

echo "start.sh: launching FastAPI backend on :8000 ..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for the backend's /health endpoint before starting the UI, so the
# very first user request doesn't race the retriever's startup-time
# corpus parse / vector-index open. Bounded wait (60s) so a genuinely
# broken backend still surfaces as a failed Cloud Run revision instead of
# hanging forever.
echo "start.sh: waiting for FastAPI /health ..."
for i in $(seq 1 60); do
    if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
        echo "start.sh: FastAPI is up."
        break
    fi
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "start.sh: FastAPI process died during startup -- see logs above." >&2
        exit 1
    fi
    sleep 1
done

echo "start.sh: launching Streamlit UI on :$PORT ..."
exec streamlit run ui/streamlit_app.py \
    --server.port="$PORT" \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false

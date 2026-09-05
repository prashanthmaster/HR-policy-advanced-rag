# T-8.1: single container serving both the FastAPI backend (internal,
# port 8000) and the Streamlit UI (public, Cloud Run's $PORT). Cloud Run
# exposes exactly one port per service, so start.sh runs uvicorn in the
# background and streamlit in the foreground bound to $PORT -- one
# container, one image, one public URL, matching M8's exit criterion.
FROM python:3.11-slim

WORKDIR /app

# System deps: qdrant-client/flashrank/lxml pull in a few things that need
# a C toolchain on slim images; kept minimal and removed from the final
# layer isn't attempted here since this is a portfolio deploy, not a
# size-optimized production image -- correctness and clarity over a
# smaller image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Prefetch the FlashRank cross-encoder weights at BUILD time, not at
# container startup. Two reasons: (1) Cloud Run's request timeout would
# otherwise start counting during a slow first-request model download,
# and (2) the weights then live in an image layer, so a cold start never
# depends on huggingface.co being reachable at that moment. See
# retrieval/reranker.py's own docstring for the same one-time-download
# constraint this project already hit locally (Session where
# scripts/prefetch_reranker_model.py was introduced).
RUN python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-TinyBERT-L-2-v2', cache_dir='/root/.flashrank_cache')"

# Now the actual application code -- copied after the dependency layers
# above so an ordinary code change doesn't invalidate the (slow) pip
# install / model-download layers on the next build.
COPY . .

ENV PYTHONUNBUFFERED=1 \
    FLASHRANK_CACHE_DIR=/root/.flashrank_cache

EXPOSE 8080

RUN chmod +x start.sh
CMD ["./start.sh"]

# Milestone 8 — Deployment: step-by-step guide (run on your own machine)

Everything below needs real network access (OpenAI, Qdrant Cloud, Google
Cloud), which the sandboxed assistant session cannot reach. Run each block
in your own PowerShell, in the repo root (`C:\Project\HR policy RAG`), and
paste back any error output.

Do these in order — each step gates the next, so you never spend cloud
time/money on a broken local setup.

---

## Step 0 — local smoke test, no cloud involved yet

Confirm the new FastAPI + Streamlit pieces actually work against your
existing local index before touching anything remote.

```powershell
.venv-win\Scripts\Activate.ps1
$env:API_BASE_URL = "http://localhost:8000"
# Terminal 1:
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

In a second PowerShell window (same repo, same venv activated):

```powershell
.venv-win\Scripts\Activate.ps1
$env:API_BASE_URL = "http://localhost:8000"
streamlit run ui/streamlit_app.py
```

Open the URL Streamlit prints (usually http://localhost:8501), ask a real
question (e.g. one from the golden set), and confirm you get an answer.
Ctrl-C both terminals when done. If this step fails, tell me the error —
we fix it here before going anywhere near the cloud.

---

## Step 1 — Qdrant Cloud (T-8.2)

1. Go to https://cloud.qdrant.io, sign up, create a **free-tier cluster**
   (1 GB is far more than this project's ~84 points need).
2. From the cluster's dashboard, copy its **URL** (looks like
   `https://xxxxxxxx-xxxx-xxxx.us-east4-0.gcp.cloud.qdrant.io:6333`) and
   create an **API key**.
3. Add both to `.env` at the repo root:

```
QDRANT_URL=<paste the cluster URL>
QDRANT_API_KEY=<paste the API key>
```

4. Push the corpus into it (reuses your already-paid-for OpenAI
   embeddings via the existing cache — this should cost close to $0):

```powershell
.venv-win\Scripts\Activate.ps1
python scripts\build_vector_index_cloud.py
```

You should see `Built and upserted <N> unit(s) into the 'hrpolicy_clauses'
collection on Qdrant Cloud.` Paste back the output.

5. Re-run Step 0's two terminals — same commands — to confirm the app
   still works with `QDRANT_URL`/`QDRANT_API_KEY` now set in `.env` (the
   code automatically prefers Qdrant Cloud over the local index the
   moment `QDRANT_URL` is present — see api/main.py's `_build_retriever`).
   This proves the cloud index actually works *before* you deploy a
   container that depends on it.

---

## Step 2 — Google Cloud setup (one-time)

1. Install the gcloud CLI if you don't have it:
   https://cloud.google.com/sdk/docs/install (Windows installer).
2. In PowerShell:

```powershell
gcloud init
# pick or create a project when prompted, e.g. hr-policy-rag
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Paste back the project ID it lands on — I'll use it in the next commands.

---

## Step 3 — Deploy to Cloud Run (T-8.1 + T-8.3)

`gcloud run deploy --source .` builds the Dockerfile via Cloud Build and
deploys it — no local Docker installation needed at all.

```powershell
cd "C:\Project\HR policy RAG"
gcloud run deploy hr-policy-rag `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 2Gi `
  --timeout 300 `
  --set-env-vars "LANGSMITH_TRACING=true,LANGSMITH_PROJECT=hr-policy-rag" `
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,LANGSMITH_API_KEY=langsmith-api-key:latest,QDRANT_URL=qdrant-url:latest,QDRANT_API_KEY=qdrant-api-key:latest"
```

The `--set-secrets` flags reference Secret Manager secrets, not raw values
— that keeps your real keys out of the Cloud Run service config (visible
to anyone with read access to the service) and out of shell history.
Create them first:

```powershell
$env:OPENAI_API_KEY | gcloud secrets create openai-api-key --data-file=-
$env:LANGSMITH_API_KEY | gcloud secrets create langsmith-api-key --data-file=-
$env:QDRANT_URL | gcloud secrets create qdrant-url --data-file=-
$env:QDRANT_API_KEY | gcloud secrets create qdrant-api-key --data-file=-
```

(Run these from the same PowerShell where `.env` is loaded, or just paste
the raw values interactively if the env vars aren't set in this shell.)

If a secret already exists from a prior attempt, use
`gcloud secrets versions add <name> --data-file=-` instead of `create`.

The deploy command prints a **Service URL** when it finishes (something
like `https://hr-policy-rag-xxxxx-uc.a.run.app`). That's your public URL —
paste it back to me.

---

## Step 4 — Smoke test (T-8.5)

```powershell
curl "https://YOUR-SERVICE-URL/health"
```

Then open `https://YOUR-SERVICE-URL` in a browser (this hits Streamlit,
which Cloud Run's $PORT points at per `start.sh`), ask a real question,
and confirm a real answer with citations comes back.

Finally, open https://smith.langchain.com, find the `hr-policy-rag`
project, and confirm a trace exists for that exact query — that's the
second half of M8's exit criterion. Screenshot or describe what you see
and we'll record it in PROJECT_PLAN.md as the real, witnessed result.

---

## If something breaks

Cloud Run logs (most useful first stop for a crashed revision):

```powershell
gcloud run services logs read hr-policy-rag --region us-central1 --limit 100
```

Paste back whatever it shows — don't guess at the fix from the symptom
alone; per this project's own standing rule, we root-cause it for real.

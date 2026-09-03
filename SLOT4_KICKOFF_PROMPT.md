# Slot 4 Build — Kickoff Prompt

> Paste this as your opening message in the new Claude project once the build folder is attached. It carries forward everything decided in the planning session so the build starts immediately instead of re-litigating scope.

---

I'm Prashanth — ~10 years enterprise HRMS/IT delivery (Ramco Systems/Ramco Cements), laid off 31 Mar 2026, now building a 4-slot AI/ML portfolio for an applied AI Engineer career switch. This is **Slot 4: HR-Policy Advanced RAG**, one of four fixed portfolio slots (Slot 1 TechMart – frozen classical ML; Slot 2 Enterprise LLM Gateway & Cost Governance – in build; Slot 3 FinGuard-MCP – confirmed deployed, MCP + LangGraph HITL agent; Slot 4 – this project).

**Ground rule for this whole build, no exceptions:** no performance number, capability claim, or "production-grade" description goes into code comments, the README, or anything I say in an interview unless it was personally verified against a real run or test result. Don't let me (or yourself) assert a number we haven't actually measured.

## What this project is

An HR-policy / statutory-compliance RAG assistant. One-sentence pitch: *"A retrieval system that knows when a policy has been amended and refuses to answer from the superseded version."* The domain is deliberately anchored in my real HRMS delivery background (multi-country statutory/regulatory update management — Hapag-Lloyd, HAECO, Ahli Bank, Canadia Bank), not a generic document set.

## Core architecture (standard, built as original code — not inherited from any tutorial)

Chunk the corpus → dual retrieval index (BM25 keyword + semantic/vector embeddings) → merge via Reciprocal Rank Fusion → FlashRank reranking on the top candidates → CRAG-style grading (self-check: are these retrieved chunks actually good enough to answer from, or do we need a corrective re-query) → LLM generates the answer using only the retrieved, graded context, with citations back to the source clause → deployed on GCP Cloud Run with Qdrant as the vector store → LangSmith tracing on the retrieval/grading nodes so any answer's provenance is inspectable.

This core pipeline mirrors the industry-standard reference architecture on purpose — it is not where this project's differentiation lives. Do not reinvent it or add novelty here for its own sake.

## The one real differentiator — build this properly, it's the whole point

**Live document freshness / version handling**, connected to a single source: **Google Drive** (not Notion, not Jira — Drive is the only one that actually fits how HR-policy documents live; don't add the others without a specific reason). Requirements:
- Detect when a source document changes (polling is fine to start; a webhook is a nice-to-have, not required).
- Incrementally re-index only the changed document, not a full rebuild.
- Tag every chunk with an effective date / version.
- When a clause has been amended, the system must not blend old and new text — it either answers from the current version, or explicitly states "this was amended on [date], here is the current text," and must never silently answer from a superseded clause.
- This needs to be genuinely demoable: I should be able to edit a document in Drive live and show the system pick up the change correctly.

## Evaluation — four metrics, no more

Build one real golden dataset (20–30 HR-policy questions with known-correct answers and known-correct source clauses). Score against exactly:
1. **Context Precision** — of what's retrieved, how much is relevant.
2. **Context Recall** — of what's relevant, how much got retrieved.
3. **Faithfulness** — is the generated answer's claims actually grounded in what was retrieved (the hallucination check — this is the most important one for this domain).
4. **Answer Correctness** — does the final answer match the golden reference answer.

Plus one custom LLM-as-judge metric, matching the pattern already proven in FinGuard-MCP's own G-Eval harness: **Citation Accuracy** — does the answer's cited clause/section actually match what was retrieved. Gate all of this in CI so it re-runs and catches regressions automatically, the same discipline as FinGuard.

Do not add more RAGAS metrics than this (no context relevancy variants, no noise-sensitivity scoring) — four generation/retrieval metrics plus one custom one is the complete, defensible set. More metrics I can't cleanly distinguish under questioning is worse than fewer I can.

## Guardrail — reuse the eval metric, don't build a second system

The runtime guardrail is the Faithfulness score reused live: if a generated answer's faithfulness/groundedness falls below a threshold, the system declines to answer confidently rather than guessing, instead surfacing the closest matching (but insufficiently confident) source. One metric, two jobs — offline CI gate and live refusal gate. Do not build a separate standalone "guardrail agent" for this project; that framing belongs to FinGuard, not here.

## Explicitly out of scope for this build — do not add these without me raising it first

- **No multi-agent / supervisor architecture.** A single query doesn't need one, and this axis is already owned by FinGuard-MCP (multi-agent + MCP + HITL). Building it here creates unnecessary overlap with my own other slot.
- **No MCP exposure on this slot**, for the same reason — already proven in FinGuard, repeating it here adds no new signal.
- **No Notion or Jira connectors** — Drive only, unless a specific reason comes up and we discuss it.
- **No full multimodal/CLIP vision RAG.** If a table-handling need comes up (HR/statutory docs often have slab/threshold tables), the fix is lightweight: extract tables structurally and serialize rows as text, kept in a separate chunk stream — not computer vision.
- **No chatbot / conversational memory / "threads."** This is a stateless, single-turn query system by design — I already proved multi-turn conversational memory in the Agentic Chatbot project (LangGraph checkpointing, resumable HITL). Rebuilding that here is redundant, not additive. Each query is independent; nothing is remembered between them.
- **No fine-tuning/LoRA of any kind.**

## Corpus — confirm before ingestion starts

My original HR-policy documents came from my official employer laptop and are restricted — do not use them or anything reconstructed from memory of them. Use **public/statutory documents only** (e.g., India's labor codes, the POSH Act, Payment of Gratuity Act, EPF/ESI rules — pick a specific, bounded scope, not "all HR law everywhere"). I'll confirm the exact scope at the start of this session if it isn't already set.

## Build approach

Ship first, explain second. Build the working local prototype (full pipeline running end to end, defensible) before touching GCP/Qdrant Cloud Run deployment — that's a fast follow-up, not a same-day requirement. No fixed time budget for this session — go until the core is done. Explain design decisions inline as we build (why hybrid over pure semantic, why this grading threshold, why this rerank cutoff) rather than as a separate lecture; formal cold-narration defense-prep (explaining it back unaided, the way I'd have to in an interview) comes a day or two after the build stabilizes, not same-day.

## Reference docs (on my machine, Career_Transition folder)

`PROJECT_PORTFOLIO.md` and `CAREER_TRANSITION_MASTER.md` carry the full portfolio strategy and this slot's decisions in more detail if you need to check something. `AI_Engineer_14Day_Schedule.pdf` has the day-by-day time plan (Slot 4 is Days 1–7).

Let's start.

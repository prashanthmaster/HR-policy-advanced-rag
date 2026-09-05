"""
T-8.4: the minimal query UI, on top of the real FastAPI backend (api/main.py).

Deliberately dumb: this file contains NO pipeline logic of its own -- it
only collects the same structured inputs answer_query() already requires
(query, country, jurisdiction_scope, dates, wage -- see api/main.py's
QueryRequest and grading/answer_pipeline.py's own scope note on why these
aren't parsed from free text) and renders whatever the API returns. A UI
bug here can make the demo look worse; it can never make an answer more
or less correct than the API already decided.

Talks to the API over HTTP (requests), not by importing the pipeline
directly -- this is what makes "FastAPI backend + Streamlit frontend" a
real two-tier architecture rather than Streamlit secretly doing the work.
API_BASE_URL defaults to localhost:8000 for local dev (see start.sh, which
runs uvicorn on 8000 internally) and is overridden by the API_BASE_URL env
var if the two ever need to run as separate services.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="HR-Policy Advanced RAG", page_icon="\U0001F4CB", layout="centered")

st.markdown(
    """
    <style>
    .main { background: linear-gradient(180deg, #0f172a 0%, #111827 100%); }
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%); }
    .hr-title { font-size: 2.1rem; font-weight: 800; color: #4338ca; margin-bottom: 0; }
    .hr-subtitle { color: #6b7280; margin-top: 0.2rem; margin-bottom: 1.4rem; }
    .status-answered { background:#ecfdf5; border-left:6px solid #10b981; padding:1rem 1.2rem; border-radius:0.5rem; }
    .status-clarify { background:#fffbeb; border-left:6px solid #f59e0b; padding:1rem 1.2rem; border-radius:0.5rem; }
    .status-insufficient { background:#fef2f2; border-left:6px solid #ef4444; padding:1rem 1.2rem; border-radius:0.5rem; }
    .citation-pill { display:inline-block; background:#e0e7ff; color:#3730a3; border-radius:999px;
                      padding:0.15rem 0.75rem; margin:0.2rem 0.3rem 0.2rem 0; font-size:0.85rem; font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="hr-title">HR-Policy Advanced RAG</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hr-subtitle">Portfolio Slot 4 &mdash; live freshness handling, temporal reasoning, '
    "and an honest refusal when the corpus doesn't support an answer.</p>",
    unsafe_allow_html=True,
)

with st.form("query_form"):
    query = st.text_area("Your question", placeholder="e.g. What is my gratuity if I resign after 3 years in the UAE office?", height=90)

    col1, col2 = st.columns(2)
    with col1:
        country = st.selectbox("Country (optional)", ["Any", "India", "UAE", "Germany"], index=0)
    with col2:
        jurisdiction_scope = st.text_input("Jurisdiction scope (optional)", placeholder="leave blank unless you know this")

    st.caption("Fill these in only if your question depends on them (e.g. a gratuity or notice-period calculation).")
    col3, col4, col5 = st.columns(3)
    with col3:
        service_start_date = st.date_input("Service start date", value=None)
    with col4:
        valuation_date = st.date_input("As-of / termination date", value=None)
    with col5:
        monthly_wage = st.number_input("Monthly wage (optional)", min_value=0.0, value=0.0, step=1000.0)

    submitted = st.form_submit_button("Ask", use_container_width=True)

if submitted:
    if not query.strip():
        st.warning("Type a question first.")
    else:
        payload = {
            "query": query.strip(),
            "country": None if country == "Any" else country,
            "jurisdiction_scope": jurisdiction_scope.strip() or None,
            "service_start_date": service_start_date.isoformat() if service_start_date else None,
            "valuation_date": valuation_date.isoformat() if valuation_date else None,
            "monthly_wage": monthly_wage or None,
        }
        with st.spinner("Retrieving, grading, and generating..."):
            try:
                resp = requests.post(f"{API_BASE_URL}/query", json=payload, timeout=60)
                resp.raise_for_status()
                result = resp.json()
            except requests.exceptions.RequestException as exc:
                st.error(f"Couldn't reach the API backend: {exc}")
                result = None

        if result is not None:
            status = result["status"]

            if status == "ANSWERED":
                st.markdown(f'<div class="status-answered"><b>Answer</b><br>{result["answer_text"]}</div>', unsafe_allow_html=True)
                if result.get("computed_amount") is not None:
                    st.metric("Computed amount", f"{result['computed_amount']:,.2f}")
                if result.get("computed_days") is not None:
                    st.metric("Computed days", f"{result['computed_days']:,.1f}")
                if result.get("superseded_warning"):
                    st.warning(result["superseded_warning"])
                if result.get("citations"):
                    st.markdown("**Cited clauses:**")
                    st.markdown(
                        "".join(f'<span class="citation-pill">{c["clause_id"]}</span>' for c in result["citations"]),
                        unsafe_allow_html=True,
                    )

            elif status == "NEEDS_CLARIFICATION":
                st.markdown('<div class="status-clarify"><b>Needs clarification</b></div>', unsafe_allow_html=True)
                for m in result.get("missing_facts", []):
                    st.write(f"- **{m['fact']}**: {m['why']}")
                for ca in result.get("conditional_answers", []):
                    st.write(f"- If {ca['condition']}...")

            else:  # INSUFFICIENT
                st.markdown('<div class="status-insufficient"><b>The system is refusing to guess</b></div>', unsafe_allow_html=True)
                st.write("The corpus doesn't contain enough to answer this confidently. Reasons:")
                for r in result.get("insufficient_reasons", []):
                    st.write(f"- {r}")

st.divider()
st.caption(
    "Every answer above is generated by a deterministic template over retrieved, graded clauses -- "
    "no free-text LLM generation, so nothing here can hallucinate a number or a clause that isn't real."
)

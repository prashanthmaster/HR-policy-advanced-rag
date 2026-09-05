"""
T-8.4: the minimal query UI, on top of the real FastAPI backend (api/main.py).

Deliberately dumb: this file contains NO pipeline logic of its own -- it
only collects the same structured inputs answer_query() already requires
(query, country, jurisdiction_scope, dates, wage -- see api/main.py's
QueryRequest and grading/answer_pipeline.py's own scope note on why these
aren't parsed from free text) and renders whatever the API returns. A UI
bug here can make the demo look worse; it can never make an answer more
or less correct than the API already decided.

Design note (Session 10, after real user feedback on the first version):
the structured country/date/wage fields are real -- answer_query() truly
cannot parse them out of a sentence, since no NL fact-extraction step was
ever built (see grading/answer_pipeline.py's own docstring) -- but forcing
them into view up front made this look like a form, not a RAG chat. They
now live inside a collapsed "Add details" expander so the default,
first-glance experience is exactly what someone expects from a RAG demo:
type a question, hit Ask. Anyone who skips the expander on a question
that genuinely needs a date/country still gets a real NEEDS_CLARIFICATION
response from the pipeline itself explaining what's missing and why --
that's the system's own designed behaviour (Finding 5's stateless
clarification contract), not a UI failure.

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
    /* Page background -- a soft indigo gradient, not Streamlit's default dark/white */
    .stApp { background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 45%, #fdf4ff 100%); }

    /* THE ROOT CAUSE OF THE INVISIBLE LABELS: Streamlit inherits the browser/OS colour
       scheme for its own text (labels, captions, help text, markdown) independently of
       whatever we do to the page background above. On a system in dark mode, that text
       renders in a light grey meant for a dark page -- nearly invisible against this
       light gradient. Force every one of those text roles to a solid, readable dark
       colour explicitly, app-wide, rather than patching individual widgets one at a time. */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"] {
        color: #1f2937 !important;
    }

    .hr-title { font-size: 2.2rem; font-weight: 800;
                background: linear-gradient(90deg, #4338ca, #9333ea);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                margin-bottom: 0; }
    .hr-subtitle { color: #6b7280 !important; margin-top: 0.2rem; margin-bottom: 0.6rem; }
    .hr-explainer { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 0.75rem;
                     padding: 0.9rem 1.1rem; margin-bottom: 1.2rem; color: #374151 !important;
                     font-size: 0.92rem; line-height: 1.5; }
    .hr-explainer b { color: #4338ca !important; }

    /* The query form sits in its own bright white card, not directly on the gradient */
    div[data-testid="stForm"] {
        background: #ffffff; border-radius: 1rem; padding: 1.5rem 1.5rem 1rem 1.5rem;
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.08); border: 1px solid #e5e7eb;
    }

    /* Example-question chip buttons above the form */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: #eef2ff !important; color: #3730a3 !important;
        border: 1px solid #c7d2fe !important; border-radius: 999px !important;
        font-size: 0.8rem !important; padding: 0.3rem 0.9rem !important;
    }

    /* Force every text input / textarea / number input / select / date field to a light
       background with dark text, regardless of the viewer's system/browser theme. */
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-baseweb="select"],
    div[data-baseweb="select"] *,
    div[data-baseweb="input"],
    div[data-baseweb="input"] *,
    div[data-baseweb="base-input"],
    div[data-baseweb="base-input"] * {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-baseweb="select"] > div:first-child,
    div[data-baseweb="base-input"] {
        border: 1.5px solid #c7d2fe !important;
        border-radius: 0.5rem !important;
    }
    div[data-testid="stTextArea"] textarea::placeholder,
    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stDateInput"] input::placeholder {
        color: #9ca3af !important;
    }
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stDateInput"] input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.15) !important;
    }
    div[data-baseweb="select"] svg, div[data-testid="stDateInput"] svg {
        fill: #4b5563 !important; color: #4b5563 !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="popover"] *,
    div[data-baseweb="menu"], div[data-baseweb="menu"] *,
    div[data-baseweb="calendar"], div[data-baseweb="calendar"] * {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    div[data-baseweb="menu"] li:hover { background-color: #eef2ff !important; }

    /* Expander header ("Add details...") */
    div[data-testid="stExpander"] summary {
        background: #f5f3ff !important; color: #4338ca !important;
        border-radius: 0.5rem !important; font-weight: 600 !important;
    }

    /* Primary "Ask" button -- gradient, not Streamlit's default grey */
    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #4338ca, #9333ea) !important;
        color: #ffffff !important; border: none !important; border-radius: 0.6rem !important;
        font-weight: 700 !important; padding: 0.6rem 0 !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover { filter: brightness(1.08); }
    div[data-testid="stFormSubmitButton"] button p { color: #ffffff !important; }

    /* Result boxes -- explicit colour wins over the broad text-colour fix above because
       these selectors (div.status-x, div.status-x *) are more specific and declared later. */
    div.status-answered, div.status-answered * { background:#ecfdf5 !important; color:#065f46 !important; }
    div.status-answered { border-left:6px solid #10b981; padding:1rem 1.2rem; border-radius:0.5rem; }
    div.status-clarify, div.status-clarify * { background:#fffbeb !important; color:#92400e !important; }
    div.status-clarify { border-left:6px solid #f59e0b; padding:1rem 1.2rem; border-radius:0.5rem; }
    div.status-insufficient, div.status-insufficient * { background:#fef2f2 !important; color:#991b1b !important; }
    div.status-insufficient { border-left:6px solid #ef4444; padding:1rem 1.2rem; border-radius:0.5rem; }
    .citation-pill { display:inline-block; background:#e0e7ff !important; color:#3730a3 !important; border-radius:999px;
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
st.markdown(
    """
    <div class="hr-explainer">
    <b>What this is:</b> ask a plain-English HR question about employment policy in
    <b>India, the UAE, or Germany</b> (a mix of real statutory law and a fictional
    company's own policy). Type your question below and hit <b>Ask</b> &mdash; that's it
    for most questions.<br><br>
    <b>What makes this different from a normal chatbot:</b> it never guesses. If your
    question needs a fact it doesn't have (like a service start date, for a gratuity
    calculation) it will ask you for it directly instead of assuming one. If the policy
    corpus genuinely has nothing on your topic, it says so honestly instead of inventing
    an answer. Every number and clause it cites is pulled from the real underlying
    documents, never generated freely by a language model.
    </div>
    """,
    unsafe_allow_html=True,
)

EXAMPLES = [
    "I joined 1 Jan 2014 and I'm resigning 30 Sep 2026. Basic + DA is ₹3,00,000/month. India. What gratuity do I get?",
    "I've been with the DIFC entity since 2017 and I'm leaving this year. What's my end of service?",
    "How much annual leave do I get? I'm in Dubai.",
    "What paternity leave am I entitled to? I'm based in Germany.",
]

if "query_text" not in st.session_state:
    st.session_state["query_text"] = ""

st.caption("Try an example, or just type your own question below:")
chip_cols = st.columns(len(EXAMPLES))
for col, example in zip(chip_cols, EXAMPLES):
    label = example if len(example) <= 28 else example[:26] + "…"
    if col.button(label, key=f"chip_{hash(example)}", help=example, use_container_width=True):
        st.session_state["query_text"] = example

with st.form("query_form"):
    query = st.text_area(
        "Your question",
        key="query_text",
        placeholder="e.g. What is my gratuity if I resign after 3 years in the UAE office?",
        height=90,
    )

    with st.expander("Add details (only needed for some questions -- e.g. a gratuity or leave calculation)"):
        st.caption(
            "This system never guesses these from your sentence -- if your question needs one and you "
            "leave it blank, it will ask you for it instead of assuming an answer."
        )
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox("Country", ["Any", "India", "UAE", "Germany"], index=0)
        with col2:
            jurisdiction_scope = st.text_input("Jurisdiction scope", placeholder="leave blank unless you know this")

        col3, col4, col5 = st.columns(3)
        with col3:
            service_start_date = st.date_input("Service start date", value=None)
        with col4:
            valuation_date = st.date_input("As-of / termination date", value=None)
        with col5:
            monthly_wage = st.number_input("Monthly wage", min_value=0.0, value=0.0, step=1000.0)

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
                st.markdown(
                    '<div class="status-clarify"><b>Needs clarification</b> -- the system won\'t guess this, it needs one more fact from you:</div>',
                    unsafe_allow_html=True,
                )
                for m in result.get("missing_facts", []):
                    st.write(f"- **{m['fact']}**: {m['why']}")
                if result.get("conditional_answers"):
                    st.markdown("**Here's the answer for each possibility, so you don't have to come back:**")
                    for ca in result["conditional_answers"]:
                        # ca["condition"] already reads like "if country = India" -- capitalize
                        # it as its own sentence rather than prefixing a second "If".
                        condition_sentence = ca["condition"][0].upper() + ca["condition"][1:]
                        st.markdown(f"**{condition_sentence}:** {ca.get('answer_text', '(no answer text returned)')}")

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

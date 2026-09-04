"""
T-6.6 -- shared, minimal RAGAS invocation for a SINGLE live faithfulness
score (as opposed to eval/run_ragas_eval.py's T-5.3 batch of 4 metrics
over the whole golden set).

Deliberately a separate, small module rather than a refactor of
eval/run_ragas_eval.py itself: that script is already DONE and proven
against real runs (see its own docstring for the full nest_asyncio root-
cause story -- ragas 0.3.1 calls nest_asyncio.apply() unconditionally at
import time, incompatible with Python 3.11+'s asyncio.timeout()). This
project's own rule is to verify a fix against its original symptom before
trusting it; touching an already-measured, working script to satisfy DRY
for a ~10-line guard is a real risk for a marginal benefit, so the guard
is duplicated here (small, well-understood, cross-referenced) rather than
imported.
"""

from __future__ import annotations

import inspect

JUDGE_MODEL = "gpt-4o-mini"  # same locked budget model as eval/run_ragas_eval.py


def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """Real RAGAS Faithfulness score for one (question, answer, contexts)
    triple. Makes a real OpenAI call (JUDGE_MODEL) -- costs real money,
    however small. Never call this from a test; grading/faithfulness_gate.py
    takes a scorer as a parameter specifically so tests can inject a fake
    one instead."""
    try:
        import nest_asyncio as _nest_asyncio_module
        _nest_asyncio_module.apply = lambda *a, **k: None  # see module docstring
    except ImportError:
        pass

    from langchain_openai import ChatOpenAI
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.metrics import faithfulness

    llm = ChatOpenAI(model=JUDGE_MODEL, temperature=0)
    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=contexts or [""],
    )
    dataset = EvaluationDataset(samples=[sample])
    evaluate_kwargs = dict(metrics=[faithfulness], llm=llm)
    if "allow_nest_asyncio" in inspect.signature(evaluate).parameters:
        evaluate_kwargs["allow_nest_asyncio"] = False

    result = evaluate(dataset, **evaluate_kwargs)
    df = result.to_pandas()
    return float(df.iloc[0]["faithfulness"])

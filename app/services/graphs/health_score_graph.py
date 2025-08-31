# app/services/graphs/health_score_graph.py
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from pydantic import ValidationError
from app.models.health_score import HealthScoreInput, HealthScoreOutput
from app.services.gemini.gemini_healthscore import score_with_gemini

class S(dict):  # minimal graph state
    pass

def _validate_in(state: S) -> S:
    HealthScoreInput(**state["input"])  # raises if bad
    return state

def _llm_score(state: S) -> S:
    result = score_with_gemini(state["input"])
    state["result"] = result
    return state

def _validate_out(state: S) -> S:
    HealthScoreOutput(**state["result"])
    return state

def build_health_score_graph():
    g = StateGraph(S)
    g.add_node("validate_in", _validate_in)
    g.add_node("llm_score", _llm_score)
    g.add_node("validate_out", _validate_out)

    g.add_edge(START, "validate_in")
    g.add_edge("validate_in", "llm_score")
    g.add_edge("llm_score", "validate_out")
    g.add_edge("validate_out", END)
    return g.compile()

def run_health_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    graph = build_health_score_graph()
    out = graph.invoke({"input": payload})
    return out["result"]

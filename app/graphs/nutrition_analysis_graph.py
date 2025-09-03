# app/graphs/nutrition_analysis_graph.py
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, START, END
from app.services.gemini.gemini_nutrition import llm_nutrition_breakdown

class S(TypedDict):
    hint: str
    context: Dict[str, Any]
    result: Dict[str, Any]

def _validate_input(state: S) -> S:
    if "hint" not in state or not state["hint"]:
        raise ValueError("hint required (e.g., 'karaage curry bento')")
    return state

def _llm_breakdown(state: S) -> S:
    # Pass the entire state to llm_nutrition_breakdown since it expects the full input dict
    state["result"] = llm_nutrition_breakdown(state)
    return state

def _validate_output(state: S) -> S:
    # Ensure exact keys exist (surface-level validation)
    out = state["result"]
    # basic invariants: totals ~ sums (allow small rounding diffs)
    totals = {
        "kcal": sum(i["kcal"] for i in out["items_kcal"]),
        "carbs_g": sum(i["carbs_g"] for i in out["items_nutrition"]),
        "fat_g": sum(i["fat_g"] for i in out["items_nutrition"]),
        "protein_g": sum(i["protein_g"] for i in out["items_nutrition"]),
        "grams": sum(i["grams"] for i in out["items_grams"]),
    }
    def close(a, b, tol=2.0):  # allow minor rounding error
        return abs(a - b) <= tol

    assert close(out["total_kcal"], totals["kcal"]), "total_kcal mismatch"
    assert close(out["total_carbs_g"], totals["carbs_g"]), "total_carbs_g mismatch"
    assert close(out["total_fat_g"], totals["fat_g"]), "total_fat_g mismatch"
    assert close(out["total_protein_g"], totals["protein_g"]), "total_protein_g mismatch"
    assert close(out["total_grams"], totals["grams"], tol=5.0), "total_grams mismatch"
    return state

def build_nutrition_analysis_graph():
    g = StateGraph(S)
    g.add_node("validate_input", _validate_input)
    g.add_node("llm_breakdown", _llm_breakdown)
    g.add_node("validate_output", _validate_output)

    g.add_edge(START, "validate_input")
    g.add_edge("validate_input", "llm_breakdown")
    g.add_edge("llm_breakdown", "validate_output")
    g.add_edge("validate_output", END)
    return g.compile()

def run_nutrition_analysis(hint: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    graph = build_nutrition_analysis_graph()
    out = graph.invoke({"hint": hint, "context": context or {}})
    return out["result"]

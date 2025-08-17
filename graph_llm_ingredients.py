# graph_llm_ingredients.py
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
import time

from gemini_recognize import gemini_recognize_dish
from gemini_ingredients import ingredients_from_image
from gemini_calories import calories_from_ingredients

from logmeal_ingredients import ingredients_from_logmeal
import os
USE_LOGMEAL = os.getenv("USE_LOGMEAL", "1")

class S(TypedDict):
    image_paths: List[str]
    project: Optional[str]
    location: str
    model: str

    dish: str
    ingredients: List[str]
    gemini_conf: float

    items: List[Dict[str, Any]]  # [{name, grams, note?}]
    total_grams: Optional[float]
    ing_conf: Optional[float]
    ing_notes: Optional[str]

    nutr_items: List[Dict[str, Any]]   # [{name,kcal,protein_g,carbs_g,fat_g,method?}]
    total_kcal: Optional[float]
    total_protein_g: Optional[float]
    total_carbs_g: Optional[float]
    total_fat_g: Optional[float]
    kcal_conf: Optional[float]
    kcal_notes: Optional[str]

    timings: Dict[str, float]   # per-node ms
    total_ms: Optional[float]   # pipeline ms

    debug: Dict[str, Any]
    error: Optional[str]

def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000.0, 2)

def node_recognize(state: S) -> S:
    t0 = time.perf_counter()
    data = gemini_recognize_dish(state["project"], state["location"], state["model"], state["image_paths"])
    state["timings"]["recognize_ms"] = _ms(t0)

    if "error" in data:
        state["error"] = f"recognition_failed: {data.get('error')}"
        state["debug"]["rec_raw"] = data.get("raw")
        print(f"[recognize] ❌ error in {state['timings']['recognize_ms']} ms")
        return state

    state["dish"] = data.get("dish","")
    state["ingredients"] = [str(x) for x in (data.get("ingredients") or [])]
    state["gemini_conf"] = float(data.get("confidence", 0.0))

    # Print compact summary
    ing_preview = ", ".join(state["ingredients"][:6])
    print(f"[recognize] ✅ dish='{state['dish']}'  conf={state['gemini_conf']:.2f}  "
          f"ingredients=[{ing_preview}{'…' if len(state['ingredients'])>6 else ''}]  "
          f"took {state['timings']['recognize_ms']} ms")
    return state

def node_ing_quant(state: S) -> S:
    t0 = time.perf_counter()

    # Check if use_logmeal is specified in state, otherwise fall back to environment variable
    use_logmeal = state.get("use_logmeal")
    if use_logmeal is None:
        use_logmeal = USE_LOGMEAL == "1"
    
    if use_logmeal:
        # --- NEW: call LogMeal ---
        res = ingredients_from_logmeal(state["image_paths"])
        stage_name = "ing_quant(logmeal)"
    else:
        # --- fallback: your old Gemini qty node ---
        from gemini_ingredients import ingredients_from_image
        res = ingredients_from_image(
            state["project"], state["location"], state["model"], state["image_paths"],
            dish_hint=state.get("dish",""), ing_hint=state.get("ingredients", [])
        )
        stage_name = "ing_quant(gemini)"

    state["timings"]["ing_quant_ms"] = _ms(t0)

    if "error" in res:
        state["error"] = f"ingredients_failed: {res['error']}"
        state["debug"]["ingredients_raw"] = res.get("raw")
        print(f"[{stage_name}] ❌ error in {state['timings']['ing_quant_ms']} ms")
        return state

    # Map into your state
    state["items"] = res.get("items", [])
    state["total_grams"] = float(res.get("total_grams") or 0.0)
    state["ing_conf"] = float(res.get("confidence") or 0.0) if res.get("confidence") is not None else None
    state["ing_notes"] = res.get("notes")

    # Optional: if LogMeal filled dish/ingredients, keep them (don't override Gemini's if present)
    if not state.get("dish"):
        state["dish"] = res.get("dish","")
    if not state.get("ingredients"):
        state["ingredients"] = [str(x) for x in (res.get("ingredients") or [])]

    # Compact summary (kept same style)
    n_items = len(state["items"])
    oil = next((x for x in state["items"] if "oil" in (x.get("name","")).lower()), None)
    oil_g = f"{oil.get('grams',0)} g" if oil else "n/a"
    print(f"[{stage_name}] ✅ items={n_items}  total_grams={state['total_grams']:.0f} g  "
          f"conf={state['ing_conf'] if state['ing_conf'] is not None else 'n/a'}  "
          f"oil={oil_g}  took {state['timings']['ing_quant_ms']} ms")

    return state

def node_calories(state: S) -> S:
    t0 = time.perf_counter()
    if not state.get("items"):
        state["error"] = "No ingredient items."
        state["timings"]["calories_ms"] = _ms(t0)
        print(f"[calories] ❌ no items  in {state['timings']['calories_ms']} ms")
        return state

    res = calories_from_ingredients(
        state["project"], state["location"], state["model"],
        state.get("dish",""), state["items"]
    )
    state["timings"]["calories_ms"] = _ms(t0)

    if "error" in res:
        state["error"] = f"calories_failed: {res['error']}"
        state["debug"]["calories_raw"] = res.get("raw")
        print(f"[calories] ❌ error in {state['timings']['calories_ms']} ms")
        return state

    state["nutr_items"] = res.get("items", [])
    state["total_kcal"] = float(res.get("total_kcal", 0.0))
    state["total_protein_g"] = float(res.get("total_protein_g", 0.0))
    state["total_carbs_g"] = float(res.get("total_carbs_g", 0.0))
    state["total_fat_g"] = float(res.get("total_fat_g", 0.0))
    state["kcal_conf"] = float(res.get("confidence", 0.0))
    state["kcal_notes"] = res.get("notes")

    print(f"[calories] ✅ total={state['total_kcal']:.0f} kcal  P={state['total_protein_g']:.1f}g  "
          f"C={state['total_carbs_g']:.1f}g  F={state['total_fat_g']:.1f}g  "
          f"conf={state['kcal_conf']:.2f}  took {state['timings']['calories_ms']} ms")
    return state

def build_graph():
    g = StateGraph(S)
    g.add_node("recognize", node_recognize)
    g.add_node("ing_quant", node_ing_quant)
    g.add_node("calories", node_calories)

    g.set_entry_point("recognize")
    g.add_edge("recognize", "ing_quant")
    g.add_edge("ing_quant", "calories")
    g.add_edge("calories", END)
    return g.compile()

def run_pipeline(image_paths: List[str], project: Optional[str], location: str, model: str, use_logmeal: Optional[bool] = None):
    init: S = {
        "image_paths": image_paths,
        "project": project,
        "location": location,
        "model": model,
        "use_logmeal": use_logmeal,  # Add the use_logmeal parameter to state
        "dish": "", "ingredients": [], "gemini_conf": 0.0,
        "items": [], "total_grams": None, "ing_conf": None, "ing_notes": None,
        "nutr_items": [], "total_kcal": None, "total_protein_g": None, "total_carbs_g": None, "total_fat_g": None,
        "kcal_conf": None, "kcal_notes": None,
        "timings": {},
        "total_ms": None,
        "debug": {}, "error": None
    }

    t0_total = time.perf_counter()
    graph = build_graph()
    out = graph.invoke(init)
    out["total_ms"] = round((time.perf_counter() - t0_total) * 1000.0, 2)

    print(f"[pipeline] ⏱ total {out['total_ms']} ms "
          f"(recognize {out['timings'].get('recognize_ms','?')} ms, "
          f"ing_quant {out['timings'].get('ing_quant_ms','?')} ms, "
          f"calories {out['timings'].get('calories_ms','?')} ms)")

    return out

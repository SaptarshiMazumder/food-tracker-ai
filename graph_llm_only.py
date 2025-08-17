# graph_llm_only.py
from typing import TypedDict, Optional, Dict, Any, List
import numpy as np
import cv2
from langgraph.graph import StateGraph, END

from gemini_recognize import gemini_recognize_dish
from gemini_mass import mass_from_image
from nutrition import lookup_kcal_for_dish, calories_for_grams

class S(TypedDict):
    image_path: str
    project: str | None
    location: str
    model: str

    # recognition
    dish: str
    ingredients: List[str]
    gemini_conf: float

    # grams (LLM only)
    grams_low: Optional[float]
    grams_high: Optional[float]
    llm_conf: Optional[float]
    llm_notes: Optional[str]

    # nutrition
    kcal_per_100g: Optional[float]
    kcal_low: Optional[float]
    kcal_high: Optional[float]
    picked_food_desc: Optional[str]

    overlay_path: Optional[str]
    debug: Dict[str, Any]
    error: Optional[str]

# --- nodes ---
def node_recognize(state: S) -> S:
    data = gemini_recognize_dish(state["project"], state["location"], state["model"], state["image_path"])
    if "error" in data:
        state["error"] = f"recognition_failed: {data.get('error')}"
        state["debug"]["rec_raw"] = data.get("raw")
        return state
    state["dish"] = data["dish"]
    state["ingredients"] = data["ingredients"]
    state["gemini_conf"] = float(data["confidence"])
    return state

def node_llm_mass(state: S) -> S:
    res = mass_from_image(state["project"], state["location"], state["model"],
                          state["image_path"], dish=state.get("dish",""), ingredients=state.get("ingredients",[]))
    if "error" in res:
        state["error"] = f"mass_failed: {res['error']}"
        state["debug"]["mass_raw"] = res.get("raw")
        return state
    state["grams_low"] = float(res["grams_low"])
    state["grams_high"] = float(res["grams_high"])
    state["llm_conf"] = float(res.get("confidence", 0.6))
    state["llm_notes"] = res.get("notes")
    return state

def node_nutrition(state: S) -> S:
    if state.get("grams_low") is None or state.get("grams_high") is None:
        state["error"] = "No grams estimate."
        return state
    res = lookup_kcal_for_dish(state.get("dish",""), state.get("ingredients", []))
    if "error" in res:
        state["debug"]["nutrition_error"] = res
        return state
    state["kcal_per_100g"] = float(res["kcal_per_100g"])
    cal = calories_for_grams(state["grams_low"], state["grams_high"], state["kcal_per_100g"])
    state["kcal_low"] = float(cal["kcal_low"])
    state["kcal_high"] = float(cal["kcal_high"])
    state["picked_food_desc"] = res.get("description")
    return state

def node_overlay(state: S) -> S:
    # simple overlay with dish + grams + kcal (no masks)
    img = cv2.imdecode(np.fromfile(state["image_path"], dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        state["error"] = "Failed to read image for overlay."
        return state
    h, w = img.shape[:2]
    pad = 12
    lines = [
        f"dish: {state.get('dish') or '(unknown)'}",
        f"grams: {state['grams_low']:.0f}–{state['grams_high']:.0f} g" if state.get("grams_low") is not None else None,
        (f"calories: {state['kcal_low']:.0f}–{state['kcal_high']:.0f} kcal "
         f"(per 100g: {state['kcal_per_100g']:.0f})") if state.get("kcal_low") is not None else None,
    ]
    lines = [x for x in lines if x]
    if lines:
        bw = max(380, 16*max(len(x) for x in lines))
        box_h = 30 + 26*len(lines)
        cv2.rectangle(img, (10,10), (10+bw, 10+box_h), (255,255,255), -1)
        y = 35
        for t in lines:
            cv2.putText(img, t, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2, cv2.LINE_AA)
            y += 26
    out = state["image_path"].rsplit(".",1)[0] + "_llm_overlay.jpg"
    cv2.imencode(".jpg", img)[1].tofile(out)
    state["overlay_path"] = out
    return state

def build_graph():
    g = StateGraph(S)
    g.add_node("recognize", node_recognize)
    g.add_node("llm_mass", node_llm_mass)
    g.add_node("nutrition", node_nutrition)
    g.add_node("overlay", node_overlay)

    g.set_entry_point("recognize")
    g.add_edge("recognize", "llm_mass")
    g.add_edge("llm_mass", "nutrition")
    g.add_edge("nutrition", "overlay")
    g.add_edge("overlay", END)
    return g.compile()

def run_pipeline(image_path: str, project: Optional[str], location: str, model: str):
    init: S = {
        "image_path": image_path,
        "project": project,
        "location": location,
        "model": model,
        "dish": "", "ingredients": [], "gemini_conf": 0.0,
        "grams_low": None, "grams_high": None, "llm_conf": None, "llm_notes": None,
        "kcal_per_100g": None, "kcal_low": None, "kcal_high": None, "picked_food_desc": None,
        "overlay_path": None,
        "debug": {}, "error": None
    }
    graph = build_graph()
    return graph.invoke(init)

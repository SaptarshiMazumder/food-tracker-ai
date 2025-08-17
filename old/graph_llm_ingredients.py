# graph_llm_ingredients.py
from typing import TypedDict, Optional, Dict, Any, List
import numpy as np, cv2
from langgraph.graph import StateGraph, END

from gemini_recognize import gemini_recognize_dish
from gemini_ingredients import ingredients_from_image
from gemini_calories import calories_from_ingredients

class S(TypedDict):
    image_path: str
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

    kcal_items: List[Dict[str, Any]]  # [{name,kcal,method?}]
    total_kcal: Optional[float]
    kcal_conf: Optional[float]
    kcal_notes: Optional[str]

    overlay_path: Optional[str]
    debug: Dict[str, Any]
    error: Optional[str]

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

def node_ing_quant(state: S) -> S:
    res = ingredients_from_image(state["project"], state["location"], state["model"],
                                 state["image_path"], dish_hint=state.get("dish",""),
                                 ing_hint=state.get("ingredients", []))
    if "error" in res:
        state["error"] = f"ingredients_failed: {res['error']}"
        state["debug"]["ingredients_raw"] = res.get("raw")
        return state
    state["items"] = res["items"]
    state["total_grams"] = float(res["total_grams"])
    state["ing_conf"] = float(res.get("confidence", 0.6))
    state["ing_notes"] = res.get("notes")
    return state

def node_calories(state: S) -> S:
    if not state.get("items"):
        state["error"] = "No ingredient items."
        return state
    res = calories_from_ingredients(state["project"], state["location"], state["model"],
                                    state.get("dish",""), state["items"])
    if "error" in res:
        state["error"] = f"calories_failed: {res['error']}"
        state["debug"]["calories_raw"] = res.get("raw")
        return state
    state["kcal_items"] = res["items"]
    state["total_kcal"] = float(res["total_kcal"])
    state["kcal_conf"] = float(res.get("confidence", 0.6))
    state["kcal_notes"] = res.get("notes")
    return state

def node_overlay(state: S) -> S:
    img = cv2.imdecode(np.fromfile(state["image_path"], dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        state["error"] = "Failed to read image."
        return state
    lines = [
        f"dish: {state.get('dish') or '(unknown)'} (conf {state.get('gemini_conf',0.0):.2f})",
        f"total: {state.get('total_grams',0):.0f} g  |  {state.get('total_kcal',0):.0f} kcal"
    ]
    w = max(420, 12*max(len(x) for x in lines))
    h = 30 + 26*len(lines)
    cv2.rectangle(img, (10,10), (10+w, 10+h), (255,255,255), -1)
    y=35
    for t in lines:
        cv2.putText(img, t, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2, cv2.LINE_AA)
        y+=26
    out = state["image_path"].rsplit(".",1)[0] + "_ing_overlay.jpg"
    cv2.imencode(".jpg", img)[1].tofile(out)
    state["overlay_path"] = out
    return state

def build_graph():
    g = StateGraph(S)
    g.add_node("recognize", node_recognize)
    g.add_node("ing_quant", node_ing_quant)
    g.add_node("calories", node_calories)
    g.add_node("overlay", node_overlay)

    g.set_entry_point("recognize")
    g.add_edge("recognize", "ing_quant")
    g.add_edge("ing_quant", "calories")
    g.add_edge("calories", "overlay")
    g.add_edge("overlay", END)
    return g.compile()

def run_pipeline(image_path: str, project: Optional[str], location: str, model: str):
    init: S = {
        "image_path": image_path,
        "project": project,
        "location": location,
        "model": model,
        "dish": "", "ingredients": [], "gemini_conf": 0.0,
        "items": [], "total_grams": None, "ing_conf": None, "ing_notes": None,
        "kcal_items": [], "total_kcal": None, "kcal_conf": None, "kcal_notes": None,
        "overlay_path": None, "debug": {}, "error": None
    }
    graph = build_graph()
    return graph.invoke(init)

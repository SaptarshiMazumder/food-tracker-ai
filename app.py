# pip install langgraph langchain requests pillow numpy
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import base64, io, requests
from PIL import Image
from combo_vision import vision_detect_combo
# ---------- State ----------
class S(TypedDict):
    image_b64: str
    dish_guess: str
    ingredients_guess: List[str]
    portion_grams: float
    kcal_per_100g: Optional[float]
    calories: Optional[int]
    route: str
    debug: Dict[str, Any]

# ---------- Vision (swap with your favorite) ----------
# Option A (hosted): call your multimodal model -> {dish, ingredients[]}
# Option B (local): OpenCLIP/Food101 classifier + simple rules
def vision_detect(state):
    out = vision_detect_combo(state["image_b64"])
    state["dish_guess"] = out["dish_guess"]
    state["ingredients_guess"] = out["ingredients_guess"]
    state["debug"]["vision"] = {
        "labels_topk": out["labels_topk"],
        "conf_topk": out["conf_topk"],
        "caption": out["caption"],
        "confidence": out["confidence"]
    }
    return state

# ---------- Portion Estimator ----------
# Start simple; upgrade later (plate diameter ref, hand/palm reference, or depth model)
CANONICAL_PORTIONS = {
    "margherita pizza": 320,  # grams per slice (generous slice)
    "pizza": 300,
    "ramen": 480,
}
def portion_estimator(state: S) -> S:
    g = CANONICAL_PORTIONS.get(state["dish_guess"], 350.0)
    state["portion_grams"] = float(g)
    state["debug"]["portion"] = {"grams": g}
    return state

# ---------- Nutrition lookup (USDA/Edamam or any source) ----------
# Example: pluggable adapter. Keep it deterministic.
USDA_API_KEY = "YOUR_FDC_KEY"

def usda_search_foods(query: str) -> Optional[float]:
    """Return kcal per 100g for the best match, or None."""
    # NOTE: Swap with your real call. Here is the exact wire you’d implement:
    # r = requests.get(
    #   "https://api.nal.usda.gov/fdc/v1/foods/search",
    #   params={"api_key": USDA_API_KEY, "query": query, "pageSize": 1}
    # )
    # Parse to find energy kcal per 100g (common for FDC branded/legacy entries).
    return None  # placeholder for now

# Fuzzy map for when exact dish fails
FUZZY_CANONICAL = {
    "margherita pizza": ["pizza margherita", "cheese pizza", "pizza"],
    "ramen": ["ramen pork", "ramen noodle soup", "ramen, meat"]
}

FALLBACK_TABLE = {
    # Safe static fallbacks if API down (kcal/100g)
    "margherita pizza": 266.0,
    "pizza": 266.0,
    "ramen": 130.0,
}

def nutrition_lookup_strict(state: S) -> S:
    kcal = usda_search_foods(state["dish_guess"])
    state["kcal_per_100g"] = kcal
    state["route"] = "strict" if kcal else ""
    return state

def nutrition_lookup_fuzzy(state: S) -> S:
    if state.get("kcal_per_100g"):
        return state
    for alt in FUZZY_CANONICAL.get(state["dish_guess"], []):
        kcal = usda_search_foods(alt)
        if kcal:
            state["kcal_per_100g"] = kcal
            state["route"] = "fuzzy"
            return state
    # Final static fallback
    state["kcal_per_100g"] = FALLBACK_TABLE.get(state["dish_guess"])
    state["route"] = "fallback" if state["kcal_per_100g"] else "none"
    return state

# ---------- Compute calories ----------
def calorie_compute(state: S) -> S:
    per100 = state.get("kcal_per_100g")
    grams = state.get("portion_grams", 0)
    if per100:
        cals = int(round(per100 * (grams / 100.0)))
        state["calories"] = cals
    else:
        state["calories"] = None
    state["debug"]["calc"] = {"kcal_100g": per100, "grams": grams}
    return state

# ---------- Graph ----------
from langgraph.graph import StateGraph
g = StateGraph(S)
g.add_node("vision_detect", vision_detect)
g.add_node("portion_estimator", portion_estimator)
g.add_node("nutrition_lookup_strict", nutrition_lookup_strict)
g.add_node("nutrition_lookup_fuzzy", nutrition_lookup_fuzzy)
g.add_node("calorie_compute", calorie_compute)

g.set_entry_point("vision_detect")
g.add_edge("vision_detect", "portion_estimator")
g.add_edge("portion_estimator", "nutrition_lookup_strict")
g.add_edge("nutrition_lookup_strict", "nutrition_lookup_fuzzy")
g.add_edge("nutrition_lookup_fuzzy", "calorie_compute")
g.add_edge("calorie_compute", END)
graph = g.compile()

def run(image_b64: str) -> Dict[str, Any]:
    out = graph.invoke({
        "image_b64": image_b64,
        "dish_guess": "",
        "ingredients_guess": [],
        "portion_grams": 0.0,
        "kcal_per_100g": None,
        "calories": None,
        "route": "",
        "debug": {}
    })
    return {
        "dish": out["dish_guess"],
        "portionGrams": out["portion_grams"],
        "kcalPer100g": out["kcal_per_100g"],
        "caloriesEstimate": out["calories"],
        "route": out["route"],
        "debug": out["debug"]
    }

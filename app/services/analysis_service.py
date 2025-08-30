import time
from typing import List, Dict, Any, Generator
from flask import current_app

from ..utils.helpers import fnum, normalize_name, sse_pack, call_with_heartbeat
from ..models.analysis import (
    AnalyzeItemGrams, AnalyzeItemKcal, AnalyzeNutritionItem, 
    AnalyzeItemDensity, AnalysisResponse
)

# Import external modules
from ..services.graph_llm_ingredients import run_pipeline
from ..services.gemini.gemini_recognize import gemini_recognize_dish
from ..services.gemini.gemini_ingredients import ingredients_from_image
from ..services.gemini.gemini_calories import calories_from_ingredients

class AnalysisService:
    """Service for handling food analysis operations"""
    
    def __init__(self):
        self.project = current_app.config['GOOGLE_CLOUD_PROJECT']
        self.location = current_app.config['GOOGLE_CLOUD_LOCATION']
        self.default_model = current_app.config['DEFAULT_MODEL']
    
    def run_full_analysis(self, image_paths: List[str], model: str) -> Dict[str, Any]:
        """Run complete analysis pipeline"""
        try:
            res = run_pipeline(image_paths, self.project, self.location, model)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Pipeline exception: {str(e)}")
            print(f"[ERROR] Full traceback: {error_details}")
            return {"error": "pipeline_exception", "msg": str(e), "details": error_details}
        
        if res.get("error"):
            return {"error": res["error"], "dish": res.get("dish")}
        
        return res
    
    def finalize_payload(self, res: Dict[str, Any], save_paths: List[str]) -> Dict[str, Any]:
        """Convert raw analysis result to final API payload"""
        # normalize grams
        grams_items = []
        for it in (res.get("items") or []):
            grams_items.append({
                "name": it.get("name"),
                "grams": fnum(it.get("grams")),
                **({"note": it["note"]} if it.get("note") else {})
            })

        nutr_items = (res.get("nutr_items") or [])

        nutr_map = {normalize_name(it.get("name", "")): it for it in nutr_items}
        ordered_nutrition = []
        for g in grams_items:
            key = normalize_name(g["name"])
            ni = nutr_map.get(key, {})
            ordered_nutrition.append({
                "name": g["name"],
                "kcal": fnum(ni.get("kcal")),
                "protein_g": fnum(ni.get("protein_g")),
                "carbs_g": fnum(ni.get("carbs_g")),
                "fat_g": fnum(ni.get("fat_g")),
                **({"method": ni["method"]} if ni.get("method") else {})
            })

        # densities
        densities = []
        for g, n in zip(grams_items, ordered_nutrition):
            grams_val = g["grams"] or 0.0
            if grams_val > 0:
                densities.append({
                    "name": g["name"],
                    "kcal_per_g": round(n["kcal"] / grams_val, 4),
                    "protein_per_g": round(n["protein_g"] / grams_val, 4),
                    "carbs_per_g": round(n["carbs_g"] / grams_val, 4),
                    "fat_per_g": round(n["fat_g"] / grams_val, 4),
                })
            else:
                densities.append({
                    "name": g["name"], 
                    "kcal_per_g": 0, 
                    "protein_per_g": 0, 
                    "carbs_per_g": 0, 
                    "fat_per_g": 0
                })

        return {
            "dish": res.get("dish"),
            "dish_confidence": round(fnum(res.get("gemini_conf")), 2),
            "ingredients_detected": res.get("ingredients", []),

            "items_grams": grams_items,
            "total_grams": fnum(res.get("total_grams")),
            "grams_confidence": round(fnum(res.get("ing_conf")), 2),

            "items_nutrition": ordered_nutrition,
            "items_kcal": [{
                "name": it["name"], 
                "kcal": fnum(it["kcal"]), 
                **({"method": it["method"]} if it.get("method") else {})
            } for it in ordered_nutrition],
            "items_density": densities,

            "total_kcal": fnum(res.get("total_kcal")),
            "total_protein_g": fnum(res.get("total_protein_g")),
            "total_carbs_g": fnum(res.get("total_carbs_g")),
            "total_fat_g": fnum(res.get("total_fat_g")),
            "kcal_confidence": round(fnum(res.get("kcal_conf")), 2),

            "notes": res.get("kcal_notes") or res.get("ing_notes"),
            "angles_used": len(save_paths),

            "timings": res.get("timings", {}),
            "total_ms": res.get("total_ms", 0.0),
        }
    
    def stream_analysis(self, image_paths: List[str], model: str) -> Generator[str, None, None]:
        """Stream analysis results via SSE"""
        timings: Dict[str, float] = {}
        state: Dict[str, Any] = {"timings": timings}
        t_total = time.perf_counter()

        # -------- recognize --------
        t0 = time.perf_counter()
        rec = yield from call_with_heartbeat(
            lambda: gemini_recognize_dish(self.project, self.location, model, image_paths)
        )
        timings["recognize_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in rec:
            yield sse_pack("error", {"stage": "recognize", "msg": rec.get("error")})
            yield sse_pack("done", {"error": "recognition_failed"})
            return

        state["dish"] = rec.get("dish", "")
        state["ingredients_detected"] = [str(x) for x in (rec.get("ingredients") or [])]
        state["dish_confidence"] = round(fnum(rec.get("confidence")), 2)
        yield sse_pack("recognize", {
            "dish": state["dish"],
            "dish_confidence": state["dish_confidence"],
            "ingredients_detected": state["ingredients_detected"],
            "timings": timings
        })

        # -------- ing_quant --------
        t0 = time.perf_counter()
        
        # Use Gemini for ingredient detection
        ing = yield from call_with_heartbeat(
            lambda: ingredients_from_image(
                self.project, self.location, model, image_paths,
                dish_hint=state["dish"], ing_hint=state["ingredients_detected"]
            )
        )
        timings["ing_quant_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in ing:
            yield sse_pack("error", {"stage": "ing_quant", "msg": ing.get("error")})
            yield sse_pack("done", {"error": "ingredients_failed"})
            return

        items_grams = []
        for it in (ing.get("items") or []):
            items_grams.append({
                "name": it.get("name"),
                "grams": fnum(it.get("grams")),
                **({"note": it["note"]} if it.get("note") else {})
            })
        state["items"] = items_grams
        state["total_grams"] = fnum(ing.get("total_grams"))
        state["grams_confidence"] = round(fnum(ing.get("confidence")), 2)
        state["ing_notes"] = ing.get("notes")

        yield sse_pack("ing_quant", {
            "items_grams": items_grams,
            "total_grams": state["total_grams"],
            "grams_confidence": state["grams_confidence"],
            "notes": state["ing_notes"],
            "timings": timings
        })

        # -------- calories --------
        t0 = time.perf_counter()
        cal = yield from call_with_heartbeat(
            lambda: calories_from_ingredients(self.project, self.location, model, state["dish"], state["items"])
        )
        timings["calories_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in cal:
            yield sse_pack("error", {"stage": "calories", "msg": cal.get("error")})
            yield sse_pack("done", {"error": "calories_failed"})
            return

        # fold calories into a final payload identical to /analyze
        state.update({
            "nutr_items": cal.get("items", []),
            "total_kcal": fnum(cal.get("total_kcal")),
            "total_protein_g": fnum(cal.get("total_protein_g")),
            "total_carbs_g": fnum(cal.get("total_carbs_g")),
            "total_fat_g": fnum(cal.get("total_fat_g")),
            "kcal_conf": fnum(cal.get("confidence")),
            "kcal_notes": cal.get("notes"),
            "gemini_conf": state.get("dish_confidence", 0.0),
            "ingredients": state.get("ingredients_detected", []),
        })
        total_ms = round((time.perf_counter() - t_total) * 1000.0, 2)

        # build full API payload
        final_payload = self.finalize_payload(
            {
                "dish": state["dish"],
                "ingredients": state["ingredients"],
                "gemini_conf": state.get("gemini_conf"),
                "items": state["items"],
                "total_grams": state.get("total_grams"),
                "ing_conf": state.get("grams_confidence"),
                "ing_notes": state.get("ing_notes"),
                "nutr_items": state["nutr_items"],
                "total_kcal": state["total_kcal"],
                "total_protein_g": state["total_protein_g"],
                "total_carbs_g": state["total_carbs_g"],
                "total_fat_g": state["total_fat_g"],
                "kcal_conf": state["kcal_conf"],
                "kcal_notes": state["kcal_notes"],
                "timings": timings,
                "total_ms": total_ms,
            },
            image_paths,
        )

        # emit the calories event (useful if UI wants to update before 'done')
        yield sse_pack("calories", {
            "items_nutrition": final_payload["items_nutrition"],
            "items_kcal": final_payload["items_kcal"],
            "items_density": final_payload["items_density"],
            "total_kcal": final_payload["total_kcal"],
            "total_protein_g": final_payload["total_protein_g"],
            "total_carbs_g": final_payload["total_carbs_g"],
            "total_fat_g": final_payload["total_fat_g"],
            "kcal_confidence": final_payload["kcal_confidence"],
            "notes": final_payload.get("notes"),
            "timings": timings,
        })

        yield sse_pack("done", final_payload)

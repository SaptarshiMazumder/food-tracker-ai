import time
from typing import List, Dict, Any, Generator

from ...utils.helpers import fnum, sse_pack, call_with_heartbeat
from ...services.gemini.gemini_recognize import gemini_recognize_dish
from .food_analysis_ingredient_quantifier_factory import FoodAnalysisIngredientQuantifierFactory
from ...services.gemini.gemini_calories import calories_from_ingredients
from .food_analysis_config import FoodAnalysisConfig
from .food_analysis_formatter import FoodAnalysisFormatter


class FoodAnalysisStreamer:
    """Handles real-time streaming of food analysis results via SSE"""
    
    def __init__(self, config: FoodAnalysisConfig):
        self.config = config
    
    def stream_analysis(self, image_paths: List[str], model: str) -> Generator[str, None, None]:
        """Stream analysis results via SSE"""
        timings: Dict[str, float] = {}
        state: Dict[str, Any] = {"timings": timings}
        t_total = time.perf_counter()

        # -------- recognize --------
        t0 = time.perf_counter()
        rec = yield from call_with_heartbeat(
            lambda: gemini_recognize_dish(self.config.project, self.config.location, model, image_paths)
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
        
        # Use configured provider for ingredient detection
        quantifier = FoodAnalysisIngredientQuantifierFactory.create_quantifier()
        ing = yield from call_with_heartbeat(
            lambda: quantifier.quantify_ingredients(
                self.config.project, self.config.location, model, image_paths,
                dish_hint=state["dish"], ing_hint=state["ingredients_detected"]
            )
        )
        timings["ing_quant_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in ing:
            yield sse_pack("error", {"stage": "ing_quant", "msg": ing.get("error")})
            yield sse_pack("done", {"error": "ingredients_failed"})
            return

        items_grams = FoodAnalysisFormatter.normalize_grams_items(ing.get("items"))
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
            lambda: calories_from_ingredients(self.config.project, self.config.location, model, state["dish"], state["items"])
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
        final_payload = FoodAnalysisFormatter.create_final_payload(
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

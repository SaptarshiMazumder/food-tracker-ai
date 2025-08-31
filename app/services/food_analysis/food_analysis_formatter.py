from typing import List, Dict, Any

from ...utils.helpers import fnum, normalize_name


class FoodAnalysisFormatter:
    """Handles data formatting and response payload creation"""
    
    @staticmethod
    def normalize_grams_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize grams items with proper formatting"""
        grams_items = []
        for it in (items or []):
            grams_items.append({
                "name": it.get("name"),
                "grams": fnum(it.get("grams")),
                **({"note": it["note"]} if it.get("note") else {})
            })
        return grams_items
    
    @staticmethod
    def build_nutrition_items(grams_items: List[Dict[str, Any]], nutr_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build ordered nutrition items from grams and nutrition data"""
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
        return ordered_nutrition
    
    @staticmethod
    def calculate_densities(grams_items: List[Dict[str, Any]], nutrition_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate density values for each item"""
        densities = []
        for g, n in zip(grams_items, nutrition_items):
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
        return densities
    
    @staticmethod
    def create_final_payload(res: Dict[str, Any], save_paths: List[str]) -> Dict[str, Any]:
        """Convert raw analysis result to final API payload"""
        grams_items = FoodAnalysisFormatter.normalize_grams_items(res.get("items"))
        nutr_items = res.get("nutr_items") or []
        ordered_nutrition = FoodAnalysisFormatter.build_nutrition_items(grams_items, nutr_items)
        densities = FoodAnalysisFormatter.calculate_densities(grams_items, ordered_nutrition)

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

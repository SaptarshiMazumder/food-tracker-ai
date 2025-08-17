from typing import Callable, Dict
import pandas as pd

# Adapters return a DataFrame with at least these columns:
# id (str), dish_name (str), ingredients (List[str]), cooking_method (str|""),
# cuisine (str|""), language (str|""), image_url (str|""), source_dataset (str)

Loader = Callable[..., pd.DataFrame]

from .mm_food_100k import load as load_mmfood
from .gurumurthy_cooking_recipe import load as load_gurumurthy

ADAPTERS: Dict[str, Loader] = {
    "mmfood": load_mmfood,
    "gurumurthy": load_gurumurthy,
}
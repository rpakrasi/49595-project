import json

def save_recipe_json(recipe: dict, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)

def validate_recipe(recipe: dict) -> bool:
    return (
        isinstance(recipe.get("title"), str)
        and isinstance(recipe.get("ingredients_raw"), list)
        and len(recipe["ingredients_raw"]) > 0
        and isinstance(recipe.get("instructions"), list)
        and len(recipe["instructions"]) > 0
    )

def print_recipe_summary(recipe: dict):
    print("\n--- Recipe Summary ---")
    print("Title:", recipe["title"])
    print("Ingredients:", len(recipe["ingredients_raw"]))
    print("Steps:", len(recipe["instructions"]))
    print("Source:", recipe["metadata"]["host"])

import re

def normalize_ingredient(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()
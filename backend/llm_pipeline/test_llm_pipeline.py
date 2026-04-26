import ast

from backend.data_extraction import extract_recipe
from backend.llm_pipeline.llm import gpt
from backend.semantic_parsing.ingredient_parser import process_recipe


def test_llm_pipeline():
    website_name = "Food.com - Best Banana Bread"
    recipe_url = "https://www.food.com/recipe/best-banana-bread-2886"
    user_prompt = "Make it vegan"

    print(f"\n{'=' * 80}")
    print(f"TESTING: {website_name}")
    print(f"URL: {recipe_url}")
    print(f"{'=' * 80}\n")

    # Part 1
    enriched_recipe = process_recipe(extract_recipe(recipe_url))
    for ing in enriched_recipe['ingredients'][:3]:
        print(f"    • {ing}")
    for ing in enriched_recipe['instructions'][:3]:
        print(f"    • {ing}")

    # Part 2
    adapted_recipe = gpt(enriched_recipe, user_prompt)

    subs = adapted_recipe["adaptation_summary"].get("substitutions_made", [])
    if subs:
        print(f"    Substitutions made: {len(subs)}")
        for sub in subs[:3]:  # Show first 3
            print(f"      • {sub}")


from flask import Flask, request, jsonify
from flask_cors import CORS
import math

from backend.data_extraction.scraper import extract_recipe
from backend.semantic_parsing.ingredient_parser import process_recipe
from backend.recipe_generation.recipe_generator import RecipeGenerator

app = Flask(__name__)
CORS(app)

def clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        return obj

@app.post("/api/recipe/compare")
def compare_recipe():
    data = request.get_json(force=True)
    recipe_url = data.get("url", "").strip()
    constraint = data.get("constraint", "").strip()

    if not recipe_url:
        return jsonify({"error": "Missing recipe URL"}), 400

    try:
        original_recipe = extract_recipe(recipe_url)
        enriched_recipe = process_recipe(original_recipe)

        generator = RecipeGenerator(use_llm=False)
        adapted_recipe = generator.generate(enriched_recipe, constraint or "Make it vegan")

        return jsonify({
            "original_recipe": clean_for_json(enriched_recipe),
            "adapted_recipe": clean_for_json(adapted_recipe),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
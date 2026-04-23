import json

from backend.semantic_parsing.ingredient_parser import process_recipe

if __name__ == "__main__":
    sample_scraper_output = {
        "title": "Classic Chocolate Chip Cookies",
        "source_url": "https://example.com/cookies",
        "ingredients_raw": [
            "2 ¼ cups all-purpose flour",
            "1 tsp baking soda",
            "1 tsp salt",
            "1 cup (2 sticks) butter, softened",
            "¾ cup granulated sugar",
            "¾ cup packed brown sugar",
            "2 large eggs",
            "2 tsp vanilla extract",
            "2 cups chocolate chips",
            "½ cup chopped walnuts (optional)",
            "1 (8 ounce) box elbow macaroni",
        ]
    }

    result = process_recipe(sample_scraper_output)
    print(json.dumps(result, indent=2, default=str))

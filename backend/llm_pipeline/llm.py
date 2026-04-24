import ast
import sys

# Ensure Windows console can print UTF-8 log symbols.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import openai
import backend.llm_pipeline.keys as keys

done = False
written = True
client = openai.AzureOpenAI(
    azure_endpoint=keys.azure_openai_endpoint,
    api_key=keys.azure_openai_key,
    api_version=keys.azure_openai_api_version
)

format = """"{
            "instructions": list like ['Preheat oven to 350°F (175°C).', 'In a large bowl, mix flour, sugar, and salt.'],
            "ingredients": list like [{'raw': '1/2 cup butter, softened', 'qty': 0.5, 'unit': 'cup', 'name': 'butter', 'functional_role': 'fat', 'modifiers': ['softened'], 'confidence': 1.0, 'notes': []}],
            "adaptation_summary": {
                "parsed_constraints": {
                    "dietary": list like ['vegan', 'gluten-free'],
                    "allergies": list like ['eggs', 'peanuts'],
                    "exclude": list like ['salt'],
                    "preferences": list like ['lower heat'],
                },
                "substitutions_made": list like [{'new_qty': 1.0, 'original_ingredient': {'confidence': 1.0, 'functional_role': 'fat', 'modifiers': [], 'name': 'butter', 'qty': 1.0, 'raw': '1 cup butter', 'unit': 'cup'}, 'original_qty': 1.0, 'quantity_adjusted': False, 'reason': 'adapted for constraints: vegan', 'substituted_ingredient': {'confidence': 1.0, 'functional_role': 'fat', 'modifiers': [], 'name': 'coconut oil', 'original_name': 'butter', 'qty': 1.0, 'raw': '1 cup butter', 'substitution_notes': '1:1 ratio by weight; similar consistency; adds subtle coconut flavor (use refined oil for neutral taste)', 'swap_ratio': 1.0, 'unit': 'cup'}, 'substitution': {'constraints': ['vegan', 'vegetarian', 'gluten-free', 'dairy-free', 'keto', 'paleo', 'whole30', 'low-sodium', 'low-sugar', 'kosher', 'nut-free'], 'functional_role': 'fat', 'heat_adjustment': nan, 'notes': '1:1 ratio by weight; similar consistency; adds subtle coconut flavor (use refined oil for neutral taste)', 'original_ingredient': 'butter', 'original_role': 'fat', 'substitute_ingredient': 'coconut oil', 'substitute_role': 'fat', 'swap_ratio': 1.0}}],
            },
        }"""
system_content = (
        "I am going to give you a recipe in the format of a JSON object with the following fields: title, ingredients" +
        "(a list of strings), and instructions (a list of strings). I will also give you dietary/allergy restrictions and " +
        "cooking preferences. Your task is to rewrite the recipe and output it as a python dictionary in the following format:" +
        format)


def gpt(enriched_recipe, constraints):
    chat = client.chat.completions.create(
        messages=[{"role": "system", "content": system_content},
                  {"role": "user", "content": f"Recipe: {enriched_recipe}. \n Constraints: {constraints}"}],
        model="gpt-4",
        max_tokens=3000,
        temperature=0.7,
    )
    adapted_recipe = chat.choices[0].message.content
    result = {
        "title": enriched_recipe.get("title", ""),
        "source_url": enriched_recipe.get("source_url", ""),
        "original_title": enriched_recipe.get("title", ""),
        "metadata": {
            **enriched_recipe.get("metadata", {}),
            "total_time_minutes": None,
            "adapted_for": {
                "dietary_constraints": None,
                "allergies": None,
                "excluded_ingredients": None,
                "preferences": None,
            },
        }}
    # result = "".join(adapted_recipe.split())
    adapted_recipe = adapted_recipe.replace("false", "False").replace("true", "True").replace("null", "None")
    adapted_recipe = ast.literal_eval(adapted_recipe)
    result["adaptation_summary"] = adapted_recipe["adaptation_summary"]
    result["adaptation_summary"]["user_prompt"] = None
    result["adaptation_summary"]["steps_rewritten"] = True
    result["adaptation_summary"]["cooking_time"] = None
    result["adaptation_summary"]["cooking_heat"] = None
    result["adaptation_summary"]["substitution_summary"] = None
    result["ingredients"] = adapted_recipe["ingredients"]
    result["instructions"] = adapted_recipe["instructions"]
    return result

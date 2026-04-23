"""
Full Pipeline Test Script

Tests all three parts of the recipe adaptation pipeline:
1. Data Extraction (scraper.py)
2. Semantic Parsing (ingredient_parser.py)
3. Recipe Generation (recipe_generator.py)

Each function tests one recipe from a website without firewall protection.
Uncomment/comment functions below to control which recipes are tested.
"""

from backend.data_extraction.scraper import extract_recipe
from backend.semantic_parsing.ingredient_parser import process_recipe
from backend.recipe_generation.recipe_generator import RecipeGenerator
from backend.recipe_generation.utils import format_recipe_for_display, compare_recipes


def test_recipe(recipe_url: str, website_name: str, user_constraint: str = "Make it vegan"):
    """
    Test all three pipeline stages on a single recipe.
    
    Args:
        recipe_url: URL to the recipe
        website_name: Display name of the website
        user_constraint: Dietary constraint to apply
    """
    print(f"\n{'='*80}")
    print(f"TESTING: {website_name}")
    print(f"URL: {recipe_url}")
    print(f"{'='*80}\n")
    
    try:
        # ──────────────────────────────────────────────────────────────────────────
        # PART 1: Data Extraction
        # ──────────────────────────────────────────────────────────────────────────
        print("📡 PART 1: Data Extraction")
        print("-" * 80)
        try:
            raw_recipe = extract_recipe(recipe_url)
            print(f"✓ Successfully extracted recipe")
            print(f"  Title: {raw_recipe['title']}")
            print(f"  Ingredients: {len(raw_recipe['ingredients_raw'])}")
            print(f"  Instructions: {len(raw_recipe['instructions'])}")
            print(f"  Source: {raw_recipe['metadata'].get('host', 'Unknown')}")
            print(f"  Extraction method: {raw_recipe['metadata'].get('extraction_method', 'Unknown')}")
            
            # Show first 3 ingredients
            print("\n  Sample ingredients:")
            for ing in raw_recipe['ingredients_raw'][:3]:
                print(f"    • {ing}")
            print()
        except Exception as e:
            print(f"✗ FAILED at Part 1: {e}\n")
            return
        
        # ──────────────────────────────────────────────────────────────────────────
        # PART 2: Semantic Parsing
        # ──────────────────────────────────────────────────────────────────────────
        print("🔍 PART 2: Semantic Parsing")
        print("-" * 80)
        try:
            enriched_recipe = process_recipe(raw_recipe)
            print(f"✓ Successfully parsed ingredients")
            print(f"  Parsed ingredients: {len(enriched_recipe['ingredients'])}")
            print(f"  Functional roles found: {enriched_recipe.get('graph_summary', {})}")
            
            # Show sample parsed ingredients
            print("\n  Sample parsed ingredients:")
            for ing in enriched_recipe['ingredients'][:3]:
                print(f"    • {ing['raw']}")
                print(f"      → {ing['qty']} {ing['unit']} of {ing['name']} (role: {ing['functional_role']})")
            print()
        except Exception as e:
            print(f"✗ FAILED at Part 2: {e}\n")
            return
        
        # ──────────────────────────────────────────────────────────────────────────
        # PART 3: Recipe Generation
        # ──────────────────────────────────────────────────────────────────────────
        print("🧑‍🍳 PART 3: Recipe Generation")
        print("-" * 80)
        try:
            generator = RecipeGenerator(use_llm=False)
            print(f"✓ RecipeGenerator initialized (use_llm=False)")
            print(f"  Applying constraint: '{user_constraint}'")
            
            adapted_recipe = generator.generate(enriched_recipe, user_constraint)
            print(f"✓ Recipe adapted successfully")
            
            # Show adaptation summary
            if adapted_recipe.get("adaptation_summary"):
                summary = adapted_recipe["adaptation_summary"]
                constraints = summary.get("parsed_constraints", {})
                
                print(f"\n  Adaptation Summary:")
                if constraints.get("dietary"):
                    print(f"    Dietary constraints: {', '.join(constraints['dietary'])}")
                if constraints.get("allergies"):
                    print(f"    Allergies: {', '.join(constraints['allergies'])}")
                if constraints.get("exclude"):
                    print(f"    Excluded ingredients: {', '.join(constraints['exclude'])}")
                
                subs = summary.get("substitutions_made", [])
                if subs:
                    print(f"    Substitutions made: {len(subs)}")
                    for sub in subs[:3]:  # Show first 3
                        print(f"      • {sub}")
            
            print(f"\n  Original ingredients: {len(enriched_recipe['ingredients'])}")
            print(f"  Adapted ingredients: {len(adapted_recipe['ingredients'])}")
            print()
            
        except Exception as e:
            print(f"✗ FAILED at Part 3: {e}\n")
            return
        
        print("✅ SUCCESS: All three pipeline stages completed!\n")
        
    except Exception as e:
        print(f"✗ UNEXPECTED ERROR: {e}\n")


# ══════════════════════════════════════════════════════════════════════════════
# TEST RECIPES - Uncomment/comment to enable/disable individual tests
# ══════════════════════════════════════════════════════════════════════════════

def test_food_com():
    """Food.com - Best Banana Bread"""
    test_recipe(
        "https://www.food.com/recipe/best-banana-bread-2886",
        "Food.com - Best Banana Bread",
        "Make it vegan"
    )


def test_epicurious():
    """Epicurious - Easy Banana Bread"""
    test_recipe(
        "https://www.epicurious.com/recipes/food/views/easy-banana-bread-recipe",
        "Epicurious - Easy Banana Bread",
        "Make it gluten-free"
    )


def test_foodnetwork():
    """Food Network - Banana Bread"""
    test_recipe(
        "https://www.foodnetwork.com/recipes/banana-bread-recipe-1969572",
        "Food Network - Banana Bread",
        "Low sugar version"
    )


def test_budgetbytes():
    """Budget Bytes - Homemade Banana Bread"""
    test_recipe(
        "https://www.budgetbytes.com/homemade-banana-bread/",
        "Budget Bytes - Homemade Banana Bread",
        "Make it vegan and gluten-free"
    )


def test_minimalistbaker():
    """Minimalist Baker - One Bowl Gluten-Free Banana Bread"""
    test_recipe(
        "https://minimalistbaker.com/one-bowl-gluten-free-banana-bread/",
        "Minimalist Baker - One Bowl Gluten-Free Banana Bread",
        "I'm allergic to eggs"
    )


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FULL PIPELINE TEST - Recipe Adaptation System")
    print("="*80)
    print("\nTesting: Data Extraction → Semantic Parsing → Recipe Generation")
    print("Constraint: Apply vegan/gluten-free/allergy adaptations\n")
    
    # ──────────────────────────────────────────────────────────────────────────
    # RUN TESTS (Uncomment/comment to enable/disable)
    # ──────────────────────────────────────────────────────────────────────────
    
    test_food_com()              # Food.com
    test_epicurious()             # Epicurious
    test_foodnetwork()            # Food Network
    test_budgetbytes()            # Budget Bytes
    test_minimalistbaker()        # Minimalist Baker
    
    print("\n" + "="*80)
    print("✓ All tests completed!")
    print("="*80)

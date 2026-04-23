"""
Test suite for Part 3: Recipe Generation

Tests constraint parsing, substitution engine, and full recipe generation.
"""

import pytest
from backend.recipe_generation.constraint_parser import ConstraintParser, ParsedConstraints
from backend.recipe_generation.substitution_library import SubstitutionLibrary, Substitution
from backend.recipe_generation.substitution_engine import SubstitutionEngine
from backend.recipe_generation.recipe_generator import RecipeGenerator
from backend.recipe_generation.utils import format_recipe_for_display


def test_constraint_parser_basic():
    """Test basic constraint parsing."""
    parser = ConstraintParser()
    
    prompt = "Make it vegan and gluten-free"
    constraints = parser.parse(prompt)
    
    assert "vegan" in constraints.dietary_constraints
    assert "gluten-free" in constraints.dietary_constraints


def test_constraint_parser_allergies():
    """Test allergen detection."""
    parser = ConstraintParser()
    
    prompt = "I'm allergic to peanuts and shellfish"
    constraints = parser.parse(prompt)
    
    assert "peanuts" in constraints.allergies
    assert "shellfish" in constraints.allergies


def test_constraint_parser_exclusions():
    """Test ingredient exclusion detection."""
    parser = ConstraintParser()
    
    prompt = "Can you remove the garlic and onions?"
    constraints = parser.parse(prompt)
    
    assert any("garlic" in excl for excl in constraints.exclude_ingredients)


def test_constraint_parser_cooking_adjustments():
    """Test cooking preference parsing."""
    parser = ConstraintParser()
    
    prompt_quick = "I need a quick recipe"
    assert parser.parse(prompt_quick).cooking_time_adjustment == "reduce"
    
    prompt_slow = "I want a slow-cooked version"
    assert parser.parse(prompt_slow).cooking_time_adjustment == "increase"
    
    prompt_high_heat = "Use high heat"
    assert parser.parse(prompt_high_heat).cooking_level_adjustment == "increase"


def test_substitution_library_loading():
    """Test loading substitution library."""
    library = SubstitutionLibrary()
    
    # Should load CSV successfully
    assert not library.df.empty, "Substitution library should not be empty"
    
    # Check required columns
    required_cols = [
        "original_ingredient", "substitute_ingredient", 
        "swap_ratio", "functional_role", "constraints"
    ]
    for col in required_cols:
        assert col in library.df.columns, f"Missing column: {col}"


def test_substitution_library_find():
    """Test finding substitutions."""
    library = SubstitutionLibrary()
    
    # Find vegan butter substitutes
    subs = library.find_substitutions("butter", "fat", ["vegan"])
    
    assert len(subs) > 0, "Should find vegan butter substitutes"
    assert all(isinstance(s, Substitution) for s in subs)
    assert all("vegan" in s.constraints for s in subs)


def test_substitution_engine():
    """Test substitution engine."""
    library = SubstitutionLibrary()
    engine = SubstitutionEngine(library)
    
    # Create a test recipe
    recipe = {
        "title": "Simple Cake",
        "ingredients": [
            {
                "raw": "2 cups all-purpose flour",
                "qty": 2.0,
                "unit": "cups",
                "name": "all-purpose flour",
                "functional_role": "structure",
                "modifiers": [],
                "confidence": 1.0,
            },
            {
                "raw": "1 cup butter",
                "qty": 1.0,
                "unit": "cup",
                "name": "butter",
                "functional_role": "fat",
                "modifiers": [],
                "confidence": 1.0,
            },
        ],
        "instructions": ["Mix flour and butter", "Bake at 350F for 30 minutes"],
    }
    
    # Apply vegan constraints
    modified = engine.substitute_recipe(recipe, ["vegan"])
    
    assert "ingredients" in modified
    assert len(modified.get("substitutions_applied", [])) > 0
    
    # Butter should be substituted
    ing_names = [ing["name"] for ing in modified["ingredients"]]
    assert "butter" not in ing_names or any(
        "vegan" in ing.get("substitution_notes", "") for ing in modified["ingredients"]
    )


def test_recipe_generator_integration():
    """Test full recipe generation pipeline."""
    generator = RecipeGenerator(use_llm=False)  # Disable LLM for testing
    
    # Create a test enriched recipe (from Part 2)
    enriched_recipe = {
        "title": "Classic Mac and Cheese",
        "source_url": "https://example.com/recipe",
        "ingredients": [
            {
                "raw": "1 lb pasta",
                "qty": 1.0,
                "unit": "lb",
                "name": "pasta",
                "functional_role": "structure",
                "modifiers": [],
                "confidence": 1.0,
            },
            {
                "raw": "4 tablespoons butter",
                "qty": 4.0,
                "unit": "tbsp",
                "name": "butter",
                "functional_role": "fat",
                "modifiers": [],
                "confidence": 1.0,
            },
            {
                "raw": "2 cups milk",
                "qty": 2.0,
                "unit": "cups",
                "name": "milk",
                "functional_role": "liquid",
                "modifiers": [],
                "confidence": 1.0,
            },
        ],
        "instructions": [
            "Boil water and cook pasta",
            "Make roux with butter and flour",
            "Add milk and cheese",
            "Toss pasta in sauce",
        ],
        "graph_summary": {"structure": 1, "fat": 1, "liquid": 1},
        "metadata": {
            "total_time_minutes": 30,
            "extraction_method": "test",
        },
    }
    
    # Generate vegan version
    user_prompt = "Make it vegan"
    result = generator.generate(enriched_recipe, user_prompt)
    
    assert "adaptation_summary" in result
    assert "vegan" in result["adaptation_summary"]["parsed_constraints"]["dietary"]
    assert "substitutions_applied" in result["adaptation_summary"]
    assert len(result.get("ingredients", [])) > 0
    assert len(result.get("instructions", [])) > 0


def test_recipe_generator_with_exclusions():
    """Test recipe generation with ingredient exclusions."""
    generator = RecipeGenerator(use_llm=False)
    
    recipe = {
        "title": "Pasta Aglio e Olio",
        "ingredients": [
            {
                "qty": 1.0, "unit": "lb", "name": "pasta",
                "functional_role": "structure", "modifiers": [], "confidence": 1.0, "raw": "1 lb pasta"
            },
            {
                "qty": 0.5, "unit": "cup", "name": "garlic",
                "functional_role": "aromatic", "modifiers": [], "confidence": 1.0, "raw": "0.5 cup garlic"
            },
            {
                "qty": 0.5, "unit": "cup", "name": "olive oil",
                "functional_role": "fat", "modifiers": [], "confidence": 1.0, "raw": "0.5 cup olive oil"
            },
        ],
        "instructions": ["Cook pasta", "Sauté garlic in oil", "Toss pasta in oil"],
        "metadata": {"total_time_minutes": 20},
    }
    
    prompt = "Remove the garlic"
    result = generator.generate(recipe, prompt)
    
    assert "garlic" in result["adaptation_summary"]["parsed_constraints"]["exclude"]


def test_format_recipe_for_display():
    """Test recipe formatting."""
    recipe = {
        "title": "Test Recipe",
        "ingredients": [
            {
                "qty": 2.0, "unit": "cups", "name": "flour",
                "modifiers": ["sifted"], "original_name": None
            },
            {
                "qty": 1.0, "unit": "cup", "name": "coconut oil",
                "modifiers": [], "original_name": "butter", "substitution_notes": "Use for vegan version"
            },
        ],
        "instructions": ["Mix dry ingredients", "Add wet ingredients", "Bake"],
        "metadata": {"total_time_minutes": 45, "source_url": "https://example.com"},
        "adaptation_summary": {
            "parsed_constraints": {"dietary": ["vegan"], "allergies": [], "exclude": []},
        },
    }
    
    output = format_recipe_for_display(recipe)
    
    assert "Test Recipe" in output
    assert "INGREDIENTS" in output
    assert "INSTRUCTIONS" in output
    assert "45 minutes" in output
    assert "vegan" in output.lower()


if __name__ == "__main__":
    # Run tests manually
    print("Testing Constraint Parser...")
    test_constraint_parser_basic()
    test_constraint_parser_allergies()
    test_constraint_parser_exclusions()
    test_constraint_parser_cooking_adjustments()
    print("✓ Constraint parser tests passed\n")
    
    print("Testing Substitution Library...")
    test_substitution_library_loading()
    test_substitution_library_find()
    print("✓ Substitution library tests passed\n")
    
    print("Testing Substitution Engine...")
    test_substitution_engine()
    print("✓ Substitution engine tests passed\n")
    
    print("Testing Recipe Generator...")
    test_recipe_generator_integration()
    test_recipe_generator_with_exclusions()
    print("✓ Recipe generator tests passed\n")
    
    print("Testing Formatting...")
    test_format_recipe_for_display()
    print("✓ Formatting tests passed\n")
    
    print("All tests passed! ✓")

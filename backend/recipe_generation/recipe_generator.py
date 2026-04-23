"""
Recipe Generator - Main Orchestrator

Coordinates the full recipe generation pipeline:
1. Parse user constraints
2. Find ingredient substitutions
3. Rewrite cooking steps
4. Generate final modified recipe
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from backend.semantic_parsing.utils import EnrichedRecipeOutput
from backend.recipe_generation.constraint_parser import ConstraintParser, ParsedConstraints
from backend.recipe_generation.substitution_library import SubstitutionLibrary
from backend.recipe_generation.substitution_engine import SubstitutionEngine
from backend.recipe_generation.step_rewriter import StepRewriter


class RecipeGenerator:
    """
    Main orchestrator for Part 3: Constraint Logic & Recipe Generation.
    
    Generates adapted recipes based on user dietary constraints and preferences.
    """
    
    def __init__(
        self,
        library_path: Optional[str] = None,
        llm_provider: str = "openai",
        llm_model: str = "gpt-3.5-turbo",
        use_llm: bool = True,
    ):
        """
        Initialize the recipe generator.
        
        Args:
            library_path: Path to substitutions CSV (default: package location)
            llm_provider: "openai" or "local"
            llm_model: LLM model name
            use_llm: Whether to use LLM for step rewriting (fallback if False)
        """
        self.library = SubstitutionLibrary(library_path)
        self.constraint_parser = ConstraintParser()
        self.substitution_engine = SubstitutionEngine(self.library)
        
        self.use_llm = use_llm
        if use_llm:
            try:
                self.step_rewriter = StepRewriter(llm_provider, llm_model, use_llm=True)
            except ImportError as e:
                print(f"Warning: {e}")
                print("Falling back to text-based step rewriting.")
                self.use_llm = False
                self.step_rewriter = StepRewriter(use_llm=False)
        else:
            self.step_rewriter = StepRewriter(use_llm=False)
    
    def generate(
        self,
        enriched_recipe: dict,  # EnrichedRecipeOutput as dict from Part 2
        user_prompt: str,
    ) -> dict:
        """
        Generate a modified recipe based on user constraints.
        
        Args:
            enriched_recipe: Output from semantic_parsing.ingredient_parser.process_recipe()
            user_prompt: Natural language request (e.g., "Make it vegan and gluten-free")
        
        Returns:
            Modified recipe dict with:
            - substituted ingredients
            - rewritten steps
            - metadata about changes
        """
        # Step 1: Parse user constraints
        constraints = self.constraint_parser.parse(user_prompt)
        
        # Step 2: Apply ingredient substitutions
        substituted_recipe = self.substitution_engine.substitute_recipe(
            enriched_recipe,
            constraints=constraints.dietary_constraints + constraints.allergies,
            exclude_ingredients=constraints.exclude_ingredients,
        )
        
        # Step 3: Rewrite cooking steps
        if substituted_recipe.get("ingredients") and substituted_recipe.get("instructions"):
            rewritten_steps = self.step_rewriter.rewrite_steps(
                original_steps=substituted_recipe["instructions"],
                substitutions=substituted_recipe.get("substitutions_applied", []),
                constraints=constraints,
                original_ingredients=enriched_recipe.get("ingredients", []),
                new_ingredients=substituted_recipe.get("ingredients", []),
            )
            
            # Adjust cooking time
            original_time = enriched_recipe.get("metadata", {}).get("total_time_minutes")
            adjusted_time = self.step_rewriter.adjust_cooking_time(original_time, constraints)
        else:
            rewritten_steps = substituted_recipe.get("instructions", [])
            adjusted_time = enriched_recipe.get("metadata", {}).get("total_time_minutes")
        
        # Step 4: Build final output
        final_recipe = {
            "title": substituted_recipe.get("title", ""),
            "source_url": substituted_recipe.get("source_url", ""),
            "original_title": enriched_recipe.get("title", ""),
            "ingredients": substituted_recipe.get("ingredients", []),
            "instructions": rewritten_steps,
            "metadata": {
                **enriched_recipe.get("metadata", {}),
                "total_time_minutes": adjusted_time,
                "adapted_for": {
                    "dietary_constraints": constraints.dietary_constraints,
                    "allergies": constraints.allergies,
                    "excluded_ingredients": constraints.exclude_ingredients,
                    "preferences": constraints.preferences,
                },
            },
            "adaptation_summary": {
                "user_prompt": user_prompt,
                "parsed_constraints": {
                    "dietary": constraints.dietary_constraints,
                    "allergies": constraints.allergies,
                    "exclude": constraints.exclude_ingredients,
                    "preferences": constraints.preferences,
                    "cooking_time": constraints.cooking_time_adjustment,
                    "cooking_heat": constraints.cooking_level_adjustment,
                },
                "substitutions_made": substituted_recipe.get("substitutions_applied", []),
                "steps_rewritten": len(rewritten_steps) > 0,
                "substitution_summary": self.substitution_engine.get_substitution_summary(),
            },
        }
        
        return final_recipe
    
    def generate_with_fallback(
        self,
        enriched_recipe: dict,
        user_prompt: str,
    ) -> dict:
        """
        Generate recipe with fallback error handling.
        Returns original recipe if generation fails.
        
        Args:
            enriched_recipe: Output from Part 2
            user_prompt: User's natural language request
        
        Returns:
            Modified recipe, or original if generation fails
        """
        try:
            return self.generate(enriched_recipe, user_prompt)
        except Exception as e:
            print(f"Error in recipe generation: {e}")
            print("Returning original recipe.")
            
            # Return original recipe with error note
            enriched_recipe["adaptation_summary"] = {
                "error": str(e),
                "status": "failed",
                "original_recipe": True,
            }
            return enriched_recipe
    
    def batch_generate(
        self,
        recipes: list[dict],
        user_prompt: str,
    ) -> list[dict]:
        """
        Generate multiple adapted recipes.
        
        Args:
            recipes: List of EnrichedRecipeOutput dicts
            user_prompt: Same user prompt for all recipes
        
        Returns:
            List of modified recipes
        """
        return [self.generate(recipe, user_prompt) for recipe in recipes]
    
    def get_available_constraints(self) -> list[str]:
        """Get list of all recognized constraints in the library."""
        return self.library.get_all_constraints()
    
    def add_substitution(
        self,
        original_ingredient: str,
        original_role: str,
        substitute_ingredient: str,
        substitute_role: str,
        functional_role: str,
        swap_ratio: float = 1.0,
        constraints: Optional[list[str]] = None,
        notes: str = "",
        heat_adjustment: Optional[str] = None,
    ) -> None:
        """
        Add a new substitution to the library (in-memory only).
        
        Args:
            original_ingredient: E.g., "butter"
            original_role: Original ingredient's semantic role
            substitute_ingredient: E.g., "coconut oil"
            substitute_role: Substitute's semantic role
            functional_role: The role both satisfy (e.g., "fat")
            swap_ratio: Quantity multiplier (e.g., 0.75 for 75%)
            constraints: List of constraints this satisfies
            notes: Cooking notes
            heat_adjustment: E.g., "reduce_by_10%"
        """
        self.library.add_substitution(
            original_ingredient=original_ingredient,
            original_role=original_role,
            substitute_ingredient=substitute_ingredient,
            substitute_role=substitute_role,
            functional_role=functional_role,
            swap_ratio=swap_ratio,
            constraints=constraints,
            notes=notes,
            heat_adjustment=heat_adjustment,
        )
    
    def save_library(self, path: Optional[str] = None) -> None:
        """Persist library to CSV."""
        self.library.save_to_csv(path)

"""
Substitution Engine

Applies ingredient substitutions to parsed recipes based on constraints.
Handles quantity adjustments and tracks all modifications.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.recipe_generation.utils import normalize_ingredient
from backend.recipe_generation.substitution_library import SubstitutionLibrary, Substitution
from backend.semantic_parsing.utils import ParsedIngredient


@dataclass
class SubstitutionResult:
    """Result of a substitution operation."""
    original_ingredient: ParsedIngredient
    substituted_ingredient: ParsedIngredient
    substitution: Substitution
    reason: str  # why this substitution was made
    quantity_adjusted: bool  # whether quantity was adjusted
    original_qty: Optional[float]
    new_qty: Optional[float]


class SubstitutionEngine:
    """
    Applies ingredient substitutions to recipes based on constraints.
    """

    def __init__(self, library: SubstitutionLibrary):
        """
        Initialize engine with a substitution library.
        
        Args:
            library: SubstitutionLibrary instance
        """
        self.library = library
        self.substitutions_applied: list[SubstitutionResult] = []

    def substitute_recipe(
            self,
            recipe: dict,  # EnrichedRecipeOutput as dict
            dietary_constraints: list[str],
            allergen_constraints: list[str],
            exclude_ingredients: Optional[list[str]] = None,
    ) -> dict:
        """
        Apply substitutions to all ingredients in a recipe.
        
        Args:
            recipe: EnrichedRecipeOutput as dict (from semantic_parsing)
            constraints: List of dietary constraints (e.g., ["vegan", "gluten-free"])
            exclude_ingredients: Specific ingredients to remove/replace
        
        Returns:
            Modified recipe dict with substituted ingredients
        """
        if 'dairy' in allergen_constraints:
            dietary_constraints.append('dairy-free')
        exclude_ingredients = exclude_ingredients or []
        exclude_lower = [ing.lower() for ing in exclude_ingredients]

        self.substitutions_applied = []
        substituted_ingredients = []

        for ingredient in recipe.get("ingredients", []):
            # Check if ingredient should be excluded
            if any(excl in ingredient["name"].lower() for excl in exclude_lower):
                # Find a substitution for this ingredient
                sub_list = self.library.find_substitutions(
                    ingredient["name"],
                    ingredient["functional_role"],
                    dietary_constraints
                )

                if sub_list:
                    best_sub = sub_list[0]
                    new_ing = self._apply_substitution(
                        ingredient, best_sub, "ingredient excluded by user"
                    )
                    substituted_ingredients.append(new_ing)
                else:
                    # No substitution found, skip ingredient
                    continue
            else:
                # Check if this ingredient needs substitution for constraints
                sub_list = self.library.find_substitutions(
                    ingredient["name"],
                    ingredient["functional_role"],
                    dietary_constraints
                )

                if sub_list:
                    # Check if original ingredient already satisfies constraints
                    satisfies_dietary_constraints, missing_constraints = self._satisfies_constraints(ingredient, dietary_constraints)
                    satisfies_allergen_constraints = True
                    for allergen in allergen_constraints:
                        if normalize_ingredient(allergen) in normalize_ingredient(ingredient["name"]):
                            satisfies_allergen_constraints = False
                            break
                    if satisfies_dietary_constraints and satisfies_allergen_constraints:
                        substituted_ingredients.append(ingredient)
                    else:
                        # Apply substitution
                        adaption_message = f"adapted for constraints: {', '.join(missing_constraints)}"
                        if not satisfies_allergen_constraints:
                            adaption_message = f"allergy adaption"
                        best_sub = sub_list[0]
                        new_ing = self._apply_substitution(
                            ingredient, best_sub, adaption_message
                        )
                        substituted_ingredients.append(new_ing)
                else:
                    # No substitution needed or available
                    substituted_ingredients.append(ingredient)

        # Return modified recipe
        result = recipe.copy()
        result["ingredients"] = substituted_ingredients
        result["substitutions_applied"] = [asdict(s) for s in self.substitutions_applied]

        # Adjust instructions for gluten-free baking
        title = recipe.get("title", "").lower()
        if "gluten-free" in dietary_constraints:
            adjusted_instructions = []
            for instr in result["instructions"]:
                if "bake" in instr.lower():
                    if "cookie" in title:
                        adjusted_instructions.append(
                            instr + "\n⚠️ When baking gluten-free cookies, increase baking time by 5-10 minutes and reduce temperature by 25° F.")
                    elif "bread" in title:
                        adjusted_instructions.append(
                            instr + "\n⚠️ When baking gluten-free bread, increase baking time by 10-20 minutes and reduce temperature by 25° F.")
                    elif "bread" in title:
                        adjusted_instructions.append(
                            instr + "\n⚠️ When baking gluten-free bread, increase baking time by 50 % and reduce temperature by 25° F.")
                    else:
                        adjusted_instructions.append(
                            instr + "\n⚠️ When baking gluten-free, increase baking time by 5-20 minutes and reduce temperature by 15-25° F.")
                else:
                    adjusted_instructions.append(instr)
                result["instructions"] = adjusted_instructions

        return result

    def _apply_substitution(
            self,
            original: dict,
            substitution: Substitution,
            reason: str,
    ) -> dict:
        """Apply a single substitution to an ingredient."""
        # Adjust quantity based on swap ratio
        new_qty = None
        if original.get("qty") is not None:
            new_qty = original["qty"] * substitution.swap_ratio

        new_ingredient = original.copy()
        new_ingredient["name"] = substitution.substitute_ingredient
        new_ingredient["qty"] = new_qty
        new_ingredient["original_name"] = original["name"]
        new_ingredient["swap_ratio"] = substitution.swap_ratio
        new_ingredient["substitution_notes"] = substitution.notes

        # Track this substitution
        result = SubstitutionResult(
            original_ingredient=original,
            substituted_ingredient=new_ingredient,
            substitution=substitution,
            reason=reason,
            quantity_adjusted=new_qty != original.get("qty"),
            original_qty=original.get("qty"),
            new_qty=new_qty,
        )
        self.substitutions_applied.append(result)

        return new_ingredient

    @staticmethod
    def _satisfies_constraints(ingredient: dict, constraints: list[str]):
        """
        Check if an ingredient already satisfies all constraints.
        This is a simple check; a more sophisticated version could check
        ingredient metadata against constraint definitions.
        
        Args:
            ingredient: ParsedIngredient as dict
            constraints: List of constraint keywords
        
        Returns:
            True if ingredient satisfies constraints, False otherwise
            List of unsatisfied constraints (if any)
        """
        # For simplicity, assume most ingredients don't satisfy non-standard constraints
        # In production, you'd check ingredient metadata
        if not constraints:
            return True, []
        df = pd.read_csv(Path(Path(__file__).parent / "ingredient_constraints.csv"))

        ingredient_name_lower = ingredient.get("name", "").lower()

        mask1 = df["ingredient"].str.lower().str.contains(
            ingredient_name_lower, na=False
        )

        satisfied_constraints = df.loc[mask1, "satisfied_constraints"]

        # Fallback: ingredient_name contains df value
        if satisfied_constraints.empty:
            mask2 = df["ingredient"].fillna("").str.lower().apply(
                lambda x: x in ingredient_name_lower
            )
            satisfied_constraints = df.loc[mask2, "satisfied_constraints"]

        if satisfied_constraints.empty:
            return False, constraints
        satisfied_constrains = satisfied_constraints.iloc[0].replace(" ", "")
        satisfied_constrains = set(satisfied_constrains.split(';'))
        if all(constraint in satisfied_constrains for constraint in constraints):
            return True, []
        else:
            return False, set(constraints) - set(satisfied_constrains)

    def get_heat_adjustments(self) -> dict:
        """
        Extract heat adjustments from applied substitutions.
        
        Returns:
            Dict mapping from original ingredient to heat adjustment needed
        """
        adjustments = {}
        for result in self.substitutions_applied:
            if result.substitution.heat_adjustment:
                original_name = result.original_ingredient.get("name", "")
                adjustments[original_name] = result.substitution.heat_adjustment

        return adjustments

    def get_substitution_summary(self) -> str:
        """Generate a human-readable summary of all substitutions made."""
        if not self.substitutions_applied:
            return "No substitutions applied."

        lines = []
        for result in self.substitutions_applied:
            qty_note = ""
            if result.quantity_adjusted:
                qty_note = f" (qty: {result.original_qty} → {result.new_qty})"

            lines.append(
                f"• {result.original_ingredient.get('name')} → {result.substituted_ingredient['name']}{qty_note}\n"
                f"  Reason: {result.reason}"
            )

        return "\n".join(lines)

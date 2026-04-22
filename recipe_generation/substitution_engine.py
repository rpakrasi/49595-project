"""
Substitution Engine

Applies ingredient substitutions to parsed recipes based on constraints.
Handles quantity adjustments and tracks all modifications.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from semantic_parsing.utils import ParsedIngredient, EnrichedRecipeOutput
from recipe_generation.substitution_library import SubstitutionLibrary, Substitution


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
        constraints: list[str],
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
                    constraints
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
                    constraints
                )
                
                if sub_list:
                    # Check if original ingredient already satisfies constraints
                    if self._satisfies_constraints(ingredient, constraints):
                        substituted_ingredients.append(ingredient)
                    else:
                        # Apply substitution
                        best_sub = sub_list[0]
                        new_ing = self._apply_substitution(
                            ingredient, best_sub, f"adapted for constraints: {', '.join(constraints)}"
                        )
                        substituted_ingredients.append(new_ing)
                else:
                    # No substitution needed or available
                    substituted_ingredients.append(ingredient)
        
        # Return modified recipe
        result = recipe.copy()
        result["ingredients"] = substituted_ingredients
        result["substitutions_applied"] = [asdict(s) for s in self.substitutions_applied]
        
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
    
    def _satisfies_constraints(self, ingredient: dict, constraints: list[str]) -> bool:
        """
        Check if an ingredient already satisfies all constraints.
        This is a simple check; a more sophisticated version could check
        ingredient metadata against constraint definitions.
        
        Args:
            ingredient: ParsedIngredient as dict
            constraints: List of constraint keywords
        
        Returns:
            True if ingredient satisfies constraints, False otherwise
        """
        # For simplicity, assume most ingredients don't satisfy non-standard constraints
        # In production, you'd check ingredient metadata
        ingredient_name_lower = ingredient.get("name", "").lower()
        
        # Simple heuristic: if "organic", "free-range", etc. in name, it may satisfy some constraints
        positive_markers = ["organic", "free-range", "wild-caught", "hormone-free"]
        satisfies = any(marker in ingredient_name_lower for marker in positive_markers)
        
        return satisfies
    
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

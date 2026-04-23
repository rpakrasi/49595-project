"""
Constraint Parser

Parses natural language user prompts to extract dietary constraints,
allergies, and cooking preferences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedConstraints:
    """Represents parsed user constraints."""
    dietary_constraints: list[str] = field(default_factory=list)  # e.g., ["vegan", "gluten-free"]
    allergies: list[str] = field(default_factory=list)  # e.g., ["peanuts", "shellfish"]
    preferences: list[str] = field(default_factory=list)  # e.g., ["low-sodium", "low-carb"]
    exclude_ingredients: list[str] = field(default_factory=list)  # specific items to remove
    cooking_level_adjustment: str = "none"  # "reduce", "increase", or "none"
    cooking_time_adjustment: str = "none"  # "reduce", "increase", or "none"
    raw_prompt: str = ""  # original user input


class ConstraintParser:
    """
    Parses natural language prompts to extract dietary and cooking constraints.
    """
    
    # Standard dietary patterns
    DIETARY_PATTERNS = {
        "vegan": r"\b(vegan|no animal)\b",
        "vegetarian": r"\b(vegetarian|no meat|meat-free)\b",
        "gluten-free": r"\b(gluten.?free|gluten-free|no gluten|gf)\b",
        "dairy-free": r"\b(dairy.?free|dairy-free|no dairy|lactose.?free)\b",
        "keto": r"\b(keto|ketogenic|low.?carb|no carb)\b",
        "paleo": r"\b(paleo|paleolithic)\b",
        "whole-30": r"\b(whole.?30|whole-30|w30)\b",
        "low-sodium": r"\b(low.?sodium|low salt|salt.?free)\b",
        "low-sugar": r"\b(low.?sugar|sugar.?free|no sugar)\b",
        "kosher": r"\b(kosher|halal)\b",
        "nut-free": r"\b(nut.?free|nut-free|no nut)\b",
    }
    
    # Allergen patterns
    ALLERGEN_PATTERNS = {
        "peanuts": r"\b(peanut|peanuts|groundnut|groundnuts)\b",
        "tree nuts": r"\b(tree nut|tree nuts|almond|cashew|walnut|pecan|hazelnut)\b",
        "shellfish": r"\b(shellfish|shrimp|prawn|crab|lobster|clam|oyster|mussel)\b",
        "fish": r"\b(fish|salmon|tuna|cod|halibut)\b",
        "dairy": r"\b(dairy|milk|cheese|butter|cream|yogurt|lactose)\b",
        "eggs": r"\b(egg|eggs)\b",
        "soy": r"\b(soy|soybean|edamame|tofu|tempeh|miso)\b",
        "sesame": r"\b(sesame)\b",
    }
    
    # Cooking preference patterns
    COOKING_PATTERNS = {
        "quick": r"\b(quick|fast|quick.?meal|in a hurry|short|easy)\b",
        "slow": r"\b(slow|low.?and.?slow|braised|stewed)\b",
        "low-heat": r"\b(low.?heat|gentle|low temperature)\b",
        "high-heat": r"\b(high.?heat|sear|seared|crispy|crisped)\b",
    }
    
    def __init__(self, custom_constraints: Optional[list[str]] = None):
        """
        Initialize parser with optional custom constraint patterns.
        
        Args:
            custom_constraints: List of additional constraint keywords to recognize
        """
        self.custom_constraints = custom_constraints or []
    
    def parse(self, prompt: str) -> ParsedConstraints:
        """
        Parse a natural language prompt into structured constraints.
        
        Args:
            prompt: User's natural language request (e.g., "Make it vegan and gluten-free")
        
        Returns:
            ParsedConstraints object with extracted info
        """
        prompt_lower = prompt.lower()
        constraints = ParsedConstraints(raw_prompt=prompt)
        
        # Extract dietary constraints
        for diet, pattern in self.DIETARY_PATTERNS.items():
            if re.search(pattern, prompt_lower):
                constraints.dietary_constraints.append(diet)
        
        # Extract allergies
        for allergen, pattern in self.ALLERGEN_PATTERNS.items():
            if re.search(pattern, prompt_lower):
                constraints.allergies.append(allergen)
        
        # Extract cooking preferences
        if re.search(self.COOKING_PATTERNS.get("quick", ""), prompt_lower):
            constraints.cooking_time_adjustment = "reduce"
        if re.search(self.COOKING_PATTERNS.get("slow", ""), prompt_lower):
            constraints.cooking_time_adjustment = "increase"
        
        if re.search(self.COOKING_PATTERNS.get("high-heat", ""), prompt_lower):
            constraints.cooking_level_adjustment = "increase"
        if re.search(self.COOKING_PATTERNS.get("low-heat", ""), prompt_lower):
            constraints.cooking_level_adjustment = "reduce"
        
        # Extract specific ingredient exclusions (e.g., "without onions", "no garlic")
        exclude_match = re.findall(
            r"(?:without|no|exclude|skip|remove|avoid)\s+([a-z\s]+?)(?:\b(?:and|,|or|because)\b|$)",
            prompt_lower
        )

        def normalize_ingredient(text: str) -> str:
            return re.sub(r"^(the|a|an)\s+", "", text.strip())

        for match in exclude_match:
            ingredients = [normalize_ingredient(ing) for ing in re.split(r"(?:and|,|or)", match)]
            constraints.exclude_ingredients.extend([ing for ing in ingredients if ing])

        # Add custom constraints if found
        for custom in self.custom_constraints:
            if custom.lower() in prompt_lower:
                constraints.preferences.append(custom)
        
        # Remove duplicates
        constraints.dietary_constraints = list(set(constraints.dietary_constraints))
        constraints.allergies = list(set(constraints.allergies))
        constraints.preferences = list(set(constraints.preferences))
        constraints.exclude_ingredients = list(set(constraints.exclude_ingredients))
        
        return constraints
    
    def format_for_llm(self, constraints: ParsedConstraints) -> str:
        """
        Format parsed constraints into a human-readable string for LLM prompting.
        
        Args:
            constraints: ParsedConstraints object
        
        Returns:
            Formatted string summarizing all constraints
        """
        parts = []
        
        if constraints.dietary_constraints:
            parts.append(
                f"Dietary constraints: {', '.join(constraints.dietary_constraints)}"
            )
        
        if constraints.allergies:
            parts.append(
                f"Allergies to avoid: {', '.join(constraints.allergies)}"
            )
        
        if constraints.exclude_ingredients:
            parts.append(
                f"Exclude ingredients: {', '.join(constraints.exclude_ingredients)}"
            )
        
        if constraints.cooking_time_adjustment != "none":
            parts.append(f"Cooking time: {constraints.cooking_time_adjustment}")
        
        if constraints.cooking_level_adjustment != "none":
            parts.append(f"Cooking heat level: {constraints.cooking_level_adjustment}")
        
        if constraints.preferences:
            parts.append(f"Preferences: {', '.join(constraints.preferences)}")
        
        return "\n".join(parts) if parts else "No specific constraints"

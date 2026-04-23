"""
Part 3: Constraint Logic & Recipe Generation

This module takes semantically parsed recipes and adapts them based on user constraints.
It performs ingredient substitutions and uses an LLM to rewrite cooking instructions.

Main entry point: RecipeGenerator.generate()
"""

from backend.recipe_generation.recipe_generator import RecipeGenerator
from backend.recipe_generation.substitution_library import SubstitutionLibrary
from backend.recipe_generation.constraint_parser import ConstraintParser

__all__ = [
    "RecipeGenerator",
    "SubstitutionLibrary", 
    "ConstraintParser",
]

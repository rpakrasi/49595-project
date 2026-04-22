"""
Part 3: Constraint Logic & Recipe Generation

This module takes semantically parsed recipes and adapts them based on user constraints.
It performs ingredient substitutions and uses an LLM to rewrite cooking instructions.

Main entry point: RecipeGenerator.generate()
"""

from recipe_generation.recipe_generator import RecipeGenerator
from recipe_generation.substitution_library import SubstitutionLibrary
from recipe_generation.constraint_parser import ConstraintParser

__all__ = [
    "RecipeGenerator",
    "SubstitutionLibrary", 
    "ConstraintParser",
]

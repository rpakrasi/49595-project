"""
Part 3 Utilities

Shared utilities and helpers for recipe generation.
"""

from __future__ import annotations

import json

import spacy


def save_generated_recipe(recipe: dict, output_path: str) -> None:
    """
    Save a generated recipe to JSON.
    
    Args:
        recipe: Generated recipe dict
        output_path: Path to output file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)


def format_recipe_for_display(recipe: dict) -> str:
    """
    Format a recipe for human-readable display.
    
    Args:
        recipe: Generated recipe dict
    
    Returns:
        Formatted recipe as string
    """
    lines = []

    lines.append(f"{'=' * 60}")
    lines.append(f"RECIPE: {recipe.get('title', 'Untitled')}")
    lines.append(f"{'=' * 60}")

    if recipe.get("adaptation_summary"):
        summary = recipe["adaptation_summary"]
        if "parsed_constraints" in summary:
            constraints = summary["parsed_constraints"]
            if constraints.get("dietary"):
                lines.append(f"Dietary: {', '.join(constraints['dietary'])}")
            if constraints.get("allergies"):
                lines.append(f"Allergies: {', '.join(constraints['allergies'])}")
            if constraints.get("exclude"):
                lines.append(f"Exclude: {', '.join(constraints['exclude'])}")

        if summary.get("substitution_summary"):
            lines.append("\nSUBSTITUTIONS:")
            lines.append(summary["substitution_summary"])

    lines.append("\nINGREDIENTS:")
    for ing in recipe.get("ingredients", []):
        qty_str = ""
        if ing.get("qty"):
            unit = ing.get("unit", "")
            qty_str = f"{ing['qty']} {unit}".strip()

        original = ""
        if ing.get("original_name") and ing["original_name"] != ing.get("name"):
            original = f" (was: {ing['original_name']})"

        lines.append(f"  • {qty_str} {ing.get('name', '')}{original}")

        if ing.get("substitution_notes"):
            lines.append(f"    Note: {ing['substitution_notes']}")

    lines.append("\nINSTRUCTIONS:")
    for i, step in enumerate(recipe.get("instructions", []), 1):
        lines.append(f"  {i}. {step}")

    if recipe.get("metadata", {}).get("total_time_minutes"):
        lines.append(f"\nTotal time: {recipe['metadata']['total_time_minutes']} minutes")

    lines.append(f"\nSource: {recipe.get('source_url', 'N/A')}")

    return "\n".join(lines)


def compare_recipes(original: dict, adapted: dict) -> str:
    """
    Generate a comparison between original and adapted recipes.
    
    Args:
        original: Original EnrichedRecipeOutput dict
        adapted: Adapted recipe dict from RecipeGenerator
    
    Returns:
        Comparison as formatted string
    """
    lines = []
    lines.append("RECIPE COMPARISON")
    lines.append("=" * 60)

    lines.append(f"\nOriginal: {original.get('title', 'N/A')}")
    lines.append(f"Adapted:  {adapted.get('title', 'N/A')}")

    orig_ing_count = len(original.get("ingredients", []))
    adapt_ing_count = len(adapted.get("ingredients", []))
    lines.append(f"\nIngredients: {orig_ing_count} → {adapt_ing_count}")

    orig_step_count = len(original.get("instructions", []))
    adapt_step_count = len(adapted.get("instructions", []))
    lines.append(f"Steps: {orig_step_count} → {adapt_step_count}")

    orig_time = original.get("metadata", {}).get("total_time_minutes")
    adapt_time = adapted.get("metadata", {}).get("total_time_minutes")
    if orig_time and adapt_time:
        lines.append(f"Time: {orig_time} min → {adapt_time} min")

    if adapted.get("adaptation_summary"):
        subs = adapted["adaptation_summary"]
        if subs.get("parsed_constraints"):
            constraints = subs["parsed_constraints"]
            applied = []
            if constraints.get("dietary"):
                applied.append(f"Dietary: {', '.join(constraints['dietary'])}")
            if constraints.get("allergies"):
                applied.append(f"Allergies: {', '.join(constraints['allergies'])}")
            if constraints.get("exclude"):
                applied.append(f"Exclude: {', '.join(constraints['exclude'])}")

            if applied:
                lines.append("\nConstraints Applied:")
                for item in applied:
                    lines.append(f"  • {item}")

    return "\n".join(lines)


def ingredient_dict_to_string(ingredient: dict) -> str:
    """
    Convert an ingredient dict to a readable string.
    
    Args:
        ingredient: ParsedIngredient as dict
    
    Returns:
        E.g., "2.0 cups all-purpose flour, sifted"
    """
    parts = []

    if ingredient.get("qty"):
        parts.append(str(ingredient["qty"]))

    if ingredient.get("unit"):
        parts.append(ingredient["unit"])

    parts.append(ingredient.get("name", ""))

    result = " ".join(parts)

    if ingredient.get("modifiers"):
        result += f", {', '.join(ingredient['modifiers'])}"

    if ingredient.get("notes"):
        result += f", {', '.join(ingredient['notes'])}"

    return result


def expand_semicolon_list(lst):
    result = []
    for item in lst:
        result.extend([x.strip() for x in item.split(";") if x.strip()])
    return result


nlp = spacy.load("en_core_web_sm")


def normalize_ingredient(text: str) -> str:
    doc = nlp(text.strip())

    tokens = [
        token.lemma_.lower()
        for token in doc
        if token.pos_ != "DET"
    ]

    return " ".join(tokens).strip()

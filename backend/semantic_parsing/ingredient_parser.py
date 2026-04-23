from __future__ import annotations

import re
from dataclasses import asdict

from backend.semantic_parsing.ingredient_knowledge_graph import IngredientKnowledgeGraph
from backend.semantic_parsing.utils import EnrichedRecipeOutput, ParsedIngredient, parse_quantity_unit, \
    extract_modifiers, strip_notes


def process_recipe(part1_recipe: dict) -> dict:
    """
    Args:
        part1_recipe: dict with keys:
            - title (str)
            - source_url (str)
            - ingredients_raw (list[str])
            - instructions (list[str])
            - metadata (dict[str, Any])

    Returns:
        EnrichedRecipeOutput as a dict (JSON-serializable)
    """
    kg = IngredientKnowledgeGraph()
    parsed_ingredients = []

    for raw in part1_recipe.get("ingredients_raw", []):
        if not raw.strip():
            continue

        # Step 0: Preprocessing - extract notes in parentheses and brackets
        raw_without_notes, notes = strip_notes(raw.replace("*", ""))

        # Step 1: NER — quantity + unit
        qty, unit, remainder = parse_quantity_unit(raw_without_notes)

        # Step 2: Modifiers
        modifiers, name = extract_modifiers(remainder)

        # Clean up name
        name = re.sub(r'\s+', ' ', name).strip().lower()
        name = name.strip(',').strip()

        # Step 3: Functional role from knowledge graph
        role, confidence = kg.lookup_role(name)

        parsed_ingredients.append(ParsedIngredient(
            raw=raw,
            qty=qty,
            unit=unit,
            name=name,
            functional_role=role,
            modifiers=modifiers,
            confidence=confidence,
            notes = notes,
        ))

    # Build role summary for Part 3
    role_counts: dict[str, int] = {}
    for ing in parsed_ingredients:
        role_counts[ing.functional_role] = role_counts.get(ing.functional_role, 0) + 1

    output = EnrichedRecipeOutput(
        title=part1_recipe.get("title", "Untitled Recipe"),
        source_url=part1_recipe.get("source_url", ""),
        ingredients=parsed_ingredients,
        instructions=part1_recipe.get("instructions", []),
        graph_summary=role_counts,
    )

    # Convert to JSON-serializable dict
    result = asdict(output)
    return result

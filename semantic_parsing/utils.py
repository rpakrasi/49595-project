from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# DATA CONTRACT  (shared schema for all three parts)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedIngredient:
    raw: str
    qty: Optional[float]
    unit: Optional[str]
    name: str
    functional_role: str
    modifiers: list[str]  # e.g. ["finely chopped", "room temperature"]
    confidence: float  # 0-1 NER confidence


@dataclass
class EnrichedRecipeOutput:
    """The JSON schema Part 3 receives from Part 2."""
    title: str
    source_url: str
    ingredients: list[ParsedIngredient]
    instructions: list[str]
    graph_summary: dict  # high-level role counts for Part 3 logic


# ──────────────────────────────────────────────────────────────────────────────
# UNIT VOCABULARY
# ──────────────────────────────────────────────────────────────────────────────

UNIT_MAP: dict[str, str] = {
    # volume
    "cup": "cup", "cups": "cup", "c": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbs": "tbsp", "tb": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "t": "tsp",
    "fluid ounce": "fl oz", "fluid ounces": "fl oz", "fl oz": "fl oz", "fl. oz.": "fl oz",
    "pint": "pint", "pints": "pint", "pt": "pint",
    "quart": "quart", "quarts": "quart", "qt": "quart",
    "gallon": "gallon", "gallons": "gallon", "gal": "gallon",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml", "mL": "ml",
    "liter": "L", "liters": "L", "l": "L",
    # weight
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    # descriptor units
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "package": "pkg", "packages": "pkg", "pkg": "pkg",
    "slice": "slice", "slices": "slice",
    "piece": "piece", "pieces": "piece",
    "bunch": "bunch", "bunches": "bunch",
    "sprig": "sprig", "sprigs": "sprig",
    "handful": "handful", "handfuls": "handful",
    "pinch": "pinch", "pinches": "pinch",
    "dash": "dash", "dashes": "dash",
    "drop": "drop", "drops": "drop",
    "head": "head", "heads": "head",
    "stalk": "stalk", "stalks": "stalk",
    "stick": "stick", "sticks": "stick",
    "sheet": "sheet", "sheets": "sheet",
    "large": "large", "medium": "medium", "small": "small",
}

FRACTION_MAP: dict[str, float] = {
    "½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75,
    "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
    "1/2": 0.5, "1/3": 1 / 3, "2/3": 2 / 3, "1/4": 0.25, "3/4": 0.75,
    "1/8": 0.125, "3/8": 0.375, "5/8": 0.625, "7/8": 0.875,
}

MODIFIER_PHRASES = [
    "finely chopped", "roughly chopped", "coarsely chopped", "thinly sliced",
    "freshly ground", "freshly squeezed", "lightly beaten", "softened",
    "room temperature", "at room temperature", "melted", "chilled", "frozen",
    "toasted", "divided", "optional", "to taste", "or to taste",
    "plus more", "plus extra", "for serving", "for garnish",
    "packed", "sifted", "unsalted", "salted", "low-sodium", "reduced-fat",
    "whole grain", "whole wheat", "extra virgin", "extra-virgin",
    "pitted", "peeled", "seeded", "cored", "trimmed", "halved", "quartered",
    "drained", "rinsed", "patted dry", "at room temp",
]

# ──────────────────────────────────────────────────────────────────────────────
# REGEX-BASED NER  (rule-based, no model dependency — fast & interpretable)
# ──────────────────────────────────────────────────────────────────────────────

# Matches: "2 1/2", "1½", "½", "2", "2.5", "1/4"
QTY_PATTERN = re.compile(
    r"""
    (?:
        (\d+)\s+         # whole part
        ([\d/½⅓⅔¼¾⅛⅜⅝⅞]+)  # fraction
    |
        ([½⅓⅔¼¾⅛⅜⅝⅞])   # unicode fraction alone
    |
        (\d+\.?\d*)      # decimal or integer
    |
        ([\d/]+)         # ASCII fraction alone
    )
    """,
    re.VERBOSE,
)

UNIT_PATTERN = re.compile(
    r"\b(" + "|".join(
        re.escape(u) for u in sorted(UNIT_MAP, key=len, reverse=True)
    ) + r")\b\.?",
    re.IGNORECASE,
)


def _parse_qty(token: str) -> Optional[float]:
    """Convert a qty token string to a float."""
    token = token.strip()
    if token in FRACTION_MAP:
        return FRACTION_MAP[token]
    if "/" in token:
        parts = token.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(token)
    except ValueError:
        return None


def parse_quantity_unit(raw: str) -> tuple[Optional[float], Optional[str], str]:
    """
    Returns (qty, unit, remainder) from an ingredient string.
    'remainder' is the string with qty + unit tokens removed.
    """
    text = raw.strip()

    # 1. Extract quantity
    qty_val: Optional[float] = None
    qty_end = 0

    m = QTY_PATTERN.match(text)
    if m:
        whole_str = m.group(1)
        frac_str = m.group(2)
        uni_frac = m.group(3)
        dec_str = m.group(4)
        asc_frac = m.group(5)

        if whole_str and frac_str:
            frac = FRACTION_MAP.get(frac_str) or _parse_qty(frac_str) or 0
            qty_val = float(whole_str) + frac
        elif uni_frac:
            qty_val = FRACTION_MAP.get(uni_frac, 0)
        elif dec_str:
            qty_val = float(dec_str)
        elif asc_frac:
            qty_val = _parse_qty(asc_frac)

        qty_end = m.end()
        # check for a following fraction after a space, e.g. "1 ½"
        rest = text[qty_end:].strip()
        m2 = re.match(r'^([½⅓⅔¼¾⅛⅜⅝⅞]|\d+/\d+)', rest)
        if m2 and qty_val is not None:
            extra = FRACTION_MAP.get(m2.group(1)) or _parse_qty(m2.group(1)) or 0
            qty_val += extra
            qty_end += 1 + m2.end()  # +1 for the space

    remainder = text[qty_end:].strip()

    # 2. Extract unit
    unit_val: Optional[str] = None
    m_unit = UNIT_PATTERN.match(remainder)
    if m_unit:
        raw_unit = m_unit.group(1)
        unit_val = UNIT_MAP.get(raw_unit.lower(), raw_unit.lower())
        remainder = remainder[m_unit.end():].strip()

    return qty_val, unit_val, remainder


def extract_modifiers(text: str) -> tuple[list[str], str]:
    """Pull known modifier phrases out of text; return (modifiers, cleaned_text)."""
    found = []
    cleaned = text

    # Remove parenthetical modifiers first
    parens = re.findall(r'\(([^)]+)\)', cleaned)
    for p in parens:
        found.append(p.strip())
        cleaned = cleaned.replace(f"({p})", "").strip()

    # Remove known modifier phrases
    for phrase in sorted(MODIFIER_PHRASES, key=len, reverse=True):
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        if pattern.search(cleaned):
            found.append(phrase)
            cleaned = pattern.sub("", cleaned).strip()

    # Strip trailing commas / conjunctions
    cleaned = re.sub(r'[,;]+$', '', cleaned).strip()
    return found, cleaned

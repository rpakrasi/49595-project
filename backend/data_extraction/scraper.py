from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me


@dataclass
class RecipeOutput:
    source_url: str
    title: str
    ingredients_raw: list[str]
    instructions: list[str]
    metadata: dict[str, Any]


class RecipeExtractionError(Exception):
    """Raised when a recipe cannot be extracted from a URL."""


def clean_text(text: str) -> str:
    """Normalize whitespace and strip surrounding spaces."""
    return re.sub(r"\s+", " ", text).strip()


def split_instructions(text: str) -> list[str]:
    """
    Convert a large instruction block into a clean list of steps.
    Handles numbered steps and paragraph-style text.
    """
    if not text:
        return []

    text = text.strip()

    # Try splitting on numbered instructions like "1. ..." or "2) ..."
    numbered_parts = re.split(r"(?:^|\n|\r)\s*\d+\s*[\.\)]\s*", text)
    numbered_parts = [clean_text(p) for p in numbered_parts if clean_text(p)]
    if len(numbered_parts) >= 2:
        return numbered_parts

    # Fallback: split by line
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    if len(lines) >= 2:
        return lines

    # Last fallback: split by sentence boundaries where it seems step-like
    sentence_parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    sentence_parts = [clean_text(p) for p in sentence_parts if clean_text(p)]
    return sentence_parts if sentence_parts else [clean_text(text)]


def parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """
    Convert common recipe time strings to minutes.
    Examples:
      '1 hr 20 mins' -> 80
      '45 mins' -> 45
    """
    if not time_str:
        return None

    s = time_str.lower()
    hours = 0
    minutes = 0

    hr_match = re.search(r"(\d+)\s*(?:hour|hours|hr|hrs|h)\b", s)
    min_match = re.search(r"(\d+)\s*(?:minute|minutes|min|mins|m)\b", s)

    if hr_match:
        hours = int(hr_match.group(1))
    if min_match:
        minutes = int(min_match.group(1))

    # handle simple number if only one unit is implied poorly
    if hours == 0 and minutes == 0:
        only_num = re.search(r"(\d+)", s)
        if only_num:
            minutes = int(only_num.group(1))

    total = hours * 60 + minutes
    return total if total > 0 else None


def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch raw HTML for fallback extraction."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_with_recipe_scrapers(url: str) -> RecipeOutput:
    """
    Primary extraction path using recipe-scrapers.
    """
    scraper = scrape_me(url, wild_mode=True)

    title = clean_text(scraper.title() or "")
    ingredients = [clean_text(x) for x in scraper.ingredients() if clean_text(x)]

    instructions_raw = scraper.instructions() or ""
    instructions = split_instructions(instructions_raw)

    total_time = parse_time_to_minutes(scraper.total_time())
    yields = scraper.yields()

    image = None
    try:
        image = scraper.image()
    except Exception:
        image = None

    metadata = {
        "total_time_minutes": total_time,
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "yields": clean_text(yields) if yields else None,
        "image": image,
        "host": urlparse(url).netloc,
        "extraction_method": "recipe-scrapers",
    }

    if not title and not ingredients and not instructions:
        raise RecipeExtractionError("recipe-scrapers returned empty content")

    return RecipeOutput(
        source_url=url,
        title=title,
        ingredients_raw=ingredients,
        instructions=instructions,
        metadata=metadata,
    )


def extract_json_ld_recipe(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    """
    Fallback extractor for Schema.org Recipe JSON-LD.
    """
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]

        # Also support @graph
        expanded_candidates = []
        for item in candidates:
            if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                expanded_candidates.extend(item["@graph"])
            else:
                expanded_candidates.append(item)

        for item in expanded_candidates:
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type")
            if item_type == "Recipe" or (isinstance(item_type, list) and "Recipe" in item_type):
                return item

    return None


def extract_with_bs4_fallback(url: str) -> RecipeOutput:
    """
    Secondary extraction path using requests + BeautifulSoup.
    Tries JSON-LD Recipe first, then basic HTML heuristics.
    """
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    recipe_json = extract_json_ld_recipe(soup)

    if recipe_json:
        title = clean_text(recipe_json.get("name", ""))

        ingredients = recipe_json.get("recipeIngredient", [])
        if not isinstance(ingredients, list):
            ingredients = []
        ingredients = [clean_text(x) for x in ingredients if isinstance(x, str) and clean_text(x)]

        instructions_field = recipe_json.get("recipeInstructions", [])
        instructions: list[str] = []

        if isinstance(instructions_field, str):
            instructions = split_instructions(instructions_field)
        elif isinstance(instructions_field, list):
            for step in instructions_field:
                if isinstance(step, str):
                    cleaned = clean_text(step)
                    if cleaned:
                        instructions.append(cleaned)
                elif isinstance(step, dict):
                    text = step.get("text") or step.get("name")
                    if isinstance(text, str) and clean_text(text):
                        instructions.append(clean_text(text))

        image = recipe_json.get("image")
        if isinstance(image, list) and image:
            image = image[0]
        elif isinstance(image, dict):
            image = image.get("url")

        metadata = {
            "total_time_minutes": None,
            "prep_time_minutes": None,
            "cook_time_minutes": None,
            "yields": recipe_json.get("recipeYield"),
            "image": image,
            "host": urlparse(url).netloc,
            "extraction_method": "bs4_jsonld",
        }

        return RecipeOutput(
            source_url=url,
            title=title,
            ingredients_raw=ingredients,
            instructions=instructions,
            metadata=metadata,
        )

    # Very lightweight heuristic fallback
    title_tag = soup.find("h1")
    title = clean_text(title_tag.get_text()) if title_tag else ""

    ingredients = []
    for li in soup.find_all("li"):
        text = clean_text(li.get_text(" ", strip=True))
        lower = text.lower()
        if len(text) > 3 and any(
            token in lower
            for token in ["cup", "cups", "tsp", "tbsp", "oz", "pound", "lb", "grams", "g", "ml"]
        ):
            ingredients.append(text)

    instructions = []
    for p in soup.find_all(["p", "li"]):
        text = clean_text(p.get_text(" ", strip=True))
        if len(text) > 25:
            instructions.append(text)

    # Deduplicate while preserving order
    ingredients = list(dict.fromkeys(ingredients))[:50]
    instructions = list(dict.fromkeys(instructions))[:50]

    if not title and not ingredients and not instructions:
        raise RecipeExtractionError("Fallback HTML extraction failed")

    metadata = {
        "total_time_minutes": None,
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "yields": None,
        "image": None,
        "host": urlparse(url).netloc,
        "extraction_method": "bs4_heuristic",
    }

    return RecipeOutput(
        source_url=url,
        title=title,
        ingredients_raw=ingredients,
        instructions=instructions,
        metadata=metadata,
    )


def extract_recipe(url: str) -> dict[str, Any]:
    """
    Public function
    """
    try:
        recipe = extract_with_recipe_scrapers(url)
    except Exception:
        recipe = extract_with_bs4_fallback(url)

    # Final cleanup
    recipe.ingredients_raw = [x for x in recipe.ingredients_raw if x]
    recipe.instructions = [x for x in recipe.instructions if x]

    if not recipe.ingredients_raw:
        raise RecipeExtractionError("No ingredients found")
    if not recipe.instructions:
        raise RecipeExtractionError("No instructions found")

    return asdict(recipe)


if __name__ == "__main__":
    test_url = input("Enter recipe URL: ").strip()
    result = extract_recipe(test_url)
    print(json.dumps(result, indent=2))
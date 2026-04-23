"""
Step Rewriter

Uses an LLM (via LangChain) to rewrite cooking instructions based on
ingredient substitutions and constraint-driven modifications.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.recipe_generation.constraint_parser import ParsedConstraints


class StepRewriter:
    """
    Rewrites recipe steps using an LLM chain or text-based fallback.
    Handles cooking time/temp adjustments and ingredient-specific modifications.
    """
    
    def __init__(self, llm_provider: str = "openai", model: str = "gpt-3.5-turbo", use_llm: bool = True):
        """
        Initialize the step rewriter.
        
        Args:
            llm_provider: "openai" or "local" (for transformers)
            model: Model name (e.g., "gpt-3.5-turbo", "gpt-4")
            use_llm: Whether to use LLM (if False, uses text-based fallback)
        """
        self.llm_provider = llm_provider
        self.model = model
        self.use_llm = use_llm
        self.llm_chain = self._initialize_chain() if use_llm else None
    
    def _initialize_chain(self):
        """Initialize LangChain with appropriate LLM."""
        try:
            from langchain.llms import OpenAI
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain
        except ImportError:
            raise ImportError(
                "Install LangChain: pip install langchain openai\n"
                "Also set OPENAI_API_KEY environment variable."
            )
        
        if self.llm_provider == "openai":
            llm = OpenAI(model_name=self.model, temperature=0.7)
        else:
            # Fallback to local models would go here
            llm = OpenAI(model_name=self.model, temperature=0.7)
        
        return llm
    
    def rewrite_steps(
        self,
        original_steps: list[str],
        substitutions: list[dict],
        constraints: ParsedConstraints,
        original_ingredients: list[dict],
        new_ingredients: list[dict],
    ) -> list[str]:
        """
        Rewrite recipe steps based on ingredient changes and constraints.
        
        Args:
            original_steps: Original cooking instructions
            substitutions: List of applied substitutions (with swap_ratio, notes)
            constraints: ParsedConstraints object with user preferences
            original_ingredients: Original ingredient list (with names)
            new_ingredients: Substituted ingredient list
        
        Returns:
            List of rewritten steps
        """
        # Build a mapping of original → new ingredients
        ingredient_map = self._build_ingredient_map(substitutions)
        
        # If not using LLM, use fallback immediately
        if not self.use_llm:
            return self._fallback_rewrite(
                original_steps, ingredient_map, constraints
            )
        
        # Build the LLM prompt
        prompt = self._build_prompt(
            original_steps,
            ingredient_map,
            constraints,
            substitutions,
        )
        
        try:
            response = self.llm_chain.run(prompt)
            rewritten_steps = self._parse_response(response)
        except Exception as e:
            # Fallback: return original steps with basic adjustments
            print(f"LLM error: {e}. Using fallback rewriting.")
            rewritten_steps = self._fallback_rewrite(
                original_steps, ingredient_map, constraints
            )
        
        return rewritten_steps
    
    def _build_ingredient_map(self, substitutions: list[dict]) -> dict:
        """Build a mapping of original → new ingredient names."""
        mapping = {}
        for sub in substitutions:
            original = sub.get("original_ingredient", {}).get("name", "")
            new = sub.get("substituted_ingredient", {}).get("name", "")
            if original and new:
                mapping[original.lower()] = {
                    "new_name": new,
                    "swap_ratio": sub.get("substitution", {}).get("swap_ratio", 1.0),
                    "notes": sub.get("substitution", {}).get("notes", ""),
                }
        return mapping
    
    def _build_prompt(
        self,
        steps: list[str],
        ingredient_map: dict,
        constraints: ParsedConstraints,
        substitutions: list[dict],
    ) -> str:
        """Build the prompt for the LLM."""
        steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
        
        # Build ingredient substitution details
        subs_text = ""
        if ingredient_map:
            subs_text = "The following ingredient substitutions have been made:\n"
            for orig, info in ingredient_map.items():
                subs_text += (
                    f"- {orig} → {info['new_name']} "
                    f"(use {info['swap_ratio']*100:.0f}% of original amount)\n"
                )
                if info["notes"]:
                    subs_text += f"  Note: {info['notes']}\n"
        
        # Build constraints text
        constraints_text = (
            "User constraints and preferences:\n"
            f"{self._format_constraints(constraints)}"
        )
        
        prompt = f"""You are an expert chef tasked with adapting a recipe.

Original recipe steps:
{steps_text}

{subs_text}

{constraints_text}

Your task:
1. Replace ingredient names with new ones in the steps
2. Adjust cooking times if needed (based on substitution types)
3. Adjust heat levels if specified
4. Add any important notes (e.g., "substitute browns faster")
5. Keep the overall cooking technique and structure

Return ONLY the rewritten steps as a numbered list (1. 2. 3. etc), nothing else.
Do not include explanations or meta-commentary."""
        
        return prompt
    
    def _format_constraints(self, constraints: ParsedConstraints) -> str:
        """Format constraints for the LLM prompt."""
        parts = []
        
        if constraints.dietary_constraints:
            parts.append(f"Dietary: {', '.join(constraints.dietary_constraints)}")
        
        if constraints.exclude_ingredients:
            parts.append(f"Exclude: {', '.join(constraints.exclude_ingredients)}")
        
        if constraints.cooking_time_adjustment != "none":
            parts.append(f"Cooking time should be {constraints.cooking_time_adjustment}d")
        
        if constraints.cooking_level_adjustment != "none":
            parts.append(f"Heat level should be {constraints.cooking_level_adjustment}d")
        
        return "\n".join(f"  • {p}" for p in parts) if parts else "  • No specific constraints"
    
    def _parse_response(self, response: str) -> list[str]:
        """Parse LLM response into list of steps."""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("markdown"):
                response = response[8:]
            response = response.strip()
        
        # Split by numbered lines (1. 2. 3. etc)
        import re
        steps = re.split(r"^\d+\.\s+", response, flags=re.MULTILINE)
        steps = [s.strip() for s in steps if s.strip()]
        
        return steps if steps else ["No steps returned from LLM"]
    
    def _fallback_rewrite(
        self,
        steps: list[str],
        ingredient_map: dict,
        constraints: ParsedConstraints,
    ) -> list[str]:
        """Fallback text-based rewriting when LLM is unavailable."""
        rewritten = []
        
        for step in steps:
            new_step = step
            
            # Replace ingredient names
            for orig, info in ingredient_map.items():
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(orig), re.IGNORECASE)
                new_step = pattern.sub(info["new_name"], new_step)
            
            # Add cooking time adjustments if applicable
            if constraints.cooking_time_adjustment == "reduce":
                if any(word in new_step.lower() for word in ["minute", "hour", "cook"]):
                    new_step = f"{new_step} [reduced cooking time]"
            
            if constraints.cooking_level_adjustment == "reduce":
                if any(word in new_step.lower() for word in ["heat", "temperature", "medium", "high"]):
                    new_step = f"{new_step} [use lower heat]"
            
            rewritten.append(new_step)
        
        return rewritten
    
    def adjust_cooking_time(
        self,
        original_time_minutes: Optional[int],
        constraints: ParsedConstraints,
    ) -> Optional[int]:
        """
        Adjust cooking time based on constraints.
        
        Args:
            original_time_minutes: Original cooking time
            constraints: Parsed user constraints
        
        Returns:
            Adjusted time or None if no adjustment
        """
        if not original_time_minutes:
            return None
        
        if constraints.cooking_time_adjustment == "reduce":
            return max(5, int(original_time_minutes * 0.75))  # Reduce by 25%
        elif constraints.cooking_time_adjustment == "increase":
            return int(original_time_minutes * 1.25)  # Increase by 25%
        
        return original_time_minutes

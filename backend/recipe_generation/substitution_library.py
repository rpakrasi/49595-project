"""
Substitution Library Manager

Manages a pandas DataFrame of ingredient substitutions with filtering
for dietary constraints, allergies, and preferences.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.recipe_generation.utils import expand_semicolon_list


@dataclass
class Substitution:
    """Represents a single substitution option."""
    original_ingredient: str
    original_role: str
    substitute_ingredient: str
    substitute_role: str
    swap_ratio: float  # e.g., 1.0 means 1:1 ratio, 0.75 means use 75% of original quantity
    functional_role: str  # the role they both satisfy (e.g., "fat", "protein")
    constraints: list[str]  # e.g., ["vegan", "gluten-free", "keto"]
    notes: str  # cooking notes (e.g., "may brown faster", "adds nuttier flavor")
    heat_adjustment: Optional[str]  # e.g., "reduce_by_10%", "increase_by_15%"


class SubstitutionLibrary:
    """
    Manages a CSV-based library of ingredient substitutions.
    
    Provides filtering by dietary constraints, functional role, and ingredient matching.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the substitution library.
        
        Args:
            library_path: Path to CSV file. If None, uses default location.
        """
        if library_path is None:
            # Default location relative to this module
            library_path = Path(__file__).parent / "substitutions.csv"

        self.library_path = Path(library_path)
        self.df = self._load_library()

    def _load_library(self) -> pd.DataFrame:
        """Load substitutions from CSV."""
        if not self.library_path.exists():
            # Return empty DataFrame if file doesn't exist yet
            return pd.DataFrame(columns=[
                "original_ingredient", "original_role", "substitute_ingredient",
                "substitute_role", "swap_ratio", "functional_role",
                "constraints", "notes", "heat_adjustment"
            ])

        df = pd.read_csv(self.library_path)

        # Parse constraints (comma-separated into lists)
        if "constraints" in df.columns:
            df["constraints"] = df["constraints"].fillna("").apply(
                lambda x: [c.strip() for c in x.split(",") if c.strip()]
            )
        else:
            df["constraints"] = [[] for _ in range(len(df))]

        # Parse swap_ratio to float
        df["swap_ratio"] = pd.to_numeric(df["swap_ratio"], errors="coerce").fillna(1.0)

        return df

    def find_substitutions(
            self,
            ingredient_name: str,
            functional_role: str,
            constraints: Optional[list[str]] = None,
    ) -> list[Substitution]:
        """
        Find substitutions for a given ingredient and role.
        
        Args:
            ingredient_name: Original ingredient name (e.g., "butter")
            functional_role: The role it serves (e.g., "fat")
            constraints: List of constraints to filter by (e.g., ["vegan", "gluten-free"])
        
        Returns:
            List of Substitution objects sorted by constraint match count.
        """
        if self.df.empty:
            return []

        constraints = constraints or []
        constraints_lower = [c.lower() for c in constraints]

        # Find rows where original_ingredient matches (case-insensitive substring)
        ingredient = ingredient_name.lower()
        role = functional_role.lower()

        mask1 = (
                    self.df["original_ingredient"].str.lower().str.contains(
                        ingredient, na=False, regex=False
                    )
                ) & (
                        self.df["functional_role"].str.lower().str.contains(
                        role, na=False, regex=False
                    )
                )

        def matches2(r):
            ing = r["original_ingredient"]
            func = r["functional_role"]

            if isinstance(ing, list):
                ing_match = any(
                    isinstance(x, str) and x.lower() in ingredient for x in ing
                )
            elif isinstance(ing, str):
                ing_match = ing.lower() in ingredient
            else:
                ing_match = False

            if isinstance(func, list):
                role_match = any(
                    isinstance(x, str) and x.lower() == role for x in func
                )
            elif isinstance(func, str):
                role_match = func.lower() == role
            else:
                role_match = False

            return ing_match and role_match

        mask2 = self.df.apply(matches2, axis=1)

        # combine masks instead of concatenating DataFrames
        matches = self.df[mask1 | mask2]

        results = []

        for _, row in matches.iterrows():
            # Check if substitute satisfies all constraints
            row_constraints_lower = [c.lower() for c in row["constraints"]]
            row_constraints_lower = expand_semicolon_list(row_constraints_lower)
            # If constraints specified, filter: substitute must have all requested constraints
            if constraints_lower:
                if not all(c in row_constraints_lower for c in constraints_lower):
                    continue

            sub = Substitution(
                original_ingredient=row["original_ingredient"],
                original_role=row["original_role"],
                substitute_ingredient=row["substitute_ingredient"],
                substitute_role=row["substitute_role"],
                swap_ratio=float(row["swap_ratio"]),
                functional_role=row["functional_role"],
                constraints=row_constraints_lower,
                notes=row.get("notes", ""),
                heat_adjustment=row.get("heat_adjustment"),
            )
            results.append(sub)

        # Sort by constraint match count (best matches first)
        results.sort(
            key=lambda x: (
                -sum(1 for c in x.constraints if c.lower() in constraints_lower),
                -len(x.constraints)  # then by total constraints
            )
        )

        return results

    def add_substitution(
            self,
            original_ingredient: str,
            original_role: str,
            substitute_ingredient: str,
            substitute_role: str,
            functional_role: str,
            swap_ratio: float = 1.0,
            constraints: Optional[list[str]] = None,
            notes: str = "",
            heat_adjustment: Optional[str] = None,
    ) -> None:
        """Add a new substitution to the library (in-memory only, not persisted)."""
        constraints_str = ",".join(constraints) if constraints else ""

        new_row = pd.DataFrame([{
            "original_ingredient": original_ingredient,
            "original_role": original_role,
            "substitute_ingredient": substitute_ingredient,
            "substitute_role": substitute_role,
            "swap_ratio": swap_ratio,
            "functional_role": functional_role,
            "constraints": constraints_str,
            "notes": notes,
            "heat_adjustment": heat_adjustment or "",
        }])

        self.df = pd.concat([self.df, new_row], ignore_index=True)

    def save_to_csv(self, path: Optional[str] = None) -> None:
        """Persist library to CSV."""
        save_path = Path(path) if path else self.library_path

        # Convert constraints list back to comma-separated string for CSV
        df_to_save = self.df.copy()
        df_to_save["constraints"] = df_to_save["constraints"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else x
        )

        df_to_save.to_csv(save_path, index=False)

    def get_all_constraints(self) -> list[str]:
        """Get unique list of all available constraints in library."""
        all_constraints = set()
        for constraints_list in self.df["constraints"]:
            if isinstance(constraints_list, list):
                all_constraints.update(constraints_list)
        return sorted(list(all_constraints))

    def get_substitutions_by_role(self, functional_role: str) -> list[str]:
        """Get all substitute ingredients available for a given role."""
        role_subs = self.df[
            self.df["functional_role"].str.lower() == functional_role.lower()
            ]
        return role_subs["substitute_ingredient"].unique().tolist()
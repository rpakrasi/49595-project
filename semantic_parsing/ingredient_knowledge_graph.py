from __future__ import annotations
import networkx as nx

from semantic_parsing.role_taxonomy import ROLE_TAXONOMY

_HAS_NX = True

class IngredientKnowledgeGraph:
    """
    A lightweight directed graph where:
      - Nodes are functional role categories (e.g. 'fat', 'structure')
      - Edges encode culinary relationships (e.g. fat → structure: 'tenderizes')
    Ingredients are mapped to their role node on lookup.
    """

    ROLE_RELATIONSHIPS = [
        # (source_role, target_role, relationship_label)
        ("fat", "structure", "tenderizes"),
        ("fat", "protein", "carries_flavor_to"),
        ("leavening", "structure", "lifts"),
        ("acid", "protein", "denatures"),
        ("acid", "leavening", "activates"),
        ("liquid", "structure", "hydrates"),
        ("liquid", "leavening", "activates"),
        ("sweetener", "structure", "softens"),
        ("sweetener", "protein", "inhibits_browning"),
        ("protein", "structure", "binds"),
        ("aromatic", "flavoring", "base_for"),
        ("herb", "flavoring", "brightens"),
        ("spice", "flavoring", "deepens"),
        ("thickener", "liquid", "gels"),
        ("emulsifier", "fat", "stabilizes"),
        ("emulsifier", "liquid", "stabilizes"),
        ("coating", "protein", "encrusts"),
        ("seasoning", "flavoring", "enhances"),
    ]

    # Human-readable role descriptions for Part 3
    ROLE_DESCRIPTIONS = {
        "structure": "Provides bulk and physical framework",
        "leavening": "Creates lift and airy texture via gas production",
        "fat": "Adds richness, moisture, and carries flavor",
        "protein": "Binds ingredients and provides nutrition",
        "liquid": "Hydrates dry ingredients and carries heat",
        "sweetener": "Adds sweetness and affects browning",
        "acid": "Brightens flavors and activates leaveners",
        "seasoning": "Enhances all other flavors",
        "aromatic": "Foundational savory flavor base",
        "herb": "Fresh or dried botanical flavoring",
        "spice": "Dried seed/bark/root flavoring with warmth",
        "flavoring": "Concentrated flavor agent",
        "vegetable": "Adds texture, nutrition, and volume",
        "fruit": "Adds sweetness, acidity, and texture",
        "nut": "Adds crunch, fat, and richness",
        "seed": "Adds texture, nutrition, and mild flavor",
        "thickener": "Increases viscosity of liquids",
        "emulsifier": "Helps fat and water combine stably",
        "coating": "Forms a crust or protective layer",
        "unknown": "Role could not be determined",
    }

    def __init__(self):
        if _HAS_NX:
            self.G = nx.DiGraph()
            self._build_graph()
        else:
            self.G = None

    def _build_graph(self):
        """Populate nodes and edges from the role taxonomy."""
        for role, desc in self.ROLE_DESCRIPTIONS.items():
            self.G.add_node(role, description=desc)
        for src, tgt, label in self.ROLE_RELATIONSHIPS:
            self.G.add_edge(src, tgt, relationship=label)

    def lookup_role(self, ingredient_name: str) -> tuple[str, float]:
        """
        Match ingredient name to a functional role.
        Returns (role, confidence) where confidence reflects match quality.
        """
        name_lower = ingredient_name.lower().strip()

        # Exact match
        if name_lower in ROLE_TAXONOMY:
            return ROLE_TAXONOMY[name_lower], 1.0

        # Substring match (longest matching key wins)
        candidates = [
            (key, role)
            for key, role in ROLE_TAXONOMY.items()
            if key in name_lower or name_lower in key
        ]
        if candidates:
            best_key, best_role = max(candidates, key=lambda x: len(x[0]))
            confidence = len(best_key) / max(len(name_lower), 1)
            confidence = min(confidence, 0.9)
            return best_role, confidence

        # Word-level match
        words = set(name_lower.split())
        for key, role in ROLE_TAXONOMY.items():
            key_words = set(key.split())
            if words & key_words:
                return role, 0.7

        return "unknown", 0.3

    def get_relationships(self, role: str) -> list[dict]:
        """Return all edges from/to a role node with their labels."""
        if not _HAS_NX or self.G is None:
            return []
        rels = []
        for _, tgt, data in self.G.out_edges(role, data=True):
            rels.append({"type": "affects", "target": tgt, "how": data.get("relationship", "")})
        for src, _, data in self.G.in_edges(role, data=True):
            rels.append({"type": "affected_by", "source": src, "how": data.get("relationship", "")})
        return rels

    def substitution_candidates(self, role: str) -> list[str]:
        """
        Returns other ingredient categories that could substitute for this role.
        Useful hint for Part 3's constraint solver.
        """
        same_role = [
            ing for ing, r in ROLE_TAXONOMY.items() if r == role
        ]
        return list(dict.fromkeys(same_role))  # dedup, preserve order

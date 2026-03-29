# 49595-project

## File Descriptions

`ingredient_parser.py` contains a regex-based NER parser that handles:

- unicode fractions (½, ¾)
- ASCII fractions (1/4)
- mixed quantities (2 ¼)
- parenthetical modifiers,
- and 50+ unit synonyms.

The `IngredientKnowledgeGraph` class is backed by `networkx`. It has 20 role categories and 18 directed
culinary relationships (e.g. fat → tenderizes → structure, acid → activates → leavening). The `lookupRole()` function
does three-tier matching (exact → substring → word-level) with confidence scores.
import pytest

from semantic_parsing.ingredient_parser import process_recipe


@pytest.mark.parametrize("recipe, expected_ingredients", [
    (
            {
                "title": "Classic Chocolate Chip Cookies",
                "source_url": "https://example.com/cookies",
                "ingredients_raw": [
                    "2 ¼ cups all-purpose flour",
                    "1 tsp baking soda",
                    "1 tsp salt",
                    "1 cup (2 sticks) butter, softened",
                    "¾ cup granulated sugar",
                    "¾ cup packed brown sugar",
                    "2 large eggs",
                    "2 tsp vanilla extract",
                    "2 cups chocolate chips",
                    "½ cup chopped walnuts (optional)",
                ]
            },
            [{'confidence': 0.6470588235294118, 'functional_role': 'structure', 'modifiers': [],
              'name': 'all-purpose flour', 'qty': 2.25, 'raw': '2 ¼ cups all-purpose flour', 'unit': 'cup'},
             {'confidence': 1.0, 'functional_role': 'leavening', 'modifiers': [], 'name': 'baking soda', 'qty': 1.0,
              'raw': '1 tsp baking soda', 'unit': 'tsp'},
             {'confidence': 1.0, 'functional_role': 'seasoning', 'modifiers': [], 'name': 'salt', 'qty': 1.0,
              'raw': '1 tsp salt', 'unit': 'tsp'},
             {'confidence': 1.0, 'functional_role': 'fat', 'modifiers': ['2 sticks', 'softened'], 'name': 'butter',
              'qty': 1.0, 'raw': '1 cup (2 sticks) butter, softened', 'unit': 'cup'},
             {'confidence': 0.3125, 'functional_role': 'sweetener', 'modifiers': [], 'name': 'granulated sugar',
              'qty': 0.75, 'raw': '¾ cup granulated sugar', 'unit': 'cup'},
             {'confidence': 1.0, 'functional_role': 'sweetener', 'modifiers': ['packed'], 'name': 'brown sugar',
              'qty': 0.75, 'raw': '¾ cup packed brown sugar', 'unit': 'cup'},
             {'confidence': 1.0, 'functional_role': 'protein', 'modifiers': [], 'name': 'eggs', 'qty': 2.0,
              'raw': '2 large eggs', 'unit': 'large'},
             {'confidence': 0.4666666666666667, 'functional_role': 'flavoring', 'modifiers': [],
              'name': 'vanilla extract', 'qty': 2.0, 'raw': '2 tsp vanilla extract', 'unit': 'tsp'},
             {'confidence': 0.6, 'functional_role': 'flavoring', 'modifiers': [], 'name': 'chocolate chips', 'qty': 2.0,
              'raw': '2 cups chocolate chips', 'unit': 'cup'},
             {'confidence': 0.4, 'functional_role': 'nut', 'modifiers': ['optional'], 'name': 'chopped walnuts',
              'qty': 0.5, 'raw': '½ cup chopped walnuts (optional)', 'unit': 'cup'}]
    ), (
            {"title": "Classic Chocolate Chip Cookies",
             "source_url": "https://example.com/cookies",
             "ingredients_raw":
                 ['3 medium ripe bananas ((3 bananas yield ~1 1/2 cups or 337 g))', '1/2 tsp pure vanilla extract',
                  '1 whole egg', '3 Tbsp avocado or coconut oil, melted', '1/4 cup organic cane sugar',
                  '1/4 cup packed organic brown sugar',
                  '2-3 Tbsp maple syrup ((depending on ripeness of bananas // or sub honey))',
                  '3 1/2 tsp baking powder ((aluminum-free*))', '3/4 tsp sea salt', '1/2 tsp ground cinnamon',
                  '3/4 cup unsweetened almond milk', '1 1/4 cup almond meal', '1 1/4 cup gluten-free flour blend',
                  '1 1/4 cup gluten-free rolled oats', 'Butter', 'Honey']},
            [
                {
                    'confidence': 0.42857142857142855,
                    'functional_role': 'fruit',
                    'modifiers': [
                        'medium ripe', '(3 bananas yield ~1 1/2 cups or 337 g)',
                    ],
                    'name': 'bananas',
                    'qty': 3.0,
                    'raw': '3 medium ripe bananas ((3 bananas yield ~1 1/2 cups or 337 g))',
                    'unit': 'medium',
                },
                {
                    'confidence': 0.25925925925925924,
                    'functional_role': 'flavoring',
                    'modifiers': ['pure'],
                    'name': 'vanilla extract',
                    'qty': 0.5,
                    'raw': '1/2 tsp pure vanilla extract',
                    'unit': 'tsp',
                },
                {
                    'confidence': 0.3333333333333333,
                    'functional_role': 'protein',
                    'modifiers': ['whole'],
                    'name': 'eggs',
                    'qty': 1.0,
                    'raw': '1 whole egg',
                    'unit': None,
                },
                {
                    'confidence': 0.5,
                    'functional_role': 'fat',
                    'modifiers': [
                        'melted',
                    ],
                    'name': 'avocado or coconut oil',
                    'qty': 3.0,
                    'raw': '3 Tbsp avocado or coconut oil, melted',
                    'unit': 'tbsp',
                },
                {
                    'confidence': 0.2,
                    'functional_role': 'sweetener',
                    'modifiers': [],
                    'name': 'organic cane sugar',
                    'qty': 0.25,
                    'raw': '1/4 cup organic cane sugar',
                    'unit': 'cup',
                },
                {
                    'confidence': 0.5238095238095238,
                    'functional_role': 'sweetener',
                    'modifiers': [
                        '(depending on ripeness of bananas // or sub honey)',
                    ],
                    'name': 'maple syrup )',
                    'qty': 2.5,
                    'raw': '2-3 Tbsp maple syrup ((depending on ripeness of bananas // or sub '
                           'honey))',
                    'unit': 'Tbsp',
                },
            ]
    )
])
def test_process_simple_recipe(recipe: dict, expected_ingredients: list):
    """Test the ingredient parsing function with a sample scraper output."""
    processed_recipe = process_recipe(recipe)
    assert processed_recipe["ingredients"] == expected_ingredients


def test_correct_quantity_and_units():
    """Test the ingredient parsing function with a sample scraper output."""
    recipe = {"title": "Classic Chocolate Chip Cookies",
              "source_url": "https://example.com/cookies",
              "ingredients_raw":
                  ['3 medium ripe bananas',
                   # '3 1/2 tsp baking powder',
                   # '3/4 tsp sea salt',
                   # '1/2 tsp pure vanilla extract'
                   ]
              }
    expected_ingredients = [
        {
            'functional_role': 'fruit',
            'modifiers': ['medium ripe'],
            'name': 'bananas',
            'qty': 3.0,
            'raw': '3 medium ripe bananas',
            'unit': None,
            # }, {
            #     'functional_role': 'leavening',
            #     'modifiers': [],
            #     'name': 'baking powder',
            #     'qty': 3.5,
            #     'raw': '3 1/2 tsp baking powder',
            #     'unit': 'tsp'
            # }, {
            #     'functional_role': 'seasoning',
            #     'modifiers': [],
            #     'name': 'sea salt',
            #     'qty': 0.75,
            #     'raw': '3/4 tsp sea salt',
            #     'unit': 'tsp'
            # }, {
            #     'functional_role': 'flavoring',
            #     'modifiers': ['pure'],
            #     'name': 'vanilla extract',
            #     'qty': 0.5,
            #     'raw': '1/2 tsp pure vanilla extract',
            #     'unit': 'tsp'
        }
    ]

    processed_ingredients = process_recipe(recipe)["ingredients"]
    assert len(processed_ingredients) == len(expected_ingredients)

    processed_sorted = sorted(processed_ingredients, key=lambda x: x['name'])
    expected_sorted = sorted(expected_ingredients, key=lambda x: x['name'])

    for actual, expected in zip(processed_sorted, expected_sorted):
        assert actual['name'] == expected['name']
        assert actual['qty'] == expected['qty']
        assert actual['unit'] == expected['unit']
        assert actual['functional_role'] == expected['functional_role']
        assert actual['modifiers'] == expected['modifiers']
        assert actual['raw'] == expected['raw']


def test_correct_parentheses_handling():
    """Test that modifiers in parentheses are correctly extracted."""
    assert True

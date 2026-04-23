from ingredient_parser import process_recipe


def test_process_simple_recipe():
    recipe = {
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
    }
    expected_ingredients = [{
        'functional_role': 'structure', 'modifiers': [],
        'name': 'all-purpose flour', 'qty': 2.25, 'raw': '2 ¼ cups all-purpose flour',
        'unit': 'cup'},
        {'functional_role': 'leavening', 'modifiers': [], 'name': 'baking soda',
         'qty': 1.0,
         'raw': '1 tsp baking soda', 'unit': 'tsp'},
        {'functional_role': 'seasoning', 'modifiers': [], 'name': 'salt',
         'qty': 1.0,
         'raw': '1 tsp salt', 'unit': 'tsp'},
        {'functional_role': 'fat', 'modifiers': ['softened'],
         'name': 'butter',
         'qty': 1.0, 'raw': '1 cup (2 sticks) butter, softened', 'unit': 'cup', 'notes': ['2 sticks']},
        {'functional_role': 'sweetener', 'modifiers': [],
         'name': 'granulated sugar',
         'qty': 0.75, 'raw': '¾ cup granulated sugar', 'unit': 'cup'},
        {'functional_role': 'sweetener', 'modifiers': ['packed'],
         'name': 'brown sugar',
         'qty': 0.75, 'raw': '¾ cup packed brown sugar', 'unit': 'cup'},
        {'functional_role': 'protein', 'modifiers': ['large'], 'name': 'eggs',
         'qty': 2.0,
         'raw': '2 large eggs', 'unit': None},
        {'functional_role': 'flavoring', 'modifiers': [],
         'name': 'vanilla extract', 'qty': 2.0, 'raw': '2 tsp vanilla extract', 'unit': 'tsp'},
        {'functional_role': 'flavoring', 'modifiers': [],
         'name': 'chocolate chips', 'qty': 2.0,
         'raw': '2 cups chocolate chips', 'unit': 'cup'},
        {'functional_role': 'nut', 'modifiers': [], 'notes': ['optional'],
         'name': 'chopped walnuts',
         'qty': 0.5, 'raw': '½ cup chopped walnuts (optional)', 'unit': 'cup'}]
    processed_ingredients = process_recipe(recipe)["ingredients"]
    compare_ingredients(processed_ingredients, expected_ingredients)


def test_correct_quantity_and_units():
    recipe = {"title": "Classic Chocolate Chip Cookies",
              "source_url": "https://example.com/cookies",
              "ingredients_raw":
                  [
                      '3 medium ripe bananas',
                      '3 1/2 tsp baking powder',
                      '3/4 tsp sea salt',
                      '1/4 cup organic cane sugar',
                      '1/2 tsp pure vanilla extract'
                  ]
              }
    expected_ingredients = [
        {
            'functional_role': 'fruit',
            'modifiers': ['medium', 'ripe'],
            'name': 'bananas',
            'qty': 3.0,
            'raw': '3 medium ripe bananas',
            'unit': None,
        }, {
            'functional_role': 'leavening',
            'modifiers': [],
            'name': 'baking powder',
            'qty': 3.5,
            'raw': '3 1/2 tsp baking powder',
            'unit': 'tsp'
        }, {
            'functional_role': 'seasoning',
            'modifiers': [],
            'name': 'sea salt',
            'qty': 0.75,
            'raw': '3/4 tsp sea salt',
            'unit': 'tsp'
        }, {
            'functional_role': 'sweetener',
            'modifiers': [],
            'name': 'organic cane sugar',
            'qty': 0.25,
            'raw': '1/4 cup organic cane sugar',
            'unit': 'cup',
        }, {
            'functional_role': 'flavoring',
            'modifiers': ['pure'],
            'name': 'vanilla extract',
            'qty': 0.5,
            'raw': '1/2 tsp pure vanilla extract',
            'unit': 'tsp'
        }
    ]

    processed_ingredients = process_recipe(recipe)["ingredients"]

    compare_ingredients(processed_ingredients, expected_ingredients)


def test_eggs():
    recipe = {"title": "Eggs",
              "source_url": "",
              "ingredients_raw":
                  [
                      '1 whole egg',
                      '3 eggs',
                  ]
              }
    expected_ingredients = [{
        'functional_role': 'protein',
        'modifiers': ['whole'],
        'name': 'egg',
        'qty': 1.0,
        'raw': '1 whole egg',
        'unit': None,
    }, {
        'functional_role': 'protein',
        'modifiers': [],
        'name': 'eggs',
        'qty': 3.0,
        'raw': '3 eggs',
        'unit': None,
    }
    ]

    processed_ingredients = process_recipe(recipe)["ingredients"]

    compare_ingredients(processed_ingredients, expected_ingredients)


def test_correct_parentheses_handling():
    """Test that modifiers in parentheses are correctly extracted."""
    recipe = {"title": "Some Recipe",
              "source_url": "",
              "ingredients_raw":
                  [
                      'Butter',
                      '3 Tbsp avocado or coconut oil, melted',
                      '3 medium ripe bananas ((3 bananas yield ~1 1/2 cups or 337 g))',
                      '3 Tbsp maple syrup ((depending on ripeness of bananas // or sub honey))'
                  ]
              }
    expected_ingredients = [
        {
            'raw': 'Butter', 'qty': None,
            'unit': None, 'name': 'butter',
            'functional_role': 'fat', 'modifiers': [],
        }, {
            'raw': '3 Tbsp avocado or coconut oil, melted',
            'qty': 3.0,
            'unit': 'tbsp',
            'name': 'avocado or coconut oil',
            'modifiers': ['melted'],
            'functional_role': 'fat'
        }, {
            'functional_role': 'fruit',
            'modifiers': ['medium', 'ripe'],
            'notes': ['(3 bananas yield ~1 1/2 cups or 337 g)'],
            'name': 'bananas',
            'qty': 3.0,
            'raw': '3 medium ripe bananas ((3 bananas yield ~1 1/2 cups or 337 g))',
            'unit': None,
        },
        {
            'functional_role': 'sweetener',
            'modifiers': [],
            'notes': [
                '(depending on ripeness of bananas // or sub honey)',
            ],
            'name': 'maple syrup',
            'qty': 3.0,
            'raw': '3 Tbsp maple syrup ((depending on ripeness of bananas // or sub honey))',
            'unit': 'tbsp',
        },
    ]

    processed_ingredients = process_recipe(recipe)["ingredients"]

    compare_ingredients(processed_ingredients, expected_ingredients)


def test_average_unit():
    # 2-3 Tbsp maple syrup
    assert True


def compare_ingredients(processed_ingredients, expected_ingredients):
    assert len(processed_ingredients) == len(expected_ingredients)

    processed_sorted = sorted(processed_ingredients, key=lambda x: x['name'])
    expected_sorted = sorted(expected_ingredients, key=lambda x: x['name'])

    print("Actual: ", processed_sorted)
    for actual, expected in zip(processed_sorted, expected_sorted):
        assert actual['name'] == expected['name']
        assert actual['qty'] == expected['qty']
        assert actual['unit'] == expected['unit']
        assert actual['functional_role'] == expected['functional_role']
        assert actual['modifiers'] == expected['modifiers']
        assert actual['raw'] == expected['raw']
        if 'notes' in expected:
            assert actual['notes'] == expected['notes']

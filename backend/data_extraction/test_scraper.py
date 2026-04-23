from backend.data_extraction.scraper import extract_recipe

def main():
    urls = [
        "https://www.allrecipes.com/recipe/238691/simple-macaroni-and-cheese/",
        "https://www.foodnetwork.com/recipes/ina-garten/mac-and-cheese-recipe2-1945401",
    ]

    for url in urls:
        print("=" * 80)
        print("Testing:", url)
        try:
            recipe = extract_recipe(url)
            print("Title:", recipe["title"])
            print("Ingredients found:", len(recipe["ingredients_raw"]))
            print("Instructions found:", len(recipe["instructions"]))
            print("Method:", recipe["metadata"]["extraction_method"])
        except Exception as e:
            print("FAILED:", e)

if __name__ == "__main__":
    main()
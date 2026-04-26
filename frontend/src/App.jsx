import { useState } from "react";
import "./App.css";

function prettyQty(qty, unit) {
  if (qty == null) return unit ?? "";
  const value = Number.isInteger(qty)
    ? qty.toString()
    : qty.toFixed(2).replace(/\.00$/, "").replace(/0$/, "");
  return [value, unit].filter(Boolean).join(" ");
}

function formatInstruction(text) {
  return String(text)
    // HTML entities
    .replace(/&deg;/gi, "°")
    .replace(/&#176;/gi, "°")

    // weird spacing around degree symbol
    .replace(/(\d+)\s*°\s*F\b/gi, "$1 °F")
    .replace(/(\d+)\s*°\s*C\b/gi, "$1 °C")

    // 350F, 350 F, 350 f
    .replace(/(\d+)\s*F\b/g, "$1 °F")
    .replace(/(\d+)\s*f\b/g, "$1 °F")
    .replace(/(\d+)\s*C\b/g, "$1 °C")
    .replace(/(\d+)\s*c\b/g, "$1 °C")

    // 350 degrees F / 350 degree Fahrenheit
    .replace(/(\d+)\s*degrees?\s*Fahrenheit\b/gi, "$1 °F")
    .replace(/(\d+)\s*degrees?\s*F\b/gi, "$1 °F")
    .replace(/(\d+)\s*degrees?\s*Celsius\b/gi, "$1 °C")
    .replace(/(\d+)\s*degrees?\s*C\b/gi, "$1 °C")

    .replace(/\s+/g, " ")
    .trim();
}

function RecipeCard({ title, recipe }) {
  return (
    <div className="card recipe-card">
      <h2>{title}</h2>
      {recipe ? (
        <>
          <h3>{recipe.title}</h3>

          <div className="section-block">
            <h4>Ingredients</h4>
            {recipe.ingredients?.length ? (
              recipe.ingredients.map((ing, idx) => (
                <div className="item-row" key={idx}>
                  <div>
                    <div className="item-main">{ing.raw || ing.name}</div>
                    <div className="item-sub">
                      {[prettyQty(ing.qty, ing.unit), ing.name]
                        .filter(Boolean)
                        .join(" of ")}
                    </div>
                  </div>
                  {ing.functional_role && (
                    <span className="pill">{ing.functional_role}</span>
                  )}
                </div>
              ))
            ) : recipe.ingredients_raw?.length ? (
              recipe.ingredients_raw.map((ing, idx) => (
                <div className="item-row" key={idx}>
                  <div className="item-main">{ing}</div>
                </div>
              ))
            ) : (
              <p className="muted">No ingredients found.</p>
            )}
          </div>

          <div className="section-block">
            <h4>Instructions</h4>
            {(recipe.instructions || []).map((step, idx) => (
              <div className="step-row" key={idx}>
                <div className="step-num">{idx + 1}</div>
                <div className="instruction-text">{formatInstruction(step)}</div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">Run the pipeline to load this recipe.</p>
      )}
    </div>
  );
}

function App() {
  const [recipeUrl, setRecipeUrl] = useState(
    "https://www.food.com/recipe/best-banana-bread-2886"
  );
  const [constraint, setConstraint] = useState("Make it vegan");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [original, setOriginal] = useState(null);
  const [adapted, setAdapted] = useState(null);

  const substitutions =
    adapted?.adaptation_summary?.substitutions_made || [];
  const constraints =
    adapted?.adaptation_summary?.parsed_constraints || {};

  async function runPipeline() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("/api/recipe/compare", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: recipeUrl,
          constraint,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load recipe comparison");
      }

      setOriginal(data.original_recipe);
      setAdapted(data.adapted_recipe);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="container">
        <header className="hero">
          <p className="eyebrow">Cooking AI</p>
          <h1>Context-Aware Recipe Adaption</h1>
          <p className="subtext">
            Enter a recipe URL and dietary constraint to generate a new
            recipe with adaptations made.
          </p>
        </header>

        <section className="controls card">
          <div className="field">
            <label>Recipe URL</label>
            <input
              value={recipeUrl}
              onChange={(e) => setRecipeUrl(e.target.value)}
              placeholder="Paste a recipe URL"
            />
          </div>

          <div className="field">
            <label>Dietary constraint</label>
            <textarea
              rows="4"
              value={constraint}
              onChange={(e) => setConstraint(e.target.value)}
              placeholder="Example: Make it vegan and gluten-free"
            />
          </div>

          <button onClick={runPipeline} disabled={loading}>
            {loading ? "Running pipeline..." : "Run full pipeline"}
          </button>

          {error && <p className="error">{error}</p>}
        </section>

        {adapted?.adaptation_summary && (
          <section className="summary card">
            <h2>Adaptation Summary</h2>

            <div className="badges">
              {(constraints.dietary || []).map((item, idx) => (
                <span className="badge" key={`d-${idx}`}>
                  Dietary: {item}
                </span>
              ))}
              {(constraints.allergies || []).map((item, idx) => (
                <span className="badge danger" key={`a-${idx}`}>
                  Allergy: {item}
                </span>
              ))}
              {(constraints.exclude || []).map((item, idx) => (
                <span className="badge outline" key={`e-${idx}`}>
                  Exclude: {item}
                </span>
              ))}
            </div>

            <div className="substitutions">
              {substitutions.length ? (
                substitutions.map((sub, idx) => (
                  <div className="sub-card" key={idx}>
                    <div className="sub-title">
                      {sub.original_ingredient?.name || "Original"} →{" "}
                      {sub.substituted_ingredient?.name || "Substitute"}
                    </div>
                    {sub.reason && (
                      <div className="sub-reason">{sub.reason}</div>
                    )}
                  </div>
                ))
              ) : (
                <p className="muted">No substitutions were recorded.</p>
              )}
            </div>
          </section>
        )}

        <section className="recipes">
          <RecipeCard title="Original Recipe" recipe={original} />
          <RecipeCard title="Adapted Recipe" recipe={adapted} />
        </section>
      </div>
    </div>
  );
}

export default App;
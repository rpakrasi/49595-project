"""
Custom NER pipeline to be used instead of the regex parser.

This module provides two options for ingredient parsing:
  1. spaCy custom pipeline (rule-based + trainable) — great for QUANTITY, UNIT, INGREDIENT entities
  2. BERT fine-tuning scaffold (Hugging Face) — for higher accuracy on ambiguous cases
"""

from __future__ import annotations

import json

from semantic_parsing.ingredient_parser import IngredientKnowledgeGraph

# ══════════════════════════════════════════════════════════════════════════════
# OPTION 1: spaCy Custom NER Pipeline
# ══════════════════════════════════════════════════════════════════════════════
#
# Entity labels we train for:
#   QUANTITY  — numeric amounts ("2", "1½", "a pinch of")
#   UNIT      — measurement units ("cups", "tsp", "grams")
#   INGREDIENT — the food item name ("all-purpose flour", "vanilla extract")
#   MODIFIER  — descriptive prep state ("softened", "finely chopped", "packed")

SPACY_TRAINING_EXAMPLES = [
    # (text, {"entities": [(start, end, label), ...]})
    (
        "2 cups all-purpose flour",
        {"entities": [(0, 1, "QUANTITY"), (2, 6, "UNIT"), (7, 24, "INGREDIENT")]},
    ),
    (
        "1 tsp baking soda",
        {"entities": [(0, 1, "QUANTITY"), (2, 5, "UNIT"), (6, 17, "INGREDIENT")]},
    ),
    (
        "3/4 cup packed brown sugar",
        {"entities": [(0, 3, "QUANTITY"), (4, 7, "UNIT"), (8, 14, "MODIFIER"), (15, 26, "INGREDIENT")]},
    ),
    (
        "2 large eggs, lightly beaten",
        {"entities": [(0, 1, "QUANTITY"), (2, 7, "MODIFIER"), (8, 12, "INGREDIENT"), (14, 28, "MODIFIER")]},
    ),
    (
        "1 cup (2 sticks) unsalted butter, softened",
        {"entities": [(0, 1, "QUANTITY"), (2, 5, "UNIT"), (16, 23, "MODIFIER"), (24, 30, "INGREDIENT"), (32, 40, "MODIFIER")]},
    ),
    (
        "a pinch of kosher salt",
        {"entities": [(0, 1, "QUANTITY"), (2, 7, "UNIT"), (11, 22, "INGREDIENT")]},
    ),
    (
        "½ teaspoon freshly ground black pepper",
        {"entities": [(0, 1, "QUANTITY"), (2, 10, "UNIT"), (11, 26, "MODIFIER"), (27, 38, "INGREDIENT")]},
    ),
    (
        "2 tablespoons extra-virgin olive oil",
        {"entities": [(0, 1, "QUANTITY"), (2, 13, "UNIT"), (14, 36, "INGREDIENT")]},
    ),
]


def build_spacy_pipeline():
    """
    Builds and returns a spaCy NLP pipeline with a custom NER component.
    Run train_spacy_ner() to add training data and improve it.

    Usage:
        nlp = build_spacy_pipeline()
        doc = nlp("2 cups all-purpose flour")
        for ent in doc.ents:
            print(ent.text, ent.label_)
    """
    try:
        import spacy
        from spacy.tokens import DocBin
    except ImportError:
        raise ImportError("Install spaCy: pip install spacy && python -m spacy download en_core_web_sm")

    # Load small English model as the base (provides tokenizer, POS, dep)
    nlp = spacy.load("en_core_web_sm")

    # Add a blank NER component (we'll train it on food entities)
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")

    # Register our custom labels
    for label in ("QUANTITY", "UNIT", "INGREDIENT", "MODIFIER"):
        ner.add_label(label)

    return nlp


def train_spacy_ner(output_dir: str = "./models/spacy_food_ner", n_iter: int = 30):
    """
    Fine-tune the spaCy NER pipeline on food ingredient examples.
    In production, replace SPACY_TRAINING_EXAMPLES with 500-1000 annotated samples.

    Args:
        output_dir: where to save the trained model
        n_iter: number of training iterations
    """
    try:
        import spacy
        from spacy.training import Example
        import random
    except ImportError:
        raise ImportError("pip install spacy")

    nlp = build_spacy_pipeline()

    # Freeze all pipes except NER during training
    other_pipes = [p for p in nlp.pipe_names if p != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        for iteration in range(n_iter):
            random.shuffle(SPACY_TRAINING_EXAMPLES)
            losses = {}
            for text, annotations in SPACY_TRAINING_EXAMPLES:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                nlp.update([example], sgd=optimizer, losses=losses)
            if iteration % 10 == 0:
                print(f"  Iteration {iteration} — NER loss: {losses.get('ner', 0):.4f}")

    nlp.to_disk(output_dir)
    print(f"Model saved to {output_dir}")
    return nlp


def spacy_parse_ingredient(nlp, raw: str) -> dict:
    """
    Use a trained spaCy pipeline to parse a single ingredient string.
    Returns dict matching the ParsedIngredient schema.
    """
    doc = nlp(raw)
    result = {
        "raw": raw,
        "qty": None,
        "unit": None,
        "name": None,
        "modifiers": [],
        "confidence": 0.8,  # spaCy doesn't expose token-level confidence easily
    }

    qty_parts = []
    for ent in doc.ents:
        if ent.label_ == "QUANTITY":
            qty_parts.append(ent.text)
        elif ent.label_ == "UNIT":
            result["unit"] = ent.text.lower()
        elif ent.label_ == "INGREDIENT":
            result["name"] = ent.text.lower()
        elif ent.label_ == "MODIFIER":
            result["modifiers"].append(ent.text.lower())

    # Combine qty tokens into a float
    if qty_parts:
        from ingredient_parser import _parse_qty
        total = 0.0
        for part in qty_parts:
            v = _parse_qty(part)
            if v:
                total += v
        result["qty"] = total or None

    return result


# ══════════════════════════════════════════════════════════════════════════════
# OPTION 2: BERT Fine-tuning Scaffold (Hugging Face Transformers)
# ══════════════════════════════════════════════════════════════════════════════
#
# Install: pip install transformers torch datasets seqeval
#
# We frame ingredient parsing as token classification (BIO tagging).
# Labels: B-QTY, I-QTY, B-UNIT, I-UNIT, B-ING, I-ING, B-MOD, I-MOD, O
#
# The fine-tuning uses bert-base-uncased (or distilbert for speed).
# With ~500 annotated examples you can get >90% F1 on ingredient NER.

BIO_LABEL_LIST = [
    "O",
    "B-QUANTITY", "I-QUANTITY",
    "B-UNIT",     "I-UNIT",
    "B-INGREDIENT","I-INGREDIENT",
    "B-MODIFIER", "I-MODIFIER",
]
LABEL2ID = {l: i for i, l in enumerate(BIO_LABEL_LIST)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}

# Example BIO-tagged training sentence (word-level)
BERT_TRAINING_EXAMPLE = {
    "tokens":  ["2",    "cups", "all-purpose", "flour"],
    "labels":  ["B-QUANTITY", "B-UNIT", "B-INGREDIENT", "I-INGREDIENT"],
}


def build_bert_model(model_name: str = "distilbert-base-uncased"):
    """
    Load a pre-trained BERT/DistilBERT model for token classification.
    The classification head maps to our 9 BIO labels.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        (tokenizer, model) ready for fine-tuning
    """
    try:
        from transformers import AutoTokenizer, AutoModelForTokenClassification
    except ImportError:
        raise ImportError("pip install transformers torch")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(BIO_LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    return tokenizer, model


def fine_tune_bert(
    train_data: list[dict],
    output_dir: str = "./models/bert_food_ner",
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 2e-5,
):
    """
    Fine-tune BERT for ingredient NER.

    Args:
        train_data: list of {"tokens": [...], "labels": [...]} dicts
        output_dir: save location
        epochs, batch_size, lr: standard hyperparameters

    Expected results with 500+ examples:
        Precision: ~0.91  |  Recall: ~0.89  |  F1: ~0.90

    Recommended training data sources:
        - TASTEset (2022): 700 recipes with BIO annotations  https://github.com/tanikina/tasteset
        - NYT Cooking annotations (custom)
        - Allrecipes ingredient strings (scrape + label with Doccano)
    """
    try:
        from transformers import (
            AutoTokenizer, AutoModelForTokenClassification,
            TrainingArguments, Trainer, DataCollatorForTokenClassification,
        )
        from datasets import Dataset
        import numpy as np
        from seqeval.metrics import classification_report
    except ImportError:
        raise ImportError("pip install transformers datasets seqeval torch")

    tokenizer, model = build_bert_model()

    def tokenize_and_align_labels(examples):
        tokenized = tokenizer(
            examples["tokens"],
            truncation=True,
            is_split_into_words=True,
            padding="max_length",
            max_length=64,
        )
        all_labels = []
        for i, labels in enumerate(examples["labels"]):
            word_ids = tokenized.word_ids(batch_index=i)
            prev_word_id = None
            label_ids = []
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)  # ignore special tokens in loss
                elif word_id != prev_word_id:
                    label_ids.append(LABEL2ID[labels[word_id]])
                else:
                    # For sub-word tokens: continue with I- label or -100
                    lbl = labels[word_id]
                    if lbl.startswith("B-"):
                        label_ids.append(LABEL2ID["I-" + lbl[2:]])
                    else:
                        label_ids.append(LABEL2ID[lbl])
                prev_word_id = word_id
            all_labels.append(label_ids)
        tokenized["labels"] = all_labels
        return tokenized

    dataset = Dataset.from_list(train_data)
    tokenized_ds = dataset.map(tokenize_and_align_labels, batched=True)

    data_collator = DataCollatorForTokenClassification(tokenizer)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=lr,
        weight_decay=0.01,
        logging_steps=50,
        save_strategy="epoch",
        evaluation_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Fine-tuned model saved to {output_dir}")
    return model, tokenizer


def bert_parse_ingredient(
    tokenizer,
    model,
    raw: str,
    device: str = "cpu",
) -> dict:
    """
    Run inference with the fine-tuned BERT model on a single ingredient string.
    Returns dict matching ParsedIngredient schema.
    """
    try:
        import torch
    except ImportError:
        raise ImportError("pip install torch")

    inputs = tokenizer(raw, return_tensors="pt", truncation=True, max_length=64)
    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits[0]
    probs = torch.softmax(logits, dim=-1)
    predicted_ids = logits.argmax(dim=-1).tolist()
    confidence_scores = probs.max(dim=-1).values.tolist()

    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

    # Reconstruct entity spans from BIO tags
    entities: dict[str, list[str]] = {
        "QUANTITY": [], "UNIT": [], "INGREDIENT": [], "MODIFIER": []
    }
    avg_confidence = sum(confidence_scores[1:-1]) / max(len(confidence_scores) - 2, 1)

    for tok, pred_id, conf in zip(tokens[1:-1], predicted_ids[1:-1], confidence_scores[1:-1]):
        label = ID2LABEL[pred_id]
        if label == "O" or tok.startswith("##"):
            continue
        category = label.split("-")[-1] if "-" in label else None
        if category in entities:
            entities[category].append(tok.replace("##", ""))

    def join_tokens(toks):
        return " ".join(toks).replace(" ##", "")

    result = {
        "raw": raw,
        "qty": None,
        "unit": join_tokens(entities["UNIT"]) or None,
        "name": join_tokens(entities["INGREDIENT"]) or None,
        "modifiers": entities["MODIFIER"],
        "confidence": round(avg_confidence, 3),
    }

    qty_str = join_tokens(entities["QUANTITY"])
    if qty_str:
        from ingredient_parser import _parse_qty
        result["qty"] = _parse_qty(qty_str)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED INTERFACE — drop-in for ingredient_parser.py
# ══════════════════════════════════════════════════════════════════════════════

class AdvancedNERParser:
    """
    Wraps spaCy or BERT behind a single .parse() interface.
    ingredient_parser.py can swap this in for the regex-based parser.
    """

    def __init__(self, backend: str = "regex"):
        """
        Args:
            backend: "regex" (default, no dependencies),
                     "spacy"  (requires spacy model),
                     "bert"   (requires trained fine-tuned model)
        """
        self.backend = backend
        self._nlp = None
        self._bert_tok = None
        self._bert_model = None

    def load_spacy(self, model_path: str = "en_core_web_sm"):
        import spacy
        self._nlp = spacy.load(model_path)

    def load_bert(self, model_path: str = "./models/bert_food_ner"):
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        self._bert_tok = AutoTokenizer.from_pretrained(model_path)
        self._bert_model = AutoModelForTokenClassification.from_pretrained(model_path)

    def parse(self, raw: str) -> dict:
        if self.backend == "spacy" and self._nlp:
            return spacy_parse_ingredient(self._nlp, raw)
        elif self.backend == "bert" and self._bert_model:
            return bert_parse_ingredient(self._bert_tok, self._bert_model, raw)
        else:
            # Fall back to regex parser
            from ingredient_parser import parse_quantity_unit, extract_modifiers
            qty, unit, remainder = parse_quantity_unit(raw)
            modifiers, name = extract_modifiers(remainder)
            role, confidence = IngredientKnowledgeGraph().lookup_role(name)
            return {
                "raw": raw,
                "qty": qty,
                "unit": unit,
                "name": name.lower().strip(),
                "modifiers": modifiers,
                "role": role,
                "confidence": confidence,
            }


if __name__ == "__main__":
    parser = AdvancedNERParser(backend="regex")
    tests = [
        "2 ¼ cups all-purpose flour",
        "1 tsp baking soda",
        "¾ cup packed brown sugar",
        "2 large eggs, lightly beaten",
        "1 tbsp extra-virgin olive oil",
        "a pinch of kosher salt",
        "1 (8 ounce) box elbow macaroni",
        "0.25 cup butter",
        "0.25 cup all-purpose flour",
        "0.5 teaspoon salt",
        "ground black pepper to taste",
        "2 cups milk",
        "2 cups shredded Cheddar cheese"
    ]
    for t in tests:
        print(json.dumps(parser.parse(t), indent=2, default=str))
        print("---")

#!/usr/bin/env python3
"""Phase 2.4-2.5 — render curated rows into the PRODUCTION chat format and split.

Each curated row becomes a chat example whose assistant target is the exact production
JSON shape ({"issues":[...]}). This aligns training to how the model is actually used
(the root-cause fix). System prompt is imported verbatim from backend source.

  - Correct row    -> assistant = {"issues": []}            (teaches restraint)
  - violation row  -> assistant = {"issues":[{phrase,category,severity,explanation}]}
                      severity = English enum (matches production map_severity);
                      explanation in the sentence's language (Gemma-regenerated, clean).

Stratified 90/10 split by (label x language). Outputs data/curated/{train,val}.jsonl
with both `messages` (chat) and pre-rendered `text`.
"""
import ast
import json
import os
import random
from collections import defaultdict

from transformers import AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CURATED = os.path.join(HERE, "curated.jsonl")
LLM_CLIENT = os.path.join(REPO, "backend", "app", "modules", "analysis", "llm_client.py")
BASE_MODEL = "/data/shahafw_home/inclusify_retrain/base_model/Qwen2.5-3B-Instruct"
# Rendered JSONL is ~280MB (system prompt repeated per example) -> /data, not git.
OUT_DIR = "/data/shahafw_home/inclusify_retrain/curated_data"
USER_TEMPLATE = 'Analyze this passage for LGBTQ+ inclusive language compliance:\n"{sentence}"'
SEED = 42


def load_system_prompt():
    tree = ast.parse(open(LLM_CLIENT, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "SYSTEM_PROMPT" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("SYSTEM_PROMPT not found")


def target_json(row):
    if row["label"] == "Correct":
        return {"issues": []}
    issue = {"phrase": row["phrase"], "category": row["category"],
             "severity": row["label"], "explanation": row["explanation"]}
    return {"issues": [issue]}


def main():
    random.seed(SEED)
    sp = load_system_prompt()
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)

    rows = [json.loads(l) for l in open(CURATED, encoding="utf-8")]
    # drop violation rows that have no usable explanation (e.g. judge_error w/ None)
    usable, dropped = [], 0
    for r in rows:
        if r["label"] != "Correct" and not (r.get("explanation") or "").strip():
            dropped += 1
            continue
        usable.append(r)
    print(f"curated rows: {len(rows)}  dropped (violation w/o explanation): {dropped}  usable: {len(usable)}")

    # Phase 2.5 balancing: the (correct) relabel left ~64% Correct; cap to ~50% to match the
    # eval's natural ~50% Correct share and avoid over-leniency. Keep ALL violations;
    # subsample Correct, stratified by language.
    TARGET_CORRECT_SHARE = 0.50
    correct = [r for r in usable if r["label"] == "Correct"]
    viol = [r for r in usable if r["label"] != "Correct"]
    target_correct = min(len(correct), int(round(len(viol) * TARGET_CORRECT_SHARE /
                                                  (1 - TARGET_CORRECT_SHARE))))
    by_lang = defaultdict(list)
    for r in correct:
        by_lang[r["language"]].append(r)
    kept_correct = []
    for lang, items in by_lang.items():
        random.shuffle(items)
        share = len(items) / len(correct)
        kept_correct.extend(items[:max(1, int(round(target_correct * share)))])
    usable = viol + kept_correct
    random.shuffle(usable)
    print(f"balance: correct {len(correct)}->{len(kept_correct)}, violations {len(viol)} "
          f"-> total {len(usable)} (correct share {len(kept_correct)/len(usable):.2f})")

    examples = []
    for r in usable:
        assistant = json.dumps(target_json(r), ensure_ascii=False)
        messages = [
            {"role": "system", "content": sp},
            {"role": "user", "content": USER_TEMPLATE.format(sentence=r["sentence"])},
            {"role": "assistant", "content": assistant},
        ]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        examples.append({"messages": messages, "text": text,
                         "label": r["label"], "language": r["language"]})

    # stratified 90/10 split by (label x language)
    buckets = defaultdict(list)
    for e in examples:
        buckets[(e["label"], e["language"])].append(e)
    train, val = [], []
    for key, items in buckets.items():
        random.shuffle(items)
        k = max(1, int(round(len(items) * 0.1)))
        val.extend(items[:k])
        train.extend(items[k:])
    random.shuffle(train)
    random.shuffle(val)

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, data in (("train", train), ("val", val)):
        with open(os.path.join(OUT_DIR, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for e in data:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # token-length sanity (longest example must fit max_seq_length=1024)
    lens = sorted(len(tok(e["text"]).input_ids) for e in random.sample(examples, min(500, len(examples))))
    from collections import Counter
    def dist(data): return dict(Counter((e["label"], e["language"]) for e in data))
    stats = {
        "total": len(examples), "train": len(train), "val": len(val),
        "train_label_dist": dict(Counter(e["label"] for e in train)),
        "train_lang_dist": dict(Counter(e["language"] for e in train)),
        "correct_share_train": round(sum(1 for e in train if e["label"] == "Correct") / len(train), 3),
        "tok_len_p50": lens[len(lens)//2], "tok_len_p95": lens[int(len(lens)*0.95)],
        "tok_len_max_sampled": lens[-1],
    }
    json.dump(stats, open(os.path.join(HERE, "split_stats.json"), "w"), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

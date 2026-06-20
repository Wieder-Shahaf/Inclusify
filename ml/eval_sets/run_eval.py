#!/usr/bin/env python3
"""Phase 1.4 / Phase 4 — Production-format evaluation harness.

Scores an adapter (or the bare base model) the way production actually calls it:
the canonical SYSTEM_PROMPT + the production user template, parse {"issues":[...]},
collapse to a single sentence verdict, compare to the frozen gold label.

The SAME script scores the baseline (Phase 1.4) and every trained candidate
(Phase 4), so numbers are comparable.

Usage:
  python run_eval.py --adapter ml/adapters/qwen_r8_d0.2 --eval expert --out base_expert.json
  python run_eval.py --adapter none --eval gold --out rawbase_gold.json
  python run_eval.py --adapter /data/.../adapters_new/qwen_r8_... --eval both --out cand.json
"""
import argparse
import ast
import json
import os
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_BASE = "/data/shahafw_home/inclusify_retrain/base_model/Qwen2.5-3B-Instruct"
LLM_CLIENT = os.path.join(REPO, "backend", "app", "modules", "analysis", "llm_client.py")

# Production user template (f-string at llm_client.py ~line 491; verified verbatim).
USER_TEMPLATE = 'Analyze this passage for LGBTQ+ inclusive language compliance:\n"{sentence}"'

CANON = ["Correct", "Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"]
VIOLATIONS = {"Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"}
# severity rank for picking a single verdict from multiple issues/spans (higher=worse)
RANK = {"Correct": 0, "Outdated": 1, "Biased": 2, "Potentially Offensive": 3,
        "Factually Incorrect": 4}
LOWER_TO_TITLE = {"outdated": "Outdated", "biased": "Biased",
                  "potentially_offensive": "Potentially Offensive",
                  "factually_incorrect": "Factually Incorrect"}


def load_prod_constants():
    """Import SYSTEM_PROMPT + SEVERITY_MAP from backend source via AST (no backend deps)."""
    tree = ast.parse(open(LLM_CLIENT, encoding="utf-8").read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("SYSTEM_PROMPT", "SEVERITY_MAP"):
                    out[t.id] = ast.literal_eval(node.value)
    return out["SYSTEM_PROMPT"], out["SEVERITY_MAP"]


SYSTEM_PROMPT, SEVERITY_MAP = load_prod_constants()


def normalize_severity(s):
    """Model severity string -> canonical Title label, or None if unrecognized."""
    if s is None:
        return None
    s = str(s).strip()
    if s == "Correct":
        return "Correct"
    if s in {"Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"}:
        return s
    if s in SEVERITY_MAP:  # includes Hebrew fallbacks -> lowercase api value
        return LOWER_TO_TITLE.get(SEVERITY_MAP[s])
    return None


def parse_issues(text):
    """Faithful reimpl of production parse_llm_output: strip fences, slice {..}, load."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None
    try:
        obj = json.loads(t[i:j + 1])
    except Exception:
        return None
    if isinstance(obj, dict) and "issues" in obj:
        return obj["issues"] if isinstance(obj["issues"], list) else []
    if isinstance(obj, dict) and ("severity" in obj or "phrase" in obj):
        return [obj]  # legacy single-object form
    return []


def model_verdict(text):
    """Derive one sentence-level verdict from the model's raw output."""
    issues = parse_issues(text)
    if issues is None:
        return None, "PARSE_FAIL"
    sevs = [normalize_severity(it.get("severity")) for it in issues if isinstance(it, dict)]
    sevs = [s for s in sevs if s in VIOLATIONS]
    if not sevs:
        return "Correct", "ok"
    return max(sevs, key=lambda s: RANK[s]), "ok"


# ---------------- eval set loaders -> list of dicts {sentence, lang, gold, context_dependent} ----
def load_expert():
    recs = [json.loads(l) for l in open(os.path.join(HERE, "expert_eval.jsonl"), encoding="utf-8")]
    return [{"sentence": r["sentence"], "lang": r["lang"], "gold": r["adjudicated_label"],
             "context_dependent": r["context_dependent"], "set": "expert"} for r in recs]


def load_gold():
    recs = [json.loads(l) for l in open(os.path.join(HERE, "gold_eval.jsonl"), encoding="utf-8")]
    by = {}
    for r in recs:
        s = r["sentence"]
        by.setdefault(s, {"sentence": s, "lang": r["lang"], "labels": []})
        by[s]["labels"].append(r["label"])
    out = []
    for s, d in by.items():
        labs = d["labels"]
        gold = "Correct" if all(x == "Correct" for x in labs) else max(
            (x for x in labs if x in VIOLATIONS), key=lambda x: RANK[x])
        out.append({"sentence": s, "lang": d["lang"], "gold": gold,
                    "context_dependent": False, "set": "gold"})
    return out


# ---------------- generation ----------------
@torch.no_grad()
def generate(model, tok, sentences, batch_size=16, max_new_tokens=512):
    outs = []
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        prompts = [tok.apply_chat_template(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": USER_TEMPLATE.format(sentence=s)}],
            tokenize=False, add_generation_prompt=True) for s in batch]
        enc = tok(prompts, return_tensors="pt", padding=True, truncation=True,
                  max_length=4096).to(model.device)
        gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tok.pad_token_id)
        for k in range(len(batch)):
            comp = gen[k][enc["input_ids"].shape[1]:]
            outs.append(tok.decode(comp, skip_special_tokens=True))
        print(f"  generated {min(i+batch_size,len(sentences))}/{len(sentences)}", flush=True)
    return outs


# ---------------- metrics ----------------
def prf(items):
    """items: list of (gold, pred). Returns per-label P/R/F1, accuracy, confusion."""
    labels = CANON
    tp = {l: 0 for l in labels}; fp = {l: 0 for l in labels}; fn = {l: 0 for l in labels}
    conf = {g: {p: 0 for p in labels} for g in labels}
    correct = 0
    for g, p in items:
        if p is None:
            p = "Correct"  # parse-fail treated as no-issue (conservative; logged separately)
        conf[g][p] += 1
        if g == p:
            correct += 1; tp[g] += 1
        else:
            fp[p] += 1; fn[g] += 1
    per = {}
    f1s = []
    for l in labels:
        pr = tp[l] / (tp[l] + fp[l]) if (tp[l] + fp[l]) else 0.0
        rc = tp[l] / (tp[l] + fn[l]) if (tp[l] + fn[l]) else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) else 0.0
        per[l] = {"precision": round(pr, 3), "recall": round(rc, 3), "f1": round(f1, 3),
                  "support": tp[l] + fn[l]}
        if (tp[l] + fn[l]) > 0:
            f1s.append(f1)
    return {
        "n": len(items),
        "accuracy": round(correct / len(items), 3) if items else 0.0,
        "macro_f1": round(sum(f1s) / len(f1s), 3) if f1s else 0.0,
        "per_label": per,
        "confusion": conf,
    }


def use_mention_fp(items):
    """Of gold-Correct sentences, fraction the model flags as a violation."""
    corr = [(g, p) for g, p in items if g == "Correct"]
    if not corr:
        return None
    flagged = sum(1 for g, p in corr if p in VIOLATIONS)
    return {"n_correct": len(corr), "flagged_as_violation": flagged,
            "fp_rate": round(flagged / len(corr), 3)}


def evaluate(model, tok, data):
    sentences = [d["sentence"] for d in data]
    raw = generate(model, tok, sentences)
    parse_fail = 0
    for d, txt in zip(data, raw):
        pred, status = model_verdict(txt)
        d["pred"] = pred if pred is not None else "Correct"
        d["raw_pred"] = pred
        if status == "PARSE_FAIL":
            parse_fail += 1
    # strict set excludes context_dependent
    strict = [d for d in data if not d["context_dependent"]]
    def split(rows, lang=None):
        return [(d["gold"], d["pred"]) for d in rows if (lang is None or d["lang"] == lang)]
    report = {
        "parse_fail": parse_fail,
        "overall": prf(split(strict)),
        "en": prf(split(strict, "en")),
        "he": prf(split(strict, "he")),
        "use_mention_fp_overall": use_mention_fp(split(strict)),
        "use_mention_fp_en": use_mention_fp(split(strict, "en")),
        "use_mention_fp_he": use_mention_fp(split(strict, "he")),
        "n_context_dependent_excluded": sum(1 for d in data if d["context_dependent"]),
    }
    return report, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="adapter dir, or 'none' for bare base")
    ap.add_argument("--base-model", default=DEFAULT_BASE)
    ap.add_argument("--eval", choices=["expert", "gold", "both"], default="both")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default=None, help="name for this run in the report")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.base_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(args.base_model, dtype=torch.bfloat16,
                                                 device_map={"": 0})
    if args.adapter and args.adapter != "none":
        from peft import PeftModel
        adapter_path = os.path.abspath(args.adapter)  # PEFT treats relative as HF repo id
        model = PeftModel.from_pretrained(model, adapter_path)
        model = model.merge_and_unload()
    model.eval()

    result = {"adapter": args.adapter, "label": args.label or args.adapter,
              "base_model": args.base_model}
    for name, loader in (("expert", load_expert), ("gold", load_gold)):
        if args.eval in (name, "both"):
            print(f"== evaluating on {name} ==", flush=True)
            data = loader()
            rep, rows = evaluate(model, tok, data)
            result[name] = rep
            # dump raw rows alongside for human spot-check
            with open(args.out.replace(".json", f".{name}.rows.jsonl"), "w", encoding="utf-8") as f:
                for d in rows:
                    f.write(json.dumps({k: d[k] for k in
                            ("set", "lang", "gold", "pred", "context_dependent", "sentence")},
                            ensure_ascii=False) + "\n")
            um = rep["use_mention_fp_overall"]
            print(f"  {name}: overall_acc={rep['overall']['accuracy']} "
                  f"macroF1={rep['overall']['macro_f1']} "
                  f"EN_F1={rep['en']['macro_f1']} HE_F1={rep['he']['macro_f1']} "
                  f"use-mention_FP={um['fp_rate'] if um else 'NA'} parse_fail={rep['parse_fail']}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

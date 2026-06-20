#!/usr/bin/env python3
"""Phase 2.2 GATE — calibrate the Gemma use-mention judge against the expert set.

Runs the judge's keep/flip decision on the 80 originally-violation expert rows and
compares to the human-adjudicated truth:
    tag 'flip'           -> truth = flip_to_correct
    tag 'agree'/'relabel'-> truth = keep
    tag 'context'        -> excluded from strict agreement (reported separately)

GO/NO-GO: proceed to full relabel only if agreement >= 85% AND use-mention recall
(catching the flips) is clearly non-trivial. The judge prompt uses generic in-context
examples (not expert sentences), so measuring on all clear rows introduces no leakage.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor

from gemma_judge import judge

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERT = os.path.join(HERE, "..", "eval_sets", "expert_eval.jsonl")
CONCURRENCY = 16


def main():
    rows = [json.loads(l) for l in open(EXPERT, encoding="utf-8")]
    viol = [r for r in rows if r["original_label"] != "Correct"]
    print(f"violation rows: {len(viol)}")

    def run(r):
        res = judge(r["sentence"], r["original_label"], r["lang"], use_cache=False)
        return r, res

    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        for r, res in ex.map(run, viol):
            results.append((r, res))

    errors = [(r, res) for r, res in results if "_error" in res]
    print(f"judge errors: {len(errors)}")
    for r, res in errors[:5]:
        print("  ERR", res["_error"], "::", r["sentence"][:50])

    # strict agreement on clear rows (exclude context_dependent)
    clear = [(r, res) for r, res in results if "_error" not in res and r["adjudication_tag"] != "context"]
    truth = lambda r: "flip_to_correct" if r["adjudication_tag"] == "flip" else "keep"
    agree = sum(1 for r, res in clear if res["verdict"] == truth(r))
    # confusion on the flip axis
    tp = sum(1 for r, res in clear if truth(r) == "flip_to_correct" and res["verdict"] == "flip_to_correct")
    fn = sum(1 for r, res in clear if truth(r) == "flip_to_correct" and res["verdict"] == "keep")
    fp = sum(1 for r, res in clear if truth(r) == "keep" and res["verdict"] == "flip_to_correct")
    tn = sum(1 for r, res in clear if truth(r) == "keep" and res["verdict"] == "keep")
    n_flip = tp + fn
    recall = tp / n_flip if n_flip else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    acc = agree / len(clear) if clear else 0.0

    # context-dependent behavior (informational)
    ctx = [(r, res) for r, res in results if "_error" not in res and r["adjudication_tag"] == "context"]
    ctx_flip = sum(1 for r, res in ctx if res["verdict"] == "flip_to_correct")

    print("\n=== CALIBRATION (strict, context excluded) ===")
    print(f"clear rows: {len(clear)}  agreement: {agree}/{len(clear)} = {acc:.3f}")
    print(f"flip(use-mention) recall: {recall:.3f} ({tp}/{n_flip})   precision: {prec:.3f}")
    print(f"confusion  flip: TP={tp} FN={fn} | keep: TN={tn} FP={fp}")
    print(f"context-dependent rows: {len(ctx)}  judge flipped {ctx_flip} of them")
    gate = acc >= 0.85 and recall >= 0.5
    print(f"\nGATE (>=0.85 agreement AND >=0.5 flip-recall): {'PASS' if gate else 'FAIL'}")

    # dump disagreements for inspection
    out = os.path.join(HERE, "calibration_disagreements.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r, res in clear:
            if res["verdict"] != truth(r):
                f.write(json.dumps({
                    "lang": r["lang"], "original_label": r["original_label"],
                    "truth": truth(r), "judge": res["verdict"],
                    "sentence": r["sentence"], "note": r["note"],
                    "judge_reason": res.get("_reason", "")}, ensure_ascii=False) + "\n")
    print(f"disagreements -> {out}")

    summary = {"clear": len(clear), "agreement": round(acc, 3), "flip_recall": round(recall, 3),
               "flip_precision": round(prec, 3), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
               "errors": len(errors), "context_rows": len(ctx), "context_flipped": ctx_flip,
               "gate_pass": bool(gate)}
    json.dump(summary, open(os.path.join(HERE, "calibration_summary.json"), "w"), indent=2)
    print("summary ->", summary)


if __name__ == "__main__":
    main()

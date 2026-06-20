#!/usr/bin/env python3
"""Gemma judge client for Phase 2.2 — use-mention relabel + category + clean explanation.

One call does triple duty on a violation-labeled row:
  - verdict: keep (real violation in author's voice) vs flip_to_correct (use-mention:
    the sentence describes/attributes/historicizes/criticizes a discredited view)
  - category: Medicalization | Generalization | Demeaning Terminology (for kept violations)
  - explanation: a clean, user-facing reason in the SENTENCE's language (replaces the
    contaminated augmentation-meta explanations in the source data)

Remote endpoint (shared, LAN): http://192.168.100.112:8222/v1, model google/gemma-4-26B-A4B-it,
reasoning enabled via chat_template_kwargs.thinking. Results cached to disk keyed by
(prompt_version, sentence, original_label) so reruns are free.
"""
import hashlib
import json
import os
import re
import threading

from openai import OpenAI

BASE_URL = "http://192.168.100.112:8222/v1"
MODEL = "google/gemma-4-26B-A4B-it"
PROMPT_VERSION = "v2"
CACHE_DIR = "/data/shahafw_home/inclusify_retrain/judge_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CATEGORIES = ["Medicalization", "Generalization", "Demeaning Terminology"]

_client = OpenAI(base_url=BASE_URL, api_key="fake", timeout=180.0)
_lock = threading.Lock()

SYSTEM = """You are an expert reviewer building TRAINING DATA for an LGBTQ+ inclusive-language \
analyzer used by academics who write *critical* scholarship about LGBTQ+ topics.

You are given one sentence that a weaker model labeled as a VIOLATION (one of: Outdated, \
Biased, Potentially Offensive, Factually Incorrect). Your job has two parts.

PART 1 — USE-MENTION CHECK (the most important rule):
A sentence that DESCRIBES, ATTRIBUTES, HISTORICIZES, REPORTS, or CRITICIZES a discredited / \
pathologizing / biased view — WITHOUT asserting that view in the author's own voice — is NOT a \
violation. It is correct academic writing. Only assert a violation when the harmful claim is \
made in the author's OWN voice (endorsed/asserted as true).
  - "Homosexuality was once classified as a mental illness, a view now rejected." -> flip_to_correct (describes + rejects)
  - "Homosexuality is a mental illness." -> keep (asserted in author's voice)
If the sentence merely points out that some people hold a view, or names an outdated term while \
critiquing it, that is flip_to_correct.

CRITICAL — HEDGED OR ATTRIBUTED PROPAGATION IS STILL A VIOLATION (do not over-flip):
Attribution or hedging by itself does NOT make a sentence use-mention. Phrasings like \
"is often viewed as...", "critics contend...", "many find...", "some argue...", "it is important \
to respect...", "מבקריו טוענים", "יש הסבורים", "נתפס לעיתים כ" can still be VIOLATIONS when the \
sentence leaves the harmful frame standing without refuting it. Flip to correct ONLY when the \
sentence clearly does ONE of: (a) marks the view as historical/discredited, (b) refutes or \
criticizes it, or (c) reports it with the author's critical stance evident. If a sentence neutrally \
relays, legitimizes, or "respects" a stigmatizing framing WITHOUT distancing from it, choose keep.
  - "The 'coming out' process is often viewed as a marker of psychological instability." -> keep (relays a harmful frame, no refutation)
  - "Some claim coming out signals instability, but research finds no such link." -> flip_to_correct (refuted)

PART 2 — for sentences you KEEP as a violation, also provide:
  - category: exactly one of 'Medicalization' (framing identities as disease/disorder/treatment), \
'Generalization' (sweeping essentialist claims about LGBTQ+ people), or 'Demeaning Terminology' \
(slurs, reductive/dehumanizing wording).
  - phrase: the exact problematic span copied from the sentence (or the whole sentence if it is \
problematic as a whole).
  - explanation: ONE or TWO sentences, in the SAME LANGUAGE as the input sentence (Hebrew sentence \
-> Hebrew explanation; use correct Hebrew terminology: מיניות not סקסואליות, א־בינארי not לא-בינארי, \
להט״ב not LGBTQ+), explaining WHY it is problematic for an academic reader. Do NOT describe any \
translation or rewriting process. Do NOT mention "the sentence preserves/maintains" anything.

Respond with ONLY a JSON object, no markdown:
{"verdict":"keep"|"flip_to_correct","category":<one of the three or null>,"phrase":<string or null>,"explanation":<string or null>}
For verdict flip_to_correct, set category/phrase/explanation to null."""

USER_TMPL = """Original model label: {label}
Sentence ({lang}): "{sentence}"

Decide verdict per the use-mention rule. If keep, fill category/phrase/explanation.
LANGUAGE REQUIREMENT: write `explanation` ENTIRELY in {lang}. {lang_directive}"""

HE_DIRECTIVE = "כתוב את ההסבר כולו בעברית תקנית, ללא מילים באנגלית וללא תווים סיניים/לטיניים."
EN_DIRECTIVE = "Write the explanation entirely in English. Do not use any Hebrew or non-Latin characters."


def _script_ok(text, lang):
    """True if explanation script matches the expected language."""
    if not text:
        return True
    has_he = bool(re.search(r"[֐-׿]", text))
    has_cjk = bool(re.search(r"[一-鿿぀-ヿ]", text))
    if has_cjk:
        return False
    if lang in ("he", "HE"):
        return has_he  # Hebrew explanation must contain Hebrew
    # English: must not be dominated by Hebrew
    latin = len(re.findall(r"[A-Za-z]", text))
    heb = len(re.findall(r"[֐-׿]", text))
    return latin >= heb


def _cache_path(sentence, label):
    key = hashlib.sha256(f"{PROMPT_VERSION}|{label}|{sentence}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, key + ".json")


def _parse_json(text):
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(json)?", "", t).strip()
        t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def judge(sentence, label, lang, use_cache=True, max_tokens=2048):
    """Return dict {verdict, category, phrase, explanation, _reason, _raw} or {_error}."""
    cp = _cache_path(sentence, label)
    if use_cache and os.path.exists(cp):
        try:
            return json.load(open(cp, encoding="utf-8"))
        except Exception:
            pass
    langname = "Hebrew" if lang in ("he", "HE") else "English"
    directive = HE_DIRECTIVE if lang in ("he", "HE") else EN_DIRECTIVE

    def _call():
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": USER_TMPL.format(
                          label=label, lang=langname, sentence=sentence,
                          lang_directive=directive)}],
            temperature=0.0,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"thinking": True}},
        )
        msg = resp.choices[0].message
        obj = _parse_json(msg.content)
        return obj, msg

    try:
        obj, msg = _call()
        # one retry if a kept-violation explanation is in the wrong script/language
        if (obj and obj.get("verdict") == "keep"
                and not _script_ok(obj.get("explanation"), lang)):
            obj2, msg2 = _call()
            if obj2 and _script_ok(obj2.get("explanation"), lang):
                obj, msg = obj2, msg2
            else:
                (obj or {}).setdefault("_lang_warn", True)
        if obj is None:
            return {"_error": "parse_fail", "_raw": (msg.content or "")[:300]}
        v = obj.get("verdict")
        if v not in ("keep", "flip_to_correct"):
            return {"_error": f"bad_verdict:{v}", "_raw": (msg.content or "")[:300]}
        if v == "keep" and obj.get("category") not in CATEGORIES:
            obj["category"] = "Generalization"  # safe default; logged
        obj["_reason"] = (getattr(msg, "reasoning_content", None) or "")[:200]
        with _lock:
            json.dump(obj, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        return obj
    except Exception as e:
        return {"_error": f"api:{type(e).__name__}:{e}"[:300]}


if __name__ == "__main__":
    # smoke test: one clear use-mention (should flip) + one clear violation (should keep)
    tests = [
        ("Homosexuality was once classified as a mental disorder, a view the WHO has since rejected.",
         "Outdated", "en"),
        ("Homosexuality is a psychiatric disorder that requires treatment.", "Factually Incorrect", "en"),
        ("ההומוסקסואליות סווגה בעבר כהפרעה נפשית, תפיסה שנדחתה זה מכבר.", "Outdated", "he"),
    ]
    for s, lab, lg in tests:
        r = judge(s, lab, lg, use_cache=False)
        print(f"\n[{lg}|{lab}] {s[:60]}")
        print("  ->", {k: v for k, v in r.items() if k != "_reason"})

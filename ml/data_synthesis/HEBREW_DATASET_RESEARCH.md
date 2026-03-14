# Hebrew LGBTQ+ Dataset Generation: Research & Recommendations

**Date:** March 14, 2026
**Purpose:** Produce 10K Hebrew samples equivalent to English dataset
**Context:** Academic research for Achva LGBT organization

---

## Executive Summary

After comprehensive research into state-of-the-art Hebrew NLP methods (2026), we recommend a **hybrid approach combining translation with native Hebrew generation** using Qwen 2.5-3B (current infrastructure) and optionally Dicta-LM 3.0 (Israeli sovereign model).

**Recommended Approach:** Hybrid Translation + Native Generation
**Expected Cost:** $50-100 (if using Claude for refinement) OR $0 (all open-source)
**Expected Timeline:** 2.5 weeks
**Expected Quality:** 85-90%

---

## 1. Hebrew NLP Landscape (2026)

### Available Hebrew LLMs

| Model | Size | Context | Strengths | Availability |
|-------|------|---------|-----------|--------------|
| **Dicta-LM 3.0** | 24B/12B/1.7B | 65K | SOTA Hebrew, instruction-following | Open-weight |
| **Qwen 2.5/3.0** | 3B-72B | 128K | Multilingual (119 langs), proven | Open-weight ✅ |
| **Claude Opus 4.5** | N/A | 200K | Strong creative Hebrew | Commercial API |
| **GPT-4** | N/A | 128K | Good Hebrew support | Commercial API |
| **AlephBERT** | 110M-768M | 512 | Hebrew BERT variant | Open-weight |

**Currently Deployed:** Qwen 2.5-3B on vLLM (T4 GPU) ✅

### Hebrew Language Characteristics

**Challenges for NLP:**
1. **Morphologically Rich** - Space-delimited words contain multiple morphological tokens (prefixes, suffixes)
2. **Root-and-Template Structure** - Non-concatenative morphology (consonants = roots, vowels = patterns)
3. **RTL Text** - Right-to-left reading direction
4. **Tokenization Cost** - ~4x higher than English (letters vs words)
5. **Ambiguity** - Word boundaries can be morphemes OR separate tokens

**Implications for Dataset Generation:**
- Simple translation may produce "translationese" (unnatural Hebrew)
- Need to validate morphological correctness
- Cultural context differs from English sources
- LGBTQ+ terminology heavily borrowed from English

### Hebrew LGBTQ+ Terminology

**Standard Israeli Terms:**
- LGBTQ+ → **להט"ב** (LaHaT"aV) - official acronym
- Gay → **גיי** (borrowed) OR **עליז** (aliz, old-fashioned)
- Lesbian → **לסבית** (lesbit, borrowed)
- Transgender → **טרנסג'נדר** (borrowed)
- Non-binary → **א-בינארי/ת** (a-binari/t, Hebrew prefix)
- Gender identity → **זהות מגדרית** (zehut migdarit, native)
- Sexual orientation → **נטייה מינית** (netiya minit, native)

**Sources:** Israeli Institute for Gender and LGBTQ Studies, Israeli community usage

---

## 2. Approach Comparison

### Option A: Direct Translation (English → Hebrew)

**Method:** Use MT to translate all 10K English samples to Hebrew

**Pros:**
- ✅ Fast (1-2 days)
- ✅ Preserves English dataset structure
- ✅ Low cost ($0 with Qwen)
- ✅ Simple pipeline

**Cons:**
- ❌ Translationese artifacts (unnatural Hebrew)
- ❌ Cultural mismatch (US/UK context → Israeli context)
- ❌ Requires extensive post-editing
- ❌ May lose academic register

**Expected Quality:** 70-80%
**Cost:** $0-50
**Timeline:** 1-2 days

---

### Option B: Native Hebrew Generation

**Method:** Use Hebrew LLM to generate samples from Hebrew seeds

**Pros:**
- ✅ Culturally authentic
- ✅ Natural Hebrew phrasing
- ✅ No translation artifacts
- ✅ Can control Israeli context

**Cons:**
- ❌ Harder to control diversity
- ❌ May drift from severity categories
- ❌ Requires strong Hebrew LLM
- ❌ Need Hebrew prompt engineering

**Expected Quality:** 80-90%
**Cost:** $0-200
**Timeline:** 3-5 days

---

### Option C: Hybrid Translation + Generation (RECOMMENDED)

**Method:**
1. Translate English → Hebrew (seeds)
2. Generate Hebrew variations using Hebrew LLM
3. Quality filter and refinement

**Pros:**
- ✅ Best quality/cost ratio
- ✅ Combines structure preservation + cultural authenticity
- ✅ Leverages existing English dataset
- ✅ Controlled diversity through generation
- ✅ Can validate against English reference

**Cons:**
- ⚠️ More complex pipeline
- ⚠️ Requires both translation and generation
- ⚠️ Longer timeline

**Expected Quality:** 85-90%
**Cost:** $50-100
**Timeline:** 2.5 weeks

---

### Option D: Cross-lingual Transfer (Multilingual Model)

**Method:** Use multilingual model (Qwen) with code-switching prompts

**Pros:**
- ✅ Single system
- ✅ Leverages existing infrastructure
- ✅ Fast

**Cons:**
- ❌ Mixed language artifacts
- ❌ Less control over Hebrew quality
- ❌ May produce Hebrish (Hebrew-English mix)

**Expected Quality:** 75-85%
**Cost:** $0
**Timeline:** 2-3 days

---

## 3. Recommended Implementation Plan

### **Hybrid Approach (Option C)**

#### Phase 1: Seed Translation (Days 1-3)

**Goal:** Translate 10K English samples to Hebrew as seeds

**Method:**
```python
# Use Qwen 2.5-3B multilingual via vLLM
# Prompt template:
"""
Translate this English academic text to formal Israeli Hebrew.
Preserve LGBTQ+ terminology accuracy and academic tone.

English: {sentence}
Severity: {label}
Explanation: {explanation}

Output format:
{
  "sentence": "Hebrew translation here",
  "severity_label": "{label}",
  "explanation": "Hebrew explanation"
}
"""
```

**Validation:**
- COMET quality score > 0.7
- Manual spot-check (100 samples)
- Terminology consistency check

**Output:** 10K Hebrew seed samples

---

#### Phase 2: Hebrew Native Generation (Days 4-7)

**Goal:** Generate additional Hebrew samples for diversity

**Method:**
```python
# Use Dicta-LM 3.0-1.7B OR Qwen 2.5-3B
# Prompt template (in Hebrew):
"""
צור דוגמאות טקסט אקדמי בעברית על נושא להט"ב.

רמת חומרה: {severity_label_hebrew}
תחום: {domain} (פסיכולוגיה, סוציולוגיה, רפואה, חינוך, משפט)

דוגמאות קיימות:
1. {example_1_hebrew}
2. {example_2_hebrew}
3. {example_3_hebrew}

צור משפט חדש ושונה במבנה, מינוח, ופרספקטיבה.
שמור על טון אקדמי ורמת החומרה.

פורמט JSON:
{
  "sentence": "...",
  "severity_label": "...",
  "explanation": "..."
}
"""
```

**Parameters:**
- Generate 5K new samples
- Stratified by severity label (20% each)
- Diverse domains (rotate through 5 domains)
- Temperature: 0.9 (high diversity)

**Output:** 5K native Hebrew samples

---

#### Phase 3: Quality Filtering (Days 8-10)

**Goal:** Filter and refine low-quality samples

**Method:**
1. **COMET Quality Estimation:**
   - Score all 15K samples (10K translated + 5K native)
   - Filter: Keep samples with COMET > 0.7
   - Expected: ~12-13K samples pass

2. **Semantic Deduplication:**
   - Compute embeddings (multilingual BERT)
   - Remove duplicates (cosine similarity > 0.85)
   - Expected: ~11K unique samples

3. **Claude Refinement (Optional, if budget allows):**
   - Take bottom 20% by COMET score (~2K samples)
   - Use Claude Opus 4.5 to rewrite
   - Prompt: "Improve this Hebrew text for academic quality and naturalness"
   - Cost: ~$50-100

**Output:** 10K high-quality Hebrew samples

---

#### Phase 4: Validation (Days 11-12)

**Goal:** Ensure dataset meets quality standards

**Automated Validation:**
- ✅ COMET score distribution (median > 0.75)
- ✅ TLNLS fluency (> 0.80 for all samples)
- ✅ BERTScore semantic similarity to English (> 0.85)
- ✅ Schema compliance (100%)
- ✅ Diversity metrics (avg pairwise similarity < 0.7)

**Manual Validation (200 samples):**
- ✅ Hebrew grammatical correctness
- ✅ LGBTQ+ terminology accuracy (Israeli usage)
- ✅ Academic register appropriateness
- ✅ Cultural relevance to Israeli context
- ✅ Severity label accuracy
- ✅ Explanation coherence

**Pass Threshold:** 85% of manual samples pass all checks

---

## 4. Model Selection Recommendation

### Primary Model: **Qwen 2.5-3B Multilingual**

**Why:**
- ✅ Already deployed on vLLM (T4 GPU)
- ✅ Proven performance on English generation
- ✅ 119 languages including Hebrew
- ✅ Zero cost
- ✅ Team familiarity

**Concerns:**
- ⚠️ Not Hebrew-specialized
- ⚠️ May produce mixed-language artifacts

**Mitigation:**
- Use explicit Hebrew-only prompts
- Validate with COMET
- Filter/regenerate low-quality outputs

---

### Secondary Model (Optional): **Dicta-LM 3.0-1.7B**

**Why:**
- ✅ Israeli sovereign model (SOTA Hebrew)
- ✅ 65K context window
- ✅ 1.7B fits on T4 GPU
- ✅ Open-weight (free)

**When to use:**
- Phase 2 native generation (if Qwen quality insufficient)
- Quality refinement pass
- Israeli cultural context validation

**Setup Required:**
```bash
# Test on VM
vllm serve dicta-il/DictaLM-3.0-1.7B-Instruct \
  --port 8001 \
  --gpu-memory-utilization 0.5 \
  --max-model-len 4096
```

---

### Refinement Model (Budget-Dependent): **Claude Opus 4.5**

**Why:**
- ✅ Strong creative Hebrew generation
- ✅ 200K context window (can include many examples)
- ✅ Proven quality for Hebrew

**When to use:**
- Phase 3 quality refinement (worst 20%)
- Final polish for publication-ready dataset

**Cost Estimate:**
- Input: 2K samples × 300 tokens avg = 600K tokens × $0.015/1K = $9
- Output: 2K samples × 200 tokens avg = 400K tokens × $0.075/1K = $30
- **Total: ~$40-50**

---

## 5. Quality Metrics & Targets

### Automated Metrics

| Metric | Tool | Target | Purpose |
|--------|------|--------|---------|
| **COMET** | unbabel-comet | > 0.75 median | Translation quality |
| **TLNLS** | Custom | > 0.80 | Hebrew fluency |
| **BERTScore** | bert-score | > 0.85 | Semantic preservation |
| **Perplexity** | AlephBERT | < 30 | Language naturalness |
| **Diversity** | Cosine distance | Avg < 0.7 | Sample uniqueness |

### Manual Validation (200 samples)

**Stratified sample:** 40 per severity label

**Checklist:**
1. ✅ Hebrew grammatical correctness (morphology, syntax)
2. ✅ LGBTQ+ terminology accuracy (Israeli community standard)
3. ✅ Academic register (formal, scholarly tone)
4. ✅ Cultural relevance (Israeli vs US/UK context)
5. ✅ Severity label accuracy
6. ✅ Explanation coherence and informativeness

**Pass threshold:** 85% of samples pass all 6 checks

---

## 6. Cultural Adaptation Guidelines

### Israeli vs International Context

**Adapt:**
- Replace US/UK legal references → Israeli law (Knesset, Israeli courts)
- Replace Western academic sources → Israeli research (Hebrew University, Tel Aviv University)
- Use Israeli LGBTQ+ organizations (Hoshen, Aguda, Ma'avarim)
- Reference Israeli media and public discourse

**Preserve:**
- Universal LGBTQ+ concepts (gender identity, sexual orientation)
- Scientific terminology (psychology, biology, sociology)
- International research findings (where relevant)

### Terminology Consistency

**Build a glossary:**
```yaml
# Hebrew LGBTQ+ Terminology Glossary
LGBTQ+: "להט\"ב"
gay: "גיי"
lesbian: "לסבית"
bisexual: "ביסקסואל/ת"
transgender: "טרנסג'נדר"
non-binary: "א-בינארי/ת"
queer: "קוויר"
cisgender: "ציסג'נדר"
gender identity: "זהות מגדרית"
sexual orientation: "נטייה מינית"
coming out: "יציאה מהארון"
conversion therapy: "טיפולי המרה"
```

**Enforce in prompts:**
```python
TERMINOLOGY_PROMPT = """
Use these standard Hebrew LGBTQ+ terms:
- LGBTQ+ = להט"ב
- Transgender = טרנסג'נדר
- Gender identity = זהות מגדרית
- Sexual orientation = נטייה מינית
"""
```

---

## 7. Risk Analysis & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Dicta-LM doesn't fit on T4** | High | Medium | Use Qwen only, or quantize Dicta-LM to 4-bit |
| **Translation quality < 75%** | High | Medium | Increase Claude refinement budget to $100-150 |
| **Cultural context mismatch** | High | Medium | Manual validation by Israeli team member |
| **Terminology inconsistency** | Medium | High | Build glossary, enforce in prompts, post-process filter |
| **Dataset drift from English** | Low | Medium | Maintain parallel EN-HE validation set (100 samples) |
| **Hebrew morphology errors** | Medium | Medium | Use AlephBERT for fluency scoring, manual validation |
| **Low diversity** | Medium | Low | Increase temperature to 1.0, use domain rotation |
| **Budget overrun** | Low | Low | Stick to Qwen-only pipeline ($0 cost) |

---

## 8. Budget Options

### Option 1: All Open-Source (RECOMMENDED)

**Models:**
- Qwen 2.5-3B (translation + generation)
- Optional: Dicta-LM 3.0-1.7B (native generation)

**Cost:** $0
**Quality:** 80-85%
**Timeline:** 2 weeks
**Infrastructure:** Existing vLLM on T4

---

### Option 2: Hybrid (Open-Source + Claude Polish)

**Models:**
- Qwen 2.5-3B (bulk generation)
- Claude Opus 4.5 (20% refinement)

**Cost:** $40-100
**Quality:** 85-90%
**Timeline:** 2.5 weeks
**Infrastructure:** Existing vLLM + Anthropic API

---

### Option 3: All Claude (Maximum Quality)

**Models:**
- Claude Opus 4.5 (all generation)

**Cost:** $150-300
**Quality:** 90-95%
**Timeline:** 1 week
**Infrastructure:** Anthropic API only

---

## 9. Implementation Checklist

### Prerequisites
- [ ] vLLM on Azure VM with T4 GPU (✅ Already set up)
- [ ] Qwen 2.5-3B deployed (✅ Already working)
- [ ] Install COMET for Hebrew QE: `pip install unbabel-comet`
- [ ] Install BERTScore: `pip install bert-score`
- [ ] Test Dicta-LM 3.0-1.7B (optional): Deploy on port 8001
- [ ] Build Hebrew terminology glossary
- [ ] Prepare Hebrew few-shot examples (5 per severity label)

### Week 1: Translation Pipeline
- [ ] Day 1: Create `translate_to_hebrew.py` (adapt from `synthesize_english.py`)
- [ ] Day 1: Create Hebrew translation prompt template
- [ ] Day 2: Run pilot translation (100 samples)
- [ ] Day 2: Validate COMET scores, manual spot-check
- [ ] Day 3: Run full translation (10K samples)
- [ ] Day 3: Save to `data/hebrew_translated_seeds.jsonl`

### Week 2: Native Generation
- [ ] Day 4: Create `generate_hebrew_native.py`
- [ ] Day 4: Create Hebrew generation prompt (with examples)
- [ ] Day 5: Run pilot generation (100 samples per severity)
- [ ] Day 5: Validate diversity, quality, cultural appropriateness
- [ ] Day 6: Run full generation (5K samples)
- [ ] Day 7: Save to `data/hebrew_native_generated.jsonl`

### Week 3: Quality Assurance
- [ ] Day 8: Run COMET QE on all 15K samples
- [ ] Day 8: Filter samples (COMET > 0.7) → ~12K
- [ ] Day 9: Semantic deduplication → ~11K
- [ ] Day 10: (Optional) Claude refinement for worst 20%
- [ ] Day 11: Final filtering → 10K samples
- [ ] Day 12: Save to `data/hebrew_10k.csv`

### Week 4: Validation & Documentation
- [ ] Day 13: Run automated metrics (TLNLS, BERTScore, perplexity)
- [ ] Day 13: Generate validation report
- [ ] Day 14: Manual validation (200 samples, stratified)
- [ ] Day 14: Final quality report
- [ ] Day 15: Document methodology for thesis
- [ ] Day 15: Commit to repository

---

## 10. Success Criteria

### Quantitative Metrics
- ✅ Total samples: 10,000 ± 100
- ✅ Class distribution: 20% ± 2% per severity label
- ✅ COMET median: > 0.75
- ✅ TLNLS fluency: > 0.80 for all samples
- ✅ BERTScore: > 0.85 (semantic preservation from English)
- ✅ Diversity: Avg pairwise cosine similarity < 0.7
- ✅ Schema compliance: 100%

### Qualitative Metrics (Manual Validation)
- ✅ 85%+ samples pass all 6 validation checks
- ✅ Terminology consistency: 95%+ use standard Israeli terms
- ✅ Cultural appropriateness: 90%+ relevant to Israeli context
- ✅ Academic register: 90%+ maintain formal tone

---

## 11. Next Steps

### This Week (Days 1-3)
1. **Review this research** with team
2. **Decide on approach** (Option 1 vs 2 vs 3 based on budget)
3. **Test Dicta-LM 3.0-1.7B** on T4 GPU (optional)
4. **Install dependencies** (COMET, BERTScore)
5. **Build Hebrew terminology glossary**

### Discussion Questions
1. Do we have $40-100 budget for Claude refinement? (Recommended but optional)
2. Should we involve an Israeli team member for validation?
3. Do we want to publish methodology in academic paper?
4. Timeline constraints? (Can we take 2.5 weeks or need faster?)

### Immediate Actions
1. Create `ml/data_synthesis/translate_to_hebrew.py`
2. Create `ml/data_synthesis/prompts/hebrew_translation.txt`
3. Create `ml/data_synthesis/prompts/hebrew_generation_he.txt`
4. Set up COMET validation pipeline

---

## 12. References

### Hebrew NLP & Models
- [Dicta-LM 3.0 Technical Report (Feb 2026)](https://arxiv.org/abs/2602.02104)
- [AlephBERT: Hebrew Pre-trained Language Model](https://arxiv.org/abs/2104.04052)
- [Hebrew Open Leaderboard](https://huggingface.co/blog/leaderboard-hebrew)
- [NNLP-IL Hebrew Resources](https://github.com/NNLP-IL/Hebrew-Resources)

### Machine Translation & Quality
- [MTQE.en-he: English-Hebrew MT Quality Estimation](https://arxiv.org/abs/2602.06546)
- [Machine Translation Post-Editing Guide (2026)](https://www.eliteasia.co/machine-translation-post-editing-guide/)
- [COMET: Neural Quality Estimation](https://unbabel.github.io/COMET/)

### Hebrew Language Characteristics
- [MRL Parsing Without Tears: Hebrew](https://arxiv.org/html/2403.06970)
- [HeQ: Hebrew Reading Comprehension](https://arxiv.org/html/2508.01812)

### LGBTQ+ Terminology & Culture
- [Top LGBTQ Hebrew Words](https://www.citizencafetlv.com/blog/top-10-lgbtq-hebrew-words-need-know/)
- [Israeli Institute for Gender Studies](https://www.lgbtq-research.org.il/en)
- [LGBTQ+ Teachers in Israeli Schools (2025)](https://www.tandfonline.com/doi/full/10.1080/00918369.2025.2537845)

### Synthetic Dataset Generation
- [Synthetic Data Generation Using LLMs (2025)](https://arxiv.org/html/2503.14023v1)
- [Scaling Low-Resource MT via Synthetic Data](https://aclanthology.org/2025.emnlp-main.1408.pdf)

---

## Appendix A: Terminology Glossary

See separate file: `ml/data_synthesis/prompts/hebrew_terminology_glossary.yaml`

## Appendix B: Prompt Templates

See separate files:
- `ml/data_synthesis/prompts/hebrew_translation.txt`
- `ml/data_synthesis/prompts/hebrew_generation_he.txt`

## Appendix C: Validation Scripts

See separate files:
- `ml/data_synthesis/validate_hebrew.py`
- `ml/data_synthesis/utils/hebrew_quality_metrics.py`

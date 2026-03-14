#!/usr/bin/env python3
"""
Phased Hebrew translation pipeline test.

Runs in 3 phases to handle model swapping on single GPU:
Phase 1: EN→HE translation (Qwen on port 8000)
Phase 2: Hebrew validation (DictaLM on port 8001)
Phase 3: HE→EN back-translation (Qwen on port 8000)

Usage:
    # Phase 1
    python ml/data_synthesis/test_hebrew_pipeline_phased.py --phase 1

    # Then manually: Stop Qwen, start DictaLM on port 8001

    # Phase 2
    python ml/data_synthesis/test_hebrew_pipeline_phased.py --phase 2

    # Then manually: Stop DictaLM, start Qwen on port 8000

    # Phase 3
    python ml/data_synthesis/test_hebrew_pipeline_phased.py --phase 3

    # Analysis
    python ml/data_synthesis/test_hebrew_pipeline_phased.py --analyze
"""

import sys
import os
import time
import json
import asyncio
import argparse
from pathlib import Path

import pandas as pd
from openai import AsyncOpenAI

# Paths
INPUT_CSV = Path("data/english_10k.csv")
PHASE1_OUTPUT = Path("data/test_phase1_translations.json")
PHASE2_OUTPUT = Path("data/test_phase2_validations.json")
PHASE3_OUTPUT = Path("data/test_phase3_backtrans.json")
FINAL_REPORT = Path("data/test_hebrew_pipeline_report.json")


async def phase1_translate(n_per_category=2):
    """Phase 1: Translate English to Hebrew using Qwen."""
    print("="*70)
    print("PHASE 1: EN→HE Translation (Qwen 2.5-3B on port 8000)")
    print("="*70)

    # Load and sample data
    print(f"\nLoading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV)

    print(f"Sampling {n_per_category} from each severity category...")
    sampled = []
    for label in df['severity_label'].unique():
        category_df = df[df['severity_label'] == label]
        sample = category_df.sample(n=min(n_per_category, len(category_df)), random_state=42)
        sampled.append(sample)

    samples_df = pd.concat(sampled).reset_index(drop=True)
    print(f"✓ Sampled {len(samples_df)} rows")
    print(samples_df['severity_label'].value_counts())

    # Initialize Qwen client
    client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

    # Translate
    print(f"\nTranslating {len(samples_df)} samples...")
    start_time = time.time()

    translations = []
    for idx, row in samples_df.iterrows():
        prompt = f"""Translate this English academic text about LGBTQ+ topics to formal Israeli Hebrew.
Preserve academic tone and LGBTQ+ terminology accuracy.

English: {row['sentence']}

Output ONLY valid JSON:
{{
  "hebrew_sentence": "translation here"
}}"""

        try:
            response = await client.chat.completions.create(
                model="Qwen/Qwen2.5-3B-Instruct",
                messages=[
                    {"role": "system", "content": "You are an expert English-Hebrew translator for academic LGBTQ+ texts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            content = response.choices[0].message.content
            # Try to parse JSON
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                data = json.loads(content)
                hebrew_sent = data.get('hebrew_sentence', content)
            except:
                # Fallback: use raw content
                hebrew_sent = content

            translations.append({
                'id': idx,
                'original_english': row['sentence'],
                'severity_label': row['severity_label'],
                'explanation': row['explanation'],
                'hebrew_translation': hebrew_sent
            })

            print(f"  [{idx+1}/{len(samples_df)}] ✓")

        except Exception as e:
            print(f"  [{idx+1}/{len(samples_df)}] ✗ Error: {e}")
            translations.append({
                'id': idx,
                'original_english': row['sentence'],
                'severity_label': row['severity_label'],
                'explanation': row['explanation'],
                'hebrew_translation': f'[ERROR: {e}]'
            })

    elapsed = time.time() - start_time

    print(f"\n✓ Phase 1 completed in {elapsed:.2f}s ({elapsed/len(translations):.2f}s/sample)")

    # Save results
    results = {
        'phase': 1,
        'elapsed_seconds': elapsed,
        'samples_count': len(translations),
        'seconds_per_sample': elapsed / len(translations),
        'translations': translations
    }

    with open(PHASE1_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved to {PHASE1_OUTPUT}")
    print(f"\nNext: Stop Qwen, start DictaLM on port 8001, then run --phase 2")


async def phase2_validate():
    """Phase 2: Validate with DictaLM-Thinking."""
    print("="*70)
    print("PHASE 2: Validation (DictaLM-3.0-1.7B-Thinking on port 8001)")
    print("="*70)

    # Load phase 1 results
    print(f"\nLoading Phase 1 results from {PHASE1_OUTPUT}...")
    with open(PHASE1_OUTPUT, 'r', encoding='utf-8') as f:
        phase1_data = json.load(f)

    translations = phase1_data['translations']
    print(f"✓ Loaded {len(translations)} translations")

    # Initialize DictaLM client
    client = AsyncOpenAI(base_url="http://localhost:8001/v1", api_key="EMPTY")

    # Validate
    print(f"\nValidating {len(translations)} samples with DictaLM reasoning...")
    start_time = time.time()

    validations = []
    for idx, trans in enumerate(translations):
        prompt = f"""אתה מומחה לתרגום עברי ולמינוח להט"ב. בדוק את איכות התרגום:

מקור (אנגלית): {trans['original_english']}
תרגום (עברית): {trans['hebrew_translation']}
רמת חומרה: {trans['severity_label']}

בדוק:
1. שמירה על משמעות סמנטית
2. נכונות מינוח להט"ב (תקן ישראלי)
3. טון אקדמי
4. התאמה תרבותית
5. נכונות מורפולוגית

חשוב בקול רם ותן המלצה.

פורמט JSON (ללא markdown):
{{
  "semantic_accuracy": 0.0-1.0,
  "terminology_correct": true/false,
  "issues": ["רשימה"],
  "recommended_fix": "תיקון או null",
  "confidence": 0.0-1.0,
  "status": "EXCELLENT/GOOD/NEEDS_CORRECTION/POOR"
}}"""

        try:
            response = await client.chat.completions.create(
                model="dicta-il/DictaLM-3.0-1.7B-Thinking",
                messages=[
                    {"role": "system", "content": "אתה מומחה בדיקת תרגומים עבריים עם התמחות במינוח להט\"ב."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            content = response.choices[0].message.content

            # Extract thinking block if present
            thinking_block = ""
            if '<think>' in content:
                thinking_block = content.split('<think>')[1].split('</think>')[0].strip()
                content = content.split('</think>')[1].strip() if '</think>' in content else content

            # Parse validation result
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                validation_data = json.loads(content)
            except:
                validation_data = {
                    'status': 'PARSE_ERROR',
                    'raw_response': content
                }

            validations.append({
                **trans,
                'thinking_block': thinking_block,
                'validation': validation_data,
                'dicta_status': validation_data.get('status', 'UNKNOWN')
            })

            print(f"  [{idx+1}/{len(translations)}] ✓ Status: {validation_data.get('status', 'UNKNOWN')}")

        except Exception as e:
            print(f"  [{idx+1}/{len(translations)}] ✗ Error: {e}")
            validations.append({
                **trans,
                'thinking_block': '',
                'validation': {'status': 'ERROR', 'error': str(e)},
                'dicta_status': 'ERROR'
            })

    elapsed = time.time() - start_time

    print(f"\n✓ Phase 2 completed in {elapsed:.2f}s ({elapsed/len(validations):.2f}s/sample)")

    # Status summary
    status_counts = {}
    for v in validations:
        status = v['dicta_status']
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\nDictaLM Status Distribution:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # Save results
    results = {
        'phase': 2,
        'elapsed_seconds': elapsed,
        'samples_count': len(validations),
        'seconds_per_sample': elapsed / len(validations),
        'validations': validations,
        'status_distribution': status_counts
    }

    with open(PHASE2_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved to {PHASE2_OUTPUT}")
    print(f"\nNext: Stop DictaLM, restart Qwen on port 8000, then run --phase 3")


async def phase3_backtranslate():
    """Phase 3: Back-translate Hebrew to English."""
    print("="*70)
    print("PHASE 3: HE→EN Back-translation (Qwen 2.5-3B on port 8000)")
    print("="*70)

    # Load phase 2 results
    print(f"\nLoading Phase 2 results from {PHASE2_OUTPUT}...")
    with open(PHASE2_OUTPUT, 'r', encoding='utf-8') as f:
        phase2_data = json.load(f)

    validations = phase2_data['validations']
    print(f"✓ Loaded {len(validations)} validated translations")

    # Initialize Qwen client
    client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

    # Back-translate
    print(f"\nBack-translating {len(validations)} samples...")
    start_time = time.time()

    back_translations = []
    for idx, val in enumerate(validations):
        # Use DictaLM fix if recommended, otherwise original
        hebrew_text = val.get('validation', {}).get('recommended_fix') or val['hebrew_translation']

        prompt = f"""Translate this Hebrew text to English.

Hebrew: {hebrew_text}

Output ONLY valid JSON:
{{
  "english_sentence": "translation here"
}}"""

        try:
            response = await client.chat.completions.create(
                model="Qwen/Qwen2.5-3B-Instruct",
                messages=[
                    {"role": "system", "content": "You are an expert Hebrew-English translator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            content = response.choices[0].message.content

            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                data = json.loads(content)
                back_trans = data.get('english_sentence', content)
            except:
                back_trans = content

            back_translations.append({
                **val,
                'back_translation': back_trans
            })

            print(f"  [{idx+1}/{len(validations)}] ✓")

        except Exception as e:
            print(f"  [{idx+1}/{len(validations)}] ✗ Error: {e}")
            back_translations.append({
                **val,
                'back_translation': f'[ERROR: {e}]'
            })

    elapsed = time.time() - start_time

    print(f"\n✓ Phase 3 completed in {elapsed:.2f}s ({elapsed/len(back_translations):.2f}s/sample)")

    # Save results
    results = {
        'phase': 3,
        'elapsed_seconds': elapsed,
        'samples_count': len(back_translations),
        'seconds_per_sample': elapsed / len(back_translations),
        'back_translations': back_translations
    }

    with open(PHASE3_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved to {PHASE3_OUTPUT}")
    print(f"\nNext: Run --analyze to compute semantic delta and generate report")


def analyze_results():
    """Analyze all phases and compute semantic delta."""
    print("="*70)
    print("ANALYSIS: Computing Semantic Delta & Quality Metrics")
    print("="*70)

    # Load all phase results
    print("\nLoading results from all phases...")
    with open(PHASE1_OUTPUT, 'r') as f:
        phase1 = json.load(f)
    with open(PHASE2_OUTPUT, 'r') as f:
        phase2 = json.load(f)
    with open(PHASE3_OUTPUT, 'r') as f:
        phase3 = json.load(f)

    # Install sentence-transformers if needed
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity

        print("Loading multilingual embedding model...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

        # Compute semantic similarities
        results = []
        for item in phase3['back_translations']:
            # EN-HE semantic similarity
            en_emb = model.encode([item['original_english']])
            he_emb = model.encode([item['hebrew_translation']])
            en_he_sim = float(cosine_similarity(en_emb, he_emb)[0][0])

            # Back-translation similarity
            back_emb = model.encode([item['back_translation']])
            back_sim = float(cosine_similarity(en_emb, back_emb)[0][0])

            # Overall quality
            dicta_status = item.get('dicta_status', 'UNKNOWN')

            results.append({
                'id': item['id'],
                'severity_label': item['severity_label'],
                'original_english': item['original_english'][:100] + '...',
                'hebrew_translation': item['hebrew_translation'][:100] + '...',
                'back_translation': item['back_translation'][:100] + '...',
                'en_he_similarity': round(en_he_sim, 3),
                'back_trans_similarity': round(back_sim, 3),
                'dicta_status': dicta_status,
                'dicta_issues': item.get('validation', {}).get('issues', [])
            })

        # Compute averages
        avg_en_he = sum(r['en_he_similarity'] for r in results) / len(results)
        avg_back = sum(r['back_trans_similarity'] for r in results) / len(results)

        # Print summary
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)

        print("\n📊 TIMING SUMMARY:")
        print(f"  Phase 1 (EN→HE):     {phase1['elapsed_seconds']:.2f}s ({phase1['seconds_per_sample']:.2f}s/sample)")
        print(f"  Phase 2 (DictaLM):   {phase2['elapsed_seconds']:.2f}s ({phase2['seconds_per_sample']:.2f}s/sample)")
        print(f"  Phase 3 (HE→EN):     {phase3['elapsed_seconds']:.2f}s ({phase3['seconds_per_sample']:.2f}s/sample)")
        total_time = phase1['elapsed_seconds'] + phase2['elapsed_seconds'] + phase3['elapsed_seconds']
        print(f"  TOTAL:               {total_time:.2f}s ({total_time/10:.2f}s/sample average)")

        print("\n📈 QUALITY METRICS:")
        print(f"  Avg EN-HE Semantic Similarity:   {avg_en_he:.3f}")
        print(f"  Avg Back-translation Similarity: {avg_back:.3f}")

        print("\n  DictaLM Status Distribution:")
        for status, count in phase2['status_distribution'].items():
            print(f"    {status}: {count}")

        print("\n📝 DETAILED RESULTS:")
        for r in results:
            print(f"\n--- Sample {r['id']+1} ({r['severity_label']}) ---")
            print(f"  Original EN:  {r['original_english']}")
            print(f"  Hebrew:       {r['hebrew_translation']}")
            print(f"  Back-trans:   {r['back_translation']}")
            print(f"  EN-HE Sim:    {r['en_he_similarity']:.3f}")
            print(f"  Back Sim:     {r['back_trans_similarity']:.3f}")
            print(f"  DictaLM:      {r['dicta_status']}")
            if r['dicta_issues']:
                print(f"  Issues:       {r['dicta_issues']}")

        # Projections to 10K
        print("\n" + "="*70)
        print("PROJECTIONS FOR 10,000 SAMPLES")
        print("="*70)

        print(f"\nBased on 10-sample test:")
        print(f"  Phase 1 (EN→HE):     {phase1['seconds_per_sample']:.2f}s/sample × 10,000 = {phase1['seconds_per_sample']*10000/3600:.2f} hours")
        print(f"  Phase 2 (DictaLM):   {phase2['seconds_per_sample']:.2f}s/sample × 10,000 = {phase2['seconds_per_sample']*10000/3600:.2f} hours")
        print(f"  Phase 3 (HE→EN):     {phase3['seconds_per_sample']:.2f}s/sample × 10,000 = {phase3['seconds_per_sample']*10000/3600:.2f} hours")
        print(f"  TOTAL:               {total_time/10*10000/3600:.2f} hours")

        # Save final report
        report = {
            'test_samples': len(results),
            'timings': {
                'phase1_total': phase1['elapsed_seconds'],
                'phase2_total': phase2['elapsed_seconds'],
                'phase3_total': phase3['elapsed_seconds'],
                'total': total_time,
                'phase1_per_sample': phase1['seconds_per_sample'],
                'phase2_per_sample': phase2['seconds_per_sample'],
                'phase3_per_sample': phase3['seconds_per_sample'],
                'average_per_sample': total_time / 10
            },
            'projections_10k': {
                'phase1_hours': phase1['seconds_per_sample'] * 10000 / 3600,
                'phase2_hours': phase2['seconds_per_sample'] * 10000 / 3600,
                'phase3_hours': phase3['seconds_per_sample'] * 10000 / 3600,
                'total_hours': total_time / 10 * 10000 / 3600
            },
            'quality_metrics': {
                'avg_en_he_similarity': avg_en_he,
                'avg_backtrans_similarity': avg_back,
                'dicta_status_distribution': phase2['status_distribution']
            },
            'detailed_results': results
        }

        with open(FINAL_REPORT, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Full report saved to {FINAL_REPORT}")

    except ImportError:
        print("\n✗ sentence-transformers not installed")
        print("Run: pip install sentence-transformers scikit-learn")
        print("Then re-run --analyze")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test Hebrew translation pipeline in phases')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], help='Phase to run (1=translate, 2=validate, 3=backtrans)')
    parser.add_argument('--analyze', action='store_true', help='Analyze results from all phases')

    args = parser.parse_args()

    if args.phase == 1:
        await phase1_translate()
    elif args.phase == 2:
        await phase2_validate()
    elif args.phase == 3:
        await phase3_backtranslate()
    elif args.analyze:
        analyze_results()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

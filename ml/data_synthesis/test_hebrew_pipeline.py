#!/usr/bin/env python3
"""
Test Hebrew translation pipeline with DictaLM validation.

This script tests the proposed pipeline:
1. Sample 10 rows (2 per severity category)
2. Translate EN→HE (Qwen 2.5-3B)
3. Validate ALL with DictaLM-3.0-1.7B-Thinking (measure reasoning quality)
4. Back-translate HE→EN (Qwen 2.5-3B)
5. Compare semantic delta
6. Measure times and quality

Usage:
    python ml/data_synthesis/test_hebrew_pipeline.py
"""

import sys
import os
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.data_synthesis.utils.vllm_processor import VLLMProcessor
from ml.data_synthesis.utils.translation_validator import (
    TranslationValidator,
    HEBREW_LGBTQ_GLOSSARY
)


# Configuration
QWEN_ENDPOINT = "http://localhost:8000/v1"
QWEN_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DICTA_ENDPOINT = "http://localhost:8001/v1"
DICTA_MODEL = "dicta-il/DictaLM-3.0-1.7B-Thinking"

INPUT_CSV = "data/english_10k.csv"
OUTPUT_JSON = "data/test_results_hebrew_pipeline.json"


class PipelineTester:
    """Test the Hebrew translation pipeline."""

    def __init__(self):
        """Initialize processors."""
        print("Initializing processors...")
        self.qwen = VLLMProcessor(endpoint=QWEN_ENDPOINT, model=QWEN_MODEL)
        self.dicta = VLLMProcessor(endpoint=DICTA_ENDPOINT, model=DICTA_MODEL)
        self.validator = TranslationValidator()
        self.results = []

    def sample_data(self, csv_path: str, n_per_category: int = 2) -> pd.DataFrame:
        """
        Sample n rows from each severity category.

        Args:
            csv_path: Path to English dataset CSV
            n_per_category: Number of samples per category

        Returns:
            DataFrame with sampled rows
        """
        print(f"\nLoading dataset from {csv_path}...")
        df = pd.read_csv(csv_path)

        print(f"Total samples: {len(df)}")
        print(f"Categories: {df['severity_label'].unique()}")

        # Sample n from each category
        sampled = []
        for label in df['severity_label'].unique():
            category_df = df[df['severity_label'] == label]
            sample = category_df.sample(n=min(n_per_category, len(category_df)))
            sampled.append(sample)

        result = pd.concat(sampled).reset_index(drop=True)
        print(f"\nSampled {len(result)} rows:")
        print(result['severity_label'].value_counts())

        return result

    async def translate_english_to_hebrew(self, samples: List[Dict]) -> List[Dict]:
        """
        Step 1: Translate English to Hebrew using Qwen.

        Args:
            samples: List of English samples

        Returns:
            List of Hebrew translations with timing
        """
        print("\n" + "="*60)
        print("STEP 1: Translating English → Hebrew (Qwen 2.5-3B)")
        print("="*60)

        start_time = time.time()

        # Build requests
        requests = []
        for idx, sample in enumerate(samples):
            prompt = f"""Translate this English academic text about LGBTQ+ topics to formal Israeli Hebrew.
Preserve the academic tone and LGBTQ+ terminology accuracy.

English sentence: {sample['sentence']}

Output ONLY valid JSON (no markdown):
{{
  "sentence": "Hebrew translation here"
}}"""

            requests.append({
                "custom_id": f"translate_{idx}",
                "params": {
                    "messages": [
                        {"role": "system", "content": "You are an expert English-Hebrew translator specializing in LGBTQ+ academic texts."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            })

        # Process batch
        results = await self.qwen.generate_batch(
            requests=requests,
            batch_size=10,
            max_throughput=30,
            max_tokens=500,
            temperature=0.3
        )

        elapsed = time.time() - start_time

        # Parse results
        translations = []
        for i, result in enumerate(results):
            if result['result']['type'] == 'succeeded':
                data = result['result']['data']
                translations.append({
                    'original_english': samples[i]['sentence'],
                    'hebrew_translation': data.get('sentence', ''),
                    'severity_label': samples[i]['severity_label'],
                    'explanation': samples[i]['explanation']
                })
            else:
                print(f"ERROR: Translation failed for sample {i}")
                translations.append({
                    'original_english': samples[i]['sentence'],
                    'hebrew_translation': '[TRANSLATION FAILED]',
                    'severity_label': samples[i]['severity_label'],
                    'explanation': samples[i]['explanation']
                })

        print(f"\n✓ Translated {len(translations)} samples in {elapsed:.2f}s")
        print(f"  Average: {elapsed/len(translations):.2f}s per sample")

        return translations, elapsed

    async def validate_with_dicta(self, translations: List[Dict]) -> List[Dict]:
        """
        Step 2: Validate translations with DictaLM-3.0-1.7B-Thinking.

        Args:
            translations: List of translations from Step 1

        Returns:
            List of validation results with thinking blocks
        """
        print("\n" + "="*60)
        print("STEP 2: Validating with DictaLM-3.0-1.7B-Thinking")
        print("="*60)

        start_time = time.time()

        # Build validation requests
        requests = []
        for idx, trans in enumerate(translations):
            prompt = f"""אתה מומחה לתרגום עברי ולמינוח להט"ב. בדוק את איכות התרגום הבא:

מקור (אנגלית): {trans['original_english']}
תרגום (עברית): {trans['hebrew_translation']}
רמת חומרה: {trans['severity_label']}

בדוק:
1. שמירה על משמעות סמנטית
2. נכונות מינוח להט"ב (לפי תקן ישראלי)
3. שמירה על טון אקדמי
4. התאמה תרבותית להקשר ישראלי
5. נכונות מורפולוגית

חשוב בקול רם ולאחר מכן תן המלצה.

פורמט פלט (JSON בלבד, ללא markdown):
{{
  "semantic_accuracy": 0.0-1.0,
  "terminology_correct": true/false,
  "issues": ["רשימת בעיות"],
  "recommended_fix": "תרגום מתוקן אם נדרש או null",
  "confidence": 0.0-1.0,
  "status": "EXCELLENT/GOOD/NEEDS_CORRECTION/POOR"
}}"""

            requests.append({
                "custom_id": f"validate_{idx}",
                "params": {
                    "messages": [
                        {"role": "system", "content": "אתה מומחה בדיקת איכות תרגומים לעברית עם התמחות במינוח להט\"ב."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3
                }
            })

        # Process batch
        results = await self.dicta.generate_batch(
            requests=requests,
            batch_size=10,
            max_throughput=10,  # Lower for thinking model
            max_tokens=2000,
            temperature=0.3
        )

        elapsed = time.time() - start_time

        # Parse results
        validations = []
        for i, result in enumerate(results):
            if result['result']['type'] == 'succeeded':
                data = result['result']['data']
                validations.append({
                    **translations[i],
                    'dicta_validation': data,
                    'dicta_status': data.get('status', 'UNKNOWN'),
                    'dicta_issues': data.get('issues', []),
                    'dicta_recommended_fix': data.get('recommended_fix')
                })
            else:
                print(f"ERROR: Validation failed for sample {i}")
                validations.append({
                    **translations[i],
                    'dicta_validation': None,
                    'dicta_status': 'FAILED',
                    'dicta_issues': ['Validation failed'],
                    'dicta_recommended_fix': None
                })

        print(f"\n✓ Validated {len(validations)} samples in {elapsed:.2f}s")
        print(f"  Average: {elapsed/len(validations):.2f}s per sample")

        # Print thinking insights
        print("\nDictaLM Status Summary:")
        status_counts = {}
        for v in validations:
            status = v.get('dicta_status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

        return validations, elapsed

    async def back_translate_to_english(self, validations: List[Dict]) -> List[Dict]:
        """
        Step 3: Back-translate Hebrew to English using Qwen.

        Args:
            validations: List of validated translations

        Returns:
            List with back-translations
        """
        print("\n" + "="*60)
        print("STEP 3: Back-translating Hebrew → English (Qwen 2.5-3B)")
        print("="*60)

        start_time = time.time()

        # Build requests
        requests = []
        for idx, val in enumerate(validations):
            # Use DictaLM fix if available, otherwise original
            hebrew_text = val.get('dicta_recommended_fix') or val['hebrew_translation']

            prompt = f"""Translate this Hebrew academic text to English.
Preserve the academic tone and LGBTQ+ terminology accuracy.

Hebrew sentence: {hebrew_text}

Output ONLY valid JSON (no markdown):
{{
  "sentence": "English translation here"
}}"""

            requests.append({
                "custom_id": f"backtrans_{idx}",
                "params": {
                    "messages": [
                        {"role": "system", "content": "You are an expert Hebrew-English translator."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            })

        # Process batch
        results = await self.qwen.generate_batch(
            requests=requests,
            batch_size=10,
            max_throughput=30,
            max_tokens=500,
            temperature=0.3
        )

        elapsed = time.time() - start_time

        # Parse results
        back_translations = []
        for i, result in enumerate(results):
            if result['result']['type'] == 'succeeded':
                data = result['result']['data']
                back_translations.append({
                    **validations[i],
                    'back_translation': data.get('sentence', '')
                })
            else:
                print(f"ERROR: Back-translation failed for sample {i}")
                back_translations.append({
                    **validations[i],
                    'back_translation': '[BACK-TRANSLATION FAILED]'
                })

        print(f"\n✓ Back-translated {len(back_translations)} samples in {elapsed:.2f}s")
        print(f"  Average: {elapsed/len(back_translations):.2f}s per sample")

        return back_translations, elapsed

    def compute_semantic_delta(self, back_translations: List[Dict]) -> List[Dict]:
        """
        Step 4: Compare original English with back-translation.

        Args:
            back_translations: List with back-translations

        Returns:
            List with semantic similarity scores
        """
        print("\n" + "="*60)
        print("STEP 4: Computing Semantic Delta")
        print("="*60)

        start_time = time.time()

        results = []
        for item in back_translations:
            # Semantic similarity
            semantic_result = self.validator.validate_semantic_similarity(
                item['original_english'],
                item['hebrew_translation']
            )

            # Back-translation similarity
            backtrans_result = self.validator.validate_back_translation(
                item['original_english'],
                item['back_translation']
            )

            # Terminology check
            term_result = self.validator.validate_key_terms_preserved(
                item['original_english'],
                item['hebrew_translation'],
                HEBREW_LGBTQ_GLOSSARY
            )

            results.append({
                **item,
                'semantic_similarity': semantic_result['similarity_score'],
                'backtrans_similarity': backtrans_result['similarity_score'],
                'terminology_preservation': term_result['preservation_rate'],
                'overall_quality': self._compute_quality_score(
                    semantic_result,
                    backtrans_result,
                    term_result
                )
            })

        elapsed = time.time() - start_time
        print(f"\n✓ Computed semantic delta for {len(results)} samples in {elapsed:.2f}s")

        return results, elapsed

    def _compute_quality_score(self, semantic, backtrans, terminology) -> str:
        """Compute overall quality score."""
        score = (
            semantic['similarity_score'] * 0.4 +
            backtrans['similarity_score'] * 0.4 +
            terminology['preservation_rate'] * 0.2
        )

        if score >= 0.90:
            return "EXCELLENT"
        elif score >= 0.80:
            return "GOOD"
        elif score >= 0.70:
            return "MARGINAL"
        else:
            return "POOR"

    def print_results(self, results: List[Dict], timings: Dict):
        """Print comprehensive results."""
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)

        print("\n📊 TIMING SUMMARY:")
        print(f"  Step 1 (EN→HE):        {timings['step1']:.2f}s ({timings['step1']/10:.2f}s/sample)")
        print(f"  Step 2 (DictaLM):      {timings['step2']:.2f}s ({timings['step2']/10:.2f}s/sample)")
        print(f"  Step 3 (HE→EN):        {timings['step3']:.2f}s ({timings['step3']/10:.2f}s/sample)")
        print(f"  Step 4 (Delta):        {timings['step4']:.2f}s")
        print(f"  TOTAL:                 {timings['total']:.2f}s")

        print("\n📈 QUALITY METRICS:")
        avg_semantic = sum(r['semantic_similarity'] for r in results) / len(results)
        avg_backtrans = sum(r['backtrans_similarity'] for r in results) / len(results)
        avg_term = sum(r['terminology_preservation'] for r in results) / len(results)

        print(f"  Avg Semantic Similarity:       {avg_semantic:.3f}")
        print(f"  Avg Back-translation Similarity: {avg_backtrans:.3f}")
        print(f"  Avg Terminology Preservation:   {avg_term:.3f}")

        # Overall quality distribution
        quality_dist = {}
        for r in results:
            q = r['overall_quality']
            quality_dist[q] = quality_dist.get(q, 0) + 1

        print("\n  Overall Quality Distribution:")
        for quality, count in sorted(quality_dist.items()):
            print(f"    {quality}: {count}")

        # DictaLM status distribution
        dicta_dist = {}
        for r in results:
            status = r.get('dicta_status', 'UNKNOWN')
            dicta_dist[status] = dicta_dist.get(status, 0) + 1

        print("\n  DictaLM Validation Status:")
        for status, count in sorted(dicta_dist.items()):
            print(f"    {status}: {count}")

        # Sample outputs
        print("\n📝 SAMPLE OUTPUTS (first 3):")
        for i, r in enumerate(results[:3]):
            print(f"\n--- Sample {i+1} ({r['severity_label']}) ---")
            print(f"Original EN:  {r['original_english'][:80]}...")
            print(f"Hebrew:       {r['hebrew_translation'][:80]}...")
            print(f"Back-trans:   {r['back_translation'][:80]}...")
            print(f"Semantic:     {r['semantic_similarity']:.3f}")
            print(f"DictaLM:      {r['dicta_status']}")
            if r.get('dicta_issues'):
                print(f"Issues:       {r['dicta_issues']}")

    async def run(self):
        """Run the full test pipeline."""
        print("\n" + "="*60)
        print("HEBREW TRANSLATION PIPELINE TEST")
        print("="*60)

        total_start = time.time()

        # Sample data
        samples_df = self.sample_data(INPUT_CSV, n_per_category=2)
        samples = samples_df.to_dict('records')

        # Step 1: Translate
        translations, time1 = await self.translate_english_to_hebrew(samples)

        # Step 2: Validate with DictaLM
        validations, time2 = await self.validate_with_dicta(translations)

        # Step 3: Back-translate
        back_translations, time3 = await self.back_translate_to_english(validations)

        # Step 4: Compute delta
        final_results, time4 = self.compute_semantic_delta(back_translations)

        total_time = time.time() - total_start

        # Print results
        timings = {
            'step1': time1,
            'step2': time2,
            'step3': time3,
            'step4': time4,
            'total': total_time
        }
        self.print_results(final_results, timings)

        # Save results
        output = {
            'timings': timings,
            'results': final_results
        }
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Results saved to {OUTPUT_JSON}")


async def main():
    """Main entry point."""
    tester = PipelineTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())

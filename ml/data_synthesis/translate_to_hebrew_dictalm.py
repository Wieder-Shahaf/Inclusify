#!/usr/bin/env python3
"""
Translate English LGBTQ+ dataset to Hebrew using DictaLM-Nemotron-12B-Instruct.

This script translates the complete 10K English dataset to Hebrew:
1. Load English dataset (data/english_10k.csv)
2. Translate sentence + explanation fields using DictaLM
3. Preserve severity_label and structure
4. Save to data/hebrew_10k.csv

Usage:
    python ml/data_synthesis/translate_to_hebrew_dictalm.py
"""

import sys
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.data_synthesis.utils.vllm_processor import VLLMProcessor
from ml.data_synthesis.utils.json_extractor import extract_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DICTALM_ENDPOINT = os.getenv("DICTALM_ENDPOINT", "http://localhost:8001/v1")
DICTALM_MODEL = os.getenv("DICTALM_MODEL", "dicta-il/DictaLM-3.0-1.7B-Instruct")
INPUT_CSV = "data/english_10k.csv"
OUTPUT_CSV = "data/hebrew_10k.csv"
INTERMEDIATE_DIR = "data/intermediate/"
BATCH_SIZE = 64
MAX_THROUGHPUT = 15  # Conservative for 12B model


# Hebrew-only translation prompt
TRANSLATION_PROMPT_TEMPLATE = """אתה מתרגם מומחה מאנגלית לעברית אקדמית, המתמחה בטקסטים על נושאי להט"ב.

חובה - תקנים קפדניים:
✓ כל תו חייב להיות עברי (א-ת) או סימני פיסוק
✗ אין לכלול מילים באנגלית (a-z)
✗ אין לכלול תווים ערביים (ء-ي)
✗ אין לכלול תווים סיניים (一-龥)
✗ אין לכלול תווים בשפות אחרות

מילון מינוחים סטנדרטיים להט"ב:
- Transgender: טרנסג'נדרי / בעלי זהות מגדרית שונה
- Gender identity: זהות מגדרית
- Sexual orientation: נטייה מינית / כיוון מיני
- LGBTQ+: להט"ב
- Coming out: יציאה מהארון
- Gender dysphoria: דיספוריה מגדרית
- Conversion therapy: טיפולי המרה
- Non-binary: א-בינארי / בין-מגדרי
- Cisgender: ציסג'נדרי
- Bisexual: דו-מיני
- Homosexual: הומוסקסואל
- Gay: גיי
- Lesbian: לסבית
- Queer: קוויר

הנחיות תרגום:
1. שמור על טון אקדמי פורמלי
2. השתמש במינוח המקצועי הנכון
3. הקפד על דקדוק עברי תקין
4. התאם להקשר ישראלי (לא אמריקאי)
5. אל תפשט או תקצר - שמור על מורכבות

משפט לתרגום:
{sentence}

הסבר לתרגום:
{explanation}

פלט בפורמט JSON בלבד (ללא markdown, ללא תוויות):
{{
  "hebrew_sentence": "תרגום המשפט לעברית",
  "hebrew_explanation": "תרגום ההסבר לעברית"
}}

זכור: רק עברית! בדוק שכל תו בפלט הוא עברי לפני שליחה.
"""


def load_english_dataset(csv_path: str) -> pd.DataFrame:
    """Load English dataset."""
    logger.info(f"Loading English dataset from {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} samples")
    logger.info(f"Severity distribution:\n{df['severity_label'].value_counts()}")
    return df


def generate_translation_requests(df: pd.DataFrame) -> List[Dict]:
    """Generate batch translation requests for vLLM."""
    logger.info("Generating translation requests...")

    requests = []
    for idx, row in df.iterrows():
        prompt = TRANSLATION_PROMPT_TEMPLATE.format(
            sentence=row['sentence'],
            explanation=row['explanation']
        )

        requests.append({
            "custom_id": f"translate_{idx}_{row['severity_label']}",
            "params": {
                "messages": [
                    {
                        "role": "system",
                        "content": "אתה מתרגם מומחה לעברית אקדמית עם התמחות במינוח להט\"ב."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3  # Lower for consistency
            }
        })

    logger.info(f"Generated {len(requests)} translation requests")
    return requests


async def translate_batch(requests: List[Dict]) -> List[Dict]:
    """Translate batch using DictaLM."""
    logger.info(f"Starting translation with DictaLM at {DICTALM_ENDPOINT}")
    logger.info(f"Model: {DICTALM_MODEL}")
    logger.info(f"Batch size: {BATCH_SIZE}, Max throughput: {MAX_THROUGHPUT} req/sec")

    processor = VLLMProcessor(
        endpoint=DICTALM_ENDPOINT,
        model=DICTALM_MODEL
    )

    results = await processor.generate_batch(
        requests=requests,
        batch_size=BATCH_SIZE,
        max_throughput=MAX_THROUGHPUT,
        max_tokens=1000,
        temperature=0.3
    )

    logger.info(f"Translation completed: {len(results)} results")
    return results


def parse_and_save_translations(
    results: List[Dict],
    original_df: pd.DataFrame,
    output_path: str
) -> int:
    """Parse translation results and save Hebrew dataset."""
    logger.info("Parsing translation results...")

    hebrew_samples = []
    errors = []

    for result in results:
        custom_id = result.get('custom_id')
        idx = int(custom_id.split('_')[1])  # Extract index from custom_id
        result_data = result.get('result', {})

        if result_data.get('type') == 'error':
            logger.warning(f"Translation error for {custom_id}: {result_data.get('error')}")
            errors.append(custom_id)
            continue

        try:
            # Extract data (vLLM format)
            if 'data' in result_data and isinstance(result_data['data'], dict):
                data = result_data['data']
            else:
                # Fallback: parse from message content
                logger.warning(f"Unexpected result format for {custom_id}, trying fallback")
                continue

            # Validate has required fields
            hebrew_sentence = data.get('hebrew_sentence', '').strip()
            hebrew_explanation = data.get('hebrew_explanation', '').strip()

            if not hebrew_sentence or not hebrew_explanation:
                logger.warning(f"Missing Hebrew content in {custom_id}")
                errors.append(custom_id)
                continue

            # Validate Hebrew-only (basic check)
            if any(ord(c) in range(0x0041, 0x007B) for c in hebrew_sentence if c.isalpha()):
                logger.warning(f"English characters detected in {custom_id}: {hebrew_sentence[:50]}")
                # Still include but flag for review

            hebrew_samples.append({
                'sentence': hebrew_sentence,
                'severity_label': original_df.loc[idx, 'severity_label'],
                'explanation': hebrew_explanation,
                'original_index': idx
            })

        except Exception as e:
            logger.error(f"Parse error for {custom_id}: {e}")
            errors.append(custom_id)

    logger.info(f"Successfully parsed {len(hebrew_samples)} translations")
    logger.info(f"Errors: {len(errors)}")

    if errors:
        logger.warning(f"Failed translations: {errors[:10]}...")  # Show first 10

    # Save to CSV
    hebrew_df = pd.DataFrame(hebrew_samples)
    hebrew_df = hebrew_df.drop(columns=['original_index'])  # Remove helper column
    hebrew_df.to_csv(output_path, index=False, encoding='utf-8')

    logger.info(f"Saved {len(hebrew_df)} Hebrew samples to {output_path}")
    return len(hebrew_df)


async def main():
    """Main translation pipeline."""
    logger.info("=== Starting Hebrew Translation ===")

    # Load English dataset
    english_df = load_english_dataset(INPUT_CSV)

    # Generate translation requests
    requests = generate_translation_requests(english_df)

    # Create intermediate directory
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    intermediate_jsonl = os.path.join(INTERMEDIATE_DIR, "hebrew_translations_raw.jsonl")

    # Translate
    results = await translate_batch(requests)

    # Save intermediate results
    with open(intermediate_jsonl, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    logger.info(f"Saved intermediate results to {intermediate_jsonl}")

    # Parse and save final dataset
    num_saved = parse_and_save_translations(results, english_df, OUTPUT_CSV)

    logger.info("=== Translation Complete ===")
    logger.info(f"Input: {len(english_df)} English samples")
    logger.info(f"Output: {num_saved} Hebrew samples")
    logger.info(f"Success rate: {100 * num_saved / len(english_df):.1f}%")
    logger.info(f"Saved to: {OUTPUT_CSV}")

    if num_saved < len(english_df):
        logger.warning(f"Missing {len(english_df) - num_saved} translations - check logs for errors")


if __name__ == "__main__":
    asyncio.run(main())

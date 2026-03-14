#!/usr/bin/env python3
import requests
import json

response = requests.post(
    'http://localhost:8000/v1/completions',
    json={
        'model': 'Qwen/Qwen2.5-3B-Instruct',
        'prompt': '''Generate 5 diverse training samples for LGBTQ+ inclusive language detection in academic texts.

**Target Severity Label:** Correct

**Schema (4 fields required):**
- Sentence: Academic text sample (1-2 sentences)
- Severity Label: Correct
- Rule Category: N/A
- Explanation: Why this is classified as Correct

**Output format:** Return ONLY valid JSON array. No markdown formatting, no ```json``` blocks.

Example: [{"Sentence": "...", "Severity Label": "Correct", "Rule Category": "N/A", "Explanation": "..."}]

Generate 5 samples now:''',
        'max_tokens': 1500,
        'temperature': 0.8,
        'stop': ['\n\n\n']
    },
    timeout=120
)

result = response.json()
output = result['choices'][0]['text'].strip()

print("=== RAW OUTPUT ===")
print(output)
print("\n=== PARSING ===")

try:
    samples = json.loads(output)
    print(f"✅ Parsed {len(samples)} samples\n")
    for i, s in enumerate(samples, 1):
        print(f"{i}. {s['Sentence']}")
        print(f"   Explanation: {s['Explanation'][:80]}...\n")
except Exception as e:
    print(f"❌ Parse error: {e}")
    print(f"Output length: {len(output)} chars")

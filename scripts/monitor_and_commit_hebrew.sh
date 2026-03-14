#!/bin/bash
# Monitor running Hebrew translation and auto-commit when complete

set -e

LOG_FILE="/tmp/hebrew_translation_lenient.log"
OUTPUT_FILE="data/hebrew_10k.csv"

echo "=== Monitoring Hebrew Translation ==="
echo "Waiting for translation to complete..."
echo "Log file: $LOG_FILE"
echo ""

cd ~/inclusify

# Wait for translation process to finish
while pgrep -f "translate_to_hebrew_dictalm.py" > /dev/null; do
    # Show progress every 30 seconds
    LAST_BATCH=$(tail -100 $LOG_FILE | grep "Processing batch" | tail -1)
    if [ -n "$LAST_BATCH" ]; then
        echo "[$(date +%H:%M:%S)] $LAST_BATCH"
    fi
    sleep 30
done

echo ""
echo "✓ Translation process finished"
echo "Checking results..."
sleep 5

# Check if output file was created
if [ -f "$OUTPUT_FILE" ]; then
    ROWS=$(wc -l < "$OUTPUT_FILE")
    echo "✓ Output file created: $OUTPUT_FILE ($ROWS rows)"

    # Show final stats from log
    echo ""
    echo "Final statistics:"
    tail -20 $LOG_FILE | grep -E "Translation Complete|Input:|Output:|Success rate:" || echo "(Check log for details)"

    echo ""
    echo "Committing to git..."
    git add data/hebrew_10k.csv data/intermediate/hebrew_translations_raw.jsonl

    git commit -m "feat(05.5): add 10K Hebrew translations via DictaLM-1.7B-Instruct

Generated $(($ROWS - 1)) Hebrew samples using DictaLM-3.0-1.7B-Instruct.

Model: dicta-il/DictaLM-3.0-1.7B-Instruct (SOTA Hebrew, 1.7B params)
Infrastructure: vLLM 0.17.1 on Azure T4 GPU with CUDA 12.2
Validation: Lenient mode (accepts flexible field names)

Files:
- data/hebrew_10k.csv: Hebrew dataset
- data/intermediate/hebrew_translations_raw.jsonl: Raw responses"

    echo "✓ Committed"
    echo ""
    echo "Pushing to gsd branch..."
    git push origin gsd

    echo "✓ Pushed to GitHub"
    echo ""
    echo "=== COMPLETE ==="
    echo "Results are on GitHub (gsd branch)"
    echo "Run 'git pull origin gsd' locally to get the dataset"

else
    echo "✗ Output file not found: $OUTPUT_FILE"
    echo "Translation may have failed - check $LOG_FILE"
    exit 1
fi

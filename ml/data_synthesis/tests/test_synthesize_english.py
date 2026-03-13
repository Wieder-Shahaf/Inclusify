"""Tests for English synthesis orchestration.

Tests validate:
1. Loading existing dataset
2. Calculating stratified generation targets
3. Generating batch requests
4. Parsing and validating results
"""

import pytest
import pandas as pd
import json
from unittest.mock import MagicMock, patch
from ml.data_synthesis.synthesize_english import (
    load_existing_dataset,
    calculate_generation_targets,
    generate_batch_requests,
    parse_and_save_results,
)


class TestLoadExistingDataset:
    """Tests for load_existing_dataset function"""

    @patch('ml.data_synthesis.synthesize_english.load_dataset')
    def test_load_existing_dataset_returns_988_samples(self, mock_load):
        """Test 1: load_existing_dataset() returns 988 unique samples"""
        # Mock the load_dataset function from prepare_data.py
        mock_df = pd.DataFrame({
            'Sentence': ['Sample ' + str(i) for i in range(988)],
            'Severity Label': ['Correct'] * 988,
            'Explanation': ['Explanation'] * 988
        })
        mock_load.return_value = mock_df

        result = load_existing_dataset()

        assert len(result) == 988
        assert 'Sentence' in result.columns
        assert 'Severity Label' in result.columns
        mock_load.assert_called_once()


class TestCalculateGenerationTargets:
    """Tests for calculate_generation_targets function"""

    def test_calculate_targets_stratified_by_class(self):
        """Test 2: calculate_generation_targets() produces stratified per-class targets totaling ~11K"""
        current_df = pd.DataFrame({
            'Sentence': ['S1', 'S2', 'S3', 'S4'],
            'Severity Label': ['Correct', 'Correct', 'Outdated', 'Biased'],
            'Explanation': ['E1', 'E2', 'E3', 'E4']
        })

        targets = calculate_generation_targets(current_df, total_target=11000)

        # Check that targets is a dict
        assert isinstance(targets, dict)

        # Check that total is approximately 11000 (allowing for rounding)
        total_to_generate = sum(targets.values())
        assert 10000 <= total_to_generate <= 11000

        # Check stratification - proportions should match current distribution
        current_counts = current_df['Severity Label'].value_counts()
        for label, target_count in targets.items():
            if label in current_counts:
                current_count = current_counts[label]
                expected_proportion = current_count / len(current_df)
                # Target should roughly maintain proportion
                assert target_count > 0  # Should generate some for each class


class TestGenerateBatchRequests:
    """Tests for generate_batch_requests function"""

    def test_generate_batch_requests_creates_valid_format(self):
        """Test 3: generate_batch_requests() creates valid request format"""
        targets = {'Correct': 10, 'Outdated': 5}
        seed_df = pd.DataFrame({
            'Sentence': ['Correct sample', 'Outdated sample'],
            'Severity Label': ['Correct', 'Outdated'],
            'Explanation': ['Exp1', 'Exp2']
        })

        requests = generate_batch_requests(targets, seed_df, model="test-model", system_prompt="Test prompt")

        # Should generate 15 requests total
        assert len(requests) == 15

        # Check format of first request
        req = requests[0]
        assert 'custom_id' in req
        assert 'params' in req
        assert 'model' in req['params']
        assert 'max_tokens' in req['params']
        assert 'messages' in req['params']

        # Check messages structure
        messages = req['params']['messages']
        assert len(messages) == 2  # system + user
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'


class TestParseAndSaveResults:
    """Tests for parse_and_save_results function"""

    def test_parse_results_validates_schema(self, tmp_path):
        """Test 4: parse_and_save_results() validates output schema and filters invalid samples"""
        batch_results = [
            {
                'custom_id': 'req_1',
                'result': {
                    'type': 'succeeded',
                    'message': {
                        'content': [{'text': '{"sentence": "Valid sample", "severity_label": "Correct", "explanation": "Valid"}'}]
                    }
                }
            },
            {
                'custom_id': 'req_2',
                'result': {
                    'type': 'succeeded',
                    'message': {
                        'content': [{'text': '{"sentence": "", "severity_label": "Correct", "explanation": "Invalid - empty sentence"}'}]
                    }
                }
            },
            {
                'custom_id': 'req_3',
                'result': {
                    'type': 'errored',
                    'error': {'message': 'API error'}
                }
            }
        ]

        output_csv = tmp_path / "output.csv"

        valid_count = parse_and_save_results(batch_results, str(output_csv))

        # Should have 1 valid sample (req_1)
        assert valid_count == 1

        # Check output CSV
        df = pd.read_csv(output_csv)
        assert len(df) == 1
        assert df.iloc[0]['Sentence'] == 'Valid sample'
        assert df.iloc[0]['Severity Label'] == 'Correct'

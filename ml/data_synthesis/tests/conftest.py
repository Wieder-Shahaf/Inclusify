"""Shared pytest fixtures for data synthesis tests"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from unittest.mock import MagicMock


# Sample data fixtures
@pytest.fixture
def sample_dataset():
    """Returns small DataFrame with 10 samples (2 per severity class)"""
    return pd.DataFrame({
        'Sentence': [
            'Gender identity is distinct from sexual orientation.',
            'LGBTQ+ individuals face discrimination.',
            'The homosexual lifestyle is a choice.',
            'Transgender people suffer from mental illness.',
            'Same-sex attracted individuals need therapy.',
            'Non-binary identities are not valid.',
            'Sexual preference is determined by environment.',
            'Gender dysphoria is a psychiatric disorder.',
            'The LGBTQ community advocates for equal rights.',
            'Queer theory challenges heteronormative assumptions.'
        ],
        'Severity Label': [
            'Correct',
            'Correct',
            'Outdated',
            'Outdated',
            'Biased/Stigmatizing',
            'Biased/Stigmatizing',
            'Pathologizing',
            'Pathologizing',
            'Correct',
            'Correct'
        ],
        'Explanation': [
            'Correctly distinguishes gender identity and sexual orientation.',
            'Neutral and accurate description of discrimination.',
            'Outdated framing implying choice rather than innate identity.',
            'Pathologizes transgender identity as mental illness.',
            'Biased assumption that attraction requires therapeutic intervention.',
            'Stigmatizing denial of non-binary identities.',
            'Outdated "preference" terminology and false environmental causation.',
            'Pathologizing language treating identity as psychiatric condition.',
            'Inclusive and accurate terminology.',
            'Academic terminology used correctly without bias.'
        ]
    })


@pytest.fixture
def sample_english_text():
    """Returns list of 5 English academic sentences"""
    return [
        "Gender identity is distinct from sexual orientation.",
        "LGBTQ+ individuals face discrimination in academic settings.",
        "Non-binary identities are increasingly recognized in research.",
        "Sexual orientation is not a choice or mental disorder.",
        "Transgender people experience unique healthcare challenges."
    ]


@pytest.fixture
def sample_hebrew_text():
    """Returns list of 5 Hebrew academic sentences with LGBTQ+ terminology"""
    return [
        "זהות מגדרית ונטייה מינית הן מושגים נפרדים.",
        "קהילת הלהט״ב מתמודדת עם אפליה במוסדות אקדמיים.",
        "זהויות לא-בינאריות מקבלות הכרה הולכת וגוברת במחקר.",
        "נטייה מינית אינה בחירה או הפרעה נפשית.",
        "אנשים טרנסג'נדרים מתמודדים עם אתגרים ייחודיים בשירותי בריאות."
    ]


# Mock LLM API fixtures
@pytest.fixture
def mock_batch_api_response():
    """Returns mock BatchProcessor.poll_results() response"""
    return [
        {
            'custom_id': 'test_1',
            'response': {
                'status_code': 200,
                'body': {
                    'choices': [{
                        'message': {
                            'content': '{"sentence": "Gender identity is distinct from sexual orientation.", "severity_label": "Correct", "explanation": "Correctly distinguishes gender identity and sexual orientation."}'
                        }
                    }]
                }
            },
            'error': None
        },
        {
            'custom_id': 'test_2',
            'response': {
                'status_code': 200,
                'body': {
                    'choices': [{
                        'message': {
                            'content': '{"sentence": "The homosexual lifestyle is a choice.", "severity_label": "Outdated", "explanation": "Outdated framing implying choice rather than innate identity."}'
                        }
                    }]
                }
            },
            'error': None
        }
    ]


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mocks openai.Client for unit tests"""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.id = 'batch_test_123'
    mock_batch.status = 'completed'
    mock_client.batches.create.return_value = mock_batch
    mock_client.batches.retrieve.return_value = mock_batch

    # Mock file upload
    mock_file = MagicMock()
    mock_file.id = 'file_test_123'
    mock_client.files.upload.return_value = mock_file

    # Mock file content retrieval
    mock_client.files.content.return_value.text = '''{
        "custom_id": "test_1",
        "response": {
            "status_code": 200,
            "body": {
                "choices": [{
                    "message": {
                        "content": "{\\"sentence\\": \\"Test\\", \\"severity_label\\": \\"Correct\\", \\"explanation\\": \\"Test\\"}"
                    }
                }]
            }
        }
    }'''

    return mock_client


# File path fixtures
@pytest.fixture
def temp_csv_file(tmp_path):
    """Returns path to temporary CSV file for testing"""
    csv_path = tmp_path / "test_dataset.csv"
    return str(csv_path)


@pytest.fixture
def temp_jsonl_file(tmp_path):
    """Returns path to temporary JSONL file for batch requests"""
    jsonl_path = tmp_path / "batch_requests.jsonl"
    return str(jsonl_path)


# Embeddings fixtures
@pytest.fixture
def sample_embeddings():
    """Returns small numpy array for similarity testing"""
    # 5 samples, 384-dim embeddings (sentence-transformers default)
    np.random.seed(42)
    return np.random.rand(5, 384)


@pytest.fixture
def sample_similar_embeddings():
    """Returns embeddings with known similarity for deduplication testing"""
    base_embedding = np.random.rand(1, 384)
    similar_embeddings = np.vstack([
        base_embedding,
        base_embedding + np.random.rand(1, 384) * 0.01,  # Very similar
        base_embedding + np.random.rand(1, 384) * 0.5,   # Moderately similar
        np.random.rand(1, 384)                            # Different
    ])
    return similar_embeddings


# Quality validation fixtures
@pytest.fixture
def sample_imbalanced_dataset():
    """Returns DataFrame with class imbalance for testing validation"""
    return pd.DataFrame({
        'Sentence': ['Sample'] * 100,
        'Severity Label': ['Correct'] * 80 + ['Outdated'] * 10 + ['Biased/Stigmatizing'] * 5 + ['Pathologizing'] * 5,
        'Explanation': ['Explanation'] * 100
    })


@pytest.fixture
def sample_balanced_dataset():
    """Returns DataFrame with balanced class distribution"""
    return pd.DataFrame({
        'Sentence': ['Sample'] * 100,
        'Severity Label': ['Correct'] * 25 + ['Outdated'] * 25 + ['Biased/Stigmatizing'] * 25 + ['Pathologizing'] * 25,
        'Explanation': ['Explanation'] * 100
    })


# Hebrew-specific fixtures
@pytest.fixture
def sample_mixed_language_text():
    """Returns text with mixed Hebrew and English for validation testing"""
    return [
        "זהות מגדרית is distinct from sexual orientation.",  # Mixed
        "LGBTQ+ קהילה faces discrimination.",  # Mixed
        "זהות מגדרית ונטייה מינית הן מושגים נפרדים.",  # Pure Hebrew
        "Gender identity is distinct from sexual orientation."  # Pure English
    ]


@pytest.fixture
def sample_translation_pairs():
    """Returns sample English-Hebrew translation pairs for quality validation"""
    return pd.DataFrame({
        'english': [
            'Gender identity is distinct from sexual orientation.',
            'LGBTQ+ individuals face discrimination.'
        ],
        'hebrew': [
            'זהות מגדרית ונטייה מינית הן מושגים נפרדים.',
            'קהילת הלהט״ב מתמודדת עם אפליה.'
        ]
    })

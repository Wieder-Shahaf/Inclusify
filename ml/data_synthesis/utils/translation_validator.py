"""
Translation quality validation utilities.

Validates Hebrew translations maintain semantic equivalence with English originals
through multiple automated and semi-automated methods.
"""

import numpy as np
from typing import Dict, List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class TranslationValidator:
    """Validates translation quality through multiple methods."""

    def __init__(self):
        """Initialize validation models."""
        # Multilingual sentence embeddings (supports 50+ languages)
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    def validate_semantic_similarity(
        self,
        english_text: str,
        hebrew_text: str,
        threshold: float = 0.85
    ) -> Dict[str, float]:
        """
        Validate semantic similarity using cross-lingual embeddings.

        Args:
            english_text: Original English text
            hebrew_text: Hebrew translation
            threshold: Minimum acceptable similarity (0-1)

        Returns:
            Dict with similarity score and pass/fail status
        """
        # Generate embeddings
        en_embedding = self.embedding_model.encode([english_text])
        he_embedding = self.embedding_model.encode([hebrew_text])

        # Calculate cosine similarity
        similarity = cosine_similarity(en_embedding, he_embedding)[0][0]

        return {
            'similarity_score': float(similarity),
            'passes_threshold': similarity >= threshold,
            'threshold': threshold,
            'status': 'PASS' if similarity >= threshold else 'FAIL'
        }

    def validate_severity_consistency(
        self,
        english_text: str,
        hebrew_text: str,
        original_severity: str
    ) -> Dict[str, any]:
        """
        Validate that Hebrew translation maintains same severity classification.

        Uses zero-shot classification to predict severity from Hebrew text
        and compares with original English severity.

        Args:
            english_text: Original English text
            hebrew_text: Hebrew translation
            original_severity: Original severity label

        Returns:
            Dict with consistency check results
        """
        # This would use a Hebrew classifier if we had one trained
        # For now, return structure for future implementation
        return {
            'original_severity': original_severity,
            'hebrew_predicted_severity': None,  # Would come from classifier
            'consistent': None,  # Would compare predictions
            'status': 'PENDING_CLASSIFIER'
        }

    def validate_key_terms_preserved(
        self,
        english_text: str,
        hebrew_text: str,
        term_glossary: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Check if key LGBTQ+ terminology is correctly translated.

        Args:
            english_text: Original English text
            hebrew_text: Hebrew translation
            term_glossary: Dict mapping English terms → Hebrew terms

        Returns:
            Dict with terminology validation results
        """
        preserved = []
        missing = []

        for en_term, he_term in term_glossary.items():
            # Check if English term appears in source
            if en_term.lower() in english_text.lower():
                # Check if Hebrew equivalent appears in translation
                if he_term in hebrew_text:
                    preserved.append({
                        'english': en_term,
                        'hebrew': he_term,
                        'found': True
                    })
                else:
                    missing.append({
                        'english': en_term,
                        'expected_hebrew': he_term,
                        'found': False
                    })

        return {
            'terms_preserved': preserved,
            'terms_missing': missing,
            'preservation_rate': len(preserved) / (len(preserved) + len(missing)) if (preserved or missing) else 1.0,
            'status': 'PASS' if not missing else 'PARTIAL'
        }

    def validate_back_translation(
        self,
        original_english: str,
        back_translated_english: str,
        threshold: float = 0.80
    ) -> Dict[str, any]:
        """
        Validate translation quality using back-translation.

        Process:
        1. English → Hebrew (translation)
        2. Hebrew → English (back-translation)
        3. Compare back-translation with original

        Args:
            original_english: Original English text
            back_translated_english: English text translated back from Hebrew
            threshold: Minimum acceptable similarity

        Returns:
            Dict with back-translation validation results
        """
        # Generate embeddings
        orig_embedding = self.embedding_model.encode([original_english])
        back_embedding = self.embedding_model.encode([back_translated_english])

        # Calculate similarity
        similarity = cosine_similarity(orig_embedding, back_embedding)[0][0]

        return {
            'original': original_english,
            'back_translated': back_translated_english,
            'similarity_score': float(similarity),
            'passes_threshold': similarity >= threshold,
            'threshold': threshold,
            'status': 'PASS' if similarity >= threshold else 'FAIL'
        }

    def comprehensive_validation(
        self,
        english_text: str,
        hebrew_text: str,
        back_translated_english: str,
        original_severity: str,
        term_glossary: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Run all validation checks on a translation.

        Args:
            english_text: Original English text
            hebrew_text: Hebrew translation
            back_translated_english: Back-translation to English
            original_severity: Original severity label
            term_glossary: Terminology mapping

        Returns:
            Comprehensive validation report
        """
        return {
            'semantic_similarity': self.validate_semantic_similarity(english_text, hebrew_text),
            'back_translation': self.validate_back_translation(english_text, back_translated_english),
            'terminology': self.validate_key_terms_preserved(english_text, hebrew_text, term_glossary),
            'severity': self.validate_severity_consistency(english_text, hebrew_text, original_severity),
            'overall_status': self._compute_overall_status(
                self.validate_semantic_similarity(english_text, hebrew_text),
                self.validate_back_translation(english_text, back_translated_english),
                self.validate_key_terms_preserved(english_text, hebrew_text, term_glossary)
            )
        }

    def _compute_overall_status(
        self,
        semantic_result: Dict,
        backtrans_result: Dict,
        terminology_result: Dict
    ) -> str:
        """Compute overall validation status from individual checks."""
        checks_passed = sum([
            semantic_result['passes_threshold'],
            backtrans_result['passes_threshold'],
            terminology_result['preservation_rate'] >= 0.90
        ])

        if checks_passed == 3:
            return 'EXCELLENT'
        elif checks_passed == 2:
            return 'GOOD'
        elif checks_passed == 1:
            return 'MARGINAL'
        else:
            return 'POOR'


def validate_translation_batch(
    english_texts: List[str],
    hebrew_texts: List[str],
    back_translations: List[str],
    severities: List[str],
    term_glossary: Dict[str, str]
) -> Tuple[List[Dict], Dict[str, any]]:
    """
    Validate a batch of translations.

    Args:
        english_texts: List of original English texts
        hebrew_texts: List of Hebrew translations
        back_translations: List of back-translations to English
        severities: List of severity labels
        term_glossary: Terminology mapping

    Returns:
        Tuple of (per-sample results, aggregate statistics)
    """
    validator = TranslationValidator()
    results = []

    for en, he, back, sev in zip(english_texts, hebrew_texts, back_translations, severities):
        result = validator.comprehensive_validation(en, he, back, sev, term_glossary)
        results.append(result)

    # Aggregate statistics
    stats = {
        'total_samples': len(results),
        'excellent': sum(1 for r in results if r['overall_status'] == 'EXCELLENT'),
        'good': sum(1 for r in results if r['overall_status'] == 'GOOD'),
        'marginal': sum(1 for r in results if r['overall_status'] == 'MARGINAL'),
        'poor': sum(1 for r in results if r['overall_status'] == 'POOR'),
        'avg_semantic_similarity': np.mean([r['semantic_similarity']['similarity_score'] for r in results]),
        'avg_backtrans_similarity': np.mean([r['back_translation']['similarity_score'] for r in results]),
        'avg_term_preservation': np.mean([r['terminology']['preservation_rate'] for r in results])
    }

    return results, stats


# Hebrew LGBTQ+ terminology glossary
HEBREW_LGBTQ_GLOSSARY = {
    # Basic terms
    'LGBTQ+': 'להט"ב',
    'LGBT': 'להט"ב',
    'gay': 'גיי',
    'lesbian': 'לסבית',
    'bisexual': 'ביסקסואל',
    'transgender': 'טרנסג\'נדר',
    'queer': 'קוויר',
    'cisgender': 'ציסג\'נדר',
    'non-binary': 'א-בינארי',

    # Identity terms
    'gender identity': 'זהות מגדרית',
    'sexual orientation': 'נטייה מינית',
    'gender expression': 'ביטוי מגדרי',
    'gender dysphoria': 'דיספוריה מגדרית',

    # Community terms
    'coming out': 'יציאה מהארון',
    'pride': 'גאווה',
    'discrimination': 'אפליה',
    'homophobia': 'הומופוביה',
    'transphobia': 'טרנספוביה',

    # Clinical/academic terms
    'conversion therapy': 'טיפולי המרה',
    'hormone therapy': 'טיפול הורמונלי',
    'gender-affirming care': 'טיפול מאשר מגדר',
    'same-sex': 'חד-מיני',
    'sexual minority': 'מיעוט מיני',

    # Outdated/problematic terms (to detect, not recommend)
    'homosexuality': 'הומוסקסואליות',
    'sexual preference': 'העדפה מינית',  # Problematic framing
    'lifestyle': 'אורח חיים',  # When referring to LGBTQ+ as choice
}

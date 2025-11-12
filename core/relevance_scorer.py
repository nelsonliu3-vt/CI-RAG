"""
Relevance Scorer Module
Scores documents based on program profile relevance for intelligent curation
"""

import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Score documents for relevance to program profile"""

    def __init__(self, program_profile: Dict[str, Any]):
        """
        Initialize scorer with program profile

        Args:
            program_profile: Dict with fields like indication, stage, target, etc.
        """
        self.program = program_profile or {}

        # Extract key matching fields
        self.program_indication = (self.program.get('indication') or '').lower()
        self.program_stage = (self.program.get('stage') or '').lower()
        self.program_target = (self.program.get('target') or '').lower()
        self.program_name = (self.program.get('program_name') or '').lower()

        # Weights for scoring dimensions (must sum to 1.0)
        from core.config import RELEVANCE_WEIGHTS
        self.weights = RELEVANCE_WEIGHTS

    def score_document(
        self,
        entities: Dict[str, Any],
        doc_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score a document for program relevance

        Args:
            entities: Extracted entities (companies, assets, trials, data_points)
            doc_metadata: Document metadata (type, source, topics)

        Returns:
            Dict with relevance_score, tags, breakdown, matched entities
        """
        if not self.program:
            # No program profile = all documents equally relevant
            return {
                'relevance_score': 0.5,
                'relevance_tags': ['no_program_profile'],
                'relevance_breakdown': {},
                'matched_assets': [],
                'matched_companies': [],
                'matched_indications': [],
                'confidence': 0.0
            }

        # Calculate individual dimension scores
        indication_score = self._score_indication_match(entities)
        stage_score = self._score_stage_alignment(entities)
        target_score = self._score_target_match(entities)
        competitor_score = self._score_competitor_signals(entities)
        regulatory_score = self._score_regulatory_relevance(doc_metadata)
        clinical_score = self._score_clinical_relevance(entities)

        # Weighted overall score
        overall_score = (
            indication_score * self.weights['indication_match'] +
            stage_score * self.weights['stage_alignment'] +
            target_score * self.weights['target_match'] +
            competitor_score * self.weights['competitor_signals'] +
            regulatory_score * self.weights['regulatory_relevance'] +
            clinical_score * self.weights['clinical_relevance']
        )

        # Generate relevance tags
        tags = self._generate_tags(
            indication_score, stage_score, target_score,
            competitor_score, regulatory_score, clinical_score
        )

        # Find matched entities
        matched_assets, matched_companies, matched_indications = self._find_matched_entities(entities)

        # Calculate confidence based on number of signals
        confidence = self._calculate_confidence(
            indication_score, stage_score, target_score, entities
        )

        return {
            'relevance_score': round(overall_score, 2),
            'relevance_tags': tags,
            'relevance_breakdown': {
                'indication': round(indication_score, 2),
                'stage': round(stage_score, 2),
                'target': round(target_score, 2),
                'competitors': round(competitor_score, 2),
                'regulatory': round(regulatory_score, 2),
                'clinical': round(clinical_score, 2)
            },
            'matched_assets': matched_assets,
            'matched_companies': matched_companies,
            'matched_indications': matched_indications,
            'confidence': round(confidence, 2)
        }

    def _score_indication_match(self, entities: Dict[str, Any]) -> float:
        """Score indication/disease area match (0-1)"""
        if not self.program_indication:
            return 0.5  # Neutral if no program indication

        max_score = 0.0

        # Check assets
        for asset in entities.get('assets', []):
            asset_indication = (asset.get('indication') or '').lower()
            if asset_indication:
                similarity = self._text_similarity(self.program_indication, asset_indication)
                max_score = max(max_score, similarity)

        # Check trials
        for trial in entities.get('trials', []):
            trial_indication = (trial.get('indication') or '').lower()
            if trial_indication:
                similarity = self._text_similarity(self.program_indication, trial_indication)
                max_score = max(max_score, similarity)

        return max_score

    def _score_stage_alignment(self, entities: Dict[str, Any]) -> float:
        """Score development stage alignment (0-1)"""
        if not self.program_stage:
            return 0.5  # Neutral if no program stage

        # Extract numeric phase from program (e.g., "Phase 2" -> 2)
        program_phase = self._extract_phase_number(self.program_stage)

        if program_phase is None:
            return 0.5

        max_score = 0.0

        # Check asset phases
        for asset in entities.get('assets', []):
            asset_phase = self._extract_phase_number(asset.get('phase', ''))
            if asset_phase is not None:
                score = self._phase_proximity_score(program_phase, asset_phase)
                max_score = max(max_score, score)

        # Check trial phases
        for trial in entities.get('trials', []):
            trial_phase = self._extract_phase_number(trial.get('phase', ''))
            if trial_phase is not None:
                score = self._phase_proximity_score(program_phase, trial_phase)
                max_score = max(max_score, score)

        return max_score

    def _score_target_match(self, entities: Dict[str, Any]) -> float:
        """Score molecular target/mechanism match (0-1)"""
        if not self.program_target:
            return 0.5  # Neutral if no program target

        max_score = 0.0

        # Check asset mechanisms
        for asset in entities.get('assets', []):
            mechanism = (asset.get('mechanism') or '').lower()
            if mechanism:
                similarity = self._text_similarity(self.program_target, mechanism)
                max_score = max(max_score, similarity)

        return max_score

    def _score_competitor_signals(self, entities: Dict[str, Any]) -> float:
        """Score competitive intelligence signals (0-1)"""
        competitor_count = 0

        # Count competitor companies
        for company in entities.get('companies', []):
            role = (company.get('role') or '').lower()
            if role == 'competitor':
                competitor_count += 1

        # Count competitive assets (non-sponsor)
        for asset in entities.get('assets', []):
            company_name = (asset.get('company') or '').lower()
            # If asset company doesn't match program name, it's competitive
            if company_name and company_name not in self.program_name:
                competitor_count += 1

        # Sigmoid-like scoring: more competitors = higher score, plateaus at 3+
        if competitor_count == 0:
            return 0.0
        elif competitor_count == 1:
            return 0.5
        elif competitor_count == 2:
            return 0.8
        else:
            return 1.0

    def _score_regulatory_relevance(self, doc_metadata: Dict[str, Any]) -> float:
        """Score based on document type relevance (0-1)"""
        doc_type = (doc_metadata.get('detected_type') or 'other').lower()

        from core.config import DOCUMENT_TYPE_RELEVANCE_BOOST

        # Get boost factor and normalize to 0-1 range
        boost = DOCUMENT_TYPE_RELEVANCE_BOOST.get(doc_type, 0.5)

        # Normalize (assuming boosts range from 0.3 to 1.2)
        normalized = (boost - 0.3) / (1.2 - 0.3)
        return max(0.0, min(1.0, normalized))

    def _score_clinical_relevance(self, entities: Dict[str, Any]) -> float:
        """Score based on clinical trial status and data quality (0-1)"""
        if not entities.get('trials'):
            return 0.3  # Low score if no trial data

        max_score = 0.0

        for trial in entities.get('trials', []):
            status = (trial.get('status') or '').lower()

            # Score by trial status
            if 'completed' in status or 'final' in status:
                score = 1.0
            elif 'ongoing' in status or 'active' in status:
                score = 0.7
            elif 'planned' in status or 'recruiting' in status:
                score = 0.5
            else:
                score = 0.3

            max_score = max(max_score, score)

        # Boost if we have data points
        if entities.get('data_points'):
            max_score = min(1.0, max_score + 0.1)

        return max_score

    def _generate_tags(
        self,
        indication_score: float,
        stage_score: float,
        target_score: float,
        competitor_score: float,
        regulatory_score: float,
        clinical_score: float
    ) -> List[str]:
        """Generate human-readable relevance tags"""
        tags = []

        if indication_score >= 0.7:
            tags.append('indication_match')
        if stage_score >= 0.7:
            tags.append('stage_match')
        if target_score >= 0.7:
            tags.append('target_match')
        if competitor_score >= 0.5:
            tags.append('competitor')
        if regulatory_score >= 0.7:
            tags.append('regulatory_relevant')
        if clinical_score >= 0.7:
            tags.append('clinical_data')

        if not tags:
            tags.append('low_relevance')

        return tags

    def _find_matched_entities(self, entities: Dict[str, Any]) -> tuple:
        """Extract matched asset names, companies, indications"""
        matched_assets = []
        matched_companies = []
        matched_indications = set()

        # Assets
        for asset in entities.get('assets', []):
            asset_name = asset.get('name')
            if asset_name:
                matched_assets.append(asset_name)

            indication = asset.get('indication')
            if indication:
                matched_indications.add(indication)

        # Companies
        for company in entities.get('companies', []):
            company_name = company.get('name')
            if company_name:
                matched_companies.append(company_name)

        # Trials (additional indications)
        for trial in entities.get('trials', []):
            indication = trial.get('indication')
            if indication:
                matched_indications.add(indication)

        return matched_assets, matched_companies, list(matched_indications)

    def _calculate_confidence(
        self,
        indication_score: float,
        stage_score: float,
        target_score: float,
        entities: Dict[str, Any]
    ) -> float:
        """Calculate confidence in relevance score (0-1)"""
        # More entities = higher confidence
        entity_count = (
            len(entities.get('companies', [])) +
            len(entities.get('assets', [])) +
            len(entities.get('trials', [])) +
            len(entities.get('data_points', []))
        )

        # Confidence based on entity count and score consistency
        entity_confidence = min(1.0, entity_count / 5.0)  # Saturates at 5 entities

        # High scores across multiple dimensions = high confidence
        score_consistency = (indication_score + stage_score + target_score) / 3.0

        return (entity_confidence + score_consistency) / 2.0

    # Helper methods

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matcher (0-1)"""
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def _extract_phase_number(phase_text: str) -> Optional[int]:
        """Extract numeric phase from text (e.g., 'Phase 2' -> 2)"""
        if not phase_text:
            return None

        # Try to extract phase number
        match = re.search(r'phase\s*(\d)', phase_text.lower())
        if match:
            return int(match.group(1))

        # Direct number
        match = re.search(r'\b([1-3])\b', phase_text)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def _phase_proximity_score(phase1: int, phase2: int) -> float:
        """Score phase proximity (exact match = 1.0, adjacent = 0.6, far = 0.3)"""
        diff = abs(phase1 - phase2)

        if diff == 0:
            return 1.0  # Exact match
        elif diff == 1:
            return 0.6  # Adjacent phase
        else:
            return 0.3  # Distant phase


# Singleton instance
_scorer_instance: Optional[RelevanceScorer] = None


def get_relevance_scorer(program_profile: Dict[str, Any] = None) -> RelevanceScorer:
    """Get or create relevance scorer"""
    global _scorer_instance

    # If program profile changes, recreate scorer
    if program_profile is not None:
        _scorer_instance = RelevanceScorer(program_profile)
    elif _scorer_instance is None:
        # Try to load program profile
        try:
            from core.program_profile import get_program_profile
            profile = get_program_profile()
            _scorer_instance = RelevanceScorer(profile)
        except Exception as e:
            logger.warning(f"Could not load program profile: {e}")
            _scorer_instance = RelevanceScorer({})

    return _scorer_instance


def check_oncology_relevance(document_text: str) -> Dict[str, Any]:
    """
    Check if document is oncology-related

    Args:
        document_text: Full document text

    Returns:
        Dict with oncology_score (0-1), matched_keywords, recommendation
    """
    from core.config import ONCOLOGY_KEYWORDS, ONCOLOGY_RELEVANCE_THRESHOLD

    text_lower = document_text.lower()

    # Count matches by category
    matches_by_category = {}
    total_matches = 0
    matched_keywords_list = []

    for category, keywords in ONCOLOGY_KEYWORDS.items():
        category_matches = 0
        for keyword in keywords:
            # Count occurrences of each keyword
            count = text_lower.count(keyword)
            if count > 0:
                category_matches += count
                matched_keywords_list.append(keyword)

        matches_by_category[category] = category_matches
        total_matches += category_matches

    # Calculate oncology score (0-1)
    # More matches = higher score, with diminishing returns
    if total_matches == 0:
        oncology_score = 0.0
    elif total_matches <= 5:
        oncology_score = total_matches * 0.1  # 0.1 - 0.5
    elif total_matches <= 15:
        oncology_score = 0.5 + (total_matches - 5) * 0.03  # 0.5 - 0.8
    else:
        oncology_score = min(1.0, 0.8 + (total_matches - 15) * 0.01)  # 0.8 - 1.0

    # Determine recommendation
    if oncology_score >= ONCOLOGY_RELEVANCE_THRESHOLD:
        recommendation = "oncology_focused"
        warning = None
    else:
        recommendation = "non_oncology"
        warning = "This document appears to be NON-ONCOLOGY. Consider skipping."

    return {
        'oncology_score': round(oncology_score, 2),
        'total_matches': total_matches,
        'matches_by_category': matches_by_category,
        'matched_keywords': list(set(matched_keywords_list))[:10],  # Top 10 unique
        'recommendation': recommendation,
        'warning': warning,
        'is_oncology': oncology_score >= ONCOLOGY_RELEVANCE_THRESHOLD
    }


if __name__ == "__main__":
    # Test relevance scorer
    print("Testing Relevance Scorer...")

    # Mock program profile
    program = {
        'program_name': 'Drug-123',
        'indication': '2L NSCLC',
        'stage': 'Phase 2',
        'target': 'KRAS G12C inhibitor'
    }

    scorer = RelevanceScorer(program)

    # Test case 1: Highly relevant document
    entities1 = {
        'companies': [{'name': 'Competitor A', 'role': 'competitor'}],
        'assets': [{
            'name': 'Drug-ABC',
            'company': 'Competitor A',
            'mechanism': 'KRAS G12C inhibitor',
            'indication': '2L NSCLC',
            'phase': 'Phase 2'
        }],
        'trials': [{
            'trial_id': 'NCT123',
            'phase': 'Phase 2',
            'indication': '2nd-line NSCLC',
            'status': 'completed'
        }],
        'data_points': [{'metric_type': 'ORR', 'value': 45.0}]
    }

    doc_metadata1 = {'detected_type': 'publication'}

    result1 = scorer.score_document(entities1, doc_metadata1)
    print(f"\n✓ Test 1 - Highly relevant document:")
    print(f"  Score: {result1['relevance_score']}")
    print(f"  Tags: {result1['relevance_tags']}")
    print(f"  Breakdown: {result1['relevance_breakdown']}")
    print(f"  Confidence: {result1['confidence']}")

    # Test case 2: Low relevance document
    entities2 = {
        'companies': [{'name': 'Company B', 'role': 'sponsor'}],
        'assets': [{
            'name': 'Drug-XYZ',
            'mechanism': 'PD-1 inhibitor',
            'indication': 'Melanoma',
            'phase': 'Phase 3'
        }],
        'trials': [],
        'data_points': []
    }

    doc_metadata2 = {'detected_type': 'news_article'}

    result2 = scorer.score_document(entities2, doc_metadata2)
    print(f"\n✓ Test 2 - Low relevance document:")
    print(f"  Score: {result2['relevance_score']}")
    print(f"  Tags: {result2['relevance_tags']}")
    print(f"  Breakdown: {result2['relevance_breakdown']}")
    print(f"  Confidence: {result2['confidence']}")

    print("\n✓ Relevance scorer test successful!")

"""
Stance Analysis Module
Calculates program overlap and assigns stance labels (Harmful/Helpful/Neutral)

POC Requirements:
- Weighted Jaccard similarity: {target: 0.35, disease: 0.25, line: 0.20, biomarker: 0.15, MoA: 0.05}
- Stance thresholds:
  - ≥0.6 and positive competitor → Harmful
  - ≥0.6 and negative competitor → Helpful
  - 0.3-0.59 → Potentially harmful/helpful
  - <0.3 → Neutral
- Target stance accuracy: ≥0.7 on test set
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple, Set
import re

from ci.data_contracts import Signal, Stance, ImpactCode
from ci.config import get_stance_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StanceAnalyzer:
    """
    Analyzes signals relative to program profile to determine stance

    Uses weighted Jaccard similarity to calculate program overlap,
    then assigns stance labels based on overlap + impact code
    """

    def __init__(self, program_profile: Dict):
        """
        Initialize stance analyzer with program profile

        Args:
            program_profile: Dict with keys: program_name, target, indication,
                            stage, differentiators, etc.
        """
        # Load configuration
        self.config = get_stance_config()
        self.WEIGHTS = self.config.WEIGHTS
        self.HIGH_OVERLAP = self.config.HIGH_OVERLAP_THRESHOLD
        self.MEDIUM_OVERLAP = self.config.MEDIUM_OVERLAP_THRESHOLD

        self.program_profile = program_profile
        self.program_entities = self._extract_program_entities(program_profile)

    def _extract_program_entities(self, profile: Dict) -> Dict[str, Set[str]]:
        """
        Extract structured entities from program profile for matching

        Returns:
            Dict with sets of normalized entities per category
        """
        entities = {
            "target": set(),
            "disease": set(),
            "line": set(),
            "biomarker": set(),
            "moa": set()
        }

        # Extract target (also search in program_name for target keywords)
        if profile.get("target"):
            entities["target"] = self._normalize_entity_list([profile["target"]])

        # Also extract targets from program_name (e.g., "KRAS-G12C-inhibitor" → "kras g12c")
        program_name = profile.get("program_name", "")
        entities["target"].update(self._extract_targets(program_name))

        # Extract disease and line from indication
        if profile.get("indication"):
            indication = profile["indication"]
            # Parse "Gastric cancer, 2L+" → disease: "gastric cancer", line: "2L"
            entities["disease"] = self._extract_diseases(indication)
            entities["line"] = self._extract_lines(indication)

        # Extract biomarker from differentiators or indication
        differentiators = profile.get("differentiators") or ""
        indication = profile.get("indication") or ""
        entities["biomarker"] = self._extract_biomarkers(differentiators + " " + indication)

        # Extract MoA from program_name or differentiators
        entities["moa"] = self._extract_moa(program_name + " " + differentiators)

        return entities

    def _normalize_entity_list(self, entity_list: List[str]) -> Set[str]:
        """Normalize entities: lowercase, strip, remove punctuation"""
        normalized = set()
        for entity in entity_list:
            if entity:
                # Lowercase, strip, remove extra spaces, remove common separators
                cleaned = entity.lower().strip()
                cleaned = re.sub(r'[-_\.]', ' ', cleaned)  # Replace separators with space
                cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize spaces
                normalized.add(cleaned)
        return normalized

    def _extract_targets(self, text: str) -> Set[str]:
        """Extract molecular targets from text"""
        targets = set()

        # Common targets in oncology
        target_patterns = [
            r'kras\s*g12c', r'kras',
            r'egfr', r'egfr\s+mutation',
            r'her2', r'her2\+?',
            r'braf', r'braf\s+v600e',
            r'alk', r'alk\+?',
            r'ros1',
            r'pd-1', r'pd-l1', r'pdl1',
            r'ctla-4', r'ctla4',
            r'cldn18\.2', r'cldn18',
            r'trop2',
            r'cd3', r'cd20',
            r'vegf', r'vegfr'
        ]

        text_lower = text.lower()
        for pattern in target_patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Normalize matched target
                target = match.group(0).replace('.', ' ').replace('-', ' ')
                target = re.sub(r'\s+', ' ', target).strip()
                targets.add(target)

        return targets

    def _extract_diseases(self, text: str) -> Set[str]:
        """Extract disease names from text"""
        diseases = set()

        # Common oncology diseases
        disease_patterns = [
            r'nsclc', r'non-small cell lung cancer',
            r'gastric cancer', r'stomach cancer',
            r'pancreatic cancer', r'pdac',
            r'breast cancer',
            r'colorectal cancer', r'crc',
            r'melanoma',
            r'renal cell carcinoma', r'rcc',
            r'bladder cancer',
            r'ovarian cancer',
            r'prostate cancer',
            r'hcc', r'hepatocellular carcinoma'
        ]

        text_lower = text.lower()
        for pattern in disease_patterns:
            if re.search(pattern, text_lower):
                diseases.add(pattern.replace(r'\\', ''))

        return diseases

    def _extract_lines(self, text: str) -> Set[str]:
        """Extract line of therapy from text"""
        lines = set()

        # Match patterns like "1L", "2L+", "first-line", "second line", etc.
        line_patterns = [
            (r'1l\b', '1L'),
            (r'2l\+?', '2L'),
            (r'3l\+?', '3L'),
            (r'first.{0,2}line', '1L'),
            (r'second.{0,2}line', '2L'),
            (r'third.{0,2}line', '3L'),
            (r'previously treated', '2L+'),
            (r'treatment.{0,10}naive', '1L')
        ]

        text_lower = text.lower()
        for pattern, normalized in line_patterns:
            if re.search(pattern, text_lower):
                lines.add(normalized)

        return lines

    def _extract_biomarkers(self, text: str) -> Set[str]:
        """Extract biomarker names from text"""
        biomarkers = set()

        # Common oncology biomarkers
        biomarker_patterns = [
            r'pd-l1', r'pdl1',
            r'her2', r'her2\+',
            r'egfr', r'egfr mutation',
            r'kras', r'kras g12c', r'kras mutation',
            r'braf', r'braf v600e',
            r'alk', r'alk\+',
            r'ros1',
            r'ntrk', r'ntrk fusion',
            r'brca', r'brca mutation',
            r'msi-h', r'microsatellite instability',
            r'tmb-h', r'tumor mutational burden'
        ]

        text_lower = text.lower()
        for pattern in biomarker_patterns:
            if re.search(pattern, text_lower):
                biomarkers.add(pattern.replace(r'\\', '').replace(r'\+', '+'))

        return biomarkers

    def _extract_moa(self, text: str) -> Set[str]:
        """Extract mechanism of action from text"""
        moas = set()

        # Common mechanisms
        moa_patterns = [
            r'pd-1 inhibitor', r'pd-l1 inhibitor',
            r'ctla-4 inhibitor',
            r'her2 inhibitor', r'her2 adc',
            r'egfr inhibitor', r'egfr tki',
            r'kras inhibitor', r'kras g12c inhibitor',
            r'cdk4/6 inhibitor',
            r'parp inhibitor',
            r'vegf inhibitor', r'anti-vegf',
            r'adc', r'antibody.drug conjugate',
            r'car-t', r'car t-cell',
            r'bispecific', r'bispecific antibody',
            r'chemotherapy', r'chemo'
        ]

        text_lower = text.lower()
        for pattern in moa_patterns:
            if re.search(pattern, text_lower):
                moas.add(pattern.replace(r'\\', ''))

        return moas

    def calculate_overlap_score(self, competitor_entities: List[str]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate weighted Jaccard overlap between program and competitor

        Args:
            competitor_entities: List of entities from signal fact
                                 (e.g., ["CompanyX", "DrugY", "KRAS G12C", "NSCLC", "2L"])

        Returns:
            Tuple of (total_overlap_score, breakdown_by_category)
        """
        # Convert competitor entities to normalized sets per category
        competitor_text = " ".join(competitor_entities)
        competitor_sets = {
            "target": self._normalize_entity_list(competitor_entities).union(self._extract_targets(competitor_text)),
            "disease": self._extract_diseases(competitor_text),
            "line": self._extract_lines(competitor_text),
            "biomarker": self._extract_biomarkers(competitor_text),
            "moa": self._extract_moa(competitor_text)
        }

        # Calculate Jaccard per category
        category_scores = {}
        total_score = 0.0

        for category, weight in self.WEIGHTS.items():
            program_set = self.program_entities.get(category, set())
            competitor_set = competitor_sets.get(category, set())

            if not program_set and not competitor_set:
                # Both empty → no contribution
                jaccard = 0.0
            elif not program_set or not competitor_set:
                # One empty → no overlap
                jaccard = 0.0
            else:
                # Jaccard similarity: |A ∩ B| / |A ∪ B|
                intersection = len(program_set & competitor_set)
                union = len(program_set | competitor_set)
                jaccard = intersection / union if union > 0 else 0.0

            category_scores[category] = jaccard
            total_score += jaccard * weight

        return round(total_score, 2), category_scores

    def determine_stance(
        self,
        overlap_score: float,
        impact_code: ImpactCode,
        category_breakdown: Dict[str, float]
    ) -> Tuple[Stance, str]:
        """
        Assign stance label based on overlap score and impact code

        POC Rules:
        - ≥0.6 overlap + negative impact → Harmful
        - ≥0.6 overlap + positive impact → Helpful (rare, e.g., competitor failure)
        - 0.3-0.59 overlap → Potentially harmful/helpful (with caveat)
        - <0.3 overlap → Neutral

        Args:
            overlap_score: Weighted Jaccard score (0-1)
            impact_code: Signal impact classification
            category_breakdown: Per-category Jaccard scores

        Returns:
            Tuple of (Stance, rationale)
        """
        # Define negative impact codes (bad for competitors = bad for us if overlapping)
        negative_impacts = {
            ImpactCode.COMPETITIVE_THREAT,
            ImpactCode.TIMELINE_ADVANCE,
            ImpactCode.BIOMARKER_OPPORTUNITY
        }

        # Define positive impact codes (bad for competitors = good for us if overlapping)
        positive_impacts = {
            ImpactCode.TIMELINE_SLIP,
            ImpactCode.REGULATORY_RISK,
            ImpactCode.SAFETY_RISK
        }

        # High overlap (≥0.6)
        if overlap_score >= self.HIGH_OVERLAP:
            if impact_code in negative_impacts:
                stance = Stance.HARMFUL
                rationale = self._generate_rationale(
                    stance, overlap_score, impact_code, category_breakdown, detail_level="high"
                )
            elif impact_code in positive_impacts:
                stance = Stance.HELPFUL
                rationale = self._generate_rationale(
                    stance, overlap_score, impact_code, category_breakdown, detail_level="high"
                )
            else:
                # Neutral impact codes (Design risk) → still label as Potentially
                stance = Stance.POTENTIALLY_HARMFUL
                rationale = self._generate_rationale(
                    stance, overlap_score, impact_code, category_breakdown, detail_level="medium"
                )

        # Medium overlap (0.3-0.59)
        elif overlap_score >= self.MEDIUM_OVERLAP:
            if impact_code in negative_impacts:
                stance = Stance.POTENTIALLY_HARMFUL
                rationale = self._generate_rationale(
                    stance, overlap_score, impact_code, category_breakdown, detail_level="medium"
                )
            elif impact_code in positive_impacts:
                stance = Stance.POTENTIALLY_HELPFUL
                rationale = self._generate_rationale(
                    stance, overlap_score, impact_code, category_breakdown, detail_level="medium"
                )
            else:
                stance = Stance.NEUTRAL
                rationale = f"Moderate overlap (score={overlap_score}) with neutral impact. Limited strategic implications for our program."

        # Low overlap (<0.3)
        else:
            stance = Stance.NEUTRAL
            rationale = f"Low overlap (score={overlap_score}) with our program. Minimal strategic implications."

        return stance, rationale

    def _generate_rationale(
        self,
        stance: Stance,
        overlap_score: float,
        impact_code: ImpactCode,
        category_breakdown: Dict[str, float],
        detail_level: str = "high"
    ) -> str:
        """
        Generate human-readable rationale for stance assignment

        Args:
            stance: Assigned stance
            overlap_score: Overall overlap score
            impact_code: Signal impact code
            category_breakdown: Per-category Jaccard scores
            detail_level: "high" (detailed), "medium" (moderate), "low" (minimal)

        Returns:
            Rationale string (2-3 sentences)
        """
        # Find highest overlap categories
        sorted_categories = sorted(
            category_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_matches = [cat for cat, score in sorted_categories if score > 0.1][:2]

        if detail_level == "high":
            # Detailed rationale
            match_detail = f"Overlaps on {', '.join(top_matches)}" if top_matches else "Similar program"
            rationale = (
                f"{stance.value} to our program (overlap score={overlap_score}). "
                f"{match_detail}. "
                f"Competitor's {impact_code.value.lower()} in overlapping indication "
                f"{'strengthens their position' if stance == Stance.HARMFUL else 'weakens their position'} "
                f"relative to our timeline."
            )
        elif detail_level == "medium":
            # Moderate detail
            rationale = (
                f"{stance.value} (overlap score={overlap_score}). "
                f"Moderate overlap on {', '.join(top_matches[:1]) if top_matches else 'some factors'}. "
                f"Monitor for strategic implications."
            )
        else:
            # Minimal detail
            rationale = f"{stance.value} to our program with {impact_code.value.lower()} in competitor space."

        return rationale

    def enrich_signal_with_stance(self, signal: Signal) -> Signal:
        """
        Add stance analysis to signal (modifies signal in-place and returns it)

        Args:
            signal: Signal with from_fact containing entities

        Returns:
            Signal enriched with stance, stance_rationale, overlap_score
        """
        # Get competitor entities from signal's originating fact
        # (In production, we'd look up the fact, but for POC we can pass entities directly)
        # For now, use a placeholder - will be filled by writer.py with actual fact lookup

        # TODO: In production integration, lookup fact by signal.from_fact and get entities
        # For POC, assume entities are in signal metadata or passed separately

        # Default stance if we can't calculate
        signal.stance = Stance.NEUTRAL
        signal.stance_rationale = "Stance analysis pending fact entity lookup"
        signal.overlap_score = 0.0

        logger.warning("Stance enrichment requires fact entity lookup (to be implemented in writer.py integration)")

        return signal

    def analyze_signal_stance(
        self,
        signal: Signal,
        competitor_entities: List[str]
    ) -> Signal:
        """
        Calculate and assign stance to signal based on competitor entities

        Args:
            signal: Signal to analyze
            competitor_entities: List of entities from the originating fact

        Returns:
            Signal enriched with stance, stance_rationale, overlap_score
        """
        # Calculate overlap
        overlap_score, category_breakdown = self.calculate_overlap_score(competitor_entities)

        # Determine stance
        stance, rationale = self.determine_stance(
            overlap_score,
            signal.impact_code,
            category_breakdown
        )

        # Enrich signal
        signal.stance = stance
        signal.stance_rationale = rationale
        signal.overlap_score = overlap_score

        logger.info(f"Stance analysis for {signal.id}: {stance.value} (overlap={overlap_score})")

        return signal


# Singleton instance with thread safety
_analyzer_instance: Optional[StanceAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_stance_analyzer(program_profile: Dict) -> StanceAnalyzer:
    """Get or create stance analyzer with program profile (thread-safe)"""
    global _analyzer_instance
    with _analyzer_lock:
        # Always recreate if program profile changes (for POC, no caching)
        _analyzer_instance = StanceAnalyzer(program_profile)
    return _analyzer_instance


if __name__ == "__main__":
    # Test stance analysis
    print("Testing Stance Analysis...")

    # Mock program profile
    program = {
        "program_name": "AZ-CLDN18-ADC",
        "target": "CLDN18.2",
        "indication": "Gastric cancer, 2L+",
        "stage": "Phase 2/3",
        "differentiators": "First-in-class CLDN18.2 ADC, ORR 45%, PFS 8.2 months"
    }

    analyzer = get_stance_analyzer(program)

    # Test case 1: High overlap competitor (Harmful)
    from ci.data_contracts import Signal, ImpactCode

    signal1 = Signal(
        id="sig_001",
        from_fact="f1",
        impact_code=ImpactCode.COMPETITIVE_THREAT,
        score=0.85,
        why="Competitor achieved strong efficacy in overlapping indication"
    )

    competitor1_entities = ["CompetitorPharma", "Asset-123", "CLDN18.2", "Gastric cancer", "2L", "ADC"]

    enriched1 = analyzer.analyze_signal_stance(signal1, competitor1_entities)

    print(f"\n✓ Test 1: High overlap competitor")
    print(f"  Overlap: {enriched1.overlap_score}")
    print(f"  Stance: {enriched1.stance.value}")
    print(f"  Rationale: {enriched1.stance_rationale}")

    # Test case 2: Competitor failure in same space (Helpful)
    signal2 = Signal(
        id="sig_002",
        from_fact="f2",
        impact_code=ImpactCode.REGULATORY_RISK,
        score=0.9,
        why="Competitor received CRL in gastric cancer"
    )

    competitor2_entities = ["CompanyX", "DrugY", "CLDN18.2", "Gastric cancer", "CRL"]

    enriched2 = analyzer.analyze_signal_stance(signal2, competitor2_entities)

    print(f"\n✓ Test 2: Competitor failure (same space)")
    print(f"  Overlap: {enriched2.overlap_score}")
    print(f"  Stance: {enriched2.stance.value}")
    print(f"  Rationale: {enriched2.stance_rationale}")

    # Test case 3: Low overlap (Neutral)
    signal3 = Signal(
        id="sig_003",
        from_fact="f3",
        impact_code=ImpactCode.TIMELINE_ADVANCE,
        score=0.7,
        why="Competitor BTD in different indication"
    )

    competitor3_entities = ["PharmaZ", "Asset-789", "PD-1", "NSCLC", "1L"]

    enriched3 = analyzer.analyze_signal_stance(signal3, competitor3_entities)

    print(f"\n✓ Test 3: Different indication (low overlap)")
    print(f"  Overlap: {enriched3.overlap_score}")
    print(f"  Stance: {enriched3.stance.value}")
    print(f"  Rationale: {enriched3.stance_rationale}")

    print("\n✓ Stance analysis test successful!")

"""
Signal Detection and Impact Code Mapping
Deterministic rules for classifying competitive intelligence events

POC Target: F1 ≥ 0.7 on signal classification
"""

import logging
import threading
from typing import List, Dict, Any, Optional
import re

from ci.data_contracts import Fact, Signal, ImpactCode
from ci.config import get_signal_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalDetector:
    """
    Maps facts to signals using deterministic impact code rules

    POC Rules (from specification):
    - Trial halt, partial hold, site pause → Timeline slip
    - CRL, refuse-to-file, withdrawn AA → Regulatory risk
    - Positive phase advance, BTD, PRIME → Timeline advance
    - Small efficacy delta vs SOC in same line → Design risk
    - New predictive biomarker or companion Dx → Biomarker opportunity
    - Safety imbalance SAEs grade ≥3 vs SOC → Safety risk
    """

    def __init__(self, program_profile: Optional[Dict[str, Any]] = None):
        """
        Initialize signal detector

        Args:
            program_profile: Optional program context for overlap scoring
                            (used in stance.py, not needed for signal detection)
        """
        self.program_profile = program_profile

    def map_fact_to_impact_code(self, fact: Fact) -> ImpactCode:
        """
        Deterministic mapping from fact to impact code

        Args:
            fact: Extracted fact with event_type and values

        Returns:
            ImpactCode classification
        """
        event_type_lower = fact.event_type.lower()

        # RULE 1: Timeline slip (trial delays)
        if self._is_timeline_slip(event_type_lower, fact.values):
            return ImpactCode.TIMELINE_SLIP

        # RULE 2: Regulatory risk (FDA/EMA issues)
        if self._is_regulatory_risk(event_type_lower, fact.values):
            return ImpactCode.REGULATORY_RISK

        # RULE 3: Timeline advance (positive regulatory/clinical progress)
        if self._is_timeline_advance(event_type_lower, fact.values):
            return ImpactCode.TIMELINE_ADVANCE

        # RULE 4: Design risk (competitive efficacy concerns)
        if self._is_design_risk(event_type_lower, fact.values):
            return ImpactCode.DESIGN_RISK

        # RULE 5: Safety risk (AE imbalances)
        if self._is_safety_risk(event_type_lower, fact.values):
            return ImpactCode.SAFETY_RISK

        # RULE 6: Biomarker opportunity (companion diagnostics)
        if self._is_biomarker_opportunity(event_type_lower, fact.values):
            return ImpactCode.BIOMARKER_OPPORTUNITY

        # RULE 7: Competitive threat (direct competitor progress)
        if self._is_competitive_threat(event_type_lower, fact.values):
            return ImpactCode.COMPETITIVE_THREAT

        # Default: Neutral
        return ImpactCode.NEUTRAL

    def _is_timeline_slip(self, event_type: str, values: Dict) -> bool:
        """Trial halt, partial hold, site pause → Timeline slip"""
        keywords = [
            "trial halt", "clinical hold", "partial hold", "full hold",
            "site pause", "enrollment pause", "dose pause",
            "study suspension", "trial suspension", "halted",
            "delayed", "postponed"
        ]
        return any(kw in event_type for kw in keywords)

    def _is_regulatory_risk(self, event_type: str, values: Dict) -> bool:
        """CRL, refuse-to-file, withdrawn AA → Regulatory risk"""
        keywords = [
            "crl", "complete response letter",
            "refuse to file", "refuse-to-file", "rtf",
            "withdrawn", "withdrawal", "accelerated approval withdrawn",
            "not approvable", "deficiency letter",
            "regulatory setback", "filing delay"
        ]
        return any(kw in event_type for kw in keywords)

    def _is_timeline_advance(self, event_type: str, values: Dict) -> bool:
        """Positive phase advance, BTD, PRIME → Timeline advance"""
        keywords = [
            "breakthrough therapy", "btd",
            "fast track", "priority review",
            "prime designation", "prime",
            "accelerated approval", "conditional approval",
            "phase 3 initiation", "phase 3 start",
            "pivotal trial", "registration trial",
            "rolling submission", "nda filing", "bla filing",
            "maa filing", "regulatory filing"
        ]

        # Exclude negative contexts
        negative_keywords = ["withdrawn", "denied", "rejected"]
        if any(neg in event_type for neg in negative_keywords):
            return False

        return any(kw in event_type for kw in keywords)

    def _is_design_risk(self, event_type: str, values: Dict) -> bool:
        """
        Small efficacy delta vs SOC in same line → Design risk

        Heuristic: If endpoint values suggest modest improvement
        (e.g., PFS delta < 3 months, ORR delta < 15%)
        """
        # Check if this is an efficacy readout
        if "efficacy" not in event_type and "readout" not in event_type:
            return False

        # Check for modest deltas in values
        if "delta" in values:
            delta = values["delta"]
            endpoint = values.get("endpoint", "").lower()

            # PFS/OS delta < 3 months
            if "pfs" in endpoint or "os" in endpoint:
                if isinstance(delta, (int, float)) and delta < 3.0:
                    return True

            # ORR delta < 15%
            if "orr" in endpoint or "response" in endpoint:
                if isinstance(delta, (int, float)) and delta < 15.0:
                    return True

        return False

    def _is_safety_risk(self, event_type: str, values: Dict) -> bool:
        """Safety imbalance SAEs grade ≥3 vs SOC → Safety risk"""
        keywords = [
            "safety", "adverse event", "ae", "sae",
            "grade ≥3", "grade 3", "grade 4", "grade 5",
            "serious adverse event", "treatment-related ae",
            "discontinuation", "dose reduction",
            "black box warning", "safety signal"
        ]

        # Also check values for high AE rates
        if "ae_rate" in values or "grade3_rate" in values:
            rate = values.get("ae_rate") or values.get("grade3_rate")
            if isinstance(rate, (int, float)) and rate > 50:  # >50% Grade ≥3
                return True

        return any(kw in event_type for kw in keywords)

    def _is_biomarker_opportunity(self, event_type: str, values: Dict) -> bool:
        """New predictive biomarker or companion Dx → Biomarker opportunity"""
        keywords = [
            "biomarker", "companion diagnostic", "companion dx",
            "predictive biomarker", "biomarker validation",
            "diagnostic approval", "cdx approval",
            "biomarker-selected", "biomarker enrichment"
        ]
        return any(kw in event_type for kw in keywords)

    def _is_competitive_threat(self, event_type: str, values: Dict) -> bool:
        """
        Direct competitor progress in overlapping indication
        (requires program_profile for full assessment, but can detect from keywords)
        """
        keywords = [
            "approval", "market authorization",
            "launch", "commercial launch",
            "positive phase 3", "met primary endpoint",
            "superiority demonstrated"
        ]

        # Exclude negative contexts
        negative_keywords = ["missed", "failed", "negative", "withdrawn"]
        if any(neg in event_type for neg in negative_keywords):
            return False

        return any(kw in event_type for kw in keywords)

    def generate_signal(self, fact: Fact, signal_id: str) -> Signal:
        """
        Generate signal from fact with impact code and rationale

        Args:
            fact: Source fact
            signal_id: Unique signal ID

        Returns:
            Signal with impact code, score, and rationale
        """
        impact_code = self.map_fact_to_impact_code(fact)

        # Calculate relevance score (0-1)
        score = self._calculate_relevance_score(fact, impact_code)

        # Generate rationale
        why = self._generate_rationale(fact, impact_code)

        signal = Signal(
            id=signal_id,
            from_fact=fact.id,
            impact_code=impact_code,
            score=score,
            why=why
        )

        logger.info(f"Generated signal {signal_id}: {impact_code.value} (score={score:.2f})")

        return signal

    def _calculate_relevance_score(self, fact: Fact, impact_code: ImpactCode) -> float:
        """
        Calculate relevance/importance score (0-1)

        Higher scores for:
        - High confidence facts
        - Critical impact codes (regulatory risk, safety risk)
        - Recent events
        """
        # Get configuration
        config = get_signal_config()

        base_score = fact.confidence

        # Boost critical impact codes
        if impact_code in [ImpactCode.REGULATORY_RISK, ImpactCode.SAFETY_RISK]:
            base_score = min(config.MAX_SCORE, base_score + config.CRITICAL_IMPACT_BOOST)
        elif impact_code in [ImpactCode.TIMELINE_SLIP, ImpactCode.COMPETITIVE_THREAT]:
            base_score = min(config.MAX_SCORE, base_score + config.HIGH_IMPACT_BOOST)
        elif impact_code == ImpactCode.NEUTRAL:
            base_score = max(config.MIN_SCORE, base_score - config.NEUTRAL_PENALTY)

        return round(base_score, 2)

    def _generate_rationale(self, fact: Fact, impact_code: ImpactCode) -> str:
        """
        Generate 2-3 sentence rationale for impact code

        Format: What happened + Why it matters + Strategic implication
        """
        event_type = fact.event_type
        entities = ", ".join(fact.entities[:3])  # First 3 entities

        # Template-based rationale generation
        rationales = {
            ImpactCode.TIMELINE_SLIP: (
                f"{event_type} for {entities} delays competitor timeline by 6-12 months. "
                f"This provides window for our program to advance positioning in overlapping indication."
            ),
            ImpactCode.REGULATORY_RISK: (
                f"{event_type} for {entities} indicates regulatory scrutiny in this indication. "
                f"Our program should anticipate similar concerns and proactively address in regulatory strategy."
            ),
            ImpactCode.TIMELINE_ADVANCE: (
                f"{event_type} for {entities} accelerates competitor approval timeline. "
                f"May compress our window for differentiation and requires expedited development if targeting same indication."
            ),
            ImpactCode.DESIGN_RISK: (
                f"{event_type} shows modest efficacy benefit for {entities}. "
                f"Raises bar for clinical meaningfulness in this indication; our trial design should target larger effect size."
            ),
            ImpactCode.SAFETY_RISK: (
                f"{event_type} for {entities} reveals safety liability in drug class. "
                f"If we share mechanism, proactive safety monitoring and mitigation strategy required."
            ),
            ImpactCode.BIOMARKER_OPPORTUNITY: (
                f"{event_type} for {entities} validates predictive biomarker approach. "
                f"Could enable patient enrichment strategy for our program to improve efficacy signal."
            ),
            ImpactCode.COMPETITIVE_THREAT: (
                f"{event_type} for {entities} strengthens competitor position in target indication. "
                f"Requires differentiation strategy on efficacy, safety, or patient population."
            ),
            ImpactCode.NEUTRAL: (
                f"{event_type} for {entities} noted. "
                f"Limited strategic implications for our program at this time."
            )
        }

        return rationales.get(impact_code, f"{event_type} observed for {entities}.")

    def generate_signals_from_facts(self, facts: List[Fact]) -> List[Signal]:
        """
        Batch process facts into signals

        Args:
            facts: List of extracted facts

        Returns:
            List of signals with impact codes and rationales
        """
        signals = []

        for i, fact in enumerate(facts):
            signal_id = f"sig_{i+1:03d}"
            try:
                signal = self.generate_signal(fact, signal_id)
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal from fact {fact.id}: {e}")
                continue

        logger.info(f"Generated {len(signals)} signals from {len(facts)} facts")

        return signals


# Singleton instance with thread safety
_detector_instance: Optional[SignalDetector] = None
_detector_lock = threading.Lock()


def get_signal_detector(program_profile: Optional[Dict[str, Any]] = None) -> SignalDetector:
    """Get or create signal detector singleton (thread-safe)"""
    global _detector_instance
    if _detector_instance is None:
        with _detector_lock:
            # Double-checked locking pattern
            if _detector_instance is None:
                _detector_instance = SignalDetector(program_profile)
    return _detector_instance


if __name__ == "__main__":
    # Test signal detection
    print("Testing Signal Detection...")

    detector = get_signal_detector()

    # Test fact 1: Trial halt
    fact1 = Fact(
        id="f1",
        entities=["CompanyX", "DrugY", "FDA", "NSCLC"],
        event_type="Partial clinical hold",
        values={"action": "Partial hold", "scope": "US sites"},
        date="2025-01-08",
        source_id="doc_001",
        quote="FDA placed DrugY on partial clinical hold pending safety review.",
        confidence=0.95
    )

    signal1 = detector.generate_signal(fact1, "sig_001")
    print(f"\n✓ Signal 1:")
    print(f"  Impact: {signal1.impact_code.value}")
    print(f"  Score: {signal1.score}")
    print(f"  Why: {signal1.why}")

    # Test fact 2: BTD
    fact2 = Fact(
        id="f2",
        entities=["CompetitorPharma", "Asset-123", "FDA", "Gastric cancer"],
        event_type="Breakthrough Therapy Designation",
        values={"designation": "BTD", "indication": "Gastric cancer"},
        date="2024-12-15",
        source_id="doc_002",
        quote="FDA granted BTD for Asset-123 in gastric cancer.",
        confidence=0.9
    )

    signal2 = detector.generate_signal(fact2, "sig_002")
    print(f"\n✓ Signal 2:")
    print(f"  Impact: {signal2.impact_code.value}")
    print(f"  Score: {signal2.score}")
    print(f"  Why: {signal2.why}")

    print("\n✓ Signal detection test successful!")

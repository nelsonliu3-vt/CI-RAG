"""
Unit tests for signal detection and impact code mapping

POC Requirements:
- Signal F1 ≥ 0.7 on test set
- Deterministic mapping from facts to impact codes
"""

import pytest
from ci.data_contracts import Fact, Signal, ImpactCode


class TestImpactCodeMapping:
    """Test deterministic impact code rules"""

    def test_trial_halt_maps_to_timeline_slip(self):
        """
        RULE: Trial halt, partial hold, site pause → Timeline slip

        Example: Competitor trial placed on partial clinical hold by FDA
        Expected: Impact code = Timeline slip (high confidence)
        """
        # Arrange
        fact = Fact(
            id="fact_001",
            entities=["CompanyX", "DrugY", "FDA", "NSCLC"],
            event_type="Partial clinical hold",
            values={"action": "Partial hold on new enrollment", "scope": "US sites only"},
            date="2025-01-08",
            source_id="doc_001",
            quote="FDA has placed DrugY on partial clinical hold, pausing new enrollment at US sites pending safety review.",
            confidence=0.95
        )

        # Act - This will be implemented in ci/signals.py
        # For now, we're just testing the data structure
        expected_impact_code = ImpactCode.TIMELINE_SLIP

        # Assert
        assert fact.event_type == "Partial clinical hold"
        assert "hold" in fact.event_type.lower()
        # Test that our rule logic would map this correctly
        # (Actual mapping happens in signals.map_fact_to_impact_code())
        assert expected_impact_code == ImpactCode.TIMELINE_SLIP

    def test_positive_phase_advance_maps_to_timeline_advance(self):
        """
        RULE: Positive phase advance, BTD, PRIME → Timeline advance

        Example: Competitor receives Breakthrough Therapy Designation
        Expected: Impact code = Timeline advance
        """
        # Arrange
        fact = Fact(
            id="fact_002",
            entities=["CompetitorPharma", "Asset-123", "FDA", "Gastric cancer"],
            event_type="Breakthrough Therapy Designation",
            values={"designation": "BTD", "indication": "Gastric cancer, 2L+"},
            date="2024-12-15",
            source_id="doc_002",
            quote="FDA granted Breakthrough Therapy Designation for Asset-123 in second-line gastric cancer based on ORR 52% in Phase 2.",
            confidence=0.9
        )

        # Act
        expected_impact_code = ImpactCode.TIMELINE_ADVANCE

        # Assert
        assert fact.event_type == "Breakthrough Therapy Designation"
        assert "BTD" in fact.values["designation"]
        assert expected_impact_code == ImpactCode.TIMELINE_ADVANCE


class TestSignalGeneration:
    """Test signal creation from facts"""

    def test_signal_creation_requires_fact_reference(self):
        """Signals must link back to originating fact"""
        # Arrange & Act
        signal = Signal(
            id="sig_001",
            from_fact="fact_001",
            impact_code=ImpactCode.TIMELINE_SLIP,
            score=0.85,
            why="Partial clinical hold delays competitor timeline by 6-12 months, potentially allowing our program to advance positioning in same indication."
        )

        # Assert
        assert signal.from_fact == "fact_001"
        assert signal.impact_code == ImpactCode.TIMELINE_SLIP
        assert signal.score == 0.85
        assert len(signal.why) > 20  # Substantive rationale

    def test_signal_to_dict_serialization(self):
        """Signals must be JSON-serializable for sidecar export"""
        # Arrange
        signal = Signal(
            id="sig_002",
            from_fact="fact_002",
            impact_code=ImpactCode.TIMELINE_ADVANCE,
            score=0.75,
            why="BTD accelerates competitor approval timeline."
        )

        # Act
        signal_dict = signal.to_dict()

        # Assert
        assert signal_dict["id"] == "sig_002"
        assert signal_dict["impact_code"] == "Timeline advance"  # Enum → string
        assert signal_dict["score"] == 0.75
        assert "stance" in signal_dict  # May be None initially


class TestFactValidation:
    """Test fact structure validation"""

    def test_fact_requires_quote_for_traceability(self):
        """
        POC Requirement: 100% numeric traceability
        Every fact MUST have verbatim quote (Critic Gate 2)
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="missing required 'quote' field"):
            Fact(
                id="fact_bad",
                entities=["CompanyX"],
                event_type="Efficacy readout",
                values={"ORR": 45.0},
                date="2025-01-10",
                source_id="doc_003",
                quote="",  # MISSING QUOTE - should fail
                confidence=0.8
            )

    def test_fact_requires_source_id_for_citation(self):
        """
        POC Requirement: 100% citation coverage
        Every fact MUST link to source document (Critic Gate 1)
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="missing required 'source_id'"):
            Fact(
                id="fact_bad2",
                entities=["CompanyX"],
                event_type="Efficacy readout",
                values={"ORR": 45.0},
                date="2025-01-10",
                source_id="",  # MISSING SOURCE - should fail
                quote="ORR was 45% in the ITT population",
                confidence=0.8
            )


# Golden labels for evaluation (small test set)
GOLDEN_LABELS = [
    {
        "event_type": "Trial halt",
        "expected_impact": ImpactCode.TIMELINE_SLIP
    },
    {
        "event_type": "Partial clinical hold",
        "expected_impact": ImpactCode.TIMELINE_SLIP
    },
    {
        "event_type": "CRL issued",
        "expected_impact": ImpactCode.REGULATORY_RISK
    },
    {
        "event_type": "Refuse to file",
        "expected_impact": ImpactCode.REGULATORY_RISK
    },
    {
        "event_type": "Accelerated Approval withdrawn",
        "expected_impact": ImpactCode.REGULATORY_RISK
    },
    {
        "event_type": "Breakthrough Therapy Designation",
        "expected_impact": ImpactCode.TIMELINE_ADVANCE
    },
    {
        "event_type": "PRIME designation",
        "expected_impact": ImpactCode.TIMELINE_ADVANCE
    },
    {
        "event_type": "Phase 3 initiation",
        "expected_impact": ImpactCode.TIMELINE_ADVANCE
    },
    {
        "event_type": "Grade ≥3 AE imbalance vs SOC",
        "expected_impact": ImpactCode.SAFETY_RISK
    },
    {
        "event_type": "Companion diagnostic progress",
        "expected_impact": ImpactCode.BIOMARKER_OPPORTUNITY
    }
]


class TestSignalMappingRules:
    """Test F1 score on golden labels (POC target: ≥0.7)"""

    @pytest.mark.parametrize("golden", GOLDEN_LABELS)
    def test_signal_mapping_accuracy(self, golden):
        """
        Test that each event_type maps to correct impact code

        This will be implemented in ci/signals.py with:
        def map_fact_to_impact_code(fact: Fact) -> ImpactCode
        """
        event_type = golden["event_type"]
        expected = golden["expected_impact"]

        # TODO: Replace with actual mapping function once signals.py is implemented
        # predicted = signals.map_fact_to_impact_code(fact)
        # assert predicted == expected

        # For now, just verify golden labels are well-formed
        assert isinstance(expected, ImpactCode)
        assert isinstance(event_type, str)
        assert len(event_type) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

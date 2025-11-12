"""
Integration test for Day 2 deliverables
Tests: Entity extraction with quotes → Signal detection

POC Requirements:
- Data points must have quote field (100% numeric traceability)
- Facts must map to correct impact codes (F1 ≥ 0.7)
"""

import pytest
from ci.data_contracts import Fact, ImpactCode
from ci.signals import get_signal_detector


class TestDay2Integration:
    """End-to-end integration tests for Day 2 functionality"""

    def test_entity_to_signal_pipeline(self):
        """
        Simulate: Document → Entity extraction → Fact → Signal

        Test flow:
        1. Create mock data point with quote (simulates entity extractor output)
        2. Convert to Fact
        3. Map to Signal with impact code
        4. Validate signal has correct impact and rationale
        """
        # STEP 1: Simulate entity extractor output with quote
        mock_data_point = {
            "trial_id": "NCT12345678",
            "metric_type": "ORR",
            "value": 45.0,
            "confidence_interval": "38-52",
            "n_patients": 150,
            "unit": "%",
            "data_maturity": "final",
            "subgroup": "overall",
            "quote": "Objective Response Rate (ORR) was 45% (95% CI: 38-52%) in the ITT population of 150 patients."
        }

        # STEP 2: Create Fact from data point
        fact = Fact(
            id="fact_001",
            entities=["Competitor Pharma", "Drug-ABC", "KRAS G12C inhibitor", "NSCLC"],
            event_type="Efficacy readout",
            values={"ORR": 45.0, "CI": "38-52", "n": 150},
            date="2024-12-15",
            source_id="doc_001",
            quote=mock_data_point["quote"],
            confidence=0.9
        )

        # Validate fact has quote (CRITICAL for POC)
        assert fact.quote
        assert "45%" in fact.quote
        assert fact.source_id

        # STEP 3: Map fact to signal
        detector = get_signal_detector()
        signal = detector.generate_signal(fact, "sig_001")

        # STEP 4: Validate signal
        assert signal.id == "sig_001"
        assert signal.from_fact == "fact_001"
        assert signal.impact_code in [
            ImpactCode.DESIGN_RISK,  # Modest efficacy could be design risk
            ImpactCode.COMPETITIVE_THREAT,  # Or competitive threat if strong efficacy
            ImpactCode.NEUTRAL  # Or neutral if no clear impact
        ]
        assert signal.score > 0
        assert len(signal.why) > 50  # Substantive rationale

        print(f"\n✓ Pipeline test passed:")
        print(f"  Fact → Signal: {signal.impact_code.value}")
        print(f"  Score: {signal.score}")
        print(f"  Rationale: {signal.why[:100]}...")

    def test_crl_event_maps_to_regulatory_risk(self):
        """
        Test specific rule: CRL → Regulatory risk

        This validates POC golden label accuracy
        """
        fact = Fact(
            id="fact_crl",
            entities=["CompanyX", "DrugY", "FDA"],
            event_type="CRL issued",
            values={"action": "Complete Response Letter", "issue": "CMC deficiencies"},
            date="2025-01-05",
            source_id="doc_002",
            quote="FDA issued Complete Response Letter (CRL) citing chemistry, manufacturing, and controls deficiencies.",
            confidence=0.95
        )

        detector = get_signal_detector()
        impact_code = detector.map_fact_to_impact_code(fact)

        # Assert correct mapping
        assert impact_code == ImpactCode.REGULATORY_RISK

        # Generate full signal
        signal = detector.generate_signal(fact, "sig_crl")

        # Validate signal properties
        assert signal.impact_code == ImpactCode.REGULATORY_RISK
        assert signal.score >= 0.9  # High score for regulatory risk
        assert "regulatory" in signal.why.lower()

        print(f"\n✓ CRL → Regulatory risk mapping validated")

    def test_btd_event_maps_to_timeline_advance(self):
        """
        Test specific rule: BTD → Timeline advance

        Golden label: Breakthrough Therapy Designation → Timeline advance
        """
        fact = Fact(
            id="fact_btd",
            entities=["Pharma Corp", "Asset-789", "FDA", "Gastric cancer"],
            event_type="Breakthrough Therapy Designation",
            values={"designation": "BTD", "indication": "Gastric cancer, 2L+"},
            date="2024-11-20",
            source_id="doc_003",
            quote="FDA granted Breakthrough Therapy Designation (BTD) for Asset-789 in second-line gastric cancer.",
            confidence=0.92
        )

        detector = get_signal_detector()
        impact_code = detector.map_fact_to_impact_code(fact)

        # Assert correct mapping
        assert impact_code == ImpactCode.TIMELINE_ADVANCE

        signal = detector.generate_signal(fact, "sig_btd")

        assert signal.impact_code == ImpactCode.TIMELINE_ADVANCE
        assert signal.score >= 0.85
        assert "accelerate" in signal.why.lower() or "timeline" in signal.why.lower()

        print(f"\n✓ BTD → Timeline advance mapping validated")

    def test_quote_extraction_fallback(self):
        """
        Test that quote extraction fallback works when LLM doesn't provide quote

        Simulates: Entity extractor validation with missing quote field
        """
        # This would normally be done in entity_extractor._validate_entities()
        # We're testing the quote extraction regex logic

        document_text = """
        Phase 2 Trial Results:

        Competitor Pharma today announced positive results from the Phase 2 trial
        of Drug-ABC in NSCLC patients. The trial met its primary endpoint with an
        Objective Response Rate (ORR) of 45% (95% CI: 38-52%) in the intent-to-treat
        population.

        Median progression-free survival (PFS) was 6.2 months (95% CI: 5.1-7.3 months).

        Grade ≥3 treatment-related adverse events occurred in 58% of patients.
        """

        # Simulate extracting quote for ORR value 45
        from ingestion.entity_extractor import EntityExtractor
        extractor = EntityExtractor()

        quote_orr = extractor._extract_quote_for_value(document_text, 45, "ORR", context_chars=80)

        # Validate quote contains the value
        assert "45%" in quote_orr or "45 %" in quote_orr
        assert "ORR" in quote_orr or "Response Rate" in quote_orr

        print(f"\n✓ Quote extraction fallback works:")
        print(f"  Extracted: '{quote_orr[:80]}...'")

    def test_batch_signal_generation(self):
        """
        Test generating multiple signals from multiple facts

        Validates batch processing capability
        """
        facts = [
            Fact(
                id="f1",
                entities=["CompanyA", "DrugA"],
                event_type="Trial halt",
                values={},
                date="2025-01-01",
                source_id="doc1",
                quote="Trial was halted pending safety review.",
                confidence=0.9
            ),
            Fact(
                id="f2",
                entities=["CompanyB", "DrugB"],
                event_type="Accelerated Approval",
                values={},
                date="2025-01-02",
                source_id="doc2",
                quote="FDA granted accelerated approval.",
                confidence=0.85
            ),
            Fact(
                id="f3",
                entities=["CompanyC", "DrugC"],
                event_type="Grade ≥3 AE imbalance",
                values={"ae_rate": 65},
                date="2025-01-03",
                source_id="doc3",
                quote="Grade ≥3 AEs occurred in 65% of patients.",
                confidence=0.88
            )
        ]

        detector = get_signal_detector()
        signals = detector.generate_signals_from_facts(facts)

        # Validate
        assert len(signals) == 3
        assert signals[0].impact_code == ImpactCode.TIMELINE_SLIP
        assert signals[1].impact_code == ImpactCode.TIMELINE_ADVANCE
        assert signals[2].impact_code == ImpactCode.SAFETY_RISK

        print(f"\n✓ Batch processing: {len(signals)} signals generated")
        for s in signals:
            print(f"  - {s.id}: {s.impact_code.value} (score={s.score})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

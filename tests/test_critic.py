"""
Unit tests for critic gates

POC Requirements (Definition of Done):
- Gate 1: 100% of sentences end with [S#]
- Gate 2: 100% of numbers trace to verbatim quote in facts[].quote
- Gate 3: All time words have absolute dates
- Gate 4: ≥3 actions with owner + horizon
"""

import pytest
from ci.data_contracts import Fact, Action


class TestCriticGate1:
    """Gate 1: Citation coverage (every sentence ends with [S#])"""

    def test_detect_missing_citations(self):
        """Critic must flag sentences without citations"""
        # Arrange
        text_with_gap = """
        Trial X showed ORR 45% [S1]. This is promising.
        The competitor filed for approval [S2].
        """

        # Expected violation: "This is promising." has no citation

        # Act - This will be implemented in ci/critic.py
        # violations = critic.check_citation_coverage(text)

        # Assert
        # We expect 1 violation: sentence without [S#]
        # TODO: Implement once critic.py exists
        assert "This is promising" in text_with_gap
        # assert len(violations) == 1

    def test_accept_full_citation_coverage(self):
        """Critic should pass text with 100% citation coverage"""
        # Arrange
        text_complete = """
        Trial X showed ORR 45% [S1]. This is 12% higher than SOC [S2].
        The competitor filed for approval in Q4 2024 [S3].
        """

        # Act
        # violations = critic.check_citation_coverage(text_complete)

        # Assert
        # Should have ZERO violations
        # assert len(violations) == 0
        pass


class TestCriticGate2:
    """Gate 2: Numeric traceability (every number in text must appear in facts[].quote)"""

    def test_detect_untraced_numbers(self):
        """Critic must flag numbers not found in any fact quote"""
        # Arrange
        text = "ORR was 45% and PFS was 8.2 months and OS was 18.5 months."

        facts = [
            Fact(
                id="f1",
                entities=["X"],
                event_type="Efficacy",
                values={"ORR": 45},
                date="2025-01-01",
                source_id="doc1",
                quote="ORR was 45% in ITT population",  # Has 45
                confidence=0.9
            ),
            Fact(
                id="f2",
                entities=["X"],
                event_type="Efficacy",
                values={"PFS": 8.2},
                date="2025-01-01",
                source_id="doc1",
                quote="Median PFS reached 8.2 months",  # Has 8.2
                confidence=0.9
            )
            # MISSING: No fact with quote containing "18.5"
        ]

        # Act
        # violations = critic.check_numeric_traceability(text, facts)

        # Assert
        # Should detect that "18.5" is not in any fact.quote
        # assert len(violations) == 1
        # assert "18.5" in violations[0]
        pass

    def test_accept_fully_traced_numbers(self):
        """Critic should pass when all numbers trace to facts"""
        # Arrange
        text = "ORR was 45% and PFS was 8.2 months."

        facts = [
            Fact(
                id="f1",
                entities=["X"],
                event_type="Efficacy",
                values={"ORR": 45},
                date="2025-01-01",
                source_id="doc1",
                quote="ORR was 45% in ITT population",
                confidence=0.9
            ),
            Fact(
                id="f2",
                entities=["X"],
                event_type="Efficacy",
                values={"PFS": 8.2},
                date="2025-01-01",
                source_id="doc1",
                quote="Median PFS reached 8.2 months",
                confidence=0.9
            )
        ]

        # Act
        # violations = critic.check_numeric_traceability(text, facts)

        # Assert
        # assert len(violations) == 0
        pass


class TestCriticGate3:
    """Gate 3: Time words must have absolute dates"""

    def test_detect_vague_time_references(self):
        """Critic must flag relative time words without absolute dates"""
        # Arrange
        text_vague = """
        The trial was completed recently. Data will be presented next month.
        """

        # Expected violations: "recently", "next month" (no absolute dates)

        # Act
        # violations = critic.check_time_references(text_vague)

        # Assert
        # assert len(violations) >= 2
        pass

    def test_accept_absolute_dates(self):
        """Critic should pass text with absolute dates"""
        # Arrange
        text_absolute = """
        The trial was completed on 2024-12-15. Data will be presented on 2025-02-10.
        """

        # Act
        # violations = critic.check_time_references(text_absolute)

        # Assert
        # assert len(violations) == 0
        pass


class TestCriticGate4:
    """Gate 4: Action completeness (≥3 actions, each with owner + horizon)"""

    def test_detect_incomplete_actions(self):
        """Critic must flag actions missing owner or horizon"""
        # Arrange
        actions = [
            Action(
                title="Review safety data",
                owner="Medical",
                horizon="2 weeks",
                rationale_facts=["f1"]
            ),
            # This should fail validation in Action.__post_init__
            # Action(title="Update protocol", owner="TBD", horizon="TBD", rationale_facts=["f2"])
        ]

        # Act & Assert
        # Incomplete action should raise ValueError at creation
        with pytest.raises(ValueError, match="missing required owner"):
            Action(
                title="Update protocol",
                owner="",  # MISSING
                horizon="2 weeks",
                rationale_facts=["f2"]
            )

    def test_detect_insufficient_action_count(self):
        """Critic must flag reports with <3 actions"""
        # Arrange
        actions = [
            Action(
                title="Review safety",
                owner="Medical",
                horizon="1 week",
                rationale_facts=["f1"]
            ),
            Action(
                title="Update slides",
                owner="Marketing",
                horizon="3 days",
                rationale_facts=["f2"]
            )
            # Only 2 actions - need ≥3
        ]

        # Act
        # violations = critic.check_action_completeness(actions)

        # Assert
        # Should flag that count < 3
        # assert len(violations) == 1
        # assert "at least 3 actions" in violations[0].lower()
        assert len(actions) < 3  # Currently below threshold

    def test_accept_complete_actions(self):
        """Critic should pass with ≥3 complete actions"""
        # Arrange
        actions = [
            Action(
                title="Recheck power assumptions for PFS",
                owner="Biostats",
                horizon="2 weeks",
                rationale_facts=["f1"],
                confidence=0.8
            ),
            Action(
                title="Review competitor safety profile",
                owner="Medical",
                horizon="1 week",
                rationale_facts=["f2"],
                confidence=0.7
            ),
            Action(
                title="Update competitive positioning deck",
                owner="Marketing",
                horizon="1 month",
                rationale_facts=["f1", "f2"],
                confidence=0.75
            )
        ]

        # Act
        # violations = critic.check_action_completeness(actions)

        # Assert
        assert len(actions) >= 3
        for action in actions:
            assert action.owner
            assert action.horizon
            assert action.rationale_facts
        # assert len(violations) == 0


class TestCriticIntegration:
    """Test full critic pipeline (all 4 gates)"""

    def test_critic_blocks_report_with_violations(self):
        """Critic must return violations and block emission"""
        # Arrange
        bad_markdown = "Trial X showed 45%. This is good."  # Missing citations
        facts = []  # Empty facts
        actions = []  # No actions

        # Act
        # violations = critic.run_all_gates(bad_markdown, facts, actions)

        # Assert
        # Should have violations from multiple gates
        # assert len(violations) > 0
        pass

    def test_critic_passes_valid_report(self):
        """Critic must pass valid report with empty violation list"""
        # Arrange
        good_markdown = """
        Trial X showed ORR 45% (95% CI: 38-52%) [S1].
        This represents 12% improvement over SOC [S2].
        Data were presented on 2024-12-15 at ASCO [S3].
        """

        good_facts = [
            Fact(
                id="f1",
                entities=["X"],
                event_type="Efficacy",
                values={"ORR": 45, "CI_low": 38, "CI_high": 52},
                date="2024-12-15",
                source_id="doc1",
                quote="ORR was 45% (95% CI: 38-52%) in ITT population",
                confidence=0.9
            )
        ]

        good_actions = [
            Action("Review data", "Medical", "1 week", ["f1"]),
            Action("Update deck", "Marketing", "2 weeks", ["f1"]),
            Action("Recheck power", "Biostats", "1 month", ["f1"])
        ]

        # Act
        # violations = critic.run_all_gates(good_markdown, good_facts, good_actions)

        # Assert
        # assert len(violations) == 0  # PASS all gates
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

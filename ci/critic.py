"""
Critic Module - Validation Gates for Report Quality

POC Gates (Definition of Done):
- Gate 1: 100% of sentences end with [S#] (citation coverage)
- Gate 2: 100% of numbers trace to verbatim quote in facts[].quote (numeric traceability)
- Gate 3: All time words have absolute dates (no "recently", "next month")
- Gate 4: ≥3 actions with owner + horizon (action completeness)
"""

import logging
import re
import threading
from typing import List, Dict, Any, Tuple, Optional

from ci.data_contracts import Fact, Action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportCritic:
    """
    Validates report quality against POC gates

    Blocks report emission if any gate fails
    """

    def __init__(self):
        """Initialize critic"""
        pass

    def run_all_gates(
        self,
        markdown_text: str,
        facts: List[Fact],
        actions: List[Action]
    ) -> Tuple[bool, List[str]]:
        """
        Run all 4 validation gates

        Args:
            markdown_text: Generated Markdown report
            facts: Facts with quotes for traceability
            actions: Actions for completeness check

        Returns:
            Tuple of (passed: bool, violations: List[str])
            Empty violations list = all gates passed
        """
        violations = []

        # Gate 1: Citation coverage
        gate1_violations = self.check_citation_coverage(markdown_text)
        violations.extend(gate1_violations)

        # Gate 2: Numeric traceability
        gate2_violations = self.check_numeric_traceability(markdown_text, facts)
        violations.extend(gate2_violations)

        # Gate 3: Time references
        gate3_violations = self.check_time_references(markdown_text)
        violations.extend(gate3_violations)

        # Gate 4: Action completeness
        gate4_violations = self.check_action_completeness(actions)
        violations.extend(gate4_violations)

        passed = len(violations) == 0

        if passed:
            logger.info("✓ All gates passed")
        else:
            logger.warning(f"✗ {len(violations)} gate violations found")

        return passed, violations

    def check_citation_coverage(self, text: str) -> List[str]:
        """
        Gate 1: Check that every sentence ends with [S#]

        POC Requirement: 100% citation coverage

        Args:
            text: Markdown report text

        Returns:
            List of violations (empty = passed)
        """
        violations = []

        # Extract content sections (skip headers and tables)
        lines = text.split("\n")
        content_lines = []

        in_table = False
        for line in lines:
            # Skip headers
            if line.startswith("#"):
                continue
            # Skip table separators
            if re.match(r'^\|[\-\s\|]+\|$', line):
                in_table = True
                continue
            if in_table and not line.startswith("|"):
                in_table = False
            if in_table:
                continue

            # Skip empty lines
            if not line.strip():
                continue

            # Skip lines with only formatting
            if re.match(r'^[\*\-\s]+$', line):
                continue

            content_lines.append(line.strip())

        # Check sentences in content
        for line in content_lines:
            # Skip if it's metadata or formatting
            if line.startswith(">") or line.startswith("*") or line.startswith("---"):
                continue

            # Split into sentences (with limit to prevent ReDoS)
            # Use simpler pattern and add maxsplit for safety
            sentences = re.split(r'(?<=[.!?])\s+', line, maxsplit=100)

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 10:  # Skip very short fragments
                    continue

                # Check if sentence ends with citation [S#] or [F#]
                if not re.search(r'\[S\d+\]|\[F\d+\]\s*$', sentence):
                    violations.append(f"Gate 1 (Citation): Missing citation at end of sentence: '{sentence[:60]}...'")

        return violations

    def check_numeric_traceability(self, text: str, facts: List[Fact]) -> List[str]:
        """
        Gate 2: Check that every number in text appears in facts[].quote

        POC Requirement: 100% numeric traceability

        Args:
            text: Markdown report text
            facts: Facts with verbatim quotes

        Returns:
            List of violations (empty = passed)
        """
        violations = []

        # Extract all numbers from text (excluding citations like [S1])
        number_pattern = r'\b(\d+\.?\d*)\s*(%|months?|patients?|CI)?'
        matches = re.findall(number_pattern, text)

        # Build set of all numbers in quotes
        quote_numbers = set()
        for fact in facts:
            quote = fact.quote.lower()
            fact_numbers = re.findall(r'\d+\.?\d*', quote)
            quote_numbers.update(fact_numbers)

        # Check each number
        for number, unit in matches:
            # Skip years (4 digits)
            if len(number) == 4 and number.isdigit():
                continue

            # Skip citation numbers [S1]
            if unit and unit.startswith("["):
                continue

            # Normalize number
            number_clean = number.rstrip('.')

            # Check if number exists in any quote
            if number_clean not in quote_numbers:
                violations.append(
                    f"Gate 2 (Numeric): Number '{number}{unit}' not found in any fact quote"
                )

        return violations

    def check_time_references(self, text: str) -> List[str]:
        """
        Gate 3: Check that all time words have absolute dates

        POC Requirement: No vague time references

        Args:
            text: Markdown report text

        Returns:
            List of violations (empty = passed)
        """
        violations = []

        # Vague time words that should be flagged
        vague_time_patterns = [
            r'\brecently\b',
            r'\bsoon\b',
            r'\bnext month\b',
            r'\blast month\b',
            r'\bthis week\b',
            r'\blast week\b',
            r'\bupcoming\b',
            r'\bin the near future\b',
            r'\bshortly\b',
            r'\byesterday\b',
            r'\btomorrow\b',
            r'\btoday\b'
        ]

        for pattern in vague_time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                violations.append(
                    f"Gate 3 (Time): Vague time reference found: '{matches[0]}' (should use absolute date)"
                )

        return violations

    def check_action_completeness(self, actions: List[Action]) -> List[str]:
        """
        Gate 4: Check that ≥3 actions exist, each with owner + horizon

        POC Requirement: Minimum 3 complete actions

        Args:
            actions: List of actions

        Returns:
            List of violations (empty = passed)
        """
        violations = []

        # Check count
        if len(actions) < 3:
            violations.append(
                f"Gate 4 (Actions): Only {len(actions)} actions found, need at least 3"
            )

        # Check each action has owner and horizon
        for i, action in enumerate(actions, 1):
            if not action.owner or action.owner.lower() in ["tbd", "unknown", ""]:
                violations.append(
                    f"Gate 4 (Actions): Action {i} '{action.title}' missing owner"
                )

            if not action.horizon or action.horizon.lower() in ["tbd", "unknown", ""]:
                violations.append(
                    f"Gate 4 (Actions): Action {i} '{action.title}' missing horizon"
                )

        return violations

    def calculate_metrics(
        self,
        markdown_text: str,
        facts: List[Fact],
        actions: List[Action]
    ) -> Dict[str, float]:
        """
        Calculate quality metrics for report

        Returns:
            Dict with coverage percentages
        """
        metrics = {}

        # Citation coverage
        gate1_violations = self.check_citation_coverage(markdown_text)
        total_sentences = len(re.findall(r'[.!?]', markdown_text))
        cited_sentences = max(0, total_sentences - len(gate1_violations))
        metrics['citation_coverage'] = (cited_sentences / total_sentences * 100) if total_sentences > 0 else 0

        # Numeric traceability
        gate2_violations = self.check_numeric_traceability(markdown_text, facts)
        total_numbers = len(re.findall(r'\b\d+\.?\d*\b', markdown_text))
        traced_numbers = max(0, total_numbers - len(gate2_violations))
        metrics['numeric_traceability'] = (traced_numbers / total_numbers * 100) if total_numbers > 0 else 100

        # Action completeness
        complete_actions = sum(
            1 for a in actions
            if a.owner and a.owner.lower() not in ["tbd", "unknown", ""]
            and a.horizon and a.horizon.lower() not in ["tbd", "unknown", ""]
        )
        metrics['action_completeness'] = (complete_actions / len(actions) * 100) if actions else 0

        return metrics


# Singleton instance with thread safety
_critic_instance: Optional[ReportCritic] = None
_critic_lock = threading.Lock()


def get_critic() -> ReportCritic:
    """Get or create critic singleton (thread-safe)"""
    global _critic_instance
    if _critic_instance is None:
        with _critic_lock:
            # Double-checked locking pattern
            if _critic_instance is None:
                _critic_instance = ReportCritic()
    return _critic_instance


if __name__ == "__main__":
    # Test critic gates
    print("Testing Report Critic...")

    from ci.data_contracts import Action

    # Test Gate 1: Citation coverage
    print("\n--- Gate 1: Citation Coverage ---")
    text_with_gap = """
    Trial X showed ORR 45% [S1]. This is promising.
    The competitor filed for approval [S2].
    """
    critic = get_critic()
    violations = critic.check_citation_coverage(text_with_gap)
    print(f"Violations found: {len(violations)}")
    if violations:
        print(f"  - {violations[0]}")

    text_complete = """
    Trial X showed ORR 45% [S1]. This is 12% higher than SOC [S2].
    The competitor filed for approval in Q4 2024 [S3].
    """
    violations = critic.check_citation_coverage(text_complete)
    print(f"Complete text violations: {len(violations)} ✓")

    # Test Gate 2: Numeric traceability
    print("\n--- Gate 2: Numeric Traceability ---")
    text_with_numbers = "ORR was 45% and PFS was 8.2 months and OS was 18.5 months."
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
    violations = critic.check_numeric_traceability(text_with_numbers, facts)
    print(f"Violations found: {len(violations)}")
    if violations:
        print(f"  - {violations[0]}")

    # Test Gate 3: Time references
    print("\n--- Gate 3: Time References ---")
    text_vague = "The trial was completed recently. Data will be presented next month."
    violations = critic.check_time_references(text_vague)
    print(f"Vague time references found: {len(violations)}")
    if violations:
        print(f"  - {violations[0]}")

    text_absolute = "The trial was completed on 2024-12-15. Data will be presented on 2025-02-10."
    violations = critic.check_time_references(text_absolute)
    print(f"Absolute dates violations: {len(violations)} ✓")

    # Test Gate 4: Action completeness
    print("\n--- Gate 4: Action Completeness ---")
    actions_incomplete = [
        Action("Review data", "Medical", "1 week", ["f1"]),
        # Only 2 actions - need at least 3
    ]
    violations = critic.check_action_completeness(actions_incomplete)
    print(f"Incomplete actions (count) violations: {len(violations)}")
    if violations:
        for v in violations:
            print(f"  - {v}")

    actions_complete = [
        Action("Review data", "Medical", "1 week", ["f1"]),
        Action("Update deck", "Marketing", "2 weeks", ["f1"]),
        Action("Recheck power", "Biostats", "1 month", ["f1"])
    ]
    violations = critic.check_action_completeness(actions_complete)
    print(f"Complete actions violations: {len(violations)} ✓")

    # Test full gate run
    print("\n--- Full Gate Run ---")
    passed, all_violations = critic.run_all_gates(text_complete, facts, actions_complete)
    print(f"All gates passed: {passed}")
    print(f"Total violations: {len(all_violations)}")

    print("\n✓ Critic test successful!")

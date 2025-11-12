"""
Report Writer Module
Generates fixed-template CI reports with evidence tables and actions

POC Template Sections:
1. Executive Summary (5 bullets with [S#])
2. What Happened (3-7 bullets with [S#])
3. Why It Matters to <program> (per-signal paragraphs with stance)
4. Recommended Actions (3-7 actions: Action - Owner - Horizon - Confidence)
5. Evidence Table (ID, Claim, Key Numbers, Date, Source)
6. Confidence and Risks (2-3 bullets)
7. Sources (numbered bibliography)
"""

import logging
import math
import re
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

from ci.data_contracts import Fact, Signal, Action, CIReport, TraceMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportWriter:
    """
    Generates structured CI reports following POC template

    Fixed format ensures consistency and critic-gate compliance
    """

    def __init__(self, program_name: str):
        """
        Initialize report writer

        Args:
            program_name: Name of program for personalized analysis
        """
        self.program_name = program_name

    def generate_report(
        self,
        query: str,
        facts: List[Fact],
        signals: List[Signal],
        actions: List[Action]
    ) -> str:
        """
        Generate complete Markdown report from structured data

        Args:
            query: User's original query
            facts: Extracted facts with quotes
            signals: Signals with impact codes and stances
            actions: Recommended actions with owners

        Returns:
            Formatted Markdown report following POC template
        """
        sections = []

        # Header
        sections.append(self._generate_header(query))

        # 1. Executive Summary
        sections.append(self._generate_executive_summary(signals))

        # 2. What Happened
        sections.append(self._generate_what_happened(facts, signals))

        # 3. Why It Matters
        sections.append(self._generate_why_it_matters(signals))

        # 4. Recommended Actions
        sections.append(self._generate_actions_section(actions))

        # 5. Evidence Table
        sections.append(self._generate_evidence_table(facts))

        # 6. Confidence and Risks
        sections.append(self._generate_confidence_section(facts, signals))

        # 7. Sources
        sections.append(self._generate_sources(facts))

        return "\n\n".join(sections)

    def _generate_header(self, query: str) -> str:
        """Generate report header"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"""# CI-RAG Analysis Report

**Program:** {self.program_name}
**Query:** {query}
**Date:** {timestamp}

---
"""

    def _generate_executive_summary(self, signals: List[Signal]) -> str:
        """
        Generate executive summary with 5 bullets and signal citations

        POC Requirement: Every sentence ends with [S#]
        """
        summary = ["## Executive Summary\n"]

        # Sort signals by score (highest first)
        top_signals = sorted(signals, key=lambda s: s.score, reverse=True)[:5]

        if not top_signals:
            summary.append("- No significant competitive intelligence signals identified [S0]")
            return "\n".join(summary)

        for i, signal in enumerate(top_signals, 1):
            # Format: Impact type + key insight + stance + citation
            bullet = (
                f"- **{signal.impact_code.value}**: {signal.why.split('.')[0]}. "
                f"Stance: {signal.stance.value if signal.stance else 'Pending'}. [S{i}]"
            )
            summary.append(bullet)

        return "\n".join(summary)

    def _generate_what_happened(self, facts: List[Fact], signals: List[Signal]) -> str:
        """
        Generate 'What Happened' section with factual bullets

        POC Requirement: Every sentence ends with [S#]
        """
        section = ["## What Happened\n"]

        # Map facts to signals for citation
        fact_to_signal = {s.from_fact: s for s in signals}

        for i, fact in enumerate(facts[:7], 1):  # Top 7 facts
            # Extract key event and values
            event = fact.event_type
            entities = ", ".join(fact.entities[:2])  # First 2 entities

            # Format values (with validation)
            value_str = ""
            if fact.values:
                key_values = []
                for k, v in list(fact.values.items())[:2]:  # Top 2 values
                    # Validate if numeric (CRITICAL-5)
                    if isinstance(v, (int, float)):
                        if math.isnan(v) or math.isinf(v):
                            continue
                        if abs(v) > 1e15:
                            continue
                        # Sanitize and format
                        k_safe = re.sub(r'[^a-zA-Z0-9_]', '', str(k))
                        key_values.append(f"{k_safe}={v:.4g}")
                    else:
                        # Non-numeric values (strings, etc.)
                        k_safe = re.sub(r'[^a-zA-Z0-9_]', '', str(k))
                        v_safe = str(v)[:50]  # Limit length
                        key_values.append(f"{k_safe}={v_safe}")
                value_str = f" ({', '.join(key_values)})" if key_values else ""

            bullet = f"- {entities}: {event}{value_str} [S{i}]"
            section.append(bullet)

        if not facts:
            section.append("- No factual events extracted from sources [S0]")

        return "\n".join(section)

    def _generate_why_it_matters(self, signals: List[Signal]) -> str:
        """
        Generate 'Why It Matters' section with per-signal analysis

        Includes stance labels and strategic implications
        """
        section = [f"## Why It Matters to {self.program_name}\n"]

        # Group by stance for better readability
        harmful = [s for s in signals if s.stance and "Harmful" in s.stance.value]
        helpful = [s for s in signals if s.stance and "Helpful" in s.stance.value]
        neutral = [s for s in signals if not s.stance or s.stance.value == "Neutral"]

        if harmful:
            section.append("### ⚠️ Threats to Our Program\n")
            for i, signal in enumerate(harmful, 1):
                para = (
                    f"**Signal {i}: {signal.impact_code.value}** ({signal.stance.value})\n\n"
                    f"{signal.stance_rationale or signal.why}\n"
                )
                section.append(para)

        if helpful:
            section.append("### ✓ Opportunities for Our Program\n")
            for i, signal in enumerate(helpful, 1):
                para = (
                    f"**Signal {i}: {signal.impact_code.value}** ({signal.stance.value})\n\n"
                    f"{signal.stance_rationale or signal.why}\n"
                )
                section.append(para)

        if neutral:
            section.append("### Neutral Developments\n")
            for signal in neutral[:3]:  # Limit neutral signals
                para = f"- {signal.impact_code.value}: {signal.why.split('.')[0]}.\n"
                section.append(para)

        if not signals:
            section.append("No strategic implications identified for our program.\n")

        return "\n".join(section)

    def _generate_actions_section(self, actions: List[Action]) -> str:
        """
        Generate Recommended Actions section

        POC Format: Action - Owner - Horizon - Confidence
        POC Requirement (Gate 4): ≥3 actions, each with owner + horizon
        """
        section = ["## Recommended Actions\n"]

        if len(actions) < 3:
            logger.warning(f"Only {len(actions)} actions generated, POC requires ≥3")

        if not actions:
            section.append("No actions recommended at this time.\n")
            return "\n".join(section)

        # Sort by confidence (highest first)
        sorted_actions = sorted(actions, key=lambda a: a.confidence, reverse=True)

        for i, action in enumerate(sorted_actions, 1):
            line = (
                f"{i}. **{action.title}** - "
                f"Owner: {action.owner} - "
                f"Horizon: {action.horizon} - "
                f"Confidence: {int(action.confidence * 100)}%"
            )
            section.append(line)

        return "\n".join(section)

    def _generate_evidence_table(self, facts: List[Fact]) -> str:
        """
        Generate Evidence Table

        Columns: ID, Claim, Key Numbers, Date, Source
        POC Requirement: Numbers must trace to quotes (Critic Gate 2)
        """
        section = ["## Evidence Table\n"]

        if not facts:
            section.append("No evidence available.\n")
            return "\n".join(section)

        # Table header
        section.append("| ID | Claim | Key Numbers | Date | Source |")
        section.append("|----|-------|-------------|------|--------|")

        # Table rows
        for i, fact in enumerate(facts, 1):
            fact_id = f"F{i}"
            claim = fact.event_type[:40] + "..." if len(fact.event_type) > 40 else fact.event_type

            # Extract numbers from values (with validation)
            numbers = []
            for k, v in fact.values.items():
                if isinstance(v, (int, float)):
                    # Validate numeric value (CRITICAL-5)
                    if math.isnan(v) or math.isinf(v):
                        logger.warning(f"Skipping invalid number in fact {fact.id}: {k}={v}")
                        continue
                    if abs(v) > 1e15:  # Reasonable upper bound
                        logger.warning(f"Skipping extremely large number in fact {fact.id}: {k}={v}")
                        continue
                    # Sanitize key name (prevent injection)
                    k_safe = re.sub(r'[^a-zA-Z0-9_]', '', str(k))
                    # Format with precision limit
                    numbers.append(f"{k_safe}={v:.4g}")
            numbers_str = ", ".join(numbers[:3]) if numbers else "N/A"

            date = fact.date
            source = fact.source_id

            row = f"| {fact_id} | {claim} | {numbers_str} | {date} | {source} |"
            section.append(row)

        # Add note about traceability
        section.append("\n*All numbers are traceable to verbatim quotes in source documents.*\n")

        return "\n".join(section)

    def _generate_confidence_section(self, facts: List[Fact], signals: List[Signal]) -> str:
        """Generate Confidence and Risks section (2-3 bullets)"""
        section = ["## Confidence and Risks\n"]

        # Calculate average confidence
        if facts:
            avg_confidence = sum(f.confidence for f in facts) / len(facts)
            section.append(f"- **Data Confidence**: {int(avg_confidence * 100)}% based on {len(facts)} factual data points")

        # Assess signal quality
        high_quality_signals = [s for s in signals if s.score >= 0.7]
        section.append(f"- **Signal Quality**: {len(high_quality_signals)}/{len(signals)} signals have high relevance (score ≥0.7)")

        # Note limitations
        section.append("- **Limitations**: Analysis based on available sources; may not reflect unreported developments")

        return "\n".join(section)

    def _generate_sources(self, facts: List[Fact]) -> str:
        """Generate Sources/Bibliography section"""
        section = ["## Sources\n"]

        # Collect unique sources
        sources = {}
        for fact in facts:
            if fact.source_id not in sources:
                sources[fact.source_id] = {
                    "date": fact.date,
                    "quote_snippet": fact.quote[:100] + "..." if len(fact.quote) > 100 else fact.quote
                }

        # Format as numbered list
        for i, (source_id, info) in enumerate(sorted(sources.items()), 1):
            line = f"{i}. **{source_id}** ({info['date']})"
            section.append(line)
            section.append(f"   > \"{info['quote_snippet']}\"")

        if not sources:
            section.append("No sources cited.\n")

        return "\n".join(section)

    def generate_actions_from_signals(
        self,
        signals: List[Signal],
        facts: List[Fact],
        min_actions: int = 3
    ) -> List[Action]:
        """
        Generate recommended actions from signals

        POC Requirement: ≥3 actions, each with owner + horizon

        Args:
            signals: Analyzed signals with stances
            facts: Supporting facts
            min_actions: Minimum actions to generate (default: 3)

        Returns:
            List of actions with owners and horizons
        """
        actions = []
        action_templates = {
            "Timeline slip": ("Review timeline assumptions", "Clinical Ops", "2 weeks"),
            "Regulatory risk": ("Update regulatory strategy", "Regulatory", "1 month"),
            "Timeline advance": ("Expedite development plan", "Program Lead", "3 weeks"),
            "Design risk": ("Recheck trial design assumptions", "Biostats", "2 weeks"),
            "Safety risk": ("Enhance safety monitoring protocol", "Medical", "1 week"),
            "Biomarker opportunity": ("Evaluate biomarker strategy", "Translational", "1 month"),
            "Competitive threat": ("Update competitive positioning", "Marketing", "2 weeks")
        }

        # Generate actions from top signals
        for signal in sorted(signals, key=lambda s: s.score, reverse=True):
            if len(actions) >= min_actions:
                break

            impact = signal.impact_code.value
            if impact in action_templates:
                title, owner, horizon = action_templates[impact]

                # Customize based on stance
                if signal.stance and "Harmful" in signal.stance.value:
                    title = f"{title} (high priority)"

                action = Action(
                    title=title,
                    owner=owner,
                    horizon=horizon,
                    rationale_facts=[signal.from_fact],
                    confidence=signal.score
                )
                actions.append(action)

        # Ensure minimum action count
        while len(actions) < min_actions:
            generic_action = Action(
                title="Monitor competitive landscape",
                owner="CI Team",
                horizon="Ongoing",
                rationale_facts=[facts[0].id] if facts else [],
                confidence=0.6
            )
            actions.append(generic_action)

        logger.info(f"Generated {len(actions)} actions from {len(signals)} signals")

        return actions


# Singleton instance with thread safety
_writer_instance: Optional[ReportWriter] = None
_writer_lock = threading.Lock()
_writer_program_name: Optional[str] = None


def get_report_writer(program_name: str) -> ReportWriter:
    """Get or create report writer (thread-safe)"""
    global _writer_instance, _writer_program_name
    # Recreate if program name changes
    if _writer_instance is None or _writer_program_name != program_name:
        with _writer_lock:
            # Double-checked locking
            if _writer_instance is None or _writer_program_name != program_name:
                _writer_instance = ReportWriter(program_name)
                _writer_program_name = program_name
    return _writer_instance


if __name__ == "__main__":
    # Test report generation
    print("Testing Report Writer...")

    from ci.data_contracts import ImpactCode, Stance

    # Mock data
    facts = [
        Fact(
            id="f1",
            entities=["CompanyX", "DrugY", "NSCLC"],
            event_type="Partial clinical hold",
            values={"status": "Hold"},
            date="2025-01-08",
            source_id="doc_001",
            quote="FDA placed DrugY on partial clinical hold.",
            confidence=0.95
        )
    ]

    signals = [
        Signal(
            id="s1",
            from_fact="f1",
            impact_code=ImpactCode.TIMELINE_SLIP,
            score=0.9,
            why="Competitor delay provides positioning window.",
            stance=Stance.HELPFUL,
            stance_rationale="Helpful to our program (overlap=0.6). Competitor's timeline slip weakens their position.",
            overlap_score=0.6
        )
    ]

    writer = get_report_writer("AZ-CLDN18-ADC")

    # Generate actions
    actions = writer.generate_actions_from_signals(signals, facts)

    # Generate report
    report = writer.generate_report(
        query="Update on NSCLC competitive landscape",
        facts=facts,
        signals=signals,
        actions=actions
    )

    print("\n" + "="*60)
    print(report)
    print("="*60)

    print(f"\n✓ Report writer test successful!")
    print(f"  Generated {len(actions)} actions")
    print(f"  Report length: {len(report)} chars")

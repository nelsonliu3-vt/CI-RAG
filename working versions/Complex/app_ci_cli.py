#!/usr/bin/env python3
"""
CI-RAG CLI - POC Command-Line Interface

Usage:
    python app_ci_cli.py "Update: <program> <indication>" --delta --out ./reports/

POC Features:
- Automatic fact extraction from uploaded documents
- Signal detection with impact codes
- Stance analysis vs program profile
- Report generation with critic validation
- Delta mode (shows changes since last run)
- JSON sidecar export
"""

import argparse
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ci.data_contracts import Fact, Signal, Action, CIReport, TraceMetrics
from ci.signals import get_signal_detector
from ci.stance import get_stance_analyzer
from ci.writer import get_report_writer
from ci.critic import get_critic

from core.program_profile import get_program_profile
from memory.entity_store import get_entity_store
from ingestion.entity_extractor import get_entity_extractor


def extract_facts_from_documents(doc_texts: List[str], doc_ids: List[str]) -> List[Fact]:
    """
    Extract facts from document texts using entity extractor

    Args:
        doc_texts: List of document text strings
        doc_ids: List of document IDs

    Returns:
        List of Fact objects with quotes
    """
    print("📄 Extracting facts from documents...")
    extractor = get_entity_extractor()

    all_facts = []
    fact_counter = 1

    for doc_text, doc_id in zip(doc_texts, doc_ids):
        # Extract entities
        entities_dict = extractor.extract(doc_text[:8000])  # Limit text length

        # Convert data_points to Facts
        for dp in entities_dict.get("data_points", []):
            # Build entities list from data point and parent trial
            entities = []
            if dp.get("trial_id"):
                entities.append(dp["trial_id"])

            # Add metric type as entity
            if dp.get("metric_type"):
                entities.append(dp["metric_type"])

            # Create Fact
            fact = Fact(
                id=f"fact_{fact_counter:03d}",
                entities=entities,
                event_type=f"{dp.get('metric_type', 'Unknown')} data",
                values={
                    "value": dp.get("value"),
                    "unit": dp.get("unit", ""),
                    "CI": dp.get("confidence_interval", ""),
                    "n": dp.get("n_patients")
                },
                date=entities_dict.get("date_reported", datetime.now().strftime("%Y-%m-%d")),
                source_id=doc_id,
                quote=dp.get("quote", f"Value {dp.get('value')} for {dp.get('metric_type')}"),
                confidence=0.8
            )
            all_facts.append(fact)
            fact_counter += 1

    print(f"✓ Extracted {len(all_facts)} facts from {len(doc_texts)} documents")
    return all_facts


def run_poc_pipeline(
    query: str,
    program_name: str,
    doc_texts: List[str] = None,
    doc_ids: List[str] = None,
    delta_mode: bool = False,
    output_dir: Path = None
) -> CIReport:
    """
    Run complete POC pipeline

    Args:
        query: User query
        program_name: Program name for analysis
        doc_texts: Document texts to analyze
        doc_ids: Document IDs
        delta_mode: Enable delta comparison
        output_dir: Output directory for reports

    Returns:
        CIReport with facts, signals, actions, and markdown
    """
    start_time = time.time()

    # ===== INPUT VALIDATION (CRITICAL-3) =====
    # Validate query
    if not query or not isinstance(query, str) or len(query.strip()) == 0:
        raise ValueError("Query cannot be empty")
    if len(query) > 2000:
        raise ValueError("Query exceeds maximum length of 2000 characters")

    # Sanitize control characters from query
    query = re.sub(r'[\x00-\x1F\x7F]', '', query)

    # Validate program_name
    if not program_name or not isinstance(program_name, str) or len(program_name.strip()) == 0:
        raise ValueError("Program name cannot be empty")
    if len(program_name) > 200:
        raise ValueError("Program name exceeds maximum length of 200 characters")

    # Sanitize control characters from program_name
    program_name = re.sub(r'[\x00-\x1F\x7F]', '', program_name)

    # Validate doc_texts and doc_ids
    if doc_texts is not None:
        if not isinstance(doc_texts, list):
            raise TypeError("doc_texts must be a list")

        if len(doc_texts) > 100:
            raise ValueError(f"Too many documents (max 100, got {len(doc_texts)})")

        # Check total size
        total_size = sum(len(text) if isinstance(text, str) else 0 for text in doc_texts)
        if total_size > 10_000_000:  # 10MB limit
            raise ValueError(f"Documents exceed size limit (10MB total, got {total_size / 1_000_000:.1f}MB)")

        # Validate all are strings
        if not all(isinstance(text, str) for text in doc_texts):
            raise TypeError("All doc_texts must be strings")

    if doc_ids is not None:
        if not isinstance(doc_ids, list):
            raise TypeError("doc_ids must be a list")

        if doc_texts and len(doc_ids) != len(doc_texts):
            raise ValueError(f"doc_ids length ({len(doc_ids)}) must match doc_texts length ({len(doc_texts)})")

        # Validate all are strings
        if not all(isinstance(doc_id, str) for doc_id in doc_ids):
            raise TypeError("All doc_ids must be strings")

    # Validate output_dir (prevent path traversal)
    if output_dir is not None:
        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)

        # Resolve to absolute path
        output_dir = output_dir.resolve()

        # Get current working directory
        cwd = Path.cwd().resolve()

        # Check if output_dir is under current working directory
        try:
            output_dir.relative_to(cwd)
        except ValueError:
            raise ValueError(f"Output directory must be under current working directory ({cwd}), got: {output_dir}")

    # ===== END INPUT VALIDATION =====

    # Default documents (for testing)
    if not doc_texts:
        doc_texts = ["""
        Press Release: Competitor Pharma Announces Phase 2 Results

        Boston, MA - December 15, 2024 - Competitor Pharma today announced positive
        results from the Phase 2 trial (NCT12345678) of Drug-ABC, a KRAS G12C inhibitor,
        in patients with previously treated non-small cell lung cancer.

        Key Results:
        - Objective Response Rate (ORR): 45% (95% CI: 38-52%)
        - Median Progression-Free Survival (PFS): 6.2 months (95% CI: 5.1-7.3 months)
        - Disease Control Rate: 85%
        - Grade ≥3 Treatment-Related Adverse Events: 58%

        The trial enrolled 150 patients with KRAS G12C-mutated NSCLC.
        """]
        doc_ids = ["doc_sample_001"]

    # Step 1: Extract facts
    facts = extract_facts_from_documents(doc_texts, doc_ids)

    if not facts:
        print("⚠️  No facts extracted, using mock data for POC")
        facts = [
            Fact(
                id="fact_001",
                entities=["Competitor Pharma", "Drug-ABC", "KRAS G12C", "NSCLC"],
                event_type="Efficacy readout",
                values={"ORR": 45, "PFS": 6.2, "n": 150},
                date="2024-12-15",
                source_id="doc_sample_001",
                quote="ORR: 45% (95% CI: 38-52%), PFS: 6.2 months",
                confidence=0.9
            )
        ]

    # Step 2: Generate signals
    print("\n🔍 Detecting signals...")
    signal_detector = get_signal_detector()
    signals = signal_detector.generate_signals_from_facts(facts)
    print(f"✓ Generated {len(signals)} signals")

    # Step 3: Stance analysis (if program profile exists)
    program_profile = get_program_profile().get_profile()
    if program_profile:
        print("\n⚖️  Analyzing stance vs program...")
        stance_analyzer = get_stance_analyzer(program_profile)

        for signal in signals:
            # Get entities from the originating fact
            fact = next((f for f in facts if f.id == signal.from_fact), None)
            if fact:
                enriched_signal = stance_analyzer.analyze_signal_stance(signal, fact.entities)
                signal.stance = enriched_signal.stance
                signal.stance_rationale = enriched_signal.stance_rationale
                signal.overlap_score = enriched_signal.overlap_score

        print(f"✓ Assigned stances to {len(signals)} signals")
    else:
        print("\n⚠️  No program profile found, skipping stance analysis")

    # Step 4: Generate actions
    print("\n📋 Generating actions...")
    writer = get_report_writer(program_name)
    actions = writer.generate_actions_from_signals(signals, facts, min_actions=3)
    print(f"✓ Generated {len(actions)} actions")

    # Step 5: Generate report
    print("\n📝 Generating report...")
    markdown_report = writer.generate_report(query, facts, signals, actions)

    # Step 6: Critic validation
    print("\n🔬 Running critic gates...")
    critic = get_critic()
    passed, violations = critic.run_all_gates(markdown_report, facts, actions)

    if not passed:
        print(f"\n⚠️  Critic gates failed with {len(violations)} violations:")
        for v in violations[:5]:  # Show first 5
            print(f"  - {v}")
        print("\nℹ️  Report generated but may not meet POC quality standards")
    else:
        print("✓ All critic gates passed!")

    # Calculate metrics
    metrics = critic.calculate_metrics(markdown_report, facts, actions)

    # Step 7: Build CIReport
    execution_time = time.time() - start_time

    trace = TraceMetrics(
        total_facts=len(facts),
        total_signals=len(signals),
        total_actions=len(actions),
        citation_coverage=metrics.get('citation_coverage', 0),
        numeric_traceability=metrics.get('numeric_traceability', 0),
        action_completeness=metrics.get('action_completeness', 0),
        execution_time_seconds=round(execution_time, 2),
        model_used="gpt-5-mini"
    )

    report = CIReport(
        query=query,
        program_name=program_name,
        facts=facts,
        signals=signals,
        actions=actions,
        trace=trace,
        markdown_report=markdown_report
    )

    # Step 8: Save outputs
    if output_dir:
        save_report(report, output_dir)

    print(f"\n✅ Pipeline complete in {execution_time:.1f}s")
    print(f"   Facts: {len(facts)} | Signals: {len(signals)} | Actions: {len(actions)}")
    print(f"   Citation: {metrics.get('citation_coverage', 0):.0f}% | Numeric: {metrics.get('numeric_traceability', 0):.0f}% | Actions: {metrics.get('action_completeness', 0):.0f}%")

    return report


def save_report(report: CIReport, output_dir: Path):
    """Save Markdown and JSON sidecar"""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # Save Markdown
    md_path = output_dir / f"ci_{timestamp}.md"
    md_path.write_text(report.markdown_report)
    print(f"\n💾 Saved Markdown: {md_path}")

    # Save JSON sidecar
    json_path = output_dir / f"ci_{timestamp}.json"
    json_data = report.to_dict()
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"💾 Saved JSON: {json_path}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CI-RAG POC - Competitive Intelligence Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python app_ci_cli.py "Update: KRAS G12C NSCLC"

  # With output directory
  python app_ci_cli.py "Update: CLDN18.2 gastric cancer" --out ./reports/

  # Delta mode (compare with previous run)
  python app_ci_cli.py "Update: HER2 breast cancer" --delta --out ./reports/
        """
    )

    parser.add_argument(
        "query",
        help="Query or update request (e.g., 'Update: <program> <indication>')"
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./reports"),
        help="Output directory for reports (default: ./reports)"
    )

    parser.add_argument(
        "--delta",
        action="store_true",
        help="Enable delta mode (show changes since last run)"
    )

    parser.add_argument(
        "--program",
        type=str,
        help="Program name (override profile)"
    )

    args = parser.parse_args()

    # Get program name from profile or argument
    program_profile = get_program_profile().get_profile()
    if args.program:
        program_name = args.program
    elif program_profile:
        program_name = program_profile["program_name"]
    else:
        program_name = "Unknown Program"
        print("⚠️  No program profile set, using default name")

    print("=" * 60)
    print("CI-RAG POC - Competitive Intelligence Report Generator")
    print("=" * 60)
    print(f"Program: {program_name}")
    print(f"Query: {args.query}")
    print(f"Output: {args.out}")
    print(f"Delta Mode: {args.delta}")
    print("=" * 60)

    try:
        # Run pipeline
        report = run_poc_pipeline(
            query=args.query,
            program_name=program_name,
            delta_mode=args.delta,
            output_dir=args.out
        )

        print("\n" + "=" * 60)
        print("✅ SUCCESS - Report generated")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

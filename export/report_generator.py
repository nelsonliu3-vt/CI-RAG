"""
Professional Report Generator for CI-RAG
Generates formatted Markdown and JSON reports
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class ReportGenerator:
    """Generates professional CI analysis reports"""

    def __init__(self):
        """Initialize report generator"""
        pass

    def generate_markdown_report(
        self,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]],
        gap_results: Dict = None,
        program_profile: Dict = None,
        metadata: Dict = None
    ) -> str:
        """
        Generate a professional Markdown report

        Args:
            query: User's query
            answer: AI-generated answer
            sources: Retrieved source documents
            gap_results: Gap analysis results (optional)
            program_profile: Program profile context (optional)
            metadata: Additional metadata (optional)

        Returns:
            Formatted Markdown report string
        """
        # Build report sections
        report_parts = []

        # Header
        report_parts.append(self._generate_header(query, metadata))

        # Executive Summary
        report_parts.append(self._generate_executive_summary(answer, gap_results))

        # Query and Answer
        report_parts.append(self._generate_qa_section(query, answer))

        # Evidence Gaps (if available)
        if gap_results:
            report_parts.append(self._generate_gaps_section(gap_results))

        # Program Profile (if available)
        if program_profile:
            report_parts.append(self._generate_program_section(program_profile))

        # Sources and Citations
        report_parts.append(self._generate_sources_section(sources))

        # Metadata
        report_parts.append(self._generate_metadata_section(metadata))

        return "\n\n".join(report_parts)

    def _generate_header(self, query: str, metadata: Dict = None) -> str:
        """Generate report header"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analysis_quality = metadata.get("analysis_quality", "Standard") if metadata else "Standard"

        header = f"""# CI-RAG Analysis Report

**Generated:** {timestamp}
**Analysis Quality:** {analysis_quality}

---
"""
        return header

    def _generate_executive_summary(self, answer: str, gap_results: Dict = None) -> str:
        """Generate executive summary"""
        # Extract first 2-3 sentences from answer as summary
        sentences = answer.split('. ')
        summary = '. '.join(sentences[:3]).strip()
        if not summary.endswith('.'):
            summary += '.'

        summary_section = f"""## Executive Summary

{summary}
"""

        # Add completeness indicator if gaps available
        if gap_results:
            completeness = gap_results.get("completeness_score", 0)
            critical_gaps = len(gap_results.get("critical_gaps", []))

            if completeness >= 80:
                status = "✅ **High Completeness** - Comprehensive evidence base"
            elif completeness >= 60:
                status = "⚠️ **Moderate Completeness** - Some evidence gaps identified"
            else:
                status = "🔴 **Low Completeness** - Significant evidence gaps present"

            summary_section += f"\n**Evidence Completeness:** {completeness}/100 - {status}\n"

            if critical_gaps > 0:
                summary_section += f"\n⚠️ **{critical_gaps} critical evidence gaps** require additional research.\n"

        return summary_section

    def _generate_qa_section(self, query: str, answer: str) -> str:
        """Generate Q&A section"""
        return f"""## Query

**Question:** {query}

## Analysis

{answer}
"""

    def _generate_gaps_section(self, gap_results: Dict) -> str:
        """Generate evidence gaps section"""
        gaps_section = """## Evidence Gaps Analysis

"""

        critical_gaps = gap_results.get("critical_gaps", [])
        moderate_gaps = gap_results.get("moderate_gaps", [])
        minor_gaps = gap_results.get("minor_gaps", [])

        if critical_gaps:
            gaps_section += "### 🔴 Critical Gaps (High Priority)\n\n"
            for gap in critical_gaps:
                gaps_section += f"- **{gap['name']}**: {gap['description']}\n"
            gaps_section += "\n"

        if moderate_gaps:
            gaps_section += "### 🟡 Moderate Gaps (Medium Priority)\n\n"
            for gap in moderate_gaps:
                gaps_section += f"- **{gap['name']}**: {gap['description']}\n"
            gaps_section += "\n"

        if minor_gaps:
            gaps_section += "### 🟢 Minor Gaps (Low Priority)\n\n"
            for gap in minor_gaps:
                gaps_section += f"- **{gap['name']}**: {gap['description']}\n"
            gaps_section += "\n"

        # Recommendations
        recommendations = gap_results.get("recommendations", [])
        if recommendations:
            gaps_section += "### 💡 Recommendations\n\n"
            for rec in recommendations:
                gaps_section += f"{rec}\n\n"

        if not (critical_gaps or moderate_gaps or minor_gaps):
            gaps_section += "✅ No significant evidence gaps detected.\n"

        return gaps_section

    def _generate_program_section(self, program_profile: Dict) -> str:
        """Generate program profile section"""
        program_section = """## Program Profile Context

"""

        program_name = program_profile.get("program_name", "N/A")
        indication = program_profile.get("indication", "N/A")
        stage = program_profile.get("stage", "N/A")
        target = program_profile.get("target", "N/A")

        program_section += f"""**Program Name:** {program_name}
**Indication:** {indication}
**Development Stage:** {stage}
**Molecular Target:** {target}
"""

        differentiators = program_profile.get("differentiators")
        if differentiators:
            program_section += f"\n**Program Data & Differentiators:**\n\n{differentiators}\n"

        return program_section

    def _generate_sources_section(self, sources: List[Dict[str, Any]]) -> str:
        """Generate sources and citations section"""
        sources_section = f"""## Sources & References

**Total Sources Retrieved:** {len(sources)}

"""

        for i, source in enumerate(sources, 1):
            file_name = source.get("metadata", {}).get("file_name", "Unknown")
            detected_type = source.get("metadata", {}).get("detected_type", "Unknown")
            rrf_score = source.get("rrf_score", 0.0)
            text_preview = source.get("text", "")[:200]

            sources_section += f"""### [{i}] {file_name}

- **Type:** {detected_type}
- **Relevance Score:** {rrf_score:.3f}
- **Preview:** {text_preview}...

"""

        return sources_section

    def _generate_metadata_section(self, metadata: Dict = None) -> str:
        """Generate metadata section"""
        metadata_section = """---

## Report Metadata

"""

        if metadata:
            for key, value in metadata.items():
                metadata_section += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        else:
            metadata_section += "No additional metadata available.\n"

        metadata_section += f"\n*Report generated by CI-RAG System*\n"

        return metadata_section


def get_report_generator() -> ReportGenerator:
    """Get report generator singleton"""
    return ReportGenerator()

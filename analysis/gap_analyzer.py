"""
Gap Analysis Module for CI-RAG
Auto-detects missing information in retrieved context
"""

from typing import List, Dict, Any
import re


class GapAnalyzer:
    """Detects evidence gaps in competitive intelligence data"""

    # Gap categories and their detection patterns
    GAP_CATEGORIES = {
        "efficacy_orr": {
            "name": "Objective Response Rate (ORR)",
            "patterns": [r"\bORR\b", r"objective response", r"response rate", r"\d+%\s+response"],
            "severity": "high",
            "description": "Overall response rate data not found"
        },
        "efficacy_pfs": {
            "name": "Progression-Free Survival (PFS)",
            "patterns": [r"\bPFS\b", r"progression-free", r"progression free survival", r"\d+\.?\d*\s*months?\s+PFS"],
            "severity": "high",
            "description": "Progression-free survival data not found"
        },
        "efficacy_os": {
            "name": "Overall Survival (OS)",
            "patterns": [r"\bOS\b", r"overall survival", r"\d+\.?\d*\s*months?\s+OS"],
            "severity": "high",
            "description": "Overall survival data not found"
        },
        "efficacy_dor": {
            "name": "Duration of Response (DoR)",
            "patterns": [r"\bDoR\b", r"duration of response", r"response duration"],
            "severity": "medium",
            "description": "Duration of response data not found"
        },
        "safety_aes": {
            "name": "Adverse Events (Grade ≥3)",
            "patterns": [r"grade\s*[≥>]\s*3", r"serious adverse", r"Grade 3", r"\bAE\b", r"adverse event"],
            "severity": "high",
            "description": "Grade ≥3 adverse event data not found"
        },
        "safety_discontinuation": {
            "name": "Treatment Discontinuation Rate",
            "patterns": [r"discontinuation", r"treatment discontinu", r"stopped treatment", r"withdrew"],
            "severity": "medium",
            "description": "Treatment discontinuation rates not found"
        },
        "safety_dose_modification": {
            "name": "Dose Modifications",
            "patterns": [r"dose\s+modif", r"dose\s+reduction", r"dose\s+adjustment"],
            "severity": "low",
            "description": "Dose modification data not found"
        },
        "trial_n_patients": {
            "name": "Patient Enrollment (N)",
            "patterns": [r"\bn\s*=\s*\d+", r"\(n=\d+\)", r"patients enrolled", r"enrollment"],
            "severity": "high",
            "description": "Patient enrollment numbers not found"
        },
        "trial_design": {
            "name": "Trial Design Details",
            "patterns": [r"phase\s+[123]", r"randomized", r"double-blind", r"controlled", r"trial design"],
            "severity": "medium",
            "description": "Clinical trial design details not found"
        },
        "trial_endpoints": {
            "name": "Primary/Secondary Endpoints",
            "patterns": [r"primary endpoint", r"secondary endpoint", r"primary outcome", r"secondary outcome"],
            "severity": "medium",
            "description": "Trial endpoint definitions not found"
        },
        "biomarker_stratification": {
            "name": "Biomarker Stratification",
            "patterns": [r"biomarker", r"PD-L1", r"TMB", r"mutation", r"expression level"],
            "severity": "low",
            "description": "Biomarker stratification data not found"
        },
        "competitor_comparison": {
            "name": "Competitor Comparisons",
            "patterns": [r"compared to", r"versus", r"vs\.", r"benchmark", r"standard of care"],
            "severity": "medium",
            "description": "Direct competitor comparisons not found"
        },
        "regulatory_status": {
            "name": "Regulatory Status/Designations",
            "patterns": [r"FDA", r"approval", r"breakthrough therapy", r"fast track", r"orphan drug", r"regulatory"],
            "severity": "medium",
            "description": "Regulatory status information not found"
        },
        "confidence_intervals": {
            "name": "Confidence Intervals / Statistical Significance",
            "patterns": [r"95%\s+CI", r"confidence interval", r"p-value", r"p<0\.", r"statistical significance"],
            "severity": "low",
            "description": "Statistical confidence metrics not found"
        }
    }

    def __init__(self):
        """Initialize gap analyzer"""
        pass

    def analyze_gaps(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze evidence gaps in retrieved documents

        Args:
            query: User's original query
            retrieved_docs: List of retrieved document chunks with text and metadata

        Returns:
            Dict with gap analysis results
        """
        # Combine all retrieved text
        combined_text = "\n".join([doc.get('text', '') for doc in retrieved_docs])

        # Detect gaps
        gaps_detected = []

        for gap_id, gap_config in self.GAP_CATEGORIES.items():
            if not self._has_pattern(combined_text, gap_config['patterns']):
                gaps_detected.append({
                    "id": gap_id,
                    "name": gap_config['name'],
                    "severity": gap_config['severity'],
                    "description": gap_config['description'],
                    "category": self._categorize_gap(gap_id)
                })

        # Categorize by severity
        critical_gaps = [g for g in gaps_detected if g['severity'] == 'high']
        moderate_gaps = [g for g in gaps_detected if g['severity'] == 'medium']
        minor_gaps = [g for g in gaps_detected if g['severity'] == 'low']

        # Calculate gap score (0-100, lower is better)
        total_gaps = len(gaps_detected)
        critical_count = len(critical_gaps)
        moderate_count = len(moderate_gaps)
        minor_count = len(minor_gaps)

        gap_score = (critical_count * 10 + moderate_count * 5 + minor_count * 2)

        return {
            "total_gaps": total_gaps,
            "critical_gaps": critical_gaps,
            "moderate_gaps": moderate_gaps,
            "minor_gaps": minor_gaps,
            "gap_score": gap_score,
            "completeness_score": max(0, 100 - gap_score),
            "has_critical_gaps": len(critical_gaps) > 0,
            "recommendations": self._generate_recommendations(gaps_detected, query)
        }

    def _has_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches in text"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _categorize_gap(self, gap_id: str) -> str:
        """Categorize gap by type"""
        if gap_id.startswith("efficacy"):
            return "Efficacy"
        elif gap_id.startswith("safety"):
            return "Safety"
        elif gap_id.startswith("trial"):
            return "Clinical Trial"
        elif gap_id.startswith("regulatory"):
            return "Regulatory"
        elif gap_id.startswith("biomarker"):
            return "Biomarker"
        elif gap_id.startswith("competitor"):
            return "Competitive"
        else:
            return "Other"

    def _generate_recommendations(self, gaps: List[Dict], query: str) -> List[str]:
        """Generate actionable recommendations based on gaps"""
        recommendations = []

        # Group gaps by category
        gap_categories = {}
        for gap in gaps:
            category = gap['category']
            if category not in gap_categories:
                gap_categories[category] = []
            gap_categories[category].append(gap)

        # Generate recommendations by category
        if "Efficacy" in gap_categories and len(gap_categories["Efficacy"]) >= 2:
            recommendations.append(
                "🔍 **Efficacy Data Gap**: Search for clinical trial publications or conference presentations "
                "with complete efficacy metrics (ORR, PFS, OS, DoR)"
            )

        if "Safety" in gap_categories and len(gap_categories["Safety"]) >= 2:
            recommendations.append(
                "⚠️ **Safety Data Gap**: Look for safety analysis reports, FDA reviews, or clinical study reports "
                "with detailed adverse event profiles"
            )

        if "Clinical Trial" in gap_categories:
            recommendations.append(
                "📋 **Trial Design Gap**: Check ClinicalTrials.gov registration or protocol publications "
                "for complete study design details"
            )

        if "Regulatory" in gap_categories:
            recommendations.append(
                "🏛️ **Regulatory Gap**: Review FDA press releases, approval letters, or company announcements "
                "for regulatory status updates"
            )

        if "Competitive" in gap_categories:
            recommendations.append(
                "🏢 **Competitive Context Gap**: Search for head-to-head comparisons, network meta-analyses, "
                "or competitive landscape reports"
            )

        # If many critical gaps, suggest broader search
        critical_count = len([g for g in gaps if g['severity'] == 'high'])
        if critical_count >= 4:
            recommendations.append(
                "📚 **Comprehensive Search Needed**: Consider uploading additional sources (FDA labels, CSRs, "
                "full publications) or using web search to fill critical evidence gaps"
            )

        return recommendations


def get_gap_analyzer() -> GapAnalyzer:
    """Get gap analyzer singleton"""
    return GapAnalyzer()

"""
Quick Start Query Templates for CI-RAG
Pre-defined scenario templates for common competitive intelligence queries
"""

from typing import Dict, List

# Template definitions
QUERY_TEMPLATES = [
    {
        "id": "efficacy_comparison",
        "name": "🎯 Compare Efficacy: Competitor vs. My Program",
        "description": "Side-by-side efficacy comparison with key metrics",
        "query": "Compare the efficacy data (ORR, PFS, OS, DoR) between [Competitor Drug/Program] and our program. Include confidence intervals, patient populations, and line of therapy. Highlight key differences and competitive positioning opportunities.",
        "placeholder": "[Competitor Drug/Program]",
        "category": "Efficacy"
    },
    {
        "id": "safety_profile",
        "name": "⚠️ Safety Profile Analysis",
        "description": "Comprehensive safety data assessment",
        "query": "Analyze the safety profile of [Competitor Drug/Program] including: Grade ≥3 adverse events, treatment discontinuation rates, dose modifications, most common AEs, and serious adverse events. Compare to standard of care and identify differentiation opportunities for our program.",
        "placeholder": "[Competitor Drug/Program]",
        "category": "Safety"
    },
    {
        "id": "regulatory_pathway",
        "name": "📋 Regulatory Pathway Comparison",
        "description": "Development strategy and regulatory status",
        "query": "What is the regulatory pathway and development strategy for [Competitor Drug/Program]? Include: indication, trial design, endpoints, regulatory designations (BTD, Fast Track, Orphan), approval timeline, and any FDA feedback or regulatory actions.",
        "placeholder": "[Competitor Drug/Program]",
        "category": "Regulatory"
    },
    {
        "id": "trial_design",
        "name": "🔬 Clinical Trial Design Benchmarking",
        "description": "Trial design and endpoint analysis",
        "query": "Analyze the clinical trial design for [Competitor Drug/Program]: study phase, enrollment (N), eligibility criteria, primary/secondary endpoints, comparator arms, biomarker strategy, and trial duration. How does this compare to best practices and our program design?",
        "placeholder": "[Competitor Drug/Program]",
        "category": "Clinical"
    },
    {
        "id": "market_positioning",
        "name": "💼 Market Positioning Analysis",
        "description": "Competitive landscape and market access",
        "query": "What is the competitive positioning of [Competitor Drug/Program] in [Indication/Line of Therapy]? Include: key competitors, market share projections, commercial strategy, pricing expectations, payer landscape, and market access considerations.",
        "placeholder": "[Competitor Drug/Program], [Indication/Line of Therapy]",
        "category": "Commercial"
    },
    {
        "id": "latest_updates",
        "name": "📰 Latest Clinical Updates & Data Readouts",
        "description": "Recent trial results and conference presentations",
        "query": "What are the latest clinical trial results and data updates for [Competitor Drug/Program]? Include recent conference presentations (ASCO, ESMO, ASH), press releases, regulatory filings, and any new efficacy/safety data. Summarize key takeaways and implications for our program.",
        "placeholder": "[Competitor Drug/Program]",
        "category": "Updates"
    }
]


def get_all_templates() -> List[Dict]:
    """Get all available query templates"""
    return QUERY_TEMPLATES


def get_template_by_id(template_id: str) -> Dict:
    """Get a specific template by ID"""
    for template in QUERY_TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_templates_by_category(category: str) -> List[Dict]:
    """Get templates filtered by category"""
    return [t for t in QUERY_TEMPLATES if t["category"] == category]


def get_categories() -> List[str]:
    """Get all unique template categories"""
    return list(set(t["category"] for t in QUERY_TEMPLATES))


def format_template_query(template_id: str, replacements: Dict[str, str]) -> str:
    """
    Format a template query with user-provided replacements

    Args:
        template_id: ID of the template to use
        replacements: Dict mapping placeholders to actual values
                     e.g., {"[Competitor Drug/Program]": "Drug X"}

    Returns:
        Formatted query string
    """
    template = get_template_by_id(template_id)
    if not template:
        return ""

    query = template["query"]
    for placeholder, value in replacements.items():
        query = query.replace(placeholder, value)

    return query

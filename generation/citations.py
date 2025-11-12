"""
Citations Module
Extract and format citations from answers
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_citations(text: str) -> List[str]:
    """
    Extract citation references from text

    Args:
        text: Text with citations like [1], [doc1#5], etc.

    Returns:
        List of citation references
    """
    # Pattern: [number] or [doc#page] or [doc1#5]
    pattern = r'\[([^\]]+)\]'
    citations = re.findall(pattern, text)

    return citations


def format_citation(
    doc_name: str,
    page: int,
    source: str = None
) -> str:
    """
    Format citation string

    Args:
        doc_name: Document name
        page: Page number
        source: Optional source name

    Returns:
        Formatted citation like "[doc1#5] (NEJM)"
    """
    citation = f"[{doc_name}#p{page}]"
    if source:
        citation += f" ({source})"
    return citation


def add_citation_links(
    text: str,
    contexts: List[Dict[str, Any]]
) -> Tuple[str, Dict[int, Dict]]:
    """
    Add citation links to text and return citation details

    Args:
        text: Generated text with [1], [2] references
        contexts: List of contexts used for generation

    Returns:
        Tuple of (text with formatted citations, citation details dict)
    """
    # Build citation map
    citation_details = {}

    for i, ctx in enumerate(contexts, 1):
        metadata = ctx.get("metadata", {})
        citation_details[i] = {
            "doc_name": metadata.get("file_name", "Unknown"),
            "page": ctx.get("chunk_index", 0) + 1,
            "source": ctx.get("source", ""),
            "doc_type": ctx.get("doc_type", ""),
            "text_snippet": ctx.get("text", "")[:200] + "..."
        }

    # Replace [1], [2] with formatted citations
    def replace_citation(match):
        num_str = match.group(1)
        try:
            num = int(num_str)
            if num in citation_details:
                detail = citation_details[num]
                return format_citation(
                    detail["doc_name"],
                    detail["page"],
                    detail["source"]
                )
        except ValueError:
            pass
        return match.group(0)  # Return original if can't parse

    formatted_text = re.sub(r'\[(\d+)\]', replace_citation, text)

    return formatted_text, citation_details


def create_bibliography(citation_details: Dict[int, Dict]) -> str:
    """
    Create bibliography section from citations

    Args:
        citation_details: Dict of citation number -> details

    Returns:
        Formatted bibliography markdown
    """
    if not citation_details:
        return ""

    bib_lines = ["## References\n"]

    for num in sorted(citation_details.keys()):
        detail = citation_details[num]
        line = f"{num}. **{detail['doc_name']}** (Page {detail['page']})"

        if detail.get("source"):
            line += f" - {detail['source']}"

        if detail.get("doc_type"):
            line += f" [{detail['doc_type']}]"

        bib_lines.append(line)

    return "\n".join(bib_lines)


if __name__ == "__main__":
    # Test citations
    print("Testing Citations Module...")

    test_text = "Trial X showed 45% ORR [1]. This is higher than Trial Y which showed 38% [2]."

    test_contexts = [
        {
            "text": "Trial X: ORR 45% in 120 patients",
            "metadata": {"file_name": "trial_x.pdf"},
            "chunk_index": 2,
            "source": "NEJM",
            "doc_type": "publication"
        },
        {
            "text": "Trial Y: ORR 38% in 150 patients",
            "metadata": {"file_name": "trial_y.pdf"},
            "chunk_index": 4,
            "source": "JCO",
            "doc_type": "publication"
        }
    ]

    # Test citation extraction
    citations = extract_citations(test_text)
    print(f"\n✓ Extracted citations: {citations}")

    # Test citation formatting
    formatted_text, details = add_citation_links(test_text, test_contexts)
    print(f"\n✓ Formatted text:")
    print(formatted_text)

    # Test bibliography
    bib = create_bibliography(details)
    print(f"\n✓ Bibliography:")
    print(bib)

    print("\n✓ Citations test successful!")

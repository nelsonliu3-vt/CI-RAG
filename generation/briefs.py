"""
SAB Pre-Read Generator
Generates meeting-ready briefs with structured sections
TODO: Expand with full PDF generation and detailed formatting
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from retrieval.hybrid_search import get_hybrid_search
from generation.analyst import get_analyst
from core.program_profile import get_program_profile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SABBriefGenerator:
    """Generates SAB Pre-Read briefs"""

    def __init__(self):
        self.hybrid_search = get_hybrid_search()
        self.analyst = get_analyst()
        self.profile_manager = get_program_profile()

    def generate_preread(
        self,
        weeks_back: int = 2,
        max_items_per_section: int = 5
    ) -> Dict[str, Any]:
        """
        Generate SAB Pre-Read brief

        Args:
            weeks_back: Number of weeks to look back
            max_items_per_section: Max items per section

        Returns:
            Brief dict with sections
        """
        profile = self.profile_manager.get_profile()
        if not profile:
            return {"error": "No program profile set. Please configure in Program Profile tab."}

        sections = {
            "title": f"SAB Pre-Read: {profile['program_name']}",
            "date_range": f"Last {weeks_back} weeks",
            "generated": datetime.now().isoformat(),
            "program": self.profile_manager.format_profile_context(),
            "sections": {}
        }

        # TODO: Implement full section queries
        # For now, return stub structure

        sections["sections"]["clinical_data"] = self._get_clinical_data(weeks_back, max_items_per_section)
        sections["sections"]["regulatory"] = self._get_regulatory_actions(weeks_back, max_items_per_section)
        sections["sections"]["competitor_moves"] = self._get_competitor_moves(weeks_back, max_items_per_section)
        sections["sections"]["safety_signals"] = self._get_safety_signals(weeks_back, max_items_per_section)
        sections["sections"]["kol_commentary"] = self._get_kol_commentary(weeks_back, max_items_per_section)

        return sections

    def _get_clinical_data(self, weeks_back: int, max_items: int) -> Dict[str, Any]:
        """Query for new clinical data"""
        query = "clinical trial data ORR PFS efficacy results"
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=max_items * 2)
            # Filter by date (last N weeks)
            filtered = self._filter_by_date(results, weeks_back)
            return {"title": "New Clinical Data", "items": filtered[:max_items]}
        except:
            return {"title": "New Clinical Data", "items": []}

    def _get_regulatory_actions(self, weeks_back: int, max_items: int) -> Dict[str, Any]:
        """Query for regulatory actions"""
        query = "FDA approval EMA regulatory authorization"
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=max_items * 2)
            filtered = self._filter_by_date(results, weeks_back)
            return {"title": "Regulatory Actions", "items": filtered[:max_items]}
        except:
            return {"title": "Regulatory Actions", "items": []}

    def _get_competitor_moves(self, weeks_back: int, max_items: int) -> Dict[str, Any]:
        """Query for competitor moves"""
        query = "competitor pipeline development acquisition partnership"
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=max_items * 2)
            filtered = self._filter_by_date(results, weeks_back)
            return {"title": "Competitor Moves", "items": filtered[:max_items]}
        except:
            return {"title": "Competitor Moves", "items": []}

    def _get_safety_signals(self, weeks_back: int, max_items: int) -> Dict[str, Any]:
        """Query for safety signals"""
        query = "adverse events safety toxicity side effects"
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=max_items * 2)
            filtered = self._filter_by_date(results, weeks_back)
            return {"title": "Safety Signals", "items": filtered[:max_items]}
        except:
            return {"title": "Safety Signals", "items": []}

    def _get_kol_commentary(self, weeks_back: int, max_items: int) -> Dict[str, Any]:
        """Query for KOL commentary"""
        query = "expert opinion commentary perspective analysis"
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=max_items * 2)
            filtered = self._filter_by_date(results, weeks_back)
            return {"title": "KOL Commentary", "items": filtered[:max_items]}
        except:
            return {"title": "KOL Commentary", "items": []}

    def _filter_by_date(self, results: List[Dict[str, Any]], weeks_back: int) -> List[Dict[str, Any]]:
        """Filter results by publication date (last N weeks)"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(weeks=weeks_back)
        filtered = []

        for result in results:
            metadata = result.get('metadata', {})
            published_str = metadata.get('published', '')

            if not published_str:
                # If no date, include it (might be older content)
                filtered.append(result)
                continue

            try:
                # Parse ISO format date
                if 'T' in published_str:
                    published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                else:
                    published_date = datetime.fromisoformat(published_str)

                # Check if within date range
                if published_date.replace(tzinfo=None) >= cutoff_date:
                    filtered.append(result)
            except (ValueError, AttributeError):
                # If date parsing fails, include it
                filtered.append(result)

        return filtered

    def export_to_html(self, brief: Dict[str, Any]) -> str:
        """Export brief to HTML (stub)"""
        html = f"<h1>{brief['title']}</h1>"
        html += f"<p><strong>Date Range:</strong> {brief['date_range']}</p>"
        html += f"<p><strong>Generated:</strong> {brief['generated']}</p>"
        html += "<hr>"
        html += f"<h2>Program Context</h2><pre>{brief['program']}</pre>"
        html += "<hr>"

        for section_key, section in brief.get("sections", {}).items():
            html += f"<h2>{section.get('title', section_key)}</h2>"
            html += f"<p>Items found: {len(section.get('items', []))}</p>"

        return html

    def export_to_pdf(self, brief: Dict[str, Any], output_path: str) -> str:
        """Export brief to PDF with reportlab"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_LEFT, TA_CENTER

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='darkblue',
                spaceAfter=12,
                alignment=TA_CENTER
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor='darkblue',
                spaceAfter=10
            )

            # Title
            story.append(Paragraph(brief['title'], title_style))
            story.append(Spacer(1, 0.2*inch))

            # Metadata
            story.append(Paragraph(f"<b>Date Range:</b> {brief['date_range']}", styles['Normal']))
            story.append(Paragraph(f"<b>Generated:</b> {brief['generated']}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))

            # Program Context
            story.append(Paragraph("Program Context", heading_style))
            program_text = brief['program'].replace('\n', '<br/>')
            story.append(Paragraph(program_text, styles['Normal']))
            story.append(Spacer(1, 0.3*inch))

            # Sections
            for section_key, section in brief.get("sections", {}).items():
                story.append(Paragraph(section.get('title', section_key), heading_style))

                items = section.get('items', [])
                if items:
                    story.append(Paragraph(f"<b>Items found:</b> {len(items)}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

                    for i, item in enumerate(items[:5]):  # Limit to 5 items per section
                        text = item.get('text', '')[:500]  # Limit text length
                        source = item.get('metadata', {}).get('file_name', 'Unknown')

                        story.append(Paragraph(f"<b>{i+1}. {source}</b>", styles['Normal']))
                        story.append(Paragraph(text + "...", styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                else:
                    story.append(Paragraph("<i>No items found</i>", styles['Italic']))

                story.append(Spacer(1, 0.2*inch))

            # Build PDF
            doc.build(story)
            logger.info(f"✓ Exported SAB Pre-Read to {output_path}")
            return output_path

        except ImportError as e:
            logger.warning(f"reportlab not available: {e}, falling back to HTML")
            html = self.export_to_html(brief)
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w") as f:
                f.write(html)
            return html_path
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise


# Singleton
_brief_generator: Optional[SABBriefGenerator] = None


def get_brief_generator() -> SABBriefGenerator:
    """Get or create brief generator singleton"""
    global _brief_generator
    if _brief_generator is None:
        _brief_generator = SABBriefGenerator()
    return _brief_generator


if __name__ == "__main__":
    print("Testing SAB Brief Generator...")

    generator = get_brief_generator()
    brief = generator.generate_preread(weeks_back=2)

    print(f"\n✓ Generated brief: {brief.get('title', 'No title')}")
    print(f"  Sections: {list(brief.get('sections', {}).keys())}")

    print("\n✓ SAB Brief Generator test successful!")

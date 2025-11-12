"""
Entity Extraction Module
Extracts structured competitive intelligence entities from documents
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from core.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ENTITY_EXTRACTION_PROMPT = """You are a competitive intelligence analyst extracting structured data from pharmaceutical documents.

Extract the following entities from the document:

DOCUMENT TEXT:
{document_text}

Extract and return as JSON:
{{
  "companies": [
    {{
      "name": "Company name",
      "aliases": ["alternate names"],
      "role": "sponsor|competitor|partner"
    }}
  ],
  "assets": [
    {{
      "name": "Drug name or code",
      "company": "Company developing it",
      "mechanism": "Mechanism of action",
      "indication": "Disease/indication",
      "phase": "Development phase"
    }}
  ],
  "trials": [
    {{
      "trial_id": "NCT number or trial name",
      "asset": "Drug being tested",
      "phase": "Phase 1|2|3",
      "indication": "Disease, line of therapy, biomarker",
      "status": "ongoing|completed|planned",
      "n_patients": number_of_patients
    }}
  ],
  "data_points": [
    {{
      "trial_id": "Which trial",
      "metric_type": "ORR|PFS|OS|DOR|AE|DCR",
      "value": numerical_value,
      "confidence_interval": "e.g., 38-52",
      "n_patients": sample_size,
      "unit": "% or months or other",
      "data_maturity": "interim|final|updated",
      "subgroup": "overall|subgroup description",
      "quote": "VERBATIM text span containing this number (CRITICAL for traceability)"
    }}
  ],
  "date_reported": "YYYY-MM-DD or best estimate",
  "document_type": "press_release|publication|conference_abstract|regulatory|clinical_trial_result",
  "key_insights": ["Brief bullet points of key findings"]
}}

IMPORTANT RULES:
1. Only extract information explicitly stated in the document
2. Use "unknown" for missing required fields
3. For dates, use ISO format (YYYY-MM-DD) or "unknown"
4. Extract ALL data points mentioned (ORR, PFS, OS, safety data)
5. Include confidence intervals when provided
6. Note data maturity (interim vs final analysis)
7. If document updates previous data, note that in key_insights
8. For safety data (AEs), include grade (e.g., "Grade ≥3")
9. **CRITICAL**: For each data_point, include "quote" field with the EXACT sentence/phrase from document containing the number
10. Quote must be verbatim (copy-paste from document) for 100% traceability

Return ONLY valid JSON, no additional text.
"""


class EntityExtractor:
    """Extract structured entities from competitive intelligence documents"""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize extractor with LLM"""
        self.llm = get_llm_client(model_name)
        self.model_name = model_name

    def extract(self, document_text: str, max_text_length: int = 8000) -> Dict[str, Any]:
        """
        Extract entities from document using LLM

        Args:
            document_text: Full document text
            max_text_length: Maximum text to send to LLM (truncate if longer)

        Returns:
            Dict with extracted entities
        """
        try:
            # Truncate if too long (keep beginning and end)
            if len(document_text) > max_text_length:
                logger.warning(f"Document too long ({len(document_text)} chars), truncating to {max_text_length}")
                # Keep first 70% and last 30% (often key data in both sections)
                split_point = int(max_text_length * 0.7)
                truncated = document_text[:split_point] + "\n\n[...truncated...]\n\n" + document_text[-(max_text_length - split_point):]
                document_text = truncated

            # Prepare prompt
            prompt = ENTITY_EXTRACTION_PROMPT.format(document_text=document_text)

            # Call LLM
            logger.info("Extracting entities with LLM...")
            response = self.llm.generate_with_context(
                prompt_template="{prompt}",
                context={"prompt": prompt}
            )

            # Parse JSON response
            entities = self._parse_extraction_response(response)

            # Validate and clean (pass original text for quote extraction)
            entities = self._validate_entities(entities, document_text)

            logger.info(f"✓ Extracted: {len(entities.get('companies', []))} companies, "
                       f"{len(entities.get('assets', []))} assets, "
                       f"{len(entities.get('trials', []))} trials, "
                       f"{len(entities.get('data_points', []))} data points")

            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return self._empty_entities()

    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into JSON"""
        try:
            # Try to find JSON in response
            # Look for content between first { and last }
            start = response.find('{')
            end = response.rfind('}')

            if start == -1 or end == -1:
                raise ValueError("No JSON found in response")

            json_str = response[start:end+1]
            entities = json.loads(json_str)

            return entities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return self._empty_entities()

    def _extract_quote_for_value(self, text: str, value: Any, metric_type: str, context_chars: int = 100) -> str:
        """
        Extract verbatim quote containing a numeric value (fallback method)

        Args:
            text: Full document text
            value: Numeric value to find
            metric_type: Type of metric (ORR, PFS, etc.)
            context_chars: Characters of context around match

        Returns:
            Quote string containing the value
        """
        # Convert value to string for regex matching
        value_str = str(value).replace('.0', '')  # Handle 45.0 → 45

        # Build regex pattern: value followed by % or "months" or CI
        patterns = [
            rf"{re.escape(value_str)}\s*%",  # "45%"
            rf"{re.escape(value_str)}\s+months",  # "6.2 months"
            rf"{re.escape(value_str)}\s*\([^)]+\)",  # "45% (95% CI: 38-52%)"
            rf"{metric_type}[:\s]+{re.escape(value_str)}",  # "ORR: 45"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract context window
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                quote = text[start:end].strip()

                # Clean up quote (remove partial words at boundaries)
                quote = re.sub(r'^\S+\s+', '', quote)  # Remove partial word at start
                quote = re.sub(r'\s+\S+$', '', quote)  # Remove partial word at end

                return quote

        # Fallback: generic quote
        return f"Value {value} for {metric_type}"

    def _validate_entities(self, entities: Dict[str, Any], original_text: str = "") -> Dict[str, Any]:
        """Validate and clean extracted entities"""
        # Ensure all expected keys exist
        validated = {
            "companies": entities.get("companies", []),
            "assets": entities.get("assets", []),
            "trials": entities.get("trials", []),
            "data_points": entities.get("data_points", []),
            "date_reported": entities.get("date_reported", "unknown"),
            "document_type": entities.get("document_type", "unknown"),
            "key_insights": entities.get("key_insights", [])
        }

        # Clean date
        if validated["date_reported"] == "unknown":
            # Try to infer from text or use current date as fallback
            validated["date_reported"] = datetime.now().strftime("%Y-%m-%d")

        # Remove any entities with "unknown" as critical identifier
        validated["companies"] = [c for c in validated["companies"] if c.get("name") != "unknown"]
        validated["assets"] = [a for a in validated["assets"] if a.get("name") != "unknown"]
        validated["trials"] = [t for t in validated["trials"] if t.get("trial_id") != "unknown"]

        # Validate data_points have quotes (CRITICAL for POC traceability requirement)
        for dp in validated["data_points"]:
            if not dp.get("quote") and original_text:
                # If LLM didn't provide quote, try regex extraction
                logger.warning(f"Data point missing quote field, attempting fallback extraction for {dp.get('metric_type')}")
                dp["quote"] = self._extract_quote_for_value(
                    original_text,
                    dp.get("value", ""),
                    dp.get("metric_type", "")
                )
            elif not dp.get("quote"):
                # Last resort fallback
                dp["quote"] = f"Value {dp.get('value')} for {dp.get('metric_type')}"

        return validated

    def _empty_entities(self) -> Dict[str, Any]:
        """Return empty entity structure"""
        return {
            "companies": [],
            "assets": [],
            "trials": [],
            "data_points": [],
            "date_reported": datetime.now().strftime("%Y-%m-%d"),
            "document_type": "unknown",
            "key_insights": []
        }

    def extract_quick(self, document_text: str) -> Dict[str, Any]:
        """
        Quick extraction focusing on key entities only (faster, cheaper)

        Args:
            document_text: Document text

        Returns:
            Minimal entity dict with just companies, assets, and key data
        """
        # Use simpler prompt for quick extraction
        quick_prompt = f"""Extract key competitive intelligence from this document as JSON:

DOCUMENT:
{document_text[:4000]}

Return JSON:
{{
  "company": "Main competitor company name",
  "drug": "Main drug/asset name",
  "indication": "Disease and line",
  "key_metric": "Most important metric (e.g., ORR=45%)",
  "impact_level": "high|medium|low",
  "is_update": true/false
}}

Return ONLY JSON."""

        try:
            response = self.llm.generate_with_context(
                prompt_template="{prompt}",
                context={"prompt": quick_prompt}
            )

            # Parse response
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                try:
                    quick_data = json.loads(response[start:end+1])
                    return quick_data
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in quick extraction response: {e}")
                    logger.debug(f"Response snippet: {response[start:end+1][:200]}")
            else:
                logger.warning("No JSON object found in quick extraction response")

        except Exception as e:
            logger.error(f"Quick extraction failed: {e}")

        return {
            "company": "unknown",
            "drug": "unknown",
            "indication": "unknown",
            "key_metric": "unknown",
            "impact_level": "unknown",
            "is_update": False
        }


# Singleton instance
_extractor_instance: Optional[EntityExtractor] = None


def get_entity_extractor(model_name: str = "gpt-4o-mini") -> EntityExtractor:
    """Get or create entity extractor singleton"""
    global _extractor_instance
    if _extractor_instance is None or _extractor_instance.model_name != model_name:
        _extractor_instance = EntityExtractor(model_name)
    return _extractor_instance


if __name__ == "__main__":
    # Test entity extraction
    print("Testing Entity Extractor...")

    test_doc = """
    Press Release: Competitor Pharma Announces Phase 2 Results for Drug-ABC

    Boston, MA - June 15, 2024 - Competitor Pharma today announced positive
    top-line results from the Phase 2 trial (NCT12345678) of Drug-ABC, a KRAS
    G12C inhibitor, in patients with previously treated non-small cell lung cancer.

    Key Results:
    - Objective Response Rate (ORR): 45% (95% CI: 38-52%)
    - Median Progression-Free Survival (PFS): 6.2 months (95% CI: 5.1-7.3 months)
    - Disease Control Rate: 85%
    - Grade ≥3 Treatment-Related Adverse Events: 58%

    The trial enrolled 150 patients with KRAS G12C-mutated NSCLC who had received
    prior platinum-based chemotherapy. This represents the final analysis, updating
    the interim results presented in January 2024 (ORR: 40%, n=50).
    """

    extractor = get_entity_extractor()
    entities = extractor.extract(test_doc)

    print("\n✓ Extracted entities:")
    print(json.dumps(entities, indent=2))

    print("\n✓ Entity extraction test successful!")

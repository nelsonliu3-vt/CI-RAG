"""
Document Type Detector Module
Automatically detects document type based on content and metadata
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.config import (
    DOCUMENT_TYPES,
    NEWS_SOURCES,
    CONFERENCE_NEWS,
    JOURNAL_NAMES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentDetector:
    """Auto-detect document type and extract metadata"""

    def __init__(self):
        self.rules = self._build_detection_rules()

    def _build_detection_rules(self) -> List[Dict]:
        """Build ordered list of detection rules (check in this order)"""
        return [
            {
                "type": "ci_email",
                "check": self._is_ci_email,
                "priority": 1
            },
            {
                "type": "conference_news",
                "check": self._is_conference_news,
                "priority": 2
            },
            {
                "type": "news_article",
                "check": self._is_news_article,
                "priority": 3
            },
            {
                "type": "publication",
                "check": self._is_publication,
                "priority": 4
            },
            {
                "type": "poster",
                "check": self._is_poster,
                "priority": 5
            },
            {
                "type": "csr",
                "check": self._is_csr,
                "priority": 6
            },
            {
                "type": "presentation",
                "check": self._is_presentation,
                "priority": 7
            },
            {
                "type": "regulatory",
                "check": self._is_regulatory,
                "priority": 8
            }
        ]

    def detect(self, parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect document type and extract metadata

        Args:
            parsed_doc: Output from parser.parse()

        Returns:
            Dict with: type, confidence, source, topics, date, etc.
        """
        text = parsed_doc.get("text", "").lower()
        metadata = parsed_doc.get("metadata", {})
        file_name = metadata.get("file_name", "").lower()

        # Try each rule in priority order
        for rule in self.rules:
            result = rule["check"](text, metadata, file_name)
            if result:
                result["detected_type"] = rule["type"]
                result["type_description"] = DOCUMENT_TYPES.get(rule["type"], "Unknown")
                logger.info(f"Detected: {rule['type']} (confidence: {result.get('confidence', 0):.2f})")
                return result

        # Fallback: other
        return {
            "detected_type": "other",
            "type_description": "Uncategorized document",
            "confidence": 0.3,
            "source": "unknown",
            "topics": [],
            "date": None
        }

    def _is_ci_email(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is CI email"""
        # Email format
        if file_name.endswith(('.eml', '.msg')):
            subject = metadata.get("subject", "").lower()

            # Keywords in subject
            ci_keywords = ["competitive intelligence", "ci update", "market landscape", "competitor", "ci brief"]

            for keyword in ci_keywords:
                if keyword in subject or keyword in text[:1000]:  # Check first 1000 chars
                    return {
                        "confidence": 0.9,
                        "source": "ci_email",
                        "topics": self._extract_topics(text),
                        "date": metadata.get("date"),
                        "subject": metadata.get("subject")
                    }

            # Any email is still an email
            return {
                "confidence": 0.7,
                "source": "email",
                "topics": self._extract_topics(text),
                "date": metadata.get("date"),
                "subject": metadata.get("subject")
            }

        return None

    def _is_conference_news(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is conference news (ESMO Daily, ASCO Daily, etc.)"""
        # Check file name and title
        title = metadata.get("title", "").lower()

        for conf in CONFERENCE_NEWS:
            if conf in file_name or conf in title or conf in text[:500]:
                # Extract conference name
                conf_name = conf.upper().split()[0]  # "ESMO", "ASCO", etc.

                return {
                    "confidence": 0.95,
                    "source": f"{conf_name} Daily",
                    "topics": self._extract_topics(text),
                    "date": self._extract_date(text, metadata),
                    "conference": conf_name
                }

        return None

    def _is_news_article(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is news article (Endpoints, STAT, Fierce)"""
        url = metadata.get("url", "").lower()
        title = metadata.get("title", "").lower()

        for source_name, domains in NEWS_SOURCES.items():
            for domain in domains:
                if domain in url or domain in file_name or domain in title:
                    return {
                        "confidence": 0.95,
                        "source": source_name.capitalize(),
                        "topics": self._extract_topics(text),
                        "date": self._extract_date(text, metadata),
                        "url": metadata.get("url"),
                        "title": metadata.get("title")
                    }

        # Generic news article detection
        news_keywords = ["published", "reporter", "breaking", "news", "article"]
        keyword_count = sum(1 for kw in news_keywords if kw in text[:1000])

        if keyword_count >= 2 and file_name.endswith(".html"):
            return {
                "confidence": 0.7,
                "source": "web_article",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata)
            }

        return None

    def _is_publication(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is scientific publication"""
        # Check for journal names
        for journal in JOURNAL_NAMES:
            if journal in text[:2000]:  # Check first 2000 chars
                return {
                    "confidence": 0.9,
                    "source": journal.upper(),
                    "topics": self._extract_topics(text),
                    "date": self._extract_date(text, metadata),
                    "journal": journal
                }

        # Check for DOI
        doi_pattern = r'doi[\s:]+10\.\d{4,}\/[^\s]+'
        if re.search(doi_pattern, text[:3000], re.IGNORECASE):
            return {
                "confidence": 0.85,
                "source": "publication",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata)
            }

        # Check for publication structure
        pub_keywords = ["abstract", "methods", "results", "conclusions", "references", "authors"]
        keyword_count = sum(1 for kw in pub_keywords if kw in text[:5000])

        if keyword_count >= 4:
            return {
                "confidence": 0.75,
                "source": "publication",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata)
            }

        return None

    def _is_poster(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is conference poster/abstract"""
        # Keywords
        poster_keywords = ["abstract", "poster", "asco", "esmo", "aacr", "ash", "presentation number"]

        keyword_count = sum(1 for kw in poster_keywords if kw in text[:1000])

        if keyword_count >= 2:
            # Extract conference
            conference = None
            for conf in ["ASCO", "ESMO", "AACR", "ASH", "SITC"]:
                if conf.lower() in text[:1000]:
                    conference = conf
                    break

            return {
                "confidence": 0.85,
                "source": conference or "conference_poster",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata),
                "conference": conference
            }

        return None

    def _is_csr(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is Clinical Study Report"""
        # Keywords
        csr_keywords = ["clinical study report", "protocol", "clinical trial", "investigational product"]

        # Check for NCT ID
        nct_pattern = r'NCT\d{8}'
        has_nct = bool(re.search(nct_pattern, text[:5000]))

        keyword_count = sum(1 for kw in csr_keywords if kw in text[:3000])

        # Long document + keywords + NCT
        if (metadata.get("num_pages", 0) > 50 or len(text) > 50000) and (keyword_count >= 2 or has_nct):
            return {
                "confidence": 0.9,
                "source": "csr",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata),
                "nct_id": self._extract_nct_id(text)
            }

        return None

    def _is_presentation(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is presentation/slide deck"""
        # PPTX format
        if file_name.endswith(('.pptx', '.ppt')):
            return {
                "confidence": 0.95,
                "source": "presentation",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata)
            }

        # PDF with slide structure
        if "--- slide" in text.lower() or "slide " in text[:1000]:
            return {
                "confidence": 0.8,
                "source": "presentation",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata)
            }

        return None

    def _is_regulatory(self, text: str, metadata: Dict, file_name: str) -> Optional[Dict]:
        """Check if document is regulatory (FDA/EMA)"""
        reg_keywords = ["fda", "ema", "approval", "label", "prescribing information", "drug approval"]

        keyword_count = sum(1 for kw in reg_keywords if kw in text[:2000])

        if keyword_count >= 2:
            # Determine agency
            agency = None
            if "fda" in text[:1000]:
                agency = "FDA"
            elif "ema" in text[:1000]:
                agency = "EMA"

            return {
                "confidence": 0.85,
                "source": agency or "regulatory",
                "topics": self._extract_topics(text),
                "date": self._extract_date(text, metadata),
                "agency": agency
            }

        return None

    def _extract_topics(self, text: str, max_topics: int = 10) -> List[str]:
        """Extract key topics from text (simple keyword extraction)"""
        # Common pharma/onc topics
        topic_keywords = {
            "nsclc": ["nsclc", "non-small cell lung cancer"],
            "breast_cancer": ["breast cancer"],
            "melanoma": ["melanoma"],
            "colorectal": ["colorectal", "crc"],
            "pd-1": ["pd-1", "pd1", "programmed death"],
            "pd-l1": ["pd-l1", "pdl1"],
            "ctla-4": ["ctla-4", "ctla4"],
            "egfr": ["egfr", "epidermal growth factor"],
            "kras": ["kras"],
            "braf": ["braf"],
            "her2": ["her2"],
            "phase_1": ["phase 1", "phase i"],
            "phase_2": ["phase 2", "phase ii"],
            "phase_3": ["phase 3", "phase iii"],
            "orr": ["orr", "objective response rate"],
            "pfs": ["pfs", "progression-free survival"],
            "os": ["overall survival"]
        }

        text_lower = text.lower()
        found_topics = []

        for topic, patterns in topic_keywords.items():
            for pattern in patterns:
                if pattern in text_lower:
                    found_topics.append(topic.upper().replace("_", " "))
                    break

        return found_topics[:max_topics]

    def _extract_date(self, text: str, metadata: Dict) -> Optional[str]:
        """Extract date from text or metadata"""
        # Try metadata first
        if metadata.get("date"):
            return metadata["date"]

        # Try to find date in text (simple patterns)
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # 12/31/2024
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # 2024-12-31
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_nct_id(self, text: str) -> Optional[str]:
        """Extract NCT ID from text"""
        nct_pattern = r'(NCT\d{8})'
        match = re.search(nct_pattern, text, re.IGNORECASE)
        return match.group(1) if match else None


# Convenience function
def detect_document_type(parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect document type (convenience function)

    Args:
        parsed_doc: Output from parser.parse()

    Returns:
        Detection result dict
    """
    detector = DocumentDetector()
    return detector.detect(parsed_doc)


if __name__ == "__main__":
    # Test detector
    import sys
    from ingestion.parser import parse_document

    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        parsed = parse_document(test_file)
        detected = detect_document_type(parsed)

        print(f"\nFile: {test_file.name}")
        print(f"Type: {detected['detected_type']} ({detected['type_description']})")
        print(f"Confidence: {detected.get('confidence', 0):.2f}")
        print(f"Source: {detected.get('source', 'unknown')}")
        print(f"Topics: {', '.join(detected.get('topics', []))}")
        print(f"Date: {detected.get('date', 'N/A')}")
    else:
        print("Usage: python detector.py <file_path>")

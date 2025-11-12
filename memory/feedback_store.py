"""
Feedback Store Module for HITL (Human-in-the-Loop) System
Logs and manages user feedback on AI-generated answers
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class FeedbackStore:
    """Manages human feedback on AI answers"""

    FEEDBACK_DIR = Path("data/feedback")

    def __init__(self):
        """Initialize feedback store"""
        self.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        self.feedback_log = []

    def add_feedback(
        self,
        query: str,
        original_answer: str,
        feedback_text: str,
        feedback_type: str,
        helpful: bool = None,
        metadata: Dict = None
    ) -> str:
        """
        Add user feedback for an answer

        Args:
            query: Original user query
            original_answer: AI-generated answer
            feedback_text: User's feedback text
            feedback_type: Type of feedback (correction/deepening/redirection/general)
            helpful: Whether answer was helpful (True/False/None)
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        feedback_entry = {
            "id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "original_answer": original_answer,
            "feedback_text": feedback_text,
            "feedback_type": feedback_type,
            "helpful": helpful,
            "metadata": metadata or {}
        }

        self.feedback_log.append(feedback_entry)

        # Save to disk
        self._save_feedback(feedback_entry)

        return feedback_id

    def get_all_feedback(self) -> List[Dict]:
        """Get all feedback entries"""
        return self.feedback_log

    def get_feedback_by_type(self, feedback_type: str) -> List[Dict]:
        """Get feedback filtered by type"""
        return [f for f in self.feedback_log if f["feedback_type"] == feedback_type]

    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics"""
        total = len(self.feedback_log)
        if total == 0:
            return {
                "total_feedback": 0,
                "helpful_count": 0,
                "not_helpful_count": 0,
                "by_type": {}
            }

        helpful_count = sum(1 for f in self.feedback_log if f.get("helpful") == True)
        not_helpful_count = sum(1 for f in self.feedback_log if f.get("helpful") == False)

        by_type = {}
        for feedback in self.feedback_log:
            feedback_type = feedback["feedback_type"]
            by_type[feedback_type] = by_type.get(feedback_type, 0) + 1

        return {
            "total_feedback": total,
            "helpful_count": helpful_count,
            "not_helpful_count": not_helpful_count,
            "satisfaction_rate": helpful_count / total if total > 0 else 0,
            "by_type": by_type
        }

    def classify_feedback_type(self, feedback_text: str, query: str, answer: str) -> str:
        """
        Auto-classify feedback type based on content

        Args:
            feedback_text: User's feedback
            query: Original query
            answer: AI answer

        Returns:
            Feedback type: correction, deepening, redirection, or general
        """
        feedback_lower = feedback_text.lower()

        # Correction indicators
        correction_keywords = ["wrong", "incorrect", "error", "mistake", "actually", "correction", "should be"]
        if any(keyword in feedback_lower for keyword in correction_keywords):
            return "correction"

        # Deepening indicators
        deepening_keywords = ["more", "detail", "explain", "elaborate", "expand", "depth", "additionally", "also"]
        if any(keyword in feedback_lower for keyword in deepening_keywords):
            return "deepening"

        # Redirection indicators
        redirection_keywords = ["instead", "focus on", "different", "alternative", "rather", "prefer", "change"]
        if any(keyword in feedback_lower for keyword in redirection_keywords):
            return "redirection"

        # Default
        return "general"

    def format_feedback_for_prompt(self, feedback_text: str, feedback_type: str) -> str:
        """
        Format feedback for inclusion in regeneration prompt

        Args:
            feedback_text: User's feedback
            feedback_type: Type of feedback

        Returns:
            Formatted feedback string for prompt
        """
        type_instructions = {
            "correction": "The user has identified an error in your previous answer. Please correct this information:",
            "deepening": "The user requests more depth and detail. Please expand your answer to address:",
            "redirection": "The user wants to redirect the focus. Please adjust your answer to emphasize:",
            "general": "The user provided the following feedback:"
        }

        instruction = type_instructions.get(feedback_type, type_instructions["general"])

        return f"{instruction}\n\n{feedback_text}\n\nPlease regenerate your answer taking this feedback into account."

    def export_to_json(self, filepath: str = None) -> str:
        """
        Export feedback log to JSON

        Args:
            filepath: Optional file path to save JSON

        Returns:
            JSON string
        """
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "stats": self.get_feedback_stats(),
            "feedback": self.feedback_log
        }

        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, "w") as f:
                f.write(json_str)

        return json_str

    def _save_feedback(self, feedback_entry: Dict):
        """Save feedback entry to disk"""
        feedback_file = self.FEEDBACK_DIR / f"{feedback_entry['id']}.json"

        with open(feedback_file, "w") as f:
            json.dump(feedback_entry, f, indent=2)


# Singleton instance
_feedback_store = None


def get_feedback_store() -> FeedbackStore:
    """Get feedback store singleton"""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store

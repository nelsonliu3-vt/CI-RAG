"""
Conversation Memory Module for Multi-Round Q&A
Manages conversation history with context compaction
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class ConversationMemory:
    """Manages multi-round conversation history"""

    MAX_ROUNDS = 10  # Maximum rounds to keep
    MAX_CONTEXT_LENGTH = 5000  # Maximum context chars before compaction

    def __init__(self):
        """Initialize conversation memory"""
        self.rounds = []  # List of conversation rounds
        self.session_id = None
        self.started_at = None
        self.metadata = {}

    def start_session(self, session_id: str = None, metadata: Dict = None):
        """
        Start a new conversation session

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            metadata: Optional session metadata (program profile, user, etc.)
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.session_id = session_id
        self.started_at = datetime.now().isoformat()
        self.rounds = []
        self.metadata = metadata or {}

    def add_round(
        self,
        query: str,
        answer: str,
        sources: List[Dict],
        round_type: str = "standard",
        metadata: Dict = None
    ):
        """
        Add a Q&A round to conversation history

        Args:
            query: User's question
            answer: AI's response
            sources: Retrieved source documents
            round_type: Type of round (standard, challenge, feedback)
            metadata: Additional round metadata
        """
        round_data = {
            "round_num": len(self.rounds) + 1,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer,
            "sources": [
                {
                    "id": src.get("id"),
                    "text": src.get("text", "")[:200],  # Truncate for storage
                    "file_name": src.get("metadata", {}).get("file_name", "Unknown"),
                    "rrf_score": src.get("rrf_score", 0.0)
                }
                for src in sources
            ],
            "round_type": round_type,
            "metadata": metadata or {}
        }

        self.rounds.append(round_data)

        # Compact if needed
        if len(self.rounds) > self.MAX_ROUNDS:
            self._compact_old_rounds()

    def get_context_for_next_round(self, max_rounds: int = 5) -> str:
        """
        Get formatted context from previous rounds for next query

        Args:
            max_rounds: Maximum number of previous rounds to include

        Returns:
            Formatted context string
        """
        if not self.rounds:
            return ""

        recent_rounds = self.rounds[-max_rounds:]
        context_parts = []

        for round_data in recent_rounds:
            context_parts.append(f"**Previous Round {round_data['round_num']}:**")
            context_parts.append(f"Q: {round_data['query']}")
            context_parts.append(f"A: {round_data['answer'][:500]}...")  # Truncate long answers
            context_parts.append("")

        context = "\n".join(context_parts)

        # Compact if context is too long
        if len(context) > self.MAX_CONTEXT_LENGTH:
            context = self._compact_context(recent_rounds)

        return context

    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation"""
        if not self.rounds:
            return "No conversation history yet."

        total_rounds = len(self.rounds)
        topics = set()

        for round_data in self.rounds:
            # Extract key topics from queries (simple keyword extraction)
            query_lower = round_data['query'].lower()
            keywords = ['efficacy', 'safety', 'trial', 'regulatory', 'competition', 'market']
            for keyword in keywords:
                if keyword in query_lower:
                    topics.add(keyword.title())

        summary = f"Conversation with {total_rounds} rounds covering: {', '.join(topics) if topics else 'general topics'}"
        return summary

    def get_all_rounds(self) -> List[Dict]:
        """Get all conversation rounds"""
        return self.rounds

    def get_latest_round(self) -> Optional[Dict]:
        """Get the most recent round"""
        if self.rounds:
            return self.rounds[-1]
        return None

    def clear_conversation(self):
        """Clear all conversation history"""
        self.rounds = []
        self.session_id = None
        self.started_at = None

    def export_to_dict(self) -> Dict:
        """Export conversation to dictionary"""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "total_rounds": len(self.rounds),
            "summary": self.get_conversation_summary(),
            "metadata": self.metadata,
            "rounds": self.rounds
        }

    def export_to_json(self, filepath: str = None) -> str:
        """
        Export conversation to JSON

        Args:
            filepath: Optional file path to save JSON

        Returns:
            JSON string
        """
        data = self.export_to_dict()
        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, "w") as f:
                f.write(json_str)

        return json_str

    def _compact_old_rounds(self):
        """Compact old rounds to save memory"""
        # Keep only most recent MAX_ROUNDS
        self.rounds = self.rounds[-self.MAX_ROUNDS:]

    def _compact_context(self, rounds: List[Dict]) -> str:
        """
        Compact context by extracting key facts

        Args:
            rounds: List of round data

        Returns:
            Compacted context string
        """
        compact_parts = ["**Previous Conversation Summary:**"]

        for round_data in rounds:
            # Extract key metrics and findings from answer
            answer = round_data['answer']

            # Simple extraction of key sentences (first 2 sentences or sentences with numbers)
            sentences = answer.split('.')
            key_sentences = []

            for sent in sentences[:3]:  # First 3 sentences
                if any(char.isdigit() for char in sent) or len(sent) > 30:
                    key_sentences.append(sent.strip())

            if key_sentences:
                compact_parts.append(f"Round {round_data['round_num']}: {'. '.join(key_sentences[:2])}.")

        return "\n".join(compact_parts)


# Singleton instance
_conversation_memory = None


def get_conversation_memory() -> ConversationMemory:
    """Get conversation memory singleton"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory


def reset_conversation_memory():
    """Reset conversation memory singleton"""
    global _conversation_memory
    _conversation_memory = ConversationMemory()

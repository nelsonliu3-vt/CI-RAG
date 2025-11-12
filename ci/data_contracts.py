"""
Data Contracts for CI-RAG POC
Defines structured data formats for facts, signals, and actions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class ImpactCode(Enum):
    """Deterministic impact classifications"""
    TIMELINE_SLIP = "Timeline slip"
    TIMELINE_ADVANCE = "Timeline advance"
    REGULATORY_RISK = "Regulatory risk"
    DESIGN_RISK = "Design risk"
    SAFETY_RISK = "Safety risk"
    BIOMARKER_OPPORTUNITY = "Biomarker opportunity"
    COMPETITIVE_THREAT = "Competitive threat"
    NEUTRAL = "Neutral"


class Stance(Enum):
    """Program-relative stance labels"""
    HARMFUL = "Harmful"
    HELPFUL = "Helpful"
    POTENTIALLY_HARMFUL = "Potentially harmful"
    POTENTIALLY_HELPFUL = "Potentially helpful"
    NEUTRAL = "Neutral"


@dataclass
class Fact:
    """
    Atomic competitive intelligence fact extracted from documents

    POC Requirements:
    - Must include verbatim quote for 100% numeric traceability
    - Must link to source_id for citation
    """
    id: str
    entities: List[str]  # [company, drug, target, indication]
    event_type: str  # "Efficacy readout", "Trial halt", "CRL", etc.
    values: Dict[str, Any]  # {"endpoint": "PFS", "delta": 1.9, "unit": "months"}
    date: str  # ISO format YYYY-MM-DD
    source_id: str  # Links to document ID
    quote: str  # Verbatim text span for traceability (CRITICAL for Gate 2)
    confidence: float = 0.8

    def __post_init__(self):
        """Validate fact structure and data integrity"""
        # Validate required string fields
        if not self.id or not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Fact must have non-empty 'id' field")

        if not self.quote or not isinstance(self.quote, str):
            raise ValueError(f"Fact {self.id} missing required 'quote' field for traceability")

        if not self.source_id or not isinstance(self.source_id, str):
            raise ValueError(f"Fact {self.id} missing required 'source_id' for citation")

        if not self.event_type or not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError(f"Fact {self.id} must have non-empty 'event_type' field")

        # Validate entities list
        if not isinstance(self.entities, list):
            raise TypeError(f"Fact {self.id} entities must be a list, got {type(self.entities)}")

        if len(self.entities) == 0:
            raise ValueError(f"Fact {self.id} must have at least one entity")

        if not all(isinstance(e, str) for e in self.entities):
            raise TypeError(f"Fact {self.id} entities must all be strings")

        # Validate values dict
        if not isinstance(self.values, dict):
            raise TypeError(f"Fact {self.id} values must be a dictionary, got {type(self.values)}")

        # Validate date format
        if not self.date or not isinstance(self.date, str):
            raise ValueError(f"Fact {self.id} missing required 'date' field")

        # Check ISO date format (YYYY-MM-DD)
        from datetime import datetime
        try:
            datetime.fromisoformat(self.date)
        except ValueError:
            raise ValueError(f"Fact {self.id} date must be in ISO format (YYYY-MM-DD), got: {self.date}")

        # Validate confidence range
        if not isinstance(self.confidence, (int, float)):
            raise TypeError(f"Fact {self.id} confidence must be numeric, got {type(self.confidence)}")

        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Fact {self.id} confidence must be between 0 and 1, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict"""
        return {
            "id": self.id,
            "entities": self.entities,
            "event_type": self.event_type,
            "values": self.values,
            "date": self.date,
            "source_id": self.source_id,
            "quote": self.quote,
            "confidence": self.confidence
        }


@dataclass
class Signal:
    """
    Derived signal from fact with impact classification and program stance

    POC Requirements:
    - Must link to originating fact via from_fact
    - Must have deterministic impact_code
    - Must have program-relative stance (added by stance.py)
    """
    id: str
    from_fact: str  # Fact ID that generated this signal
    impact_code: ImpactCode
    score: float  # Relevance/importance score (0-1)
    why: str  # Rationale for impact code (2-3 sentences)
    stance: Optional[Stance] = None  # Added by stance analyzer
    stance_rationale: Optional[str] = None  # Why Harmful/Helpful/Neutral
    overlap_score: Optional[float] = None  # Program similarity (0-1)

    def __post_init__(self):
        """Validate signal structure and data integrity"""
        # Validate required string fields
        if not self.id or not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Signal must have non-empty 'id' field")

        if not self.from_fact or not isinstance(self.from_fact, str) or not self.from_fact.strip():
            raise ValueError(f"Signal {self.id} must have non-empty 'from_fact' field")

        if not self.why or not isinstance(self.why, str) or not self.why.strip():
            raise ValueError(f"Signal {self.id} must have non-empty 'why' field")

        # Validate impact_code is ImpactCode enum
        if not isinstance(self.impact_code, ImpactCode):
            raise TypeError(f"Signal {self.id} impact_code must be ImpactCode enum, got {type(self.impact_code)}")

        # Validate score range
        if not isinstance(self.score, (int, float)):
            raise TypeError(f"Signal {self.id} score must be numeric, got {type(self.score)}")

        if not 0 <= self.score <= 1:
            raise ValueError(f"Signal {self.id} score must be between 0 and 1, got {self.score}")

        # Validate optional stance
        if self.stance is not None and not isinstance(self.stance, Stance):
            raise TypeError(f"Signal {self.id} stance must be Stance enum or None, got {type(self.stance)}")

        # Validate optional overlap_score
        if self.overlap_score is not None:
            if not isinstance(self.overlap_score, (int, float)):
                raise TypeError(f"Signal {self.id} overlap_score must be numeric or None, got {type(self.overlap_score)}")

            if not 0 <= self.overlap_score <= 1:
                raise ValueError(f"Signal {self.id} overlap_score must be between 0 and 1, got {self.overlap_score}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict"""
        return {
            "id": self.id,
            "from_fact": self.from_fact,
            "impact_code": self.impact_code.value,
            "score": self.score,
            "why": self.why,
            "stance": self.stance.value if self.stance else None,
            "stance_rationale": self.stance_rationale,
            "overlap_score": self.overlap_score
        }


@dataclass
class Action:
    """
    Recommended action with owner and time horizon

    POC Requirements (Gate 4):
    - Must have owner (not "TBD")
    - Must have horizon (not "TBD")
    - Must link to supporting facts
    """
    title: str  # "Recheck power assumptions for PFS"
    owner: str  # "Biostats", "Clinical Ops", "Medical", "Regulatory"
    horizon: str  # "1 week", "2 weeks", "1 month", "3 months"
    rationale_facts: List[str]  # List of Fact IDs supporting this action
    confidence: float = 0.7

    def __post_init__(self):
        """Validate action structure and data integrity (Critic Gate 4)"""
        # Validate title
        if not self.title or not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Action must have non-empty 'title' field")

        # Validate owner
        if not self.owner or not isinstance(self.owner, str):
            raise ValueError(f"Action '{self.title}' missing required owner")

        if self.owner.lower() in ["tbd", "unknown", ""]:
            raise ValueError(f"Action '{self.title}' owner cannot be TBD or Unknown")

        # Validate horizon
        if not self.horizon or not isinstance(self.horizon, str):
            raise ValueError(f"Action '{self.title}' missing required horizon")

        if self.horizon.lower() in ["tbd", "unknown", ""]:
            raise ValueError(f"Action '{self.title}' horizon cannot be TBD or Unknown")

        # Validate rationale_facts list
        if not isinstance(self.rationale_facts, list):
            raise TypeError(f"Action '{self.title}' rationale_facts must be a list, got {type(self.rationale_facts)}")

        if not self.rationale_facts:
            raise ValueError(f"Action '{self.title}' must link to at least one fact")

        if not all(isinstance(f, str) for f in self.rationale_facts):
            raise TypeError(f"Action '{self.title}' rationale_facts must all be strings")

        # Validate confidence range
        if not isinstance(self.confidence, (int, float)):
            raise TypeError(f"Action '{self.title}' confidence must be numeric, got {type(self.confidence)}")

        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Action '{self.title}' confidence must be between 0 and 1, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict"""
        return {
            "title": self.title,
            "owner": self.owner,
            "horizon": self.horizon,
            "rationale_facts": self.rationale_facts,
            "confidence": self.confidence
        }


@dataclass
class TraceMetrics:
    """
    POC execution metrics for JSON sidecar
    """
    total_facts: int = 0
    total_signals: int = 0
    total_actions: int = 0
    citation_coverage: float = 0.0  # % of sentences with [S#]
    numeric_traceability: float = 0.0  # % of numbers with quote
    action_completeness: float = 0.0  # % of actions with owner+horizon
    execution_time_seconds: float = 0.0
    model_used: str = "gpt-5-mini"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Validate trace metrics structure and data integrity"""
        # Validate integer counts (must be non-negative)
        if not isinstance(self.total_facts, int) or self.total_facts < 0:
            raise ValueError(f"total_facts must be non-negative integer, got {self.total_facts}")

        if not isinstance(self.total_signals, int) or self.total_signals < 0:
            raise ValueError(f"total_signals must be non-negative integer, got {self.total_signals}")

        if not isinstance(self.total_actions, int) or self.total_actions < 0:
            raise ValueError(f"total_actions must be non-negative integer, got {self.total_actions}")

        # Validate percentage fields (0-100)
        for field_name in ['citation_coverage', 'numeric_traceability', 'action_completeness']:
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric, got {type(value)}")

            if not 0 <= value <= 100:
                raise ValueError(f"{field_name} must be between 0 and 100, got {value}")

        # Validate execution time (must be non-negative)
        if not isinstance(self.execution_time_seconds, (int, float)) or self.execution_time_seconds < 0:
            raise ValueError(f"execution_time_seconds must be non-negative, got {self.execution_time_seconds}")

        # Validate model_used (must be non-empty string)
        if not self.model_used or not isinstance(self.model_used, str):
            raise ValueError("model_used must be non-empty string")

        # Validate timestamp (must be non-empty string)
        if not self.timestamp or not isinstance(self.timestamp, str):
            raise ValueError("timestamp must be non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict"""
        return {
            "total_facts": self.total_facts,
            "total_signals": self.total_signals,
            "total_actions": self.total_actions,
            "citation_coverage": self.citation_coverage,
            "numeric_traceability": self.numeric_traceability,
            "action_completeness": self.action_completeness,
            "execution_time_seconds": self.execution_time_seconds,
            "model_used": self.model_used,
            "timestamp": self.timestamp
        }


@dataclass
class CIReport:
    """
    Complete CI report with all sections for JSON sidecar
    """
    query: str
    program_name: str
    facts: List[Fact] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    trace: TraceMetrics = field(default_factory=TraceMetrics)
    markdown_report: str = ""

    def __post_init__(self):
        """Validate CI report structure and data integrity"""
        # Validate query
        if not self.query or not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("CIReport must have non-empty 'query' field")

        # Validate program_name
        if not self.program_name or not isinstance(self.program_name, str) or not self.program_name.strip():
            raise ValueError("CIReport must have non-empty 'program_name' field")

        # Validate lists
        if not isinstance(self.facts, list):
            raise TypeError(f"CIReport facts must be a list, got {type(self.facts)}")

        if not all(isinstance(f, Fact) for f in self.facts):
            raise TypeError("CIReport facts must all be Fact instances")

        if not isinstance(self.signals, list):
            raise TypeError(f"CIReport signals must be a list, got {type(self.signals)}")

        if not all(isinstance(s, Signal) for s in self.signals):
            raise TypeError("CIReport signals must all be Signal instances")

        if not isinstance(self.actions, list):
            raise TypeError(f"CIReport actions must be a list, got {type(self.actions)}")

        if not all(isinstance(a, Action) for a in self.actions):
            raise TypeError("CIReport actions must all be Action instances")

        # Validate trace metrics
        if not isinstance(self.trace, TraceMetrics):
            raise TypeError(f"CIReport trace must be TraceMetrics instance, got {type(self.trace)}")

        # Validate markdown_report
        if not isinstance(self.markdown_report, str):
            raise TypeError(f"CIReport markdown_report must be string, got {type(self.markdown_report)}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict (for JSON sidecar)"""
        return {
            "query": self.query,
            "program_name": self.program_name,
            "facts": [f.to_dict() for f in self.facts],
            "signals": [s.to_dict() for s in self.signals],
            "actions": [a.to_dict() for a in self.actions],
            "trace": self.trace.to_dict()
        }

"""
CI-RAG POC Module
Signal detection, stance analysis, and critic validation for competitive intelligence
"""

from .data_contracts import Fact, Signal, Action, ImpactCode, Stance

__all__ = [
    "Fact",
    "Signal",
    "Action",
    "ImpactCode",
    "Stance"
]

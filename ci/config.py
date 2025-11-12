"""
Configuration Module for CI-RAG POC
Centralizes all magic numbers, thresholds, and tuneable parameters

This module provides dataclasses for configuring:
- Signal detection scoring
- Stance analysis thresholds and weights
- Report generation limits
- Input validation limits
- Performance limits
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SignalScoringConfig:
    """Configuration for signal scoring algorithm"""

    # Base confidence for all signals
    BASE_CONFIDENCE: float = 0.8

    # Score adjustments for different impact types
    CRITICAL_IMPACT_BOOST: float = 0.15  # For regulatory/safety risks
    HIGH_IMPACT_BOOST: float = 0.10  # For timeline slips/threats
    NEUTRAL_PENALTY: float = 0.20  # For neutral events

    # Score bounds
    MAX_SCORE: float = 1.0
    MIN_SCORE: float = 0.1


@dataclass
class StanceConfig:
    """Configuration for stance classification"""

    # Overlap thresholds for stance determination
    HIGH_OVERLAP_THRESHOLD: float = 0.55  # High overlap → Harmful/Helpful
    MEDIUM_OVERLAP_THRESHOLD: float = 0.3  # Medium overlap → Potentially

    # Weights for Jaccard similarity calculation
    WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "target": 0.35,
        "disease": 0.25,
        "line": 0.20,
        "biomarker": 0.15,
        "moa": 0.05
    })


@dataclass
class ReportGenerationConfig:
    """Configuration for report generation"""

    # Section limits
    MAX_SUMMARY_BULLETS: int = 5  # Executive summary
    MAX_WHAT_HAPPENED_FACTS: int = 7  # "What Happened" section
    MAX_VALUES_PER_FACT: int = 2  # Key-value pairs to show
    MAX_NUMBERS_IN_TABLE: int = 3  # Numbers shown in evidence table

    # Action requirements
    MIN_ACTIONS_REQUIRED: int = 3  # Minimum actions (Critic Gate 4)

    # Numeric validation
    MAX_NUMERIC_VALUE: float = 1e15  # Maximum number size
    NUMERIC_FORMAT_PRECISION: str = ".4g"  # Format precision


@dataclass
class InputValidationConfig:
    """Configuration for input validation limits"""

    # Query validation
    MAX_QUERY_LENGTH: int = 2000  # Maximum characters
    MAX_PROGRAM_NAME_LENGTH: int = 200  # Maximum characters

    # Document validation
    MAX_DOCUMENTS: int = 100  # Maximum number of documents
    MAX_TOTAL_DOCUMENT_SIZE: int = 10_000_000  # 10MB total size
    MAX_DOCUMENT_SIZE: int = 8000  # Per-document character limit

    # Path validation
    # (Paths must be under current working directory)


@dataclass
class PerformanceConfig:
    """Configuration for performance limits"""

    # Regex safety
    MAX_REGEX_SPLITS: int = 100  # Prevent ReDoS in sentence splitting

    # Batch processing
    BATCH_SIZE_EMBEDDINGS: int = 50  # Embeddings per batch

    # Rate limiting
    MAX_SIGNALS_PER_RUN: int = 1000  # Maximum signals to generate


@dataclass
class CIRAGConfig:
    """Master configuration combining all sub-configs"""

    signal_scoring: SignalScoringConfig = field(default_factory=SignalScoringConfig)
    stance: StanceConfig = field(default_factory=StanceConfig)
    report_generation: ReportGenerationConfig = field(default_factory=ReportGenerationConfig)
    input_validation: InputValidationConfig = field(default_factory=InputValidationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


# Global config instance (singleton pattern)
_config_instance: CIRAGConfig = None


def get_config() -> CIRAGConfig:
    """Get or create global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = CIRAGConfig()
    return _config_instance


def reset_config():
    """Reset configuration to defaults (useful for testing)"""
    global _config_instance
    _config_instance = None


# Convenience accessors for frequently used configs
def get_signal_config() -> SignalScoringConfig:
    """Get signal scoring configuration"""
    return get_config().signal_scoring


def get_stance_config() -> StanceConfig:
    """Get stance analysis configuration"""
    return get_config().stance


def get_report_config() -> ReportGenerationConfig:
    """Get report generation configuration"""
    return get_config().report_generation


def get_input_validation_config() -> InputValidationConfig:
    """Get input validation configuration"""
    return get_config().input_validation


def get_performance_config() -> PerformanceConfig:
    """Get performance configuration"""
    return get_config().performance


if __name__ == "__main__":
    # Test configuration
    config = get_config()

    print("Signal Scoring Config:")
    print(f"  BASE_CONFIDENCE: {config.signal_scoring.BASE_CONFIDENCE}")
    print(f"  CRITICAL_IMPACT_BOOST: {config.signal_scoring.CRITICAL_IMPACT_BOOST}")

    print("\nStance Config:")
    print(f"  HIGH_OVERLAP_THRESHOLD: {config.stance.HIGH_OVERLAP_THRESHOLD}")
    print(f"  WEIGHTS: {config.stance.WEIGHTS}")

    print("\nReport Generation Config:")
    print(f"  MAX_SUMMARY_BULLETS: {config.report_generation.MAX_SUMMARY_BULLETS}")
    print(f"  MIN_ACTIONS_REQUIRED: {config.report_generation.MIN_ACTIONS_REQUIRED}")

    print("\nInput Validation Config:")
    print(f"  MAX_QUERY_LENGTH: {config.input_validation.MAX_QUERY_LENGTH}")
    print(f"  MAX_DOCUMENTS: {config.input_validation.MAX_DOCUMENTS}")

    print("\nPerformance Config:")
    print(f"  MAX_REGEX_SPLITS: {config.performance.MAX_REGEX_SPLITS}")
    print(f"  MAX_SIGNALS_PER_RUN: {config.performance.MAX_SIGNALS_PER_RUN}")

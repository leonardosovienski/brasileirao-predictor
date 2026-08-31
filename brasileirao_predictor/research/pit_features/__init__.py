"""Scaffold de informação point-in-time; treinamento permanece bloqueado."""

from brasileirao_predictor.research.pit_features.contracts import (
    ExternalResearchGate,
    FeatureDeclaration,
    PITFeatureEvidence,
    PITFeatureExtractor,
    assert_training_unlocked,
)

__all__ = [
    "ExternalResearchGate",
    "FeatureDeclaration",
    "PITFeatureEvidence",
    "PITFeatureExtractor",
    "assert_training_unlocked",
]

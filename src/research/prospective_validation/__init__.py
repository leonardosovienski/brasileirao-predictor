"""Scaffold prospectivo de paper-trading; nunca controla capital real."""

from src.research.prospective_validation.contracts import PaperPick, PaperSettlement
from src.research.prospective_validation.metrics import CohortPolicy, evaluate_cohort, required_sample_size

__all__ = ["CohortPolicy", "PaperPick", "PaperSettlement", "evaluate_cohort", "required_sample_size"]

from dataclasses import dataclass
from enum import Enum
from typing import Any,Dict,List,Optional,Union
import numpy as np

class ImpliedMethod(Enum):
    """Available methods for calculating implied probabilities."""

    MULTIPLICATIVE = "multiplicative"
    ADDITIVE = "additive"
    POWER = "power"
    SHIN = "shin"
    DIFFERENTIAL_MARGIN_WEIGHTING = "differential_margin_weighting"
    ODDS_RATIO = "odds_ratio"
    LOGARITHMIC = "logarithmic"


@dataclass(frozen=True)
class ImpliedProbabilities:
    """
    Type-safe container for implied probability calculations.

    Attributes:
        probabilities: List of implied probabilities
        method: Method used for calculation
        margin: Bookmaker margin (overround)
        market_names: Optional names for each outcome
        method_params: Additional method-specific parameters
    """

    probabilities: List[float]
    method: ImpliedMethod
    margin: float
    market_names: Optional[List[str]] = None
    method_params: Optional[dict] = None

    def __post_init__(self):
        """Validate probabilities sum approximately to 1.0."""
        total = sum(self.probabilities)
        if not 0.95 <= total <= 1.05:  # Allow some tolerance
            raise ValueError(f"Probabilities should sum to ~1.0, got {total}")

        # Validate market_names length if provided
        if self.market_names and len(self.market_names) != len(self.probabilities):
            raise ValueError(
                f"market_names length ({len(self.market_names)}) must match "
                f"probabilities length ({len(self.probabilities)})"
            )

    @property
    def as_percentages(self) -> List[float]:
        """Return probabilities as percentages."""
        return [p * 100 for p in self.probabilities]

    @property
    def most_likely_index(self) -> int:
        """Return index of most likely outcome."""
        return int(np.argmax(self.probabilities))

    @property
    def most_likely_probability(self) -> float:
        """Return probability of most likely outcome."""
        return max(self.probabilities)

    @property
    def most_likely_name(self) -> Optional[str]:
        """Return name of most likely outcome if market_names provided."""
        if self.market_names:
            return self.market_names[self.most_likely_index]
        return None

    @property
    def least_likely_index(self) -> int:
        """Return index of least likely outcome."""
        return int(np.argmin(self.probabilities))

    @property
    def least_likely_probability(self) -> float:
        """Return probability of least likely outcome."""
        return min(self.probabilities)

    @property
    def least_likely_name(self) -> Optional[str]:
        """Return name of least likely outcome if market_names provided."""
        if self.market_names:
            return self.market_names[self.least_likely_index]
        return None

    def get_probability_by_name(self, name: str) -> float:
        """Get probability by outcome name."""
        if not self.market_names:
            raise ValueError("No market names provided")
        try:
            index = self.market_names.index(name)
            return self.probabilities[index]
        except ValueError:
            raise ValueError(f"Market name '{name}' not found in {self.market_names}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy dict format for backward compatibility."""
        result = {
            "implied_probabilities": self.probabilities,
            "method": self.method.value,
            "margin": self.margin,
        }
        if self.method_params:
            result.update(self.method_params)
        return result

    def __getitem__(self, key: Union[int, str]) -> float:
        """Allow indexing by position or name for backward compatibility."""
        if isinstance(key, int):
            return self.probabilities[key]
        elif isinstance(key, str):
            return self.get_probability_by_name(key)
        else:
            raise TypeError(f"Index must be int or str, got {type(key)}")

    def __len__(self) -> int:
        """Return number of probabilities."""
        return len(self.probabilities)

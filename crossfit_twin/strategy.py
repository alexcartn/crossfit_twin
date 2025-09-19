"""
Strategy module for CrossFit Digital Twin.

Contains classes for modeling different pacing strategies for WOD execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, Protocol
from abc import ABC, abstractmethod
from enum import Enum


class PacingStyle(Enum):
    """Enumeration of different pacing styles."""
    UNBROKEN = "unbroken"
    EVEN_SPLIT = "even_split"
    DESCENDING = "descending"
    ASCENDING = "ascending"
    NEGATIVE_SPLIT = "negative_split"
    POSITIVE_SPLIT = "positive_split"
    CONSERVATIVE = "conservative"


@dataclass
class RestPattern:
    """
    Defines a rest pattern for an exercise.
    
    Attributes:
        reps_before_rest: Number of reps to perform before taking rest
        rest_duration_seconds: Duration of rest in seconds
        max_consecutive_reps: Maximum reps to do consecutively (for fatigue limits)
    """
    
    reps_before_rest: int
    rest_duration_seconds: float
    max_consecutive_reps: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate rest pattern parameters."""
        if self.reps_before_rest <= 0:
            raise ValueError("reps_before_rest must be positive")
        if self.rest_duration_seconds < 0:
            raise ValueError("rest_duration_seconds cannot be negative")
        if self.max_consecutive_reps is not None and self.max_consecutive_reps <= 0:
            raise ValueError("max_consecutive_reps must be positive")


class PacingDecision(Protocol):
    """Protocol for pacing decisions during workout execution."""
    
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """Determine if athlete should rest before the next rep."""
        ...
    
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """Determine how long to rest."""
        ...


@dataclass
class Strategy(ABC):
    """
    Abstract base class for workout pacing strategies.
    
    Attributes:
        name: Strategy name for identification
        description: Description of the strategy approach
        exercise_patterns: Exercise-specific rest patterns
        global_fatigue_threshold: Global fatigue level that forces rest
        target_intensity: Target intensity level (0.0 to 1.0)
    """
    
    name: str
    description: str
    exercise_patterns: Dict[str, RestPattern] = field(default_factory=dict)
    global_fatigue_threshold: float = 0.8
    target_intensity: float = 0.85
    
    def __post_init__(self) -> None:
        """Validate strategy parameters."""
        if not 0.0 <= self.global_fatigue_threshold <= 1.0:
            raise ValueError("global_fatigue_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.target_intensity <= 1.0:
            raise ValueError("target_intensity must be between 0.0 and 1.0")
    
    @abstractmethod
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """
        Determine if the athlete should rest before the next repetition.
        
        Args:
            exercise_name: Name of the current exercise
            current_rep: Current repetition number (1-indexed)
            total_reps: Total repetitions for this exercise set
            current_fatigue: Current fatigue level (0.0 to 1.0+)
            time_elapsed: Time elapsed in workout (seconds)
            
        Returns:
            True if athlete should rest, False otherwise
        """
        pass
    
    @abstractmethod
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """
        Determine how long the athlete should rest.
        
        Args:
            exercise_name: Name of the current exercise
            current_rep: Current repetition number
            current_fatigue: Current fatigue level
            time_elapsed: Time elapsed in workout (seconds)
            
        Returns:
            Rest duration in seconds
        """
        pass
    
    def get_set_breakdown(self, exercise_name: str, total_reps: int) -> List[int]:
        """
        Get the breakdown of reps into sets for an exercise.
        
        Args:
            exercise_name: Name of the exercise
            total_reps: Total repetitions to break down
            
        Returns:
            List of rep counts for each set
        """
        if exercise_name in self.exercise_patterns:
            pattern = self.exercise_patterns[exercise_name]
            set_size = pattern.reps_before_rest
            
            sets = []
            remaining = total_reps
            while remaining > 0:
                sets.append(min(set_size, remaining))
                remaining -= set_size
            
            return sets
        else:
            # Default: try to do all unbroken
            return [total_reps]


@dataclass
class UnbrokenStrategy(Strategy):
    """Strategy that attempts to perform exercises unbroken (no planned rest)."""
    
    def __init__(self, fatigue_threshold: float = 0.9):
        super().__init__(
            name="Unbroken",
            description="Attempt all reps unbroken, only rest when forced by fatigue",
            global_fatigue_threshold=fatigue_threshold,
            target_intensity=0.95
        )
    
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """Only rest if fatigue exceeds threshold."""
        return current_fatigue >= self.global_fatigue_threshold
    
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """Rest duration based on fatigue level."""
        if current_fatigue < 0.5:
            return 5.0  # Short rest
        elif current_fatigue < 0.8:
            return 10.0  # Medium rest
        else:
            return 20.0  # Long rest for high fatigue


@dataclass  
class FractionedStrategy(Strategy):
    """Strategy that breaks exercises into predetermined sets with planned rest."""
    
    def __init__(
        self,
        exercise_patterns: Dict[str, RestPattern],
        name: str = "Fractioned",
        fatigue_threshold: float = 0.7
    ):
        super().__init__(
            name=name,
            description="Break exercises into planned sets with strategic rest",
            exercise_patterns=exercise_patterns,
            global_fatigue_threshold=fatigue_threshold,
            target_intensity=0.8
        )
    
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """Rest based on planned pattern or fatigue threshold."""
        # Always rest if fatigue is too high
        if current_fatigue >= self.global_fatigue_threshold:
            return True
        
        # Check if we should rest based on the pattern
        if exercise_name in self.exercise_patterns:
            pattern = self.exercise_patterns[exercise_name]
            
            # Check if we've hit the planned rest point
            if current_rep > 0 and current_rep % pattern.reps_before_rest == 0:
                return True
            
            # Check max consecutive reps limit
            if pattern.max_consecutive_reps is not None:
                reps_in_current_set = current_rep % pattern.reps_before_rest
                if reps_in_current_set == 0:
                    reps_in_current_set = pattern.reps_before_rest
                if reps_in_current_set >= pattern.max_consecutive_reps:
                    return True
        
        return False
    
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """Rest duration from pattern or based on fatigue."""
        if exercise_name in self.exercise_patterns:
            base_rest = self.exercise_patterns[exercise_name].rest_duration_seconds
            
            # Adjust rest based on fatigue
            fatigue_multiplier = 1.0 + current_fatigue * 0.5
            return base_rest * fatigue_multiplier
        else:
            # Default rest based on fatigue
            return 5.0 + current_fatigue * 10.0


@dataclass
class DescendingStrategy(Strategy):
    """Strategy that uses descending set sizes to manage fatigue."""
    
    def __init__(
        self,
        exercise_patterns: Optional[Dict[str, RestPattern]] = None,
        fatigue_threshold: float = 0.75
    ):
        super().__init__(
            name="Descending",
            description="Use descending set sizes (e.g., 6-5-4-3-2) to maintain pace",
            exercise_patterns=exercise_patterns or {},
            global_fatigue_threshold=fatigue_threshold,
            target_intensity=0.82
        )
        self._set_breakdowns: Dict[str, List[int]] = {}
    
    def get_set_breakdown(self, exercise_name: str, total_reps: int) -> List[int]:
        """Generate descending set breakdown."""
        cache_key = f"{exercise_name}_{total_reps}"
        
        if cache_key not in self._set_breakdowns:
            sets = self._generate_descending_sets(total_reps)
            self._set_breakdowns[cache_key] = sets
        
        return self._set_breakdowns[cache_key]
    
    def _generate_descending_sets(self, total_reps: int) -> List[int]:
        """Generate descending set sizes that sum to total_reps."""
        if total_reps <= 5:
            return [total_reps]
        
        sets = []
        remaining = total_reps
        
        # Start with a reasonably large first set
        current_set_size = min(total_reps // 3, 10)
        
        while remaining > 0:
            if remaining <= current_set_size * 1.5:
                # Last set or two - split remaining evenly
                if remaining <= current_set_size:
                    sets.append(remaining)
                    break
                else:
                    # Split into two roughly equal sets
                    first = remaining // 2
                    second = remaining - first
                    sets.extend([first, second])
                    break
            else:
                sets.append(current_set_size)
                remaining -= current_set_size
                current_set_size = max(1, current_set_size - 1)
        
        return sets
    
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """Rest based on descending pattern and fatigue."""
        if current_fatigue >= self.global_fatigue_threshold:
            return True
        
        # Get the planned breakdown and check if we're at a set boundary
        breakdown = self.get_set_breakdown(exercise_name, total_reps)
        
        reps_completed = 0
        for set_size in breakdown:
            reps_completed += set_size
            if current_rep == reps_completed and current_rep < total_reps:
                return True
        
        return False
    
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """Progressive rest - longer rests as fatigue increases."""
        base_rest = 8.0  # Base rest between sets
        fatigue_addition = current_fatigue * 12.0  # Add more rest for higher fatigue
        return base_rest + fatigue_addition


@dataclass
class ConservativeStrategy(Strategy):
    """Conservative strategy that prioritizes consistent pace over speed."""
    
    def __init__(
        self,
        exercise_patterns: Optional[Dict[str, RestPattern]] = None,
        fatigue_threshold: float = 0.6
    ):
        super().__init__(
            name="Conservative",
            description="Maintain low fatigue with frequent short rests for consistent pace",
            exercise_patterns=exercise_patterns or {},
            global_fatigue_threshold=fatigue_threshold,
            target_intensity=0.7
        )
    
    def should_rest(
        self,
        exercise_name: str,
        current_rep: int,
        total_reps: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> bool:
        """Rest proactively to keep fatigue low."""
        # Rest if fatigue gets moderate
        if current_fatigue >= self.global_fatigue_threshold:
            return True
        
        # Use pattern if available
        if exercise_name in self.exercise_patterns:
            pattern = self.exercise_patterns[exercise_name]
            if current_rep > 0 and current_rep % pattern.reps_before_rest == 0:
                return True
        else:
            # Default: rest every 5-8 reps depending on fatigue
            rest_frequency = max(5, int(8 - current_fatigue * 3))
            if current_rep > 0 and current_rep % rest_frequency == 0:
                return True
        
        return False
    
    def rest_duration(
        self,
        exercise_name: str,
        current_rep: int,
        current_fatigue: float,
        time_elapsed: float
    ) -> float:
        """Short, consistent rest periods."""
        if exercise_name in self.exercise_patterns:
            return self.exercise_patterns[exercise_name].rest_duration_seconds
        else:
            # Short rests to maintain low fatigue
            return 3.0 + current_fatigue * 5.0


# Factory class for creating common strategies
class StrategyFactory:
    """Factory for creating common pacing strategies."""
    
    @staticmethod
    def unbroken(fatigue_threshold: float = 0.9) -> UnbrokenStrategy:
        """Create an unbroken strategy."""
        return UnbrokenStrategy(fatigue_threshold)
    
    @staticmethod
    def fractioned(
        patterns: Dict[str, Tuple[int, float]],
        fatigue_threshold: float = 0.7
    ) -> FractionedStrategy:
        """
        Create a fractioned strategy.
        
        Args:
            patterns: Dict mapping exercise names to (reps_before_rest, rest_duration) tuples
            fatigue_threshold: Global fatigue threshold
        """
        rest_patterns = {
            exercise: RestPattern(reps_before_rest=reps, rest_duration_seconds=duration)
            for exercise, (reps, duration) in patterns.items()
        }
        return FractionedStrategy(rest_patterns, fatigue_threshold=fatigue_threshold)
    
    @staticmethod
    def descending(fatigue_threshold: float = 0.75) -> DescendingStrategy:
        """Create a descending strategy."""
        return DescendingStrategy(fatigue_threshold=fatigue_threshold)
    
    @staticmethod
    def conservative(
        patterns: Optional[Dict[str, Tuple[int, float]]] = None,
        fatigue_threshold: float = 0.6
    ) -> ConservativeStrategy:
        """Create a conservative strategy."""
        rest_patterns = {}
        if patterns:
            rest_patterns = {
                exercise: RestPattern(reps_before_rest=reps, rest_duration_seconds=duration)
                for exercise, (reps, duration) in patterns.items()
            }
        return ConservativeStrategy(rest_patterns, fatigue_threshold=fatigue_threshold)
    
    @staticmethod
    def for_workout_type(workout_type: str, **kwargs) -> Strategy:
        """Create a strategy optimized for a specific workout type."""
        if workout_type.lower() in ["sprint", "short", "for_time_short"]:
            return StrategyFactory.unbroken(fatigue_threshold=0.95)
        elif workout_type.lower() in ["medium", "for_time_medium"]:
            return StrategyFactory.descending(fatigue_threshold=0.8)
        elif workout_type.lower() in ["long", "amrap", "endurance"]:
            return StrategyFactory.conservative(fatigue_threshold=0.6)
        else:
            return StrategyFactory.fractioned({}, fatigue_threshold=0.75)
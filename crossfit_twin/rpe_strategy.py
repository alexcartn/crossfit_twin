"""
RPE-based Strategy System for CrossFit Digital Twin.

Implements strategy selection and pacing based on intended RPE (Rate of Perceived Exertion).
Replaces abstract strategy parameters with concrete, RPE-driven constraints.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math


class RPELevel(Enum):
    """RPE levels with descriptions for user interface."""
    RECOVERY = (0, 1, "Recovery - Very light activity")
    EASY = (2, 3, "Easy - Light effort, can maintain conversation")
    MODERATE = (4, 5, "Moderate - Some effort, can speak in phrases")
    VIGOROUS = (6, 7, "Vigorous - Hard effort, limited speech")
    VERY_HARD = (8, 9, "Very Hard - Very hard effort, one word responses")
    MAXIMAL = (10, 10, "Maximal - All-out effort, cannot speak")

    def __init__(self, min_rpe: int, max_rpe: int, description: str):
        self.min_rpe = min_rpe
        self.max_rpe = max_rpe
        self.description = description

    @classmethod
    def from_rpe(cls, rpe: int) -> 'RPELevel':
        """Get RPE level from numeric RPE."""
        rpe = max(0, min(10, rpe))
        for level in cls:
            if level.min_rpe <= rpe <= level.max_rpe:
                return level
        return cls.MODERATE


@dataclass
class RPEConstraints:
    """
    RPE-based constraints for workout execution.

    These constraints guide strategy selection and pacing decisions.
    """
    target_rpe: int                 # Intended RPE (0-10)

    # Load constraints
    max_load_pct: float            # Maximum % of 1RM to use
    preferred_load_pct: float      # Preferred % of 1RM for repeated efforts

    # Set size constraints
    max_set_fraction: float        # Maximum fraction of unbroken capacity to use
    preferred_set_fraction: float  # Preferred fraction for repeated sets

    # Cardiovascular constraints
    max_cardio_intensity: float    # Maximum intensity above CP (as fraction of W')
    cardio_reserve: float          # Minimum W'bal to maintain (as fraction)

    # Rest constraints
    min_rest_between_sets: float   # Minimum rest between sets (seconds)
    min_rest_between_movements: float  # Minimum rest between movements (seconds)

    # Fatigue thresholds
    local_fatigue_threshold: float     # Stop sets when local fatigue exceeds this
    global_fatigue_threshold: float    # Reduce intensity when global fatigue exceeds this


def rpe_to_constraints(rpe: int) -> RPEConstraints:
    """
    Convert RPE to concrete workout constraints.

    Args:
        rpe: Intended RPE (0-10)

    Returns:
        RPEConstraints object with appropriate limits
    """
    rpe = max(0, min(10, rpe))

    # Linear interpolation for most parameters
    def lerp(low_val: float, high_val: float, t: float) -> float:
        return low_val + (high_val - low_val) * t

    # Normalize RPE to 0-1 scale
    t = rpe / 10.0

    return RPEConstraints(
        target_rpe=rpe,

        # Load constraints: RPE 0 → 50% max, RPE 10 → 95% max
        max_load_pct=lerp(0.50, 0.95, t),
        preferred_load_pct=lerp(0.40, 0.80, t),

        # Set size: RPE 0 → 30% capacity, RPE 10 → 90% capacity
        max_set_fraction=lerp(0.30, 0.90, t),
        preferred_set_fraction=lerp(0.25, 0.70, t),

        # Cardio intensity: RPE 0 → 20% above CP, RPE 10 → 80% above CP
        max_cardio_intensity=lerp(0.20, 0.80, t),
        cardio_reserve=lerp(0.50, 0.10, 1.0 - t),  # More reserve at lower RPE

        # Rest periods: More rest at lower RPE
        min_rest_between_sets=lerp(15.0, 3.0, t),
        min_rest_between_movements=lerp(30.0, 5.0, t),

        # Fatigue thresholds: More conservative at lower RPE
        local_fatigue_threshold=lerp(0.3, 1.2, t),
        global_fatigue_threshold=lerp(0.2, 0.8, t),
    )


@dataclass
class SetScheme:
    """
    Concrete set scheme for an exercise within a round.
    """
    reps_per_set: List[int]     # Reps in each set
    rest_between_sets: List[float]  # Rest after each set (seconds)
    load_kg: Optional[float] = None     # Load for weighted exercises

    @property
    def total_reps(self) -> int:
        """Total reps across all sets."""
        return sum(self.reps_per_set)

    @property
    def total_sets(self) -> int:
        """Number of sets."""
        return len(self.reps_per_set)

    @property
    def total_rest_time(self) -> float:
        """Total rest time in seconds."""
        return sum(self.rest_between_sets)


class RPEStrategy:
    """
    Strategy class that makes pacing decisions based on RPE constraints.
    """

    def __init__(self, constraints: RPEConstraints):
        """
        Initialize RPE strategy.

        Args:
            constraints: RPE-based constraints for the workout
        """
        self.constraints = constraints

    def calculate_set_scheme(
        self,
        exercise: str,
        total_reps: int,
        unbroken_capacity: int,
        current_local_fatigue: float,
        one_rm_kg: Optional[float] = None
    ) -> SetScheme:
        """
        Calculate optimal set scheme for an exercise.

        Args:
            exercise: Exercise name
            total_reps: Total reps required
            unbroken_capacity: Maximum unbroken reps when fresh
            current_local_fatigue: Current local fatigue level
            one_rm_kg: 1RM for the exercise (if applicable)

        Returns:
            SetScheme with rep distribution and rest periods
        """
        # Adjust capacity for current fatigue
        fatigue_factor = 1.0 + current_local_fatigue * 0.3
        effective_capacity = max(1, int(unbroken_capacity / fatigue_factor))

        # Apply RPE constraints to set size
        max_set_size = max(1, int(effective_capacity * self.constraints.max_set_fraction))
        preferred_set_size = max(1, int(effective_capacity * self.constraints.preferred_set_fraction))

        # Calculate set breakdown
        if total_reps <= preferred_set_size:
            # Can do unbroken
            reps_per_set = [total_reps]
            rest_between_sets = [0.0]
        else:
            # Need to break into sets
            reps_per_set = []
            remaining_reps = total_reps

            while remaining_reps > 0:
                # Determine set size (start with preferred, adjust based on fatigue)
                current_set_size = min(preferred_set_size, remaining_reps)

                # Slightly reduce set size as fatigue accumulates
                if len(reps_per_set) > 0:
                    fatigue_reduction = len(reps_per_set) * 0.1
                    current_set_size = max(1, int(current_set_size * (1 - fatigue_reduction)))

                reps_per_set.append(current_set_size)
                remaining_reps -= current_set_size

            # Calculate rest periods
            rest_between_sets = []
            for i in range(len(reps_per_set)):
                if i == len(reps_per_set) - 1:
                    # No rest after last set
                    rest_between_sets.append(0.0)
                else:
                    # Scale rest based on set size and fatigue
                    base_rest = self.constraints.min_rest_between_sets
                    set_factor = reps_per_set[i] / preferred_set_size
                    fatigue_factor = 1.0 + current_local_fatigue * 0.5

                    rest_time = base_rest * set_factor * fatigue_factor
                    rest_between_sets.append(rest_time)

        # Determine load for weighted exercises
        load_kg = None
        if one_rm_kg is not None:
            load_kg = one_rm_kg * self.constraints.preferred_load_pct

        return SetScheme(
            reps_per_set=reps_per_set,
            rest_between_sets=rest_between_sets,
            load_kg=load_kg
        )

    def calculate_cardio_pacing(
        self,
        modality: str,
        distance_or_calories: float,
        cp: float,
        w_prime_max: float,
        current_wbal: float
    ) -> Tuple[float, float]:
        """
        Calculate pacing for cardio segments.

        Args:
            modality: Cardio modality
            distance_or_calories: Target distance (m) or calories
            cp: Critical Power/Speed
            w_prime_max: Maximum W'/D' capacity
            current_wbal: Current W'bal

        Returns:
            Tuple of (target_power_or_speed, estimated_duration)
        """
        # Available anaerobic capacity above reserve
        available_wbal = current_wbal - (w_prime_max * self.constraints.cardio_reserve)
        available_wbal = max(0, available_wbal)

        # Maximum intensity we're willing to use
        max_intensity_above_cp = w_prime_max * self.constraints.max_cardio_intensity

        # Conservative pacing: use fraction of available capacity
        target_intensity_above_cp = min(max_intensity_above_cp, available_wbal * 0.8)

        target_power_or_speed = cp + (target_intensity_above_cp / 60.0)  # Assume ~60s duration

        # Estimate duration based on distance/calories and target intensity
        if modality in ['run', 'swim']:
            # Distance-based
            estimated_duration = distance_or_calories / target_power_or_speed
        else:
            # Power-based (bike, row) - simplified
            estimated_duration = distance_or_calories / (target_power_or_speed / 15.0)  # Rough conversion

        return target_power_or_speed, estimated_duration

    def should_continue_set(
        self,
        current_reps_in_set: int,
        planned_reps_in_set: int,
        current_local_fatigue: float,
        current_global_fatigue: float
    ) -> bool:
        """
        Decide whether to continue current set or rest.

        Args:
            current_reps_in_set: Reps completed in current set
            planned_reps_in_set: Planned reps for this set
            current_local_fatigue: Current local fatigue
            current_global_fatigue: Current global fatigue

        Returns:
            True if should continue set, False if should rest
        """
        # Check if we've completed planned reps
        if current_reps_in_set >= planned_reps_in_set:
            return False

        # Check fatigue thresholds
        if current_local_fatigue > self.constraints.local_fatigue_threshold:
            return False

        if current_global_fatigue > self.constraints.global_fatigue_threshold:
            return False

        return True

    def calculate_movement_transition_rest(
        self,
        from_exercise: str,
        to_exercise: str,
        current_fatigue_levels: Dict[str, float]
    ) -> float:
        """
        Calculate rest time between different movements.

        Args:
            from_exercise: Previous exercise
            to_exercise: Next exercise
            current_fatigue_levels: Current fatigue by movement pattern

        Returns:
            Rest time in seconds
        """
        base_rest = self.constraints.min_rest_between_movements

        # Increase rest if exercises share movement patterns
        from .fatigue_models import MOVEMENT_PATTERNS
        from_patterns = set(MOVEMENT_PATTERNS.get(from_exercise, []))
        to_patterns = set(MOVEMENT_PATTERNS.get(to_exercise, []))

        overlap = len(from_patterns & to_patterns)
        if overlap > 0:
            # More rest for overlapping movement patterns
            base_rest *= (1.0 + overlap * 0.5)

        # Scale by current fatigue levels
        max_fatigue = max(current_fatigue_levels.values()) if current_fatigue_levels else 0.0
        fatigue_multiplier = 1.0 + max_fatigue * 0.3

        return base_rest * fatigue_multiplier

    def get_strategy_description(self) -> str:
        """
        Get human-readable description of the strategy.

        Returns:
            Strategy description string
        """
        rpe_level = RPELevel.from_rpe(self.constraints.target_rpe)

        return f"""RPE {self.constraints.target_rpe} Strategy - {rpe_level.description}

Load: {self.constraints.preferred_load_pct:.0%} of 1RM (max {self.constraints.max_load_pct:.0%})
Set Size: {self.constraints.preferred_set_fraction:.0%} of capacity (max {self.constraints.max_set_fraction:.0%})
Cardio: {self.constraints.max_cardio_intensity:.0%} above CP, {self.constraints.cardio_reserve:.0%} reserve
Rest: {self.constraints.min_rest_between_sets:.0f}s between sets, {self.constraints.min_rest_between_movements:.0f}s between movements"""


def create_rpe_strategy(rpe: int) -> RPEStrategy:
    """
    Create an RPE strategy for the given RPE level.

    Args:
        rpe: Intended RPE (0-10)

    Returns:
        RPEStrategy configured for the RPE level
    """
    constraints = rpe_to_constraints(rpe)
    return RPEStrategy(constraints)
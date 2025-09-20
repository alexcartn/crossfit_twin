"""
Fatigue and Recovery Models for CrossFit Digital Twin.

Implements physiological fatigue models replacing the abstract 0-100 system:
- W'bal model for cardiovascular fatigue
- Local muscle fatigue buckets for different movement patterns
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum
import math


class MovementPattern(Enum):
    """Primary movement patterns for local fatigue tracking."""
    PULL = "pull"           # Pull-ups, rows, muscle-ups
    PUSH = "push"           # Push-ups, HSPU, presses
    SQUAT = "squat"         # Squats, wall-balls, box-jumps
    HINGE = "hinge"         # Deadlifts, KB swings, burpees
    CORE = "core"           # Sit-ups, toes-to-bar, L-sits
    GRIP = "grip"           # Rope climbs, farmer's carries
    MIXED = "mixed"         # Complex movements like thrusters


# Movement to pattern mapping
MOVEMENT_PATTERNS = {
    # Gymnastics
    'pull-up': [MovementPattern.PULL, MovementPattern.GRIP],
    'chin-up': [MovementPattern.PULL, MovementPattern.GRIP],
    'muscle-up': [MovementPattern.PULL, MovementPattern.PUSH, MovementPattern.GRIP],
    'handstand-pushup': [MovementPattern.PUSH],
    'push-up': [MovementPattern.PUSH],
    'dip': [MovementPattern.PUSH],
    'toes-to-bar': [MovementPattern.CORE, MovementPattern.GRIP],
    'knees-to-elbows': [MovementPattern.CORE, MovementPattern.GRIP],
    'sit-up': [MovementPattern.CORE],
    'l-sit': [MovementPattern.CORE],

    # Weightlifting
    'squat': [MovementPattern.SQUAT],
    'front-squat': [MovementPattern.SQUAT],
    'back-squat': [MovementPattern.SQUAT],
    'overhead-squat': [MovementPattern.SQUAT, MovementPattern.PUSH],
    'deadlift': [MovementPattern.HINGE],
    'sumo-deadlift': [MovementPattern.HINGE],
    'clean': [MovementPattern.HINGE, MovementPattern.PULL],
    'snatch': [MovementPattern.HINGE, MovementPattern.PULL, MovementPattern.PUSH],
    'overhead-press': [MovementPattern.PUSH],
    'push-press': [MovementPattern.PUSH, MovementPattern.SQUAT],
    'push-jerk': [MovementPattern.PUSH, MovementPattern.SQUAT],
    'bench-press': [MovementPattern.PUSH],
    'thruster': [MovementPattern.SQUAT, MovementPattern.PUSH],

    # Other common movements
    'wall-ball': [MovementPattern.SQUAT],
    'box-jump': [MovementPattern.SQUAT],
    'burpee': [MovementPattern.HINGE, MovementPattern.PUSH],
    'kettlebell-swing': [MovementPattern.HINGE],
    'double-under': [MovementPattern.SQUAT],  # Light loading
    'air-squat': [MovementPattern.SQUAT],
}


@dataclass
class WBalState:
    """
    W'bal (W' balance) state for cardiovascular fatigue tracking.

    Based on Skiba et al. model for anaerobic work capacity.
    """
    modality: str                   # 'bike', 'row', 'run', 'swim'
    w_prime_max: float             # Maximum W' capacity (J or m)
    w_bal_current: float           # Current W' balance
    tau_recovery: float = 300.0    # Recovery time constant (seconds)

    def __post_init__(self):
        """Initialize W'bal to maximum capacity."""
        if self.w_bal_current is None:
            self.w_bal_current = self.w_prime_max

    def update(self, power_demand: float, cp: float, duration_s: float) -> None:
        """
        Update W'bal based on power demand and duration.

        Args:
            power_demand: Demanded power (W) or speed (m/s)
            cp: Critical power (W) or critical speed (m/s)
            duration_s: Duration of the interval
        """
        if power_demand <= cp:
            # Below CP: recovery
            deficit = self.w_prime_max - self.w_bal_current
            if deficit > 0:
                # Exponential recovery
                recovery = deficit * (1 - math.exp(-duration_s / self.tau_recovery))
                self.w_bal_current = min(self.w_prime_max, self.w_bal_current + recovery)
        else:
            # Above CP: depletion
            work_above_cp = (power_demand - cp) * duration_s
            self.w_bal_current = max(0, self.w_bal_current - work_above_cp)

    def get_fatigue_factor(self) -> float:
        """
        Get fatigue factor based on current W'bal state.

        Returns:
            Fatigue factor (0.0 = no fatigue, 1.0+ = significant fatigue)
        """
        if self.w_prime_max <= 0:
            return 0.0

        depletion_ratio = 1.0 - (self.w_bal_current / self.w_prime_max)
        # Exponential scaling: more sensitive at high depletion
        return depletion_ratio ** 0.7

    def can_sustain_power(self, power: float, cp: float, duration_s: float) -> bool:
        """
        Check if current W'bal can sustain given power for duration.

        Args:
            power: Required power
            cp: Critical power
            duration_s: Required duration

        Returns:
            True if sustainable, False otherwise
        """
        if power <= cp:
            return True  # Sustainable at or below CP

        required_work = (power - cp) * duration_s
        return self.w_bal_current >= required_work


@dataclass
class LocalFatigueState:
    """
    Local muscle fatigue state for movement pattern.

    Tracks fatigue accumulation and recovery for specific muscle groups.
    """
    pattern: MovementPattern
    fatigue_level: float = 0.0      # Current fatigue (0.0 = fresh, 1.0+ = fatigued)
    accumulation_rate: float = 0.1  # How quickly fatigue accumulates
    recovery_rate: float = 0.05     # How quickly fatigue recovers per second

    def add_fatigue(self, load_factor: float, reps: int) -> None:
        """
        Add fatigue from performing reps at given load.

        Args:
            load_factor: Load intensity factor (0.0-1.0+)
            reps: Number of repetitions
        """
        # Fatigue accumulation with load and rep scaling
        base_fatigue = self.accumulation_rate * reps
        load_scaling = 1.0 + load_factor  # Higher loads = more fatigue
        rep_scaling = 1.0 + (reps / 20.0) * 0.3  # More reps = diminishing efficiency

        total_fatigue = base_fatigue * load_scaling * rep_scaling
        self.fatigue_level += total_fatigue

    def recover(self, duration_s: float, recovery_quality: float = 1.0) -> None:
        """
        Recover fatigue over time.

        Args:
            duration_s: Recovery duration in seconds
            recovery_quality: Recovery quality multiplier (e.g., based on context)
        """
        if self.fatigue_level > 0:
            # Exponential recovery with diminishing returns
            recovery_amount = self.fatigue_level * (1 - math.exp(-self.recovery_rate * duration_s))
            recovery_amount *= recovery_quality
            self.fatigue_level = max(0.0, self.fatigue_level - recovery_amount)

    def get_performance_degradation(self) -> float:
        """
        Get performance degradation factor.

        Returns:
            Degradation factor (1.0 = no degradation, >1.0 = slower performance)
        """
        # Logarithmic scaling to avoid extreme degradation
        return 1.0 + (math.log(1 + self.fatigue_level) * 0.3)


@dataclass
class FatigueManager:
    """
    Manages all fatigue states for an athlete during a workout.
    """
    # Cardiovascular fatigue (W'bal) by modality
    wbal_states: Dict[str, WBalState] = field(default_factory=dict)

    # Local muscle fatigue by movement pattern
    local_fatigue: Dict[MovementPattern, LocalFatigueState] = field(default_factory=dict)

    # Global fatigue accumulator
    global_fatigue: float = 0.0
    global_recovery_rate: float = 0.02

    def __post_init__(self):
        """Initialize local fatigue states for all movement patterns."""
        for pattern in MovementPattern:
            if pattern not in self.local_fatigue:
                self.local_fatigue[pattern] = LocalFatigueState(pattern=pattern)

    def initialize_wbal(self, modality: str, w_prime_max: float, tau_recovery: float = 300.0) -> None:
        """
        Initialize W'bal state for a modality.

        Args:
            modality: Modality name ('bike', 'row', 'run', 'swim')
            w_prime_max: Maximum W' capacity
            tau_recovery: Recovery time constant
        """
        self.wbal_states[modality] = WBalState(
            modality=modality,
            w_prime_max=w_prime_max,
            w_bal_current=w_prime_max,
            tau_recovery=tau_recovery
        )

    def add_cardio_fatigue(self, modality: str, power_demand: float, cp: float, duration_s: float) -> None:
        """
        Add cardiovascular fatigue for a modality.

        Args:
            modality: Modality name
            power_demand: Power or speed demand
            cp: Critical power or speed
            duration_s: Duration
        """
        if modality in self.wbal_states:
            self.wbal_states[modality].update(power_demand, cp, duration_s)

    def add_local_fatigue(self, movement: str, load_factor: float, reps: int) -> None:
        """
        Add local fatigue for a movement.

        Args:
            movement: Movement name
            load_factor: Load intensity (e.g., % of 1RM)
            reps: Number of reps
        """
        patterns = MOVEMENT_PATTERNS.get(movement, [MovementPattern.MIXED])

        for pattern in patterns:
            if pattern in self.local_fatigue:
                # Distribute fatigue across patterns (if multiple)
                distributed_load = load_factor / len(patterns)
                self.local_fatigue[pattern].add_fatigue(distributed_load, reps)

        # Add to global fatigue
        self.global_fatigue += 0.01 * reps * (1 + load_factor)

    def recover_all(self, duration_s: float, recovery_quality: float = 1.0) -> None:
        """
        Apply recovery to all fatigue systems.

        Args:
            duration_s: Recovery duration
            recovery_quality: Quality multiplier (based on context, nutrition, etc.)
        """
        # Local fatigue recovery
        for local_state in self.local_fatigue.values():
            local_state.recover(duration_s, recovery_quality)

        # Global fatigue recovery
        if self.global_fatigue > 0:
            global_recovery = self.global_fatigue * (1 - math.exp(-self.global_recovery_rate * duration_s))
            self.global_fatigue = max(0.0, self.global_fatigue - global_recovery * recovery_quality)

    def get_movement_fatigue(self, movement: str) -> float:
        """
        Get effective fatigue level for a movement.

        Args:
            movement: Movement name

        Returns:
            Combined fatigue level affecting this movement
        """
        patterns = MOVEMENT_PATTERNS.get(movement, [MovementPattern.MIXED])

        if not patterns:
            return self.global_fatigue

        # Average fatigue across relevant patterns
        total_fatigue = sum(self.local_fatigue[pattern].fatigue_level for pattern in patterns)
        pattern_fatigue = total_fatigue / len(patterns)

        # Combine with global fatigue (non-linearly)
        combined_fatigue = pattern_fatigue + self.global_fatigue * 0.3

        return combined_fatigue

    def get_cardio_fatigue(self, modality: str) -> float:
        """
        Get cardiovascular fatigue factor for modality.

        Args:
            modality: Modality name

        Returns:
            Fatigue factor (0.0-1.0+)
        """
        if modality in self.wbal_states:
            return self.wbal_states[modality].get_fatigue_factor()
        return 0.0

    def can_sustain_cardio_power(self, modality: str, power: float, cp: float, duration_s: float) -> bool:
        """
        Check if athlete can sustain cardio power for duration.

        Args:
            modality: Modality name
            power: Required power/speed
            cp: Critical power/speed
            duration_s: Duration

        Returns:
            True if sustainable
        """
        if modality in self.wbal_states:
            return self.wbal_states[modality].can_sustain_power(power, cp, duration_s)
        return True  # If no W'bal tracking, assume sustainable

    def get_fatigue_summary(self) -> Dict[str, float]:
        """
        Get summary of all fatigue states.

        Returns:
            Dictionary with fatigue levels for each system
        """
        summary = {
            'global': self.global_fatigue
        }

        # Local fatigue
        for pattern, state in self.local_fatigue.items():
            summary[f'local_{pattern.value}'] = state.fatigue_level

        # Cardio fatigue
        for modality, state in self.wbal_states.items():
            summary[f'cardio_{modality}'] = state.get_fatigue_factor()

        return summary

    def reset_all_fatigue(self) -> None:
        """Reset all fatigue states to fresh."""
        self.global_fatigue = 0.0

        for state in self.local_fatigue.values():
            state.fatigue_level = 0.0

        for state in self.wbal_states.values():
            state.w_bal_current = state.w_prime_max
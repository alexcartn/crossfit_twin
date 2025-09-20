"""
New Athlete System for CrossFit Digital Twin.

Integrates concrete capabilities, fatigue models, and context effects
to replace the abstract 0-100 scoring system.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
import copy

from .capabilities import AthleteCapabilities
from .fatigue_models import FatigueManager, MovementPattern
from .rpe_strategy import RPEStrategy, create_rpe_strategy


@dataclass
class ContextParams:
    """Environmental context parameters affecting performance."""
    temperature_c: float = 20.0
    humidity_pct: float = 50.0
    altitude_m: float = 0.0


@dataclass
class DayState:
    """Daily state parameters affecting performance."""
    sleep_h: float = 7.5
    sleep_quality: int = 3  # 1-5 scale
    water_l: float = 2.0
    body_mass_kg: float = 75.0
    rpe_intended: int = 5   # 0-10 scale for workout intention


class AthleteV2:
    """
    New athlete class using concrete physiological parameters.

    Integrates:
    - AthleteCapabilities (1RM, CP/W', gym skills)
    - FatigueManager (W'bal, local fatigue)
    - Context effects (temperature, altitude, hydration)
    - RPE-based strategy selection
    """

    def __init__(
        self,
        name: str,
        capabilities: AthleteCapabilities,
        context: Optional[ContextParams] = None,
        day_state: Optional[DayState] = None
    ):
        """
        Initialize athlete with capabilities and current state.

        Args:
            name: Athlete name
            capabilities: Physical capabilities and performance parameters
            context: Environmental context
            day_state: Daily state (sleep, hydration, RPE intention)
        """
        self.name = name
        self.capabilities = capabilities
        self.context = context or ContextParams()
        self.day_state = day_state or DayState(body_mass_kg=capabilities.body_mass_kg)

        # Initialize fatigue management
        self.fatigue_manager = FatigueManager()

        # Initialize W'bal for available cardio modalities
        for modality, profile in capabilities.cardio_profiles.items():
            tau_recovery = self._calculate_recovery_time_constant(modality)
            self.fatigue_manager.initialize_wbal(modality, profile.w_prime, tau_recovery)

        # Cache for performance calculations
        self._context_factors_cache: Optional[Dict[str, float]] = None

    def _calculate_recovery_time_constant(self, modality: str) -> float:
        """Calculate recovery time constant based on modality and athlete characteristics."""
        base_tau = {
            'bike': 300.0,   # 5 minutes
            'row': 320.0,    # Slightly slower
            'run': 280.0,    # Slightly faster
            'swim': 350.0    # Slower due to technique demands
        }

        tau = base_tau.get(modality, 300.0)

        # Adjust based on estimated aerobic capacity
        vo2_max = self.capabilities.estimate_aerobic_capacity()
        if vo2_max:
            # Better aerobic fitness = faster recovery
            fitness_factor = vo2_max / 50.0  # Normalize around 50 ml/kg/min
            tau *= (1.0 / fitness_factor) ** 0.3

        return tau

    def _get_context_factors(self) -> Dict[str, float]:
        """Calculate context effect factors, with caching."""
        if self._context_factors_cache is not None:
            return self._context_factors_cache

        factors = {}

        # Temperature effects (U-shaped curve, optimal around 20°C)
        temp_delta = abs(self.context.temperature_c - 20.0)
        factors['temperature'] = 1.0 + (temp_delta ** 2) * 0.0008

        # Altitude effects (linear above 700m)
        if self.context.altitude_m > 700:
            altitude_factor = (self.context.altitude_m - 700) / 300.0
            factors['altitude'] = 1.0 + altitude_factor * 0.06
        else:
            factors['altitude'] = 1.0

        # Humidity effects (on recovery and cardio performance)
        factors['humidity'] = 1.0 + (self.context.humidity_pct / 100.0) * 0.2

        # Combined cardio stress
        factors['cardio_stress'] = factors['temperature'] * factors['altitude'] * factors['humidity']

        # Daily state effects
        factors['freshness'] = self._calculate_freshness_factor()
        factors['hydration'] = self._calculate_hydration_factor()

        self._context_factors_cache = factors
        return factors

    def _calculate_freshness_factor(self) -> float:
        """Calculate freshness factor from sleep."""
        sleep_effect = 0.03 * (self.day_state.sleep_h - 7.5)
        quality_effect = 0.02 * (self.day_state.sleep_quality - 3)
        return max(0.6, min(1.05, 0.8 + sleep_effect + quality_effect))

    def _calculate_hydration_factor(self) -> float:
        """Calculate hydration factor."""
        target_water = 0.033 * self.day_state.body_mass_kg
        if self.context.temperature_c > 24:
            target_water += 0.25

        ratio = self.day_state.water_l / max(0.5, target_water)
        return max(0.7, min(1.1, ratio))

    def get_rep_time(
        self,
        exercise: str,
        load_kg: Optional[float] = None,
        current_fatigue: Optional[float] = None
    ) -> float:
        """
        Calculate time for one repetition of an exercise.

        Args:
            exercise: Exercise name
            load_kg: Load in kg (for weighted exercises)
            current_fatigue: Override fatigue level (uses current if None)

        Returns:
            Time in seconds for one repetition
        """
        # Get current fatigue if not provided
        if current_fatigue is None:
            current_fatigue = self.fatigue_manager.get_movement_fatigue(exercise)

        # Get context factors
        context_factors = self._get_context_factors()

        # === BARBELL MOVEMENTS ===
        if load_kg is not None:
            rep_time = self.capabilities.get_barbell_rep_time(exercise, load_kg)
            if rep_time is not None:
                # Apply fatigue effects
                fatigue_factor = 1.0 + current_fatigue * 0.4

                # Apply context effects
                context_factor = context_factors['temperature'] * context_factors['altitude']

                # Apply daily state effects
                daily_factor = 1.0 / (context_factors['freshness'] * context_factors['hydration'])

                return rep_time * fatigue_factor * context_factor * daily_factor

        # === GYMNASTICS MOVEMENTS ===
        gym_skill = self.capabilities.get_gym_skill(exercise)
        if gym_skill is not None:
            effective_cycle_time = gym_skill.effective_cycle_time(current_fatigue)

            # Apply context effects (less impact than barbell)
            context_factor = 1.0 + (context_factors['temperature'] - 1.0) * 0.5

            # Apply daily state effects
            daily_factor = 1.0 / (context_factors['freshness'] * context_factors['hydration'] ** 0.5)

            return effective_cycle_time * context_factor * daily_factor

        # === DEFAULT/UNKNOWN MOVEMENTS ===
        # Use default pace with fatigue scaling
        default_paces = {
            'burpee': 4.0,
            'box-jump': 2.5,
            'air-squat': 1.0,
            'push-up': 1.5,
            'sit-up': 1.2,
        }

        base_time = default_paces.get(exercise, 2.0)
        fatigue_factor = 1.0 + current_fatigue * 0.3
        context_factor = context_factors['temperature']
        daily_factor = 1.0 / context_factors['freshness']

        return base_time * fatigue_factor * context_factor * daily_factor

    def get_fatigue_per_rep(self, exercise: str, load_kg: Optional[float] = None) -> float:
        """
        Calculate fatigue accumulated per repetition.

        Args:
            exercise: Exercise name
            load_kg: Load in kg

        Returns:
            Fatigue points per rep
        """
        # Base fatigue by exercise type
        base_fatigue_map = {
            # High fatigue movements
            'thruster': 0.08,
            'burpee': 0.12,
            'muscle-up': 0.15,
            'snatch': 0.15,
            'clean': 0.12,

            # Moderate fatigue
            'pull-up': 0.06,
            'wall-ball': 0.06,
            'deadlift': 0.10,
            'handstand-pushup': 0.08,

            # Lower fatigue
            'box-jump': 0.04,
            'air-squat': 0.02,
            'double-under': 0.01,
            'push-up': 0.03,
            'sit-up': 0.02,
        }

        base_fatigue = base_fatigue_map.get(exercise, 0.05)

        # Adjust for load if applicable
        load_factor = 1.0
        if load_kg is not None:
            one_rm = self.capabilities.get_one_rm(exercise)
            if one_rm and one_rm > 0:
                intensity = load_kg / one_rm
                load_factor = 1.0 + intensity * 0.5

        # Context effects (heat/altitude increase fatigue)
        context_factors = self._get_context_factors()
        context_factor = context_factors['cardio_stress'] ** 0.5

        # Daily state effects
        freshness = context_factors['freshness']
        hydration = context_factors['hydration']
        daily_factor = 1.0 / (freshness * hydration)

        return base_fatigue * load_factor * context_factor * daily_factor

    def get_cardio_pace(self, modality: str, target_duration_s: float) -> Optional[Tuple[float, bool]]:
        """
        Get sustainable pace for cardio work.

        Args:
            modality: Cardio modality ('bike', 'row', 'run', 'swim')
            target_duration_s: Target duration

        Returns:
            Tuple of (pace/power, is_sustainable) or None if modality not available
        """
        profile = self.capabilities.get_cardio_profile(modality)
        if profile is None:
            return None

        # Get current W'bal state
        wbal_state = self.fatigue_manager.wbal_states.get(modality)
        if wbal_state is None:
            return None

        # Calculate sustainable pace based on current W'bal
        sustainable_pace = profile.power_duration_curve(target_duration_s)

        # Check if we can sustain this pace with current W'bal
        can_sustain = wbal_state.can_sustain_power(sustainable_pace, profile.cp, target_duration_s)

        # Apply context effects
        context_factors = self._get_context_factors()
        context_degradation = context_factors['cardio_stress']

        effective_pace = sustainable_pace / context_degradation

        return effective_pace, can_sustain

    def recover(self, duration_s: float) -> None:
        """
        Apply recovery for given duration.

        Args:
            duration_s: Recovery duration in seconds
        """
        # Calculate recovery quality based on context and daily state
        context_factors = self._get_context_factors()

        # Hot/humid conditions reduce recovery quality
        temp_recovery_factor = 1.0 / context_factors['cardio_stress'] ** 0.3

        # Daily state affects recovery
        daily_recovery_factor = context_factors['freshness'] * context_factors['hydration']

        recovery_quality = temp_recovery_factor * daily_recovery_factor

        # Apply recovery to fatigue manager
        self.fatigue_manager.recover_all(duration_s, recovery_quality)

        # Clear context cache (may have changed)
        self._context_factors_cache = None

    def add_work(self, exercise: str, reps: int, load_kg: Optional[float] = None) -> None:
        """
        Add work and accumulate fatigue.

        Args:
            exercise: Exercise name
            reps: Number of reps
            load_kg: Load in kg
        """
        # Calculate load factor
        load_factor = 0.0
        if load_kg is not None:
            one_rm = self.capabilities.get_one_rm(exercise)
            if one_rm and one_rm > 0:
                load_factor = load_kg / one_rm

        # Add local fatigue
        self.fatigue_manager.add_local_fatigue(exercise, load_factor, reps)

        # Clear context cache
        self._context_factors_cache = None

    def add_cardio_work(self, modality: str, power_or_speed: float, duration_s: float) -> None:
        """
        Add cardiovascular work and update W'bal.

        Args:
            modality: Cardio modality
            power_or_speed: Power (W) or speed (m/s)
            duration_s: Duration in seconds
        """
        profile = self.capabilities.get_cardio_profile(modality)
        if profile is not None:
            self.fatigue_manager.add_cardio_fatigue(modality, power_or_speed, profile.cp, duration_s)

    def get_strategy_for_rpe(self, rpe: Optional[int] = None) -> RPEStrategy:
        """
        Get RPE strategy based on intended RPE or day state.

        Args:
            rpe: Override RPE (uses day_state.rpe_intended if None)

        Returns:
            RPEStrategy configured for the RPE level
        """
        target_rpe = rpe if rpe is not None else self.day_state.rpe_intended
        return create_rpe_strategy(target_rpe)

    def clone(self, **modifications) -> 'AthleteV2':
        """
        Create a clone with optional modifications.

        Args:
            **modifications: Attributes to modify

        Returns:
            New AthleteV2 instance
        """
        # Deep copy current state
        new_capabilities = copy.deepcopy(self.capabilities)
        new_context = copy.deepcopy(self.context)
        new_day_state = copy.deepcopy(self.day_state)

        # Apply modifications
        for key, value in modifications.items():
            if hasattr(new_capabilities, key):
                setattr(new_capabilities, key, value)
            elif hasattr(new_context, key):
                setattr(new_context, key, value)
            elif hasattr(new_day_state, key):
                setattr(new_day_state, key, value)
            else:
                raise ValueError(f"Unknown attribute: {key}")

        # Create new instance
        clone = AthleteV2(
            name=f"{self.name}_clone",
            capabilities=new_capabilities,
            context=new_context,
            day_state=new_day_state
        )

        return clone

    def get_performance_summary(self) -> Dict[str, any]:
        """
        Get summary of current performance state.

        Returns:
            Dictionary with performance metrics
        """
        context_factors = self._get_context_factors()
        fatigue_summary = self.fatigue_manager.get_fatigue_summary()

        return {
            'name': self.name,
            'body_mass_kg': self.capabilities.body_mass_kg,
            'relative_strength': self.capabilities.estimate_relative_strength(),
            'aerobic_capacity': self.capabilities.estimate_aerobic_capacity(),
            'context_factors': context_factors,
            'fatigue_levels': fatigue_summary,
            'intended_rpe': self.day_state.rpe_intended,
        }

    def reset_fatigue(self) -> None:
        """Reset all fatigue to fresh state."""
        self.fatigue_manager.reset_all_fatigue()
        self._context_factors_cache = None

    def __str__(self) -> str:
        """String representation."""
        summary = self.get_performance_summary()
        return f"AthleteV2({self.name}, {self.capabilities.body_mass_kg}kg, RPE {self.day_state.rpe_intended})"
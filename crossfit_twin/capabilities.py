"""
Athlete Capabilities module for CrossFit Digital Twin.

Contains concrete, measurable athlete capabilities replacing the abstract 0-100 scoring system.
Uses physiological models based on actual performance metrics.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import math


@dataclass
class BarbellProfile:
    """
    Barbell movement profile for calculating rep times based on load.

    Models the relationship between weight percentage and cycle time:
    rep_time = base_cycle_s * (1 + (load_ratio ** load_exp)) + transition_s

    Attributes:
        base_cycle_s: Base cycle time at minimal load (seconds)
        load_exp: Exponent for load scaling (higher = more sensitive to weight)
        transition_s: Fixed transition time (setup, lockout, drop)
    """
    base_cycle_s: float = 1.7       # Base cycle time for technical movement
    load_exp: float = 2.0           # Load scaling exponent
    transition_s: float = 0.4       # Setup/transition time

    def rep_time(self, load_kg: float, one_rm_kg: float) -> float:
        """
        Calculate time for one rep at given load.

        Args:
            load_kg: Weight being lifted
            one_rm_kg: One rep max for this movement

        Returns:
            Time in seconds for one repetition
        """
        if one_rm_kg <= 0:
            return self.base_cycle_s + self.transition_s

        load_ratio = max(0.0, min(1.2, load_kg / one_rm_kg))  # Cap at 120% for safety
        cycle_multiplier = 1.0 + (load_ratio ** self.load_exp)

        return self.base_cycle_s * cycle_multiplier + self.transition_s


@dataclass
class CPProfile:
    """
    Critical Power/Speed profile for monostructural movements.

    Models aerobic/anaerobic energy systems:
    - Critical Power (CP): Maximum sustainable power/speed
    - W'/D': Anaerobic capacity above CP

    For cycling/rowing: CP in watts, W' in joules
    For running/swimming: CP as critical speed (m/s), D' as anaerobic distance (m)
    """
    cp: float           # Critical Power (W) or Critical Speed (m/s)
    w_prime: float      # W' (J) or D' (m) - anaerobic capacity

    def power_duration_curve(self, duration_s: float) -> float:
        """
        Calculate sustainable power/speed for given duration.

        Args:
            duration_s: Duration in seconds

        Returns:
            Sustainable power (W) or speed (m/s)
        """
        if duration_s <= 0:
            return self.cp

        # P = CP + W'/t model
        return self.cp + (self.w_prime / duration_s)

    def time_to_exhaustion(self, power_or_speed: float) -> float:
        """
        Calculate time to exhaustion at given power/speed.

        Args:
            power_or_speed: Target power (W) or speed (m/s)

        Returns:
            Time to exhaustion in seconds (inf if below CP)
        """
        if power_or_speed <= self.cp:
            return float('inf')  # Sustainable indefinitely

        return self.w_prime / (power_or_speed - self.cp)


@dataclass
class GymSkill:
    """
    Gymnastics skill profile for bodyweight movements.

    Attributes:
        cycle_s: Base cycle time per rep when fresh (seconds)
        unbroken_cap: Maximum unbroken reps when fresh
        fatigue_slope: How much cycle time increases with local fatigue
        set_decay: How much unbroken capacity decreases with local fatigue
    """
    cycle_s: float          # Base cycle time (s/rep)
    unbroken_cap: int       # Max unbroken reps when fresh
    fatigue_slope: float = 0.35     # Cycle time degradation vs fatigue
    set_decay: float = 0.25         # Unbroken capacity reduction vs fatigue

    def effective_cycle_time(self, local_fatigue: float) -> float:
        """
        Calculate effective cycle time considering local fatigue.

        Args:
            local_fatigue: Local muscle fatigue level (0.0 = fresh, 1.0+ = significant fatigue)

        Returns:
            Effective cycle time in seconds
        """
        return self.cycle_s * (1.0 + local_fatigue * self.fatigue_slope)

    def effective_unbroken_cap(self, local_fatigue: float) -> int:
        """
        Calculate effective unbroken capacity considering local fatigue.

        Args:
            local_fatigue: Local muscle fatigue level

        Returns:
            Effective maximum unbroken reps
        """
        reduction_factor = 1.0 - (local_fatigue * self.set_decay)
        return max(1, int(self.unbroken_cap * reduction_factor))


@dataclass
class AthleteCapabilities:
    """
    Complete athlete capabilities using concrete, measurable parameters.

    Replaces the abstract 0-100 scoring system with physiological models
    based on actual performance benchmarks.
    """

    # === BASIC ANTHROPOMETRICS ===
    body_mass_kg: float
    height_cm: Optional[float] = None

    # === WEIGHTLIFTING CAPABILITIES ===
    one_rm: Dict[str, float] = field(default_factory=dict)  # kg
    barbell_profile: BarbellProfile = field(default_factory=BarbellProfile)

    # === GYMNASTICS CAPABILITIES ===
    gym_skills: Dict[str, GymSkill] = field(default_factory=dict)

    # === MONOSTRUCTURAL CAPABILITIES ===
    cardio_profiles: Dict[str, CPProfile] = field(default_factory=dict)

    # === MOVEMENT ALIASES ===
    # Maps complex movements to base movements for 1RM estimation
    lift_aliases: Dict[str, str] = field(default_factory=lambda: {
        'thruster': 'front-squat',
        'push-press': 'overhead-press',
        'hang-clean': 'clean',
        'hang-snatch': 'snatch',
        'sumo-deadlift': 'deadlift',
    })

    def get_one_rm(self, movement: str) -> Optional[float]:
        """
        Get 1RM for a movement, using aliases if direct value not available.

        Args:
            movement: Movement name

        Returns:
            1RM in kg, or None if not available
        """
        # Direct lookup first
        if movement in self.one_rm:
            return self.one_rm[movement]

        # Try alias
        if movement in self.lift_aliases:
            base_movement = self.lift_aliases[movement]
            if base_movement in self.one_rm:
                return self.one_rm[base_movement]

        return None

    def get_barbell_rep_time(self, movement: str, load_kg: float) -> Optional[float]:
        """
        Calculate rep time for barbell movement at given load.

        Args:
            movement: Movement name
            load_kg: Load in kg

        Returns:
            Rep time in seconds, or None if movement 1RM not available
        """
        one_rm = self.get_one_rm(movement)
        if one_rm is None:
            return None

        return self.barbell_profile.rep_time(load_kg, one_rm)

    def get_gym_skill(self, skill: str) -> Optional[GymSkill]:
        """
        Get gymnastics skill profile.

        Args:
            skill: Skill name

        Returns:
            GymSkill profile or None if not available
        """
        return self.gym_skills.get(skill)

    def get_cardio_profile(self, modality: str) -> Optional[CPProfile]:
        """
        Get cardio profile for modality.

        Args:
            modality: Modality name (bike, row, run, swim)

        Returns:
            CPProfile or None if not available
        """
        return self.cardio_profiles.get(modality)

    def estimate_relative_strength(self) -> Optional[float]:
        """
        Estimate relative strength using key compound movements.

        Returns:
            Relative strength ratio (bodyweight multiple), or None if insufficient data
        """
        if not self.one_rm or self.body_mass_kg <= 0:
            return None

        # Use available compound movements with weights
        movements_weights = [
            ('back-squat', 0.4),
            ('deadlift', 0.3),
            ('clean', 0.2),
            ('overhead-press', 0.1)
        ]

        total_ratio = 0.0
        total_weight = 0.0

        for movement, weight in movements_weights:
            one_rm = self.get_one_rm(movement)
            if one_rm is not None:
                ratio = one_rm / self.body_mass_kg
                total_ratio += ratio * weight
                total_weight += weight

        if total_weight > 0:
            return total_ratio / total_weight

        return None

    def estimate_aerobic_capacity(self) -> Optional[float]:
        """
        Estimate aerobic capacity from available cardio profiles.

        Returns:
            Estimated VO2 max (ml/kg/min) or None if insufficient data
        """
        # Simple estimation from rowing or running CP
        if 'row' in self.cardio_profiles:
            # Rough conversion from rowing power to VO2 max
            # Elite rowers: ~450W CP ≈ 65 ml/kg/min
            row_cp = self.cardio_profiles['row'].cp
            watts_per_kg = row_cp / self.body_mass_kg
            return max(20.0, min(80.0, watts_per_kg * 12.0))  # Rough conversion

        if 'run' in self.cardio_profiles:
            # Rough conversion from running speed to VO2 max
            # Elite runners: ~5.5 m/s ≈ 70 ml/kg/min
            run_cs = self.cardio_profiles['run'].cp
            return max(20.0, min(80.0, run_cs * 12.7))  # Rough conversion

        return None

    def validate_capabilities(self) -> Dict[str, str]:
        """
        Validate athlete capabilities for consistency and realism.

        Returns:
            Dictionary mapping parameter names to error messages
        """
        errors = {}

        # Validate body mass
        if self.body_mass_kg <= 30 or self.body_mass_kg > 200:
            errors['body_mass_kg'] = "Body mass should be between 30-200 kg"

        # Validate height if provided
        if self.height_cm is not None:
            if self.height_cm < 120 or self.height_cm > 250:
                errors['height_cm'] = "Height should be between 120-250 cm"

        # Validate 1RMs are reasonable relative to body weight
        for movement, weight_kg in self.one_rm.items():
            if weight_kg <= 0:
                errors[f'one_rm_{movement}'] = f"{movement} 1RM must be positive"
                continue

            ratio = weight_kg / self.body_mass_kg

            # Set reasonable upper bounds (elite athlete levels)
            max_ratios = {
                'back-squat': 3.5,
                'front-squat': 2.8,
                'deadlift': 4.0,
                'clean': 2.5,
                'snatch': 2.0,
                'overhead-press': 1.8,
                'bench-press': 2.5,
            }

            max_ratio = max_ratios.get(movement, 3.0)  # Default for unknown movements
            if ratio > max_ratio:
                errors[f'one_rm_{movement}'] = f"{movement} 1RM seems unrealistic ({ratio:.1f}x bodyweight)"

        # Validate gym skills
        for skill, profile in self.gym_skills.items():
            if profile.cycle_s <= 0:
                errors[f'gym_{skill}_cycle'] = f"{skill} cycle time must be positive"
            if profile.unbroken_cap <= 0:
                errors[f'gym_{skill}_unbroken'] = f"{skill} unbroken capacity must be positive"

        # Validate cardio profiles
        for modality, profile in self.cardio_profiles.items():
            if profile.cp <= 0:
                errors[f'cardio_{modality}_cp'] = f"{modality} CP must be positive"
            if profile.w_prime < 0:
                errors[f'cardio_{modality}_wprime'] = f"{modality} W' cannot be negative"

        return errors

    def __str__(self) -> str:
        """String representation of athlete capabilities."""
        lines = [f"AthleteCapabilities({self.body_mass_kg}kg)"]

        if self.one_rm:
            lines.append("  1RM:")
            for movement, weight in sorted(self.one_rm.items()):
                ratio = weight / self.body_mass_kg
                lines.append(f"    {movement}: {weight}kg ({ratio:.1f}x BW)")

        if self.gym_skills:
            lines.append("  Gymnastics:")
            for skill, profile in sorted(self.gym_skills.items()):
                lines.append(f"    {skill}: {profile.cycle_s:.1f}s/rep, max {profile.unbroken_cap}")

        if self.cardio_profiles:
            lines.append("  Cardio:")
            for modality, profile in sorted(self.cardio_profiles.items()):
                if modality in ['bike', 'row']:
                    lines.append(f"    {modality}: CP={profile.cp:.0f}W, W'={profile.w_prime:.0f}J")
                else:
                    lines.append(f"    {modality}: CS={profile.cp:.1f}m/s, D'={profile.w_prime:.0f}m")

        return "\n".join(lines)
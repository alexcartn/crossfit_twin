"""
Athlete module for CrossFit Digital Twin.

Contains the Athlete class that models a CrossFit athlete's physical and performance characteristics.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import copy
import re


@dataclass
class ContextParams:
    """
    Environmental context parameters affecting performance.
    
    Attributes:
        temperature_c: Temperature in Celsius
        humidity_pct: Humidity percentage (0-100)
        altitude_m: Altitude in meters above sea level
    """
    temperature_c: float = 20.0
    humidity_pct: float = 50.0
    altitude_m: float = 0.0


@dataclass
class DayState:
    """
    Daily state parameters affecting performance.
    
    Attributes:
        sleep_h: Hours of sleep last night
        sleep_quality: Sleep quality on 1-5 scale
        water_l: Liters of water consumed since waking
        body_mass_kg: Current body weight
    """
    sleep_h: float = 7.5
    sleep_quality: int = 3  # 1-5 scale
    water_l: float = 2.0
    body_mass_kg: float = 75.0


def parse_time_string(time_str: str) -> float:
    """Parse time string like '7:30' or '19:30' to seconds."""
    if ':' in time_str:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    else:
        return float(time_str)


def freshness_factor(sleep_h: float, sleep_quality: int) -> float:
    """Calculate freshness factor based on sleep."""
    return max(0.60, min(1.05, 0.8 + 0.03*(sleep_h-7.5) + 0.02*(sleep_quality-3)))


def hydration_factor(water_l: float, mass_kg: float, temp_c: float) -> float:
    """Calculate hydration factor."""
    target = 0.033*mass_kg + (0.25 if temp_c > 24 else 0.0)
    ratio = water_l / max(0.5, target)
    return max(0.70, min(1.10, ratio))


def u_shape_cycle_multiplier(temp_c: float, t0: float = 20.0, a: float = 8e-4) -> float:
    """Calculate temperature effect on performance (U-shaped curve)."""
    d = temp_c - t0
    return 1.0 + a*(d*d)


def hot_humid_recovery_scale(temp_c: float, hum: float, t_lin: float = 22.0, k: float = 0.012, h_amp: float = 0.4) -> float:
    """Calculate recovery scaling factor for hot/humid conditions."""
    hot = max(0.0, temp_c - t_lin)
    penalty = (k*hot)*(1 + h_amp*hum/100.0)
    return max(0.6, 1.0 - penalty)


def cardio_drift_scale(temp_c: float, hum: float, alt_m: float, t_lin: float = 22.0, k: float = 0.015, h_amp: float = 0.4) -> float:
    """Calculate cardiovascular drift scaling for environmental conditions."""
    hot = max(0.0, temp_c - t_lin)
    scale = 1.0 + (k*hot)*(1 + h_amp*hum/100.0)
    if alt_m > 700:
        steps = (alt_m - 700)/300.0
        scale *= (1.0 + 0.06*max(0.0, steps))
    return scale


def map_cardio_to_endurance(row_2k_time: float, row_5k_time: float, weight_kg: float) -> tuple[float, float]:
    """
    Map 2k/5k row times to endurance and fatigue resistance.
    
    Returns:
        tuple: (endurance_0_100, fatigue_resistance_0_100)
    """
    # Calculate power estimates (simplified)
    # Elite 2k times: ~6:00-6:30, recreational: 8:00-10:00+
    
    # Critical Power estimation from 2k and 5k
    t2 = row_2k_time / 60.0  # minutes
    t5 = row_5k_time / 60.0  # minutes
    
    # Simplified CP/W' model
    # Power = CP + W'/t
    # Solve for CP and W' from two time points
    if t5 > t2:
        # Rough estimation
        cp_watts_per_kg = 180.0 / max(t2, 6.0)  # Scales inversely with time
        w_prime = max(0, (t5 - t2) * cp_watts_per_kg * 60 * 0.1)  # Anaerobic capacity
    else:
        cp_watts_per_kg = 3.0
        w_prime = 1000.0
    
    # Map to 0-100 scales
    # Elite CP ~4.5+ W/kg, recreational ~2.5 W/kg
    endurance = max(0, min(100, (cp_watts_per_kg - 2.0) * 33.3))
    
    # W' typically 10-25 kJ, map to 0-100
    fatigue_resistance = max(0, min(100, w_prime / 250.0 * 100))
    
    return endurance, fatigue_resistance


def map_strength_lifts_to_strength(bs_1rm: float, cj_1rm: float, sn_1rm: float, weight_kg: float) -> float:
    """Map 1RM lifts to strength score."""
    # Calculate relative strength (lift / bodyweight)
    bs_ratio = bs_1rm / weight_kg
    cj_ratio = cj_1rm / weight_kg
    sn_ratio = sn_1rm / weight_kg
    
    # Elite ratios: BS ~2.5, C&J ~1.8, Sn ~1.4
    # Beginner ratios: BS ~1.0, C&J ~0.7, Sn ~0.5
    
    # Weighted average (back squat counts more for general strength)
    strength_ratio = (bs_ratio * 0.5 + cj_ratio * 0.3 + sn_ratio * 0.2)
    
    # Map to 0-100 scale
    # 1.0 ratio = 0 points, 2.5+ ratio = 100 points
    strength = max(0, min(100, (strength_ratio - 1.0) * 66.7))
    
    return strength


def map_rep_tests_to_base_pace(t_thr_10: float, t_pu_10: float, t_bur_15: float, t_wb_15: float) -> Dict[str, float]:
    """Map timed rep tests to base pace dictionary."""
    base_pace = {
        "thruster": t_thr_10 / 10.0,
        "pull-up": t_pu_10 / 10.0,
        "burpee": t_bur_15 / 15.0,
        "wall-ball": t_wb_15 / 15.0,
    }
    
    # Add derived paces for other exercises based on similar movement patterns
    base_pace.update({
        "kettlebell-swing": base_pace["thruster"] * 0.8,  # Faster than thrusters
        "box-jump": base_pace["burpee"] * 0.6,  # Faster than burpees
        "rowing": 2.0,  # seconds per calorie
        "air-squat": base_pace["thruster"] * 0.5,  # Much faster
        "push-up": base_pace["burpee"] * 0.4,  # Component of burpee
        "sit-up": base_pace["burpee"] * 0.3,  # Fast movement
        "double-under": 0.5,  # Very fast
        "deadlift": base_pace["thruster"] * 1.5,  # Slower, heavier
        "clean": base_pace["thruster"] * 2.0,  # Technical lift
        "snatch": base_pace["thruster"] * 2.2,  # Most technical
    })
    
    return base_pace


@dataclass
class Athlete:
    """
    Represents a CrossFit athlete with physical parameters and performance characteristics.
    
    Attributes:
        name: Athlete's name for identification
        strength: Overall strength level (0-100 scale)
        endurance: Cardiovascular endurance (0-100 scale)
        fatigue_resistance: Resistance to fatigue accumulation (0-100 scale)
        recovery_rate: Rate of recovery during rest periods (0-100 scale)
        weight_kg: Body weight in kilograms
        max_lifts: Dictionary of 1RM for various exercises (kg)
        base_pace: Base time per rep for different exercises when fresh (seconds)
        experience_level: Training experience (beginner, intermediate, advanced, elite)
    """
    
    name: str
    strength: float  # 0-100 scale
    endurance: float  # 0-100 scale
    fatigue_resistance: float  # 0-100 scale
    recovery_rate: float  # 0-100 scale
    weight_kg: float
    max_lifts: Dict[str, float] = field(default_factory=dict)
    base_pace: Dict[str, float] = field(default_factory=dict)
    experience_level: str = "intermediate"
    
    def __post_init__(self) -> None:
        """Validate athlete parameters and set defaults."""
        self._validate_parameters()
        self._set_default_paces()
        self._set_default_lifts()
        
        # Optional context and day state for simulation
        self._current_context: Optional[ContextParams] = None
        self._current_day_state: Optional[DayState] = None
    
    def _validate_parameters(self) -> None:
        """Validate that all parameters are within acceptable ranges."""
        for param_name, value in [
            ("strength", self.strength),
            ("endurance", self.endurance), 
            ("fatigue_resistance", self.fatigue_resistance),
            ("recovery_rate", self.recovery_rate)
        ]:
            if not 0 <= value <= 100:
                raise ValueError(f"{param_name} must be between 0 and 100, got {value}")
        
        if self.weight_kg <= 0:
            raise ValueError(f"weight_kg must be positive, got {self.weight_kg}")
        
        if self.experience_level not in ["beginner", "intermediate", "advanced", "elite"]:
            raise ValueError(f"experience_level must be one of: beginner, intermediate, advanced, elite")
    
    def _set_default_paces(self) -> None:
        """Set default base pace for common CrossFit exercises if not provided."""
        default_paces = {
            "thruster": 2.0,      # seconds per rep
            "pull-up": 1.5,
            "burpee": 4.0,
            "box-jump": 2.5,
            "kettlebell-swing": 1.8,
            "wall-ball": 2.2,
            "rowing": 2.0,        # seconds per calorie
            "air-squat": 1.0,
            "push-up": 1.5,
            "sit-up": 1.2,
            "double-under": 0.5,
            "deadlift": 3.0,
            "clean": 4.0,
            "snatch": 4.5,
        }
        
        for exercise, pace in default_paces.items():
            if exercise not in self.base_pace:
                # Adjust base pace based on experience level
                experience_multiplier = {
                    "beginner": 1.3,
                    "intermediate": 1.0,
                    "advanced": 0.8,
                    "elite": 0.6
                }
                self.base_pace[exercise] = pace * experience_multiplier[self.experience_level]
    
    def _set_default_lifts(self) -> None:
        """Set default 1RM estimates if not provided, based on bodyweight and strength level."""
        if not self.max_lifts:
            # Basic strength standards based on bodyweight and strength level
            strength_multiplier = self.strength / 100.0
            
            default_ratios = {
                "back-squat": 1.5 * strength_multiplier,
                "deadlift": 2.0 * strength_multiplier,
                "bench-press": 1.2 * strength_multiplier,
                "overhead-press": 0.8 * strength_multiplier,
                "clean": 1.0 * strength_multiplier,
                "snatch": 0.75 * strength_multiplier,
                "thruster": 0.6 * strength_multiplier,
            }
            
            for lift, ratio in default_ratios.items():
                if lift not in self.max_lifts:
                    self.max_lifts[lift] = self.weight_kg * ratio
    
    def get_rep_time(self, exercise: str, weight_kg: Optional[float] = None, fatigue: float = 0.0, 
                     ctx: Optional[ContextParams] = None, day: Optional[DayState] = None) -> float:
        """
        Calculate time to perform one repetition of an exercise.
        
        Args:
            exercise: Name of the exercise
            weight_kg: Weight used for the exercise (None for bodyweight)
            fatigue: Current fatigue level (0.0 = fresh, higher = more fatigued)
            ctx: Environmental context parameters (uses stored context if None)
            day: Daily state parameters (uses stored day state if None)
            
        Returns:
            Time in seconds for one repetition
        """
        # Use stored context/day state if not provided
        if ctx is None:
            ctx = self._current_context
        if day is None:
            day = self._current_day_state
            
        base_time = self.base_pace.get(exercise, 2.0)  # Default 2 seconds if unknown
        
        # Adjust for weight if applicable
        if weight_kg is not None and exercise in self.max_lifts:
            max_weight = self.max_lifts[exercise]
            intensity_ratio = weight_kg / max_weight if max_weight > 0 else 0.5
            # Higher intensity = slower reps
            weight_factor = 1.0 + (intensity_ratio - 0.5) * 0.5
        else:
            weight_factor = 1.0
        
        # Adjust for fatigue
        fatigue_factor = 1.0 + fatigue * 0.8  # Fatigue can slow down significantly
        
        # Adjust for endurance (better endurance = less slowdown under fatigue)
        endurance_factor = 1.0 - (self.endurance / 100.0) * 0.2
        
        # Apply context effects if provided
        context_factor = 1.0
        if ctx is not None:
            # Temperature effect (U-shaped curve)
            context_factor *= u_shape_cycle_multiplier(ctx.temperature_c)
            
            # Cardiovascular drift for cardio-intensive exercises
            if exercise in ["burpee", "rowing", "thruster", "kettlebell-swing"]:
                cardio_scale = cardio_drift_scale(ctx.temperature_c, ctx.humidity_pct, ctx.altitude_m)
                fatigue_factor *= cardio_scale
        
        # Apply day state effects if provided
        day_factor = 1.0
        if day is not None:
            # Freshness factor affects base performance slightly
            freshness = freshness_factor(day.sleep_h, day.sleep_quality)
            day_factor = 0.98 + 0.02 * freshness
        
        return base_time * weight_factor * fatigue_factor * endurance_factor * context_factor / day_factor
    
    def get_fatigue_per_rep(self, exercise: str, weight_kg: Optional[float] = None) -> float:
        """
        Calculate fatigue accumulated per repetition of an exercise.
        
        Args:
            exercise: Name of the exercise
            weight_kg: Weight used for the exercise
            
        Returns:
            Fatigue points accumulated per rep (0.0 to 1.0+ scale)
        """
        # Base fatigue varies by exercise type
        base_fatigue_map = {
            "thruster": 0.08,
            "pull-up": 0.06,
            "burpee": 0.12,
            "box-jump": 0.04,
            "kettlebell-swing": 0.05,
            "wall-ball": 0.06,
            "rowing": 0.03,  # per calorie
            "air-squat": 0.02,
            "push-up": 0.03,
            "sit-up": 0.02,
            "double-under": 0.01,
            "deadlift": 0.10,
            "clean": 0.12,
            "snatch": 0.15,
        }
        
        base_fatigue = base_fatigue_map.get(exercise, 0.05)
        
        # Adjust for weight intensity
        if weight_kg is not None and exercise in self.max_lifts:
            max_weight = self.max_lifts[exercise]
            intensity_ratio = weight_kg / max_weight if max_weight > 0 else 0.5
            weight_factor = 1.0 + intensity_ratio * 0.5
        else:
            weight_factor = 1.0
        
        # Adjust for fatigue resistance
        resistance_factor = 1.0 - (self.fatigue_resistance / 100.0) * 0.3
        
        return base_fatigue * weight_factor * resistance_factor
    
    def recover(self, rest_duration_seconds: float, current_fatigue: float,
                ctx: Optional[ContextParams] = None, day: Optional[DayState] = None) -> float:
        """
        Calculate fatigue recovery during rest period.
        
        Args:
            rest_duration_seconds: Duration of rest in seconds
            current_fatigue: Current fatigue level
            ctx: Environmental context parameters (uses stored context if None)
            day: Daily state parameters (uses stored day state if None)
            
        Returns:
            New fatigue level after recovery
        """
        # Use stored context/day state if not provided
        if ctx is None:
            ctx = self._current_context
        if day is None:
            day = self._current_day_state
            
        if current_fatigue <= 0:
            return 0.0
        
        # Recovery rate depends on athlete's recovery ability
        recovery_multiplier = self.recovery_rate / 100.0
        
        # Apply context and day state effects
        if ctx is not None and day is not None:
            # Environmental effects on recovery
            temp_humid_factor = hot_humid_recovery_scale(ctx.temperature_c, ctx.humidity_pct)
            
            # Daily state effects
            freshness = freshness_factor(day.sleep_h, day.sleep_quality)
            hydration = hydration_factor(day.water_l, day.body_mass_kg, ctx.temperature_c)
            
            # Combine all factors
            recovery_multiplier *= temp_humid_factor * freshness * hydration
        elif day is not None:
            # Only day state available
            freshness = freshness_factor(day.sleep_h, day.sleep_quality)
            hydration = hydration_factor(day.water_l, day.body_mass_kg, 20.0)  # Assume normal temp
            recovery_multiplier *= freshness * hydration
        elif ctx is not None:
            # Only context available
            temp_humid_factor = hot_humid_recovery_scale(ctx.temperature_c, ctx.humidity_pct)
            recovery_multiplier *= temp_humid_factor
        
        # Exponential recovery model - faster recovery at higher fatigue levels
        recovery_rate_per_second = 0.02 * recovery_multiplier
        
        # Calculate recovery
        fatigue_reduction = current_fatigue * (1 - (1 - recovery_rate_per_second) ** rest_duration_seconds)
        
        return max(0.0, current_fatigue - fatigue_reduction)
    
    def set_simulation_context(self, ctx: Optional[ContextParams] = None, day: Optional[DayState] = None) -> None:
        """
        Set context and day state for simulation.
        
        Args:
            ctx: Environmental context parameters
            day: Daily state parameters
        """
        self._current_context = ctx
        self._current_day_state = day
    
    def clone(self, **modifications) -> 'Athlete':
        """
        Create a clone of this athlete with optional parameter modifications.
        
        Args:
            **modifications: Keyword arguments to modify in the clone
            
        Returns:
            New Athlete instance with modifications applied
        """
        # Deep copy to avoid reference issues
        clone_data = copy.deepcopy(self.__dict__)
        
        # Apply modifications
        for key, value in modifications.items():
            if hasattr(self, key):
                clone_data[key] = value
            else:
                raise ValueError(f"Invalid attribute: {key}")
        
        # Create new instance
        cloned_athlete = Athlete.__new__(Athlete)
        cloned_athlete.__dict__.update(clone_data)
        
        # Re-validate if core parameters were changed
        if any(key in modifications for key in ['strength', 'endurance', 'fatigue_resistance', 'recovery_rate', 'weight_kg']):
            cloned_athlete._validate_parameters()
        
        return cloned_athlete
    
    @classmethod
    def from_concrete_inputs(
        cls,
        name: str,
        # Intrinsic parameters
        weight_kg: float,
        row_2k_time: str,  # "7:30" format
        row_5k_time: str,  # "19:30" format
        t_thr_10: float,   # 10 thrusters time in seconds
        t_pu_10: float,    # 10 pull-ups time in seconds
        t_bur_15: float,   # 15 burpees time in seconds
        t_wb_15: float,    # 15 wall-balls time in seconds
        bs_1rm: float,     # Back squat 1RM
        cj_1rm: float,     # Clean & Jerk 1RM
        sn_1rm: float,     # Snatch 1RM
        experience_level: str = "intermediate",
        # Recovery rate estimation (can be slider or test-based)
        recovery_rate: float = 70.0
    ) -> 'Athlete':
        """
        Create an Athlete from concrete performance inputs.
        
        Args:
            name: Athlete name
            weight_kg: Body weight in kg
            row_2k_time: 2k row time as "mm:ss" string
            row_5k_time: 5k row time as "mm:ss" string
            t_thr_10: Time for 10 thrusters (seconds)
            t_pu_10: Time for 10 pull-ups (seconds)
            t_bur_15: Time for 15 burpees (seconds)
            t_wb_15: Time for 15 wall-balls (seconds)
            bs_1rm: Back squat 1RM (kg)
            cj_1rm: Clean & Jerk 1RM (kg)
            sn_1rm: Snatch 1RM (kg)
            experience_level: Experience level
            recovery_rate: Recovery rate (0-100)
            
        Returns:
            Athlete instance with calculated parameters
        """
        # Parse row times
        row_2k_seconds = parse_time_string(row_2k_time)
        row_5k_seconds = parse_time_string(row_5k_time)
        
        # Calculate endurance and fatigue resistance from cardio
        endurance, fatigue_resistance = map_cardio_to_endurance(
            row_2k_seconds, row_5k_seconds, weight_kg
        )
        
        # Calculate strength from lifts
        strength = map_strength_lifts_to_strength(bs_1rm, cj_1rm, sn_1rm, weight_kg)
        
        # Calculate base pace from rep tests
        base_pace = map_rep_tests_to_base_pace(t_thr_10, t_pu_10, t_bur_15, t_wb_15)
        
        # Calculate max lifts including derivatives
        max_lifts = {
            "back-squat": bs_1rm,
            "clean": cj_1rm,
            "snatch": sn_1rm,
            "deadlift": bs_1rm * 1.2,  # Typically higher than squat
            "thruster": min(cj_1rm * 0.7, weight_kg * 0.8),  # Limited by front rack
            "overhead-press": cj_1rm * 0.6,  # Typically 60% of C&J
        }
        
        return cls(
            name=name,
            strength=strength,
            endurance=endurance,
            fatigue_resistance=fatigue_resistance,
            recovery_rate=recovery_rate,
            weight_kg=weight_kg,
            max_lifts=max_lifts,
            base_pace=base_pace,
            experience_level=experience_level
        )
    
    def __str__(self) -> str:
        """String representation of the athlete."""
        return (f"Athlete(name='{self.name}', strength={self.strength}, "
                f"endurance={self.endurance}, fatigue_resistance={self.fatigue_resistance}, "
                f"weight={self.weight_kg}kg, level={self.experience_level})")
    
    def __repr__(self) -> str:
        """Detailed representation of the athlete."""
        return self.__str__()
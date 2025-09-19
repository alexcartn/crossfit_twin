"""
Athlete module for CrossFit Digital Twin.

Contains the Athlete class that models a CrossFit athlete's physical and performance characteristics.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import copy


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
    
    def get_rep_time(self, exercise: str, weight_kg: Optional[float] = None, fatigue: float = 0.0) -> float:
        """
        Calculate time to perform one repetition of an exercise.
        
        Args:
            exercise: Name of the exercise
            weight_kg: Weight used for the exercise (None for bodyweight)
            fatigue: Current fatigue level (0.0 = fresh, higher = more fatigued)
            
        Returns:
            Time in seconds for one repetition
        """
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
        
        return base_time * weight_factor * fatigue_factor * endurance_factor
    
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
    
    def recover(self, rest_duration_seconds: float, current_fatigue: float) -> float:
        """
        Calculate fatigue recovery during rest period.
        
        Args:
            rest_duration_seconds: Duration of rest in seconds
            current_fatigue: Current fatigue level
            
        Returns:
            New fatigue level after recovery
        """
        if current_fatigue <= 0:
            return 0.0
        
        # Recovery rate depends on athlete's recovery ability
        recovery_multiplier = self.recovery_rate / 100.0
        
        # Exponential recovery model - faster recovery at higher fatigue levels
        recovery_rate_per_second = 0.02 * recovery_multiplier
        
        # Calculate recovery
        fatigue_reduction = current_fatigue * (1 - (1 - recovery_rate_per_second) ** rest_duration_seconds)
        
        return max(0.0, current_fatigue - fatigue_reduction)
    
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
    
    def __str__(self) -> str:
        """String representation of the athlete."""
        return (f"Athlete(name='{self.name}', strength={self.strength}, "
                f"endurance={self.endurance}, fatigue_resistance={self.fatigue_resistance}, "
                f"weight={self.weight_kg}kg, level={self.experience_level})")
    
    def __repr__(self) -> str:
        """Detailed representation of the athlete."""
        return self.__str__()
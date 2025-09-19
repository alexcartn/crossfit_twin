"""
Workout module for CrossFit Digital Twin.

Contains classes for modeling WODs (Workouts of the Day) and individual exercises.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple
from enum import Enum


class WorkoutType(Enum):
    """Enumeration of different workout types."""
    FOR_TIME = "for_time"
    AMRAP = "amrap"
    EMOM = "emom"
    TABATA = "tabata"


@dataclass
class Exercise:
    """
    Represents a single exercise within a workout.
    
    Attributes:
        name: Exercise name (e.g., "thruster", "pull-up")
        reps: Number of repetitions (None for time-based exercises)
        weight_kg: Weight in kilograms (None for bodyweight exercises)
        distance_m: Distance in meters (for running, rowing, etc.)
        calories: Target calories (for cardio machines)
        duration_seconds: Duration in seconds (for time-based exercises)
    """
    
    name: str
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    distance_m: Optional[float] = None
    calories: Optional[int] = None
    duration_seconds: Optional[float] = None
    
    def __post_init__(self) -> None:
        """Validate exercise parameters."""
        # Must have at least one target (reps, distance, calories, or duration)
        targets = [self.reps, self.distance_m, self.calories, self.duration_seconds]
        if not any(target is not None for target in targets):
            raise ValueError("Exercise must have at least one target: reps, distance, calories, or duration")
        
        # Validate positive values
        for name, value in [
            ("reps", self.reps),
            ("weight_kg", self.weight_kg),
            ("distance_m", self.distance_m),
            ("calories", self.calories),
            ("duration_seconds", self.duration_seconds)
        ]:
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
    
    def is_weighted(self) -> bool:
        """Check if this exercise uses external weight."""
        return self.weight_kg is not None and self.weight_kg > 0
    
    def is_cardio(self) -> bool:
        """Check if this is a cardio exercise (distance or calorie based)."""
        return self.distance_m is not None or self.calories is not None
    
    def is_time_based(self) -> bool:
        """Check if this exercise is time-based rather than rep-based."""
        return self.duration_seconds is not None
    
    def get_volume(self) -> Union[int, float]:
        """Get the primary volume metric for this exercise."""
        if self.reps is not None:
            return self.reps
        elif self.calories is not None:
            return self.calories
        elif self.distance_m is not None:
            return self.distance_m
        elif self.duration_seconds is not None:
            return self.duration_seconds
        else:
            return 1  # Fallback
    
    def __str__(self) -> str:
        """String representation of the exercise."""
        parts = [self.name]
        
        if self.reps is not None:
            parts.append(f"{self.reps} reps")
        if self.weight_kg is not None:
            parts.append(f"@ {self.weight_kg}kg")
        if self.distance_m is not None:
            parts.append(f"{self.distance_m}m")
        if self.calories is not None:
            parts.append(f"{self.calories} cal")
        if self.duration_seconds is not None:
            parts.append(f"{self.duration_seconds}s")
        
        return " ".join(parts)


@dataclass
class Round:
    """
    Represents a round of exercises in a workout.
    
    Attributes:
        exercises: List of exercises in this round
        repetitions: Number of times to repeat this round (default 1)
    """
    
    exercises: List[Exercise]
    repetitions: int = 1
    
    def __post_init__(self) -> None:
        """Validate round parameters."""
        if not self.exercises:
            raise ValueError("Round must contain at least one exercise")
        if self.repetitions <= 0:
            raise ValueError("Round repetitions must be positive")
    
    def get_total_reps(self) -> int:
        """Get total number of individual exercise repetitions in this round."""
        total = 0
        for exercise in self.exercises:
            if exercise.reps is not None:
                total += exercise.reps * self.repetitions
        return total
    
    def __str__(self) -> str:
        """String representation of the round."""
        exercise_strs = [str(ex) for ex in self.exercises]
        round_str = " + ".join(exercise_strs)
        
        if self.repetitions > 1:
            return f"{self.repetitions} rounds of ({round_str})"
        else:
            return round_str


@dataclass
class WOD:
    """
    Represents a complete Workout of the Day (WOD).
    
    Attributes:
        name: Workout name (e.g., "Fran", "Murph")
        workout_type: Type of workout (FOR_TIME, AMRAP, etc.)
        rounds: List of rounds in the workout
        time_cap_seconds: Maximum time allowed (None for no cap)
        rest_between_rounds: Rest time between rounds in seconds
        description: Optional description of the workout
    """
    
    name: str
    workout_type: WorkoutType
    rounds: List[Round]
    time_cap_seconds: Optional[float] = None
    rest_between_rounds: float = 0.0
    description: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate workout parameters."""
        if not self.rounds:
            raise ValueError("Workout must contain at least one round")
        
        if self.time_cap_seconds is not None and self.time_cap_seconds <= 0:
            raise ValueError("time_cap_seconds must be positive")
        
        if self.rest_between_rounds < 0:
            raise ValueError("rest_between_rounds cannot be negative")
        
        # AMRAP workouts should have a time cap
        if self.workout_type == WorkoutType.AMRAP and self.time_cap_seconds is None:
            raise ValueError("AMRAP workouts must have a time_cap_seconds")
    
    @classmethod
    def for_time(
        cls,
        name: str,
        exercises: List[Tuple[str, int, Optional[float]]] = None,
        rounds: List[Round] = None,
        time_cap_seconds: Optional[float] = None,
        description: Optional[str] = None
    ) -> 'WOD':
        """
        Create a For Time workout.
        
        Args:
            name: Workout name
            exercises: List of (exercise_name, reps, weight_kg) tuples
            rounds: Pre-built rounds (alternative to exercises)
            time_cap_seconds: Optional time cap
            description: Optional description
            
        Returns:
            WOD instance configured for For Time
        """
        if exercises is not None and rounds is not None:
            raise ValueError("Provide either exercises or rounds, not both")
        
        if exercises is not None:
            # Convert exercise tuples to Exercise objects and create a single round
            exercise_objects = []
            for ex_tuple in exercises:
                if len(ex_tuple) == 3:
                    name_ex, reps, weight = ex_tuple
                    exercise_objects.append(Exercise(name=name_ex, reps=reps, weight_kg=weight))
                else:
                    raise ValueError("Exercise tuples must be (name, reps, weight_kg)")
            
            rounds = [Round(exercises=exercise_objects)]
        
        elif rounds is None:
            raise ValueError("Must provide either exercises or rounds")
        
        return cls(
            name=name,
            workout_type=WorkoutType.FOR_TIME,
            rounds=rounds,
            time_cap_seconds=time_cap_seconds,
            description=description
        )
    
    @classmethod
    def amrap(
        cls,
        name: str,
        time_cap_seconds: float,
        exercises: List[Tuple[str, int, Optional[float]]] = None,
        rounds: List[Round] = None,
        description: Optional[str] = None
    ) -> 'WOD':
        """
        Create an AMRAP (As Many Rounds As Possible) workout.
        
        Args:
            name: Workout name
            time_cap_seconds: Time limit for the AMRAP
            exercises: List of (exercise_name, reps, weight_kg) tuples
            rounds: Pre-built rounds (alternative to exercises)
            description: Optional description
            
        Returns:
            WOD instance configured for AMRAP
        """
        if exercises is not None and rounds is not None:
            raise ValueError("Provide either exercises or rounds, not both")
        
        if exercises is not None:
            # Convert exercise tuples to Exercise objects and create a single round
            exercise_objects = []
            for ex_tuple in exercises:
                if len(ex_tuple) == 3:
                    name_ex, reps, weight = ex_tuple
                    exercise_objects.append(Exercise(name=name_ex, reps=reps, weight_kg=weight))
                else:
                    raise ValueError("Exercise tuples must be (name, reps, weight_kg)")
            
            rounds = [Round(exercises=exercise_objects)]
        
        elif rounds is None:
            raise ValueError("Must provide either exercises or rounds")
        
        return cls(
            name=name,
            workout_type=WorkoutType.AMRAP,
            rounds=rounds,
            time_cap_seconds=time_cap_seconds,
            description=description
        )
    
    def get_total_exercises(self) -> int:
        """Get total number of individual exercises in the workout."""
        total = 0
        for round_obj in self.rounds:
            total += len(round_obj.exercises) * round_obj.repetitions
        return total
    
    def get_total_reps(self) -> int:
        """Get total number of repetitions in the workout (for For Time workouts)."""
        if self.workout_type == WorkoutType.AMRAP:
            raise ValueError("Cannot calculate total reps for AMRAP workout")
        
        total = 0
        for round_obj in self.rounds:
            total += round_obj.get_total_reps()
        return total
    
    def get_all_exercises(self) -> List[Exercise]:
        """Get a flat list of all exercises in order of execution."""
        all_exercises = []
        for round_obj in self.rounds:
            for _ in range(round_obj.repetitions):
                all_exercises.extend(round_obj.exercises)
        return all_exercises
    
    def __str__(self) -> str:
        """String representation of the workout."""
        lines = [f"{self.name} ({self.workout_type.value.replace('_', ' ').title()})"]
        
        if self.time_cap_seconds:
            lines.append(f"Time Cap: {self.time_cap_seconds/60:.0f} minutes")
        
        if self.description:
            lines.append(f"Description: {self.description}")
        
        lines.append("Workout:")
        for i, round_obj in enumerate(self.rounds):
            lines.append(f"  {i+1}. {round_obj}")
        
        return "\n".join(lines)


# Predefined famous CrossFit WODs
class FamousWODs:
    """Collection of famous CrossFit benchmark WODs."""
    
    @staticmethod
    def fran() -> WOD:
        """The famous 'Fran' workout: 21-15-9 thrusters and pull-ups."""
        return WOD.for_time(
            name="Fran",
            rounds=[
                Round([Exercise("thruster", 21, 42.5), Exercise("pull-up", 21)]),
                Round([Exercise("thruster", 15, 42.5), Exercise("pull-up", 15)]),
                Round([Exercise("thruster", 9, 42.5), Exercise("pull-up", 9)])
            ],
            description="21-15-9 Thrusters (42.5kg) and Pull-ups"
        )
    
    @staticmethod
    def helen() -> WOD:
        """The 'Helen' workout: 3 rounds of 400m run, 21 KB swings, 12 pull-ups."""
        return WOD.for_time(
            name="Helen",
            rounds=[
                Round([
                    Exercise("run", distance_m=400),
                    Exercise("kettlebell-swing", 21, 24),
                    Exercise("pull-up", 12)
                ], repetitions=3)
            ],
            description="3 rounds of 400m Run, 21 KB Swings (24kg), 12 Pull-ups"
        )
    
    @staticmethod
    def cindy() -> WOD:
        """The 'Cindy' workout: AMRAP 20 min of 5 pull-ups, 10 push-ups, 15 air squats."""
        return WOD.amrap(
            name="Cindy",
            time_cap_seconds=1200,  # 20 minutes
            rounds=[
                Round([
                    Exercise("pull-up", 5),
                    Exercise("push-up", 10),
                    Exercise("air-squat", 15)
                ])
            ],
            description="AMRAP 20 min: 5 Pull-ups, 10 Push-ups, 15 Air Squats"
        )
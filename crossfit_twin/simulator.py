"""
Simulator module for CrossFit Digital Twin.

Contains the core simulation engine that executes WODs with athletes and strategies.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
import time
from enum import Enum

from .athlete import Athlete
from .workout import WOD, Exercise, WorkoutType
from .strategy import Strategy


class SimulationEventType(Enum):
    """Types of events that can occur during simulation."""
    EXERCISE_START = "exercise_start"
    REP_COMPLETED = "rep_completed"
    REST_START = "rest_start"
    REST_END = "rest_end"
    ROUND_COMPLETED = "round_completed"
    WORKOUT_COMPLETED = "workout_completed"
    TIME_CAP_REACHED = "time_cap_reached"


@dataclass
class SimulationEvent:
    """
    Represents an event during workout simulation.
    
    Attributes:
        timestamp: Time when event occurred (seconds)
        event_type: Type of simulation event
        exercise_name: Name of exercise (if applicable)
        rep_number: Repetition number (if applicable)
        round_number: Round number (1-indexed)
        fatigue_level: Athlete's fatigue at this point
        details: Additional event details
    """
    
    timestamp: float
    event_type: SimulationEventType
    exercise_name: Optional[str] = None
    rep_number: Optional[int] = None
    round_number: int = 1
    fatigue_level: float = 0.0
    details: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the event."""
        parts = [f"t={self.timestamp:.1f}s"]
        
        if self.round_number > 1:
            parts.append(f"R{self.round_number}")
        
        if self.exercise_name:
            parts.append(self.exercise_name)
        
        if self.rep_number:
            parts.append(f"rep {self.rep_number}")
        
        parts.append(f"({self.event_type.value})")
        
        if self.fatigue_level > 0:
            parts.append(f"fatigue={self.fatigue_level:.2f}")
        
        if self.details:
            parts.append(f"- {self.details}")
        
        return " ".join(parts)


@dataclass
class RoundResult:
    """
    Results for a single round of a workout.
    
    Attributes:
        round_number: Round number (1-indexed)
        start_time: When the round started (seconds)
        end_time: When the round ended (seconds)
        duration: Total round duration (seconds)
        exercises_completed: Number of exercises completed in this round
        reps_completed: Total reps completed in this round
        avg_fatigue: Average fatigue during this round
        max_fatigue: Maximum fatigue reached in this round
    """
    
    round_number: int
    start_time: float
    end_time: float
    duration: float
    exercises_completed: int
    reps_completed: int
    avg_fatigue: float
    max_fatigue: float
    
    @property
    def pace_per_rep(self) -> float:
        """Average time per rep in this round."""
        return self.duration / self.reps_completed if self.reps_completed > 0 else 0.0


@dataclass
class SimulationResult:
    """
    Complete results of a workout simulation.
    
    Attributes:
        athlete_name: Name of the athlete
        workout_name: Name of the workout
        strategy_name: Name of the strategy used
        total_time: Total time to complete workout (seconds)
        completed: Whether workout was completed
        rounds_completed: Number of complete rounds finished
        total_reps: Total repetitions completed
        final_fatigue: Final fatigue level
        round_results: Results for each round
        events: Chronological list of simulation events
        avg_pace: Average time per rep across workout
        time_splits: Time splits by round
        fatigue_curve: Fatigue progression over time
    """
    
    athlete_name: str
    workout_name: str
    strategy_name: str
    total_time: float
    completed: bool
    rounds_completed: int
    total_reps: int
    final_fatigue: float
    round_results: List[RoundResult] = field(default_factory=list)
    events: List[SimulationEvent] = field(default_factory=list)
    avg_pace: float = 0.0
    time_splits: List[float] = field(default_factory=list)
    fatigue_curve: List[Tuple[float, float]] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Calculate derived metrics."""
        if self.total_reps > 0:
            self.avg_pace = self.total_time / self.total_reps
        
        # Extract time splits from round results
        self.time_splits = [round_result.end_time for round_result in self.round_results]
        
        # Extract fatigue curve from events
        self.fatigue_curve = [
            (event.timestamp, event.fatigue_level) 
            for event in self.events 
            if event.fatigue_level > 0
        ]
    
    def get_summary(self) -> str:
        """Get a summary string of the results."""
        status = "✅ COMPLETED" if self.completed else "❌ TIME CAP"
        
        summary_lines = [
            f"=== SIMULATION RESULT ===",
            f"Athlete: {self.athlete_name}",
            f"Workout: {self.workout_name}",
            f"Strategy: {self.strategy_name}",
            f"Status: {status}",
            f"Total Time: {self.total_time:.1f}s ({self.total_time/60:.1f} min)",
            f"Rounds: {self.rounds_completed}",
            f"Total Reps: {self.total_reps}",
            f"Avg Pace: {self.avg_pace:.2f}s/rep",
            f"Final Fatigue: {self.final_fatigue:.2f}",
        ]
        
        if self.round_results:
            summary_lines.append("\n--- Round Splits ---")
            for round_result in self.round_results:
                summary_lines.append(
                    f"Round {round_result.round_number}: {round_result.duration:.1f}s "
                    f"({round_result.pace_per_rep:.2f}s/rep, max fatigue: {round_result.max_fatigue:.2f})"
                )
        
        return "\n".join(summary_lines)
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for serialization."""
        return {
            "athlete_name": self.athlete_name,
            "workout_name": self.workout_name,
            "strategy_name": self.strategy_name,
            "total_time": self.total_time,
            "completed": self.completed,
            "rounds_completed": self.rounds_completed,
            "total_reps": self.total_reps,
            "final_fatigue": self.final_fatigue,
            "avg_pace": self.avg_pace,
            "time_splits": self.time_splits,
            "fatigue_curve": self.fatigue_curve,
        }


class WorkoutSimulator:
    """
    Core simulation engine for executing CrossFit workouts.
    
    This class handles the step-by-step simulation of an athlete performing
    a workout according to a specific pacing strategy.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the simulator.
        
        Args:
            verbose: Whether to print detailed simulation progress
        """
        self.verbose = verbose
        self.reset()
    
    def reset(self) -> None:
        """Reset simulator state for a new simulation."""
        self.current_time = 0.0
        self.current_fatigue = 0.0
        self.events: List[SimulationEvent] = []
        self.round_results: List[RoundResult] = []
        self.total_reps = 0
        self.rounds_completed = 0
    
    def simulate(
        self, 
        workout: WOD, 
        athlete: Athlete, 
        strategy: Strategy
    ) -> SimulationResult:
        """
        Simulate an athlete performing a workout with a given strategy.
        
        Args:
            workout: The workout to simulate
            athlete: The athlete performing the workout
            strategy: The pacing strategy to use
            
        Returns:
            SimulationResult with complete simulation data
        """
        self.reset()
        
        if self.verbose:
            print(f"\n=== SIMULATING {workout.name} ===")
            print(f"Athlete: {athlete.name}")
            print(f"Strategy: {strategy.name}")
            print(f"Workout Type: {workout.workout_type.value}")
        
        # Handle different workout types
        if workout.workout_type == WorkoutType.FOR_TIME:
            completed = self._simulate_for_time(workout, athlete, strategy)
        elif workout.workout_type == WorkoutType.AMRAP:
            completed = self._simulate_amrap(workout, athlete, strategy)
        else:
            raise NotImplementedError(f"Workout type {workout.workout_type} not yet implemented")
        
        # Create final result
        result = SimulationResult(
            athlete_name=athlete.name,
            workout_name=workout.name,
            strategy_name=strategy.name,
            total_time=self.current_time,
            completed=completed,
            rounds_completed=self.rounds_completed,
            total_reps=self.total_reps,
            final_fatigue=self.current_fatigue,
            round_results=self.round_results,
            events=self.events
        )
        
        if self.verbose:
            print(f"\n{result.get_summary()}")
        
        return result
    
    def _simulate_for_time(
        self, 
        workout: WOD, 
        athlete: Athlete, 
        strategy: Strategy
    ) -> bool:
        """Simulate a For Time workout."""
        total_rounds = sum(round_obj.repetitions for round_obj in workout.rounds)
        current_round_global = 1
        
        for round_obj in workout.rounds:
            for round_rep in range(round_obj.repetitions):
                round_start_time = self.current_time
                round_start_fatigue = self.current_fatigue
                round_reps = 0
                fatigue_samples = []
                
                self._add_event(
                    SimulationEventType.EXERCISE_START,
                    round_number=current_round_global,
                    details=f"Starting round {current_round_global}/{total_rounds}"
                )
                
                # Execute each exercise in the round
                for exercise in round_obj.exercises:
                    if not self._simulate_exercise(exercise, athlete, strategy, current_round_global):
                        # Time cap reached
                        return False
                    
                    # Count reps completed in this round
                    if exercise.reps:
                        round_reps += exercise.reps
                
                # Record round completion
                round_end_time = self.current_time
                round_duration = round_end_time - round_start_time
                
                # Calculate round statistics
                avg_fatigue = sum(fatigue_samples) / len(fatigue_samples) if fatigue_samples else self.current_fatigue
                max_fatigue = max(fatigue_samples) if fatigue_samples else self.current_fatigue
                
                round_result = RoundResult(
                    round_number=current_round_global,
                    start_time=round_start_time,
                    end_time=round_end_time,
                    duration=round_duration,
                    exercises_completed=len(round_obj.exercises),
                    reps_completed=round_reps,
                    avg_fatigue=avg_fatigue,
                    max_fatigue=max_fatigue
                )
                
                self.round_results.append(round_result)
                self.rounds_completed += 1
                
                self._add_event(
                    SimulationEventType.ROUND_COMPLETED,
                    round_number=current_round_global,
                    details=f"Round {current_round_global} completed in {round_duration:.1f}s"
                )
                
                # Rest between rounds if specified
                if workout.rest_between_rounds > 0 and current_round_global < total_rounds:
                    self._simulate_rest(workout.rest_between_rounds, athlete, "between rounds")
                
                current_round_global += 1
        
        self._add_event(SimulationEventType.WORKOUT_COMPLETED)
        return True
    
    def _simulate_amrap(
        self, 
        workout: WOD, 
        athlete: Athlete, 
        strategy: Strategy
    ) -> bool:
        """Simulate an AMRAP workout."""
        if workout.time_cap_seconds is None:
            raise ValueError("AMRAP workout must have a time cap")
        
        round_number = 1
        
        while self.current_time < workout.time_cap_seconds:
            round_start_time = self.current_time
            round_reps = 0
            
            # Try to complete a full round
            round_completed = True
            for round_obj in workout.rounds:
                for exercise in round_obj.exercises:
                    if self.current_time >= workout.time_cap_seconds:
                        round_completed = False
                        break
                    
                    # Simulate as many reps as possible within time cap
                    reps_completed = self._simulate_exercise_with_time_limit(
                        exercise, athlete, strategy, round_number, workout.time_cap_seconds
                    )
                    
                    if exercise.reps and reps_completed < exercise.reps:
                        round_completed = False
                        break
                    
                    if exercise.reps:
                        round_reps += reps_completed
                
                if not round_completed:
                    break
            
            if round_completed:
                # Full round completed
                round_duration = self.current_time - round_start_time
                
                round_result = RoundResult(
                    round_number=round_number,
                    start_time=round_start_time,
                    end_time=self.current_time,
                    duration=round_duration,
                    exercises_completed=len(workout.rounds[0].exercises),
                    reps_completed=round_reps,
                    avg_fatigue=self.current_fatigue,
                    max_fatigue=self.current_fatigue
                )
                
                self.round_results.append(round_result)
                self.rounds_completed += 1
                
                self._add_event(
                    SimulationEventType.ROUND_COMPLETED,
                    round_number=round_number,
                    details=f"Round {round_number} completed in {round_duration:.1f}s"
                )
                
                round_number += 1
            else:
                # Partial round or time cap reached
                break
        
        self._add_event(SimulationEventType.TIME_CAP_REACHED)
        return False  # AMRAP never truly "completes"
    
    def _simulate_exercise(
        self, 
        exercise: Exercise, 
        athlete: Athlete, 
        strategy: Strategy, 
        round_number: int
    ) -> bool:
        """Simulate a complete exercise."""
        if exercise.reps is None:
            # Handle time-based or distance-based exercises
            return self._simulate_non_rep_exercise(exercise, athlete, strategy, round_number)
        
        target_reps = exercise.reps
        reps_completed = 0
        
        self._add_event(
            SimulationEventType.EXERCISE_START,
            exercise_name=exercise.name,
            round_number=round_number,
            details=f"Starting {exercise.name} x{target_reps}"
        )
        
        while reps_completed < target_reps:
            # Check if we should rest before this rep
            if strategy.should_rest(
                exercise.name,
                reps_completed,
                target_reps,
                self.current_fatigue,
                self.current_time
            ):
                rest_duration = strategy.rest_duration(
                    exercise.name,
                    reps_completed,
                    self.current_fatigue,
                    self.current_time
                )
                self._simulate_rest(rest_duration, athlete, f"during {exercise.name}")
            
            # Perform one rep
            rep_time = athlete.get_rep_time(exercise.name, exercise.weight_kg, self.current_fatigue)
            fatigue_increase = athlete.get_fatigue_per_rep(exercise.name, exercise.weight_kg)
            
            self.current_time += rep_time
            self.current_fatigue += fatigue_increase
            reps_completed += 1
            self.total_reps += 1
            
            self._add_event(
                SimulationEventType.REP_COMPLETED,
                exercise_name=exercise.name,
                rep_number=reps_completed,
                round_number=round_number
            )
            
            if self.verbose and reps_completed % 5 == 0:
                print(f"  {exercise.name}: {reps_completed}/{target_reps} reps, "
                      f"fatigue: {self.current_fatigue:.2f}, time: {self.current_time:.1f}s")
        
        return True
    
    def _simulate_exercise_with_time_limit(
        self,
        exercise: Exercise,
        athlete: Athlete,
        strategy: Strategy,
        round_number: int,
        time_cap: float
    ) -> int:
        """Simulate exercise with time cap, returning reps completed."""
        if exercise.reps is None:
            return 0
        
        target_reps = exercise.reps
        reps_completed = 0
        
        while reps_completed < target_reps and self.current_time < time_cap:
            # Check if we should rest
            if strategy.should_rest(
                exercise.name,
                reps_completed,
                target_reps,
                self.current_fatigue,
                self.current_time
            ):
                rest_duration = strategy.rest_duration(
                    exercise.name,
                    reps_completed,
                    self.current_fatigue,
                    self.current_time
                )
                
                # Don't rest if it would exceed time cap
                if self.current_time + rest_duration >= time_cap:
                    break
                
                self._simulate_rest(rest_duration, athlete, f"during {exercise.name}")
            
            # Check if we have time for one more rep
            rep_time = athlete.get_rep_time(exercise.name, exercise.weight_kg, self.current_fatigue)
            if self.current_time + rep_time > time_cap:
                break
            
            # Perform one rep
            fatigue_increase = athlete.get_fatigue_per_rep(exercise.name, exercise.weight_kg)
            
            self.current_time += rep_time
            self.current_fatigue += fatigue_increase
            reps_completed += 1
            self.total_reps += 1
            
            self._add_event(
                SimulationEventType.REP_COMPLETED,
                exercise_name=exercise.name,
                rep_number=reps_completed,
                round_number=round_number
            )
        
        return reps_completed
    
    def _simulate_non_rep_exercise(
        self, 
        exercise: Exercise, 
        athlete: Athlete, 
        strategy: Strategy, 
        round_number: int
    ) -> bool:
        """Simulate time-based or distance-based exercises."""
        if exercise.duration_seconds:
            # Time-based exercise
            self.current_time += exercise.duration_seconds
            # Assume moderate fatigue accumulation for time-based exercises
            self.current_fatigue += 0.1
        elif exercise.distance_m:
            # Distance-based exercise (estimate time)
            # Rough estimate: 1 meter per second base pace, adjusted for fitness
            base_speed = 1.0  # m/s
            fitness_factor = athlete.endurance / 100.0
            actual_speed = base_speed * (0.5 + fitness_factor)
            time_needed = exercise.distance_m / actual_speed
            
            self.current_time += time_needed
            self.current_fatigue += exercise.distance_m * 0.001  # Small fatigue per meter
        elif exercise.calories:
            # Calorie-based exercise
            # Rough estimate: 1 calorie per 2 seconds, adjusted for fitness
            base_cal_per_sec = 0.5
            fitness_factor = athlete.endurance / 100.0
            actual_cal_per_sec = base_cal_per_sec * (0.5 + fitness_factor)
            time_needed = exercise.calories / actual_cal_per_sec
            
            self.current_time += time_needed
            self.current_fatigue += exercise.calories * 0.01
        
        return True
    
    def _simulate_rest(self, duration: float, athlete: Athlete, context: str) -> None:
        """Simulate rest period with fatigue recovery."""
        if duration <= 0:
            return
        
        self._add_event(
            SimulationEventType.REST_START,
            details=f"Resting for {duration:.1f}s {context}"
        )
        
        # Recover fatigue during rest
        self.current_fatigue = athlete.recover(duration, self.current_fatigue)
        self.current_time += duration
        
        self._add_event(
            SimulationEventType.REST_END,
            details=f"Rest complete, fatigue now {self.current_fatigue:.2f}"
        )
    
    def _add_event(
        self,
        event_type: SimulationEventType,
        exercise_name: Optional[str] = None,
        rep_number: Optional[int] = None,
        round_number: int = 1,
        details: Optional[str] = None
    ) -> None:
        """Add an event to the simulation log."""
        event = SimulationEvent(
            timestamp=self.current_time,
            event_type=event_type,
            exercise_name=exercise_name,
            rep_number=rep_number,
            round_number=round_number,
            fatigue_level=self.current_fatigue,
            details=details
        )
        
        self.events.append(event)
        
        if self.verbose:
            print(f"  {event}")


# Convenience function for easy simulation
def simulate(
    workout: WOD,
    athlete: Athlete,
    strategy: Strategy,
    verbose: bool = False
) -> SimulationResult:
    """
    Convenience function to simulate a workout.
    
    Args:
        workout: The workout to simulate
        athlete: The athlete performing the workout
        strategy: The pacing strategy to use
        verbose: Whether to print detailed progress
        
    Returns:
        SimulationResult with complete simulation data
    """
    simulator = WorkoutSimulator(verbose=verbose)
    return simulator.simulate(workout, athlete, strategy)
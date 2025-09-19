"""
Unit tests for the Simulator module.
"""

import pytest
from crossfit_twin.athlete import Athlete
from crossfit_twin.workout import WOD, Exercise, Round, WorkoutType
from crossfit_twin.strategy import StrategyFactory
from crossfit_twin.simulator import (
    SimulationEvent, SimulationEventType, RoundResult, SimulationResult,
    WorkoutSimulator, simulate
)


class TestSimulationEvent:
    """Test cases for the SimulationEvent class."""
    
    def test_simulation_event_creation(self):
        """Test creating a simulation event."""
        event = SimulationEvent(
            timestamp=60.5,
            event_type=SimulationEventType.REP_COMPLETED,
            exercise_name="thruster",
            rep_number=10,
            round_number=1,
            fatigue_level=0.4,
            details="Completed thruster rep"
        )
        
        assert event.timestamp == 60.5
        assert event.event_type == SimulationEventType.REP_COMPLETED
        assert event.exercise_name == "thruster"
        assert event.rep_number == 10
        assert event.round_number == 1
        assert event.fatigue_level == 0.4
        assert event.details == "Completed thruster rep"
    
    def test_simulation_event_str_representation(self):
        """Test string representation of simulation event."""
        event = SimulationEvent(
            timestamp=60.5,
            event_type=SimulationEventType.REP_COMPLETED,
            exercise_name="thruster",
            rep_number=10,
            fatigue_level=0.4
        )
        
        str_repr = str(event)
        assert "t=60.5s" in str_repr
        assert "thruster" in str_repr
        assert "rep 10" in str_repr
        assert "rep_completed" in str_repr
        assert "fatigue=0.40" in str_repr


class TestRoundResult:
    """Test cases for the RoundResult class."""
    
    def test_round_result_creation(self):
        """Test creating a round result."""
        result = RoundResult(
            round_number=1,
            start_time=0.0,
            end_time=120.0,
            duration=120.0,
            exercises_completed=2,
            reps_completed=42,
            avg_fatigue=0.3,
            max_fatigue=0.6
        )
        
        assert result.round_number == 1
        assert result.start_time == 0.0
        assert result.end_time == 120.0
        assert result.duration == 120.0
        assert result.exercises_completed == 2
        assert result.reps_completed == 42
        assert result.avg_fatigue == 0.3
        assert result.max_fatigue == 0.6
    
    def test_round_result_pace_per_rep(self):
        """Test pace per rep calculation."""
        result = RoundResult(
            round_number=1,
            start_time=0.0,
            end_time=120.0,
            duration=120.0,
            exercises_completed=2,
            reps_completed=40,
            avg_fatigue=0.3,
            max_fatigue=0.6
        )
        
        assert result.pace_per_rep == 3.0  # 120s / 40 reps
    
    def test_round_result_pace_per_rep_zero_reps(self):
        """Test pace per rep with zero reps."""
        result = RoundResult(
            round_number=1,
            start_time=0.0,
            end_time=60.0,
            duration=60.0,
            exercises_completed=1,
            reps_completed=0,
            avg_fatigue=0.1,
            max_fatigue=0.2
        )
        
        assert result.pace_per_rep == 0.0


class TestSimulationResult:
    """Test cases for the SimulationResult class."""
    
    def test_simulation_result_creation(self):
        """Test creating a simulation result."""
        result = SimulationResult(
            athlete_name="Test Athlete",
            workout_name="Fran",
            strategy_name="Unbroken",
            total_time=180.0,
            completed=True,
            rounds_completed=3,
            total_reps=90,
            final_fatigue=0.8
        )
        
        assert result.athlete_name == "Test Athlete"
        assert result.workout_name == "Fran"
        assert result.strategy_name == "Unbroken"
        assert result.total_time == 180.0
        assert result.completed is True
        assert result.rounds_completed == 3
        assert result.total_reps == 90
        assert result.final_fatigue == 0.8
    
    def test_simulation_result_avg_pace_calculation(self):
        """Test that avg_pace is calculated automatically."""
        result = SimulationResult(
            athlete_name="Test",
            workout_name="Test WOD",
            strategy_name="Test Strategy",
            total_time=180.0,
            completed=True,
            rounds_completed=1,
            total_reps=60,
            final_fatigue=0.5
        )
        
        assert result.avg_pace == 3.0  # 180s / 60 reps
    
    def test_simulation_result_avg_pace_zero_reps(self):
        """Test avg_pace calculation with zero reps."""
        result = SimulationResult(
            athlete_name="Test",
            workout_name="Test WOD",
            strategy_name="Test Strategy",
            total_time=60.0,
            completed=False,
            rounds_completed=0,
            total_reps=0,
            final_fatigue=0.2
        )
        
        assert result.avg_pace == 0.0
    
    def test_simulation_result_get_summary(self):
        """Test getting result summary."""
        result = SimulationResult(
            athlete_name="Test Athlete",
            workout_name="Fran",
            strategy_name="Unbroken",
            total_time=180.0,
            completed=True,
            rounds_completed=3,
            total_reps=90,
            final_fatigue=0.8
        )
        
        summary = result.get_summary()
        assert "Test Athlete" in summary
        assert "Fran" in summary
        assert "Unbroken" in summary
        assert "180.0s" in summary
        assert "✅ COMPLETED" in summary
        assert "90" in summary  # total reps
    
    def test_simulation_result_get_summary_time_cap(self):
        """Test getting result summary for time cap scenario."""
        result = SimulationResult(
            athlete_name="Test Athlete",
            workout_name="Long WOD",
            strategy_name="Conservative",
            total_time=300.0,
            completed=False,
            rounds_completed=2,
            total_reps=60,
            final_fatigue=0.9
        )
        
        summary = result.get_summary()
        assert "❌ TIME CAP" in summary
    
    def test_simulation_result_to_dict(self):
        """Test converting result to dictionary."""
        result = SimulationResult(
            athlete_name="Test",
            workout_name="Test WOD",
            strategy_name="Test Strategy",
            total_time=120.0,
            completed=True,
            rounds_completed=1,
            total_reps=30,
            final_fatigue=0.4
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["athlete_name"] == "Test"
        assert result_dict["workout_name"] == "Test WOD"
        assert result_dict["total_time"] == 120.0
        assert result_dict["completed"] is True
        assert isinstance(result_dict, dict)


class TestWorkoutSimulator:
    """Test cases for the WorkoutSimulator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.athlete = Athlete(
            name="Test Athlete",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        self.strategy = StrategyFactory.unbroken()
        
        # Simple workout: 10 thrusters
        self.simple_workout = WOD.for_time(
            name="Simple Test",
            exercises=[("thruster", 10, 40.0)]
        )
    
    def test_simulator_creation(self):
        """Test creating a workout simulator."""
        simulator = WorkoutSimulator()
        
        assert simulator.verbose is False
        assert simulator.current_time == 0.0
        assert simulator.current_fatigue == 0.0
        assert len(simulator.events) == 0
    
    def test_simulator_creation_verbose(self):
        """Test creating a verbose simulator."""
        simulator = WorkoutSimulator(verbose=True)
        
        assert simulator.verbose is True
    
    def test_simulator_reset(self):
        """Test resetting simulator state."""
        simulator = WorkoutSimulator()
        
        # Modify some state
        simulator.current_time = 100.0
        simulator.current_fatigue = 0.5
        simulator.events.append(
            SimulationEvent(50.0, SimulationEventType.REP_COMPLETED)
        )
        
        simulator.reset()
        
        assert simulator.current_time == 0.0
        assert simulator.current_fatigue == 0.0
        assert len(simulator.events) == 0
    
    def test_simulate_simple_workout(self):
        """Test simulating a simple workout."""
        self.setUp()
        simulator = WorkoutSimulator()
        
        result = simulator.simulate(self.simple_workout, self.athlete, self.strategy)
        
        assert isinstance(result, SimulationResult)
        assert result.athlete_name == "Test Athlete"
        assert result.workout_name == "Simple Test"
        assert result.strategy_name == "Unbroken"
        assert result.total_time > 0
        assert result.completed is True
        assert result.total_reps == 10
        assert result.rounds_completed == 1
    
    def test_simulate_for_time_workout(self):
        """Test simulating a For Time workout."""
        self.setUp()
        
        # Fran-like workout: 21-15-9 thrusters and pull-ups
        workout = WOD(
            name="Fran-like",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[
                Round([Exercise("thruster", 21, 42.5), Exercise("pull-up", 21)]),
                Round([Exercise("thruster", 15, 42.5), Exercise("pull-up", 15)]),
                Round([Exercise("thruster", 9, 42.5), Exercise("pull-up", 9)])
            ]
        )
        
        simulator = WorkoutSimulator()
        result = simulator.simulate(workout, self.athlete, self.strategy)
        
        assert result.completed is True
        assert result.rounds_completed == 3
        assert result.total_reps == (21 + 21 + 15 + 15 + 9 + 9)  # 90 total
        assert len(result.round_results) == 3
    
    def test_simulate_amrap_workout(self):
        """Test simulating an AMRAP workout."""
        self.setUp()
        
        # Simple AMRAP: 5 minutes of 5 thrusters
        amrap_workout = WOD.amrap(
            name="5 min AMRAP",
            time_cap_seconds=300.0,  # 5 minutes
            exercises=[("thruster", 5, 40.0)]
        )
        
        simulator = WorkoutSimulator()
        result = simulator.simulate(amrap_workout, self.athlete, self.strategy)
        
        assert result.completed is False  # AMRAP never truly "completes"
        assert result.total_time <= 300.0  # Should not exceed time cap
        assert result.total_reps > 0  # Should complete some reps
        assert result.rounds_completed >= 0
    
    def test_simulate_with_time_cap(self):
        """Test simulating workout with time cap reached."""
        self.setUp()
        
        # Long workout with short time cap
        long_workout = WOD.for_time(
            name="Long Test",
            exercises=[("thruster", 100, 60.0)],  # 100 heavy thrusters
            time_cap_seconds=30.0  # Very short time cap
        )
        
        simulator = WorkoutSimulator()
        result = simulator.simulate(long_workout, self.athlete, self.strategy)
        
        assert result.total_time <= 30.0
        assert result.total_reps < 100  # Shouldn't complete all reps
    
    def test_simulate_with_fatigue_accumulation(self):
        """Test that fatigue accumulates during simulation."""
        self.setUp()
        
        simulator = WorkoutSimulator()
        result = simulator.simulate(self.simple_workout, self.athlete, self.strategy)
        
        assert result.final_fatigue > 0  # Should have some fatigue
        
        # Check that fatigue progressed through events
        fatigue_levels = [event.fatigue_level for event in result.events if event.fatigue_level > 0]
        if len(fatigue_levels) > 1:
            # Generally increasing fatigue (allowing for recovery)
            max_fatigue = max(fatigue_levels)
            assert max_fatigue > 0
    
    def test_simulate_unknown_workout_type_error(self):
        """Test that unknown workout type raises error."""
        self.setUp()
        
        # Create workout with unsupported type
        unsupported_workout = WOD(
            name="Unsupported",
            workout_type=WorkoutType.EMOM,  # Not yet implemented
            rounds=[Round([Exercise("thruster", 10, 40.0)])]
        )
        
        simulator = WorkoutSimulator()
        
        with pytest.raises(NotImplementedError, match="Workout type.*not yet implemented"):
            simulator.simulate(unsupported_workout, self.athlete, self.strategy)


class TestConvenienceFunction:
    """Test cases for the convenience simulate function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.athlete = Athlete(
            name="Test Athlete",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        self.strategy = StrategyFactory.conservative()
        
        self.workout = WOD.for_time(
            name="Test WOD",
            exercises=[("thruster", 15, 40.0), ("pull-up", 15, None)]
        )
    
    def test_convenience_simulate_function(self):
        """Test the convenience simulate function."""
        self.setUp()
        
        result = simulate(self.workout, self.athlete, self.strategy)
        
        assert isinstance(result, SimulationResult)
        assert result.athlete_name == "Test Athlete"
        assert result.workout_name == "Test WOD"
        assert result.strategy_name == "Conservative"
    
    def test_convenience_simulate_function_verbose(self):
        """Test the convenience simulate function with verbose output."""
        self.setUp()
        
        result = simulate(self.workout, self.athlete, self.strategy, verbose=True)
        
        assert isinstance(result, SimulationResult)
        # Verbose output is printed, but we can't easily test that here
    
    def test_simulate_creates_events(self):
        """Test that simulation creates appropriate events."""
        self.setUp()
        
        result = simulate(self.workout, self.athlete, self.strategy)
        
        assert len(result.events) > 0
        
        # Should have workout start/completion events
        event_types = [event.event_type for event in result.events]
        assert SimulationEventType.EXERCISE_START in event_types
        
        if result.completed:
            assert SimulationEventType.WORKOUT_COMPLETED in event_types
    
    def test_simulate_creates_round_results(self):
        """Test that simulation creates round results."""
        self.setUp()
        
        result = simulate(self.workout, self.athlete, self.strategy)
        
        if result.rounds_completed > 0:
            assert len(result.round_results) == result.rounds_completed
            
            for round_result in result.round_results:
                assert isinstance(round_result, RoundResult)
                assert round_result.duration > 0
                assert round_result.exercises_completed > 0
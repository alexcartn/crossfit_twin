"""
Unit tests for the Workout module.
"""

import pytest
from crossfit_twin.workout import Exercise, Round, WOD, WorkoutType, FamousWODs


class TestExercise:
    """Test cases for the Exercise class."""
    
    def test_exercise_creation_with_reps(self):
        """Test creating exercise with repetitions."""
        exercise = Exercise(name="thruster", reps=21, weight_kg=42.5)
        
        assert exercise.name == "thruster"
        assert exercise.reps == 21
        assert exercise.weight_kg == 42.5
        assert exercise.distance_m is None
        assert exercise.calories is None
        assert exercise.duration_seconds is None
    
    def test_exercise_creation_with_distance(self):
        """Test creating exercise with distance."""
        exercise = Exercise(name="run", distance_m=400)
        
        assert exercise.name == "run"
        assert exercise.distance_m == 400
        assert exercise.reps is None
        assert exercise.weight_kg is None
    
    def test_exercise_creation_with_calories(self):
        """Test creating exercise with calories."""
        exercise = Exercise(name="rowing", calories=20)
        
        assert exercise.name == "rowing"
        assert exercise.calories == 20
        assert exercise.reps is None
        assert exercise.distance_m is None
    
    def test_exercise_creation_with_duration(self):
        """Test creating exercise with duration."""
        exercise = Exercise(name="plank", duration_seconds=60)
        
        assert exercise.name == "plank"
        assert exercise.duration_seconds == 60
        assert exercise.reps is None
    
    def test_exercise_validation_no_target(self):
        """Test that exercise must have at least one target."""
        with pytest.raises(ValueError, match="Exercise must have at least one target"):
            Exercise(name="invalid")
    
    def test_exercise_validation_negative_reps(self):
        """Test that negative reps are not allowed."""
        with pytest.raises(ValueError, match="reps must be positive"):
            Exercise(name="thruster", reps=-5)
    
    def test_exercise_validation_negative_weight(self):
        """Test that negative weight is not allowed."""
        with pytest.raises(ValueError, match="weight_kg must be positive"):
            Exercise(name="thruster", reps=10, weight_kg=-20)
    
    def test_exercise_is_weighted(self):
        """Test is_weighted method."""
        weighted = Exercise(name="thruster", reps=21, weight_kg=42.5)
        bodyweight = Exercise(name="pull-up", reps=21)
        
        assert weighted.is_weighted() is True
        assert bodyweight.is_weighted() is False
    
    def test_exercise_is_cardio(self):
        """Test is_cardio method."""
        distance_cardio = Exercise(name="run", distance_m=400)
        calorie_cardio = Exercise(name="rowing", calories=20)
        strength = Exercise(name="thruster", reps=21, weight_kg=42.5)
        
        assert distance_cardio.is_cardio() is True
        assert calorie_cardio.is_cardio() is True
        assert strength.is_cardio() is False
    
    def test_exercise_is_time_based(self):
        """Test is_time_based method."""
        time_based = Exercise(name="plank", duration_seconds=60)
        rep_based = Exercise(name="thruster", reps=21)
        
        assert time_based.is_time_based() is True
        assert rep_based.is_time_based() is False
    
    def test_exercise_get_volume(self):
        """Test get_volume method."""
        rep_exercise = Exercise(name="thruster", reps=21)
        distance_exercise = Exercise(name="run", distance_m=400)
        calorie_exercise = Exercise(name="rowing", calories=20)
        time_exercise = Exercise(name="plank", duration_seconds=60)
        
        assert rep_exercise.get_volume() == 21
        assert distance_exercise.get_volume() == 400
        assert calorie_exercise.get_volume() == 20
        assert time_exercise.get_volume() == 60
    
    def test_exercise_str_representation(self):
        """Test string representation of exercise."""
        exercise = Exercise(name="thruster", reps=21, weight_kg=42.5)
        str_repr = str(exercise)
        
        assert "thruster" in str_repr
        assert "21 reps" in str_repr
        assert "42.5kg" in str_repr


class TestRound:
    """Test cases for the Round class."""
    
    def test_round_creation(self):
        """Test creating a basic round."""
        exercises = [
            Exercise(name="thruster", reps=21, weight_kg=42.5),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises)
        
        assert len(round_obj.exercises) == 2
        assert round_obj.repetitions == 1  # default
    
    def test_round_creation_with_repetitions(self):
        """Test creating round with multiple repetitions."""
        exercises = [Exercise(name="burpee", reps=5)]
        round_obj = Round(exercises=exercises, repetitions=3)
        
        assert round_obj.repetitions == 3
    
    def test_round_validation_empty_exercises(self):
        """Test that round must contain exercises."""
        with pytest.raises(ValueError, match="Round must contain at least one exercise"):
            Round(exercises=[])
    
    def test_round_validation_zero_repetitions(self):
        """Test that round repetitions must be positive."""
        exercises = [Exercise(name="burpee", reps=5)]
        with pytest.raises(ValueError, match="Round repetitions must be positive"):
            Round(exercises=exercises, repetitions=0)
    
    def test_round_get_total_reps(self):
        """Test calculating total reps in a round."""
        exercises = [
            Exercise(name="thruster", reps=21),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises, repetitions=3)
        
        total_reps = round_obj.get_total_reps()
        assert total_reps == (21 + 21) * 3  # 126 total reps
    
    def test_round_str_representation(self):
        """Test string representation of round."""
        exercises = [
            Exercise(name="thruster", reps=21, weight_kg=42.5),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises, repetitions=3)
        
        str_repr = str(round_obj)
        assert "3 rounds" in str_repr
        assert "thruster" in str_repr
        assert "pull-up" in str_repr


class TestWOD:
    """Test cases for the WOD class."""
    
    def test_wod_creation_basic(self):
        """Test creating a basic WOD."""
        exercises = [Exercise(name="thruster", reps=21, weight_kg=42.5)]
        round_obj = Round(exercises=exercises)
        
        wod = WOD(
            name="Test WOD",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[round_obj]
        )
        
        assert wod.name == "Test WOD"
        assert wod.workout_type == WorkoutType.FOR_TIME
        assert len(wod.rounds) == 1
        assert wod.time_cap_seconds is None
        assert wod.rest_between_rounds == 0.0
    
    def test_wod_validation_empty_rounds(self):
        """Test that WOD must contain rounds."""
        with pytest.raises(ValueError, match="Workout must contain at least one round"):
            WOD(
                name="Invalid",
                workout_type=WorkoutType.FOR_TIME,
                rounds=[]
            )
    
    def test_wod_validation_negative_time_cap(self):
        """Test that time cap must be positive."""
        exercises = [Exercise(name="thruster", reps=21)]
        round_obj = Round(exercises=exercises)
        
        with pytest.raises(ValueError, match="time_cap_seconds must be positive"):
            WOD(
                name="Invalid",
                workout_type=WorkoutType.FOR_TIME,
                rounds=[round_obj],
                time_cap_seconds=-60
            )
    
    def test_wod_validation_amrap_needs_time_cap(self):
        """Test that AMRAP workouts must have time cap."""
        exercises = [Exercise(name="burpee", reps=5)]
        round_obj = Round(exercises=exercises)
        
        with pytest.raises(ValueError, match="AMRAP workouts must have a time_cap_seconds"):
            WOD(
                name="Invalid AMRAP",
                workout_type=WorkoutType.AMRAP,
                rounds=[round_obj]
                # Missing time_cap_seconds
            )
    
    def test_wod_for_time_factory(self):
        """Test WOD.for_time factory method."""
        exercises = [
            ("thruster", 21, 42.5),
            ("pull-up", 21, None)
        ]
        
        wod = WOD.for_time(
            name="Fran-like",
            exercises=exercises,
            time_cap_seconds=300
        )
        
        assert wod.name == "Fran-like"
        assert wod.workout_type == WorkoutType.FOR_TIME
        assert wod.time_cap_seconds == 300
        assert len(wod.rounds) == 1
        assert len(wod.rounds[0].exercises) == 2
    
    def test_wod_for_time_factory_with_rounds(self):
        """Test WOD.for_time factory with pre-built rounds."""
        exercise = Exercise(name="thruster", reps=21, weight_kg=42.5)
        round_obj = Round(exercises=[exercise])
        
        wod = WOD.for_time(
            name="Test",
            rounds=[round_obj]
        )
        
        assert wod.workout_type == WorkoutType.FOR_TIME
        assert len(wod.rounds) == 1
    
    def test_wod_for_time_factory_validation(self):
        """Test WOD.for_time factory validation."""
        # Cannot provide both exercises and rounds
        with pytest.raises(ValueError, match="Provide either exercises or rounds"):
            WOD.for_time(
                name="Invalid",
                exercises=[("thruster", 21, 42.5)],
                rounds=[Round(exercises=[Exercise(name="thruster", reps=21)])]
            )
        
        # Must provide either exercises or rounds
        with pytest.raises(ValueError, match="Must provide either exercises or rounds"):
            WOD.for_time(name="Invalid")
    
    def test_wod_amrap_factory(self):
        """Test WOD.amrap factory method."""
        exercises = [
            ("pull-up", 5, None),
            ("push-up", 10, None),
            ("air-squat", 15, None)
        ]
        
        wod = WOD.amrap(
            name="Cindy-like",
            time_cap_seconds=1200,  # 20 minutes
            exercises=exercises
        )
        
        assert wod.name == "Cindy-like"
        assert wod.workout_type == WorkoutType.AMRAP
        assert wod.time_cap_seconds == 1200
        assert len(wod.rounds) == 1
        assert len(wod.rounds[0].exercises) == 3
    
    def test_wod_get_total_exercises(self):
        """Test calculating total exercises in WOD."""
        exercises = [
            Exercise(name="thruster", reps=21),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises, repetitions=3)
        
        wod = WOD(
            name="Test",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[round_obj]
        )
        
        total_exercises = wod.get_total_exercises()
        assert total_exercises == 2 * 3  # 2 exercises × 3 repetitions
    
    def test_wod_get_total_reps_for_time(self):
        """Test calculating total reps for For Time WOD."""
        exercises = [
            Exercise(name="thruster", reps=21),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises)
        
        wod = WOD(
            name="Test",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[round_obj]
        )
        
        total_reps = wod.get_total_reps()
        assert total_reps == 42  # 21 + 21
    
    def test_wod_get_total_reps_amrap_error(self):
        """Test that getting total reps for AMRAP raises error."""
        exercises = [Exercise(name="burpee", reps=5)]
        round_obj = Round(exercises=exercises)
        
        wod = WOD(
            name="AMRAP Test",
            workout_type=WorkoutType.AMRAP,
            rounds=[round_obj],
            time_cap_seconds=300
        )
        
        with pytest.raises(ValueError, match="Cannot calculate total reps for AMRAP"):
            wod.get_total_reps()
    
    def test_wod_get_all_exercises(self):
        """Test getting flat list of all exercises."""
        exercises = [
            Exercise(name="thruster", reps=21),
            Exercise(name="pull-up", reps=21)
        ]
        round_obj = Round(exercises=exercises, repetitions=2)
        
        wod = WOD(
            name="Test",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[round_obj]
        )
        
        all_exercises = wod.get_all_exercises()
        assert len(all_exercises) == 4  # 2 exercises × 2 repetitions
        assert all_exercises[0].name == "thruster"
        assert all_exercises[1].name == "pull-up"
        assert all_exercises[2].name == "thruster"
        assert all_exercises[3].name == "pull-up"
    
    def test_wod_str_representation(self):
        """Test string representation of WOD."""
        exercises = [Exercise(name="thruster", reps=21, weight_kg=42.5)]
        round_obj = Round(exercises=exercises)
        
        wod = WOD(
            name="Test WOD",
            workout_type=WorkoutType.FOR_TIME,
            rounds=[round_obj],
            description="A test workout"
        )
        
        str_repr = str(wod)
        assert "Test WOD" in str_repr
        assert "For Time" in str_repr
        assert "A test workout" in str_repr
        assert "thruster" in str_repr


class TestFamousWODs:
    """Test cases for famous CrossFit WODs."""
    
    def test_fran_workout(self):
        """Test the famous Fran workout."""
        fran = FamousWODs.fran()
        
        assert fran.name == "Fran"
        assert fran.workout_type == WorkoutType.FOR_TIME
        assert len(fran.rounds) == 3  # 21-15-9 structure
        
        # Check first round
        first_round = fran.rounds[0]
        assert len(first_round.exercises) == 2
        assert first_round.exercises[0].name == "thruster"
        assert first_round.exercises[0].reps == 21
        assert first_round.exercises[0].weight_kg == 42.5
        assert first_round.exercises[1].name == "pull-up"
        assert first_round.exercises[1].reps == 21
    
    def test_helen_workout(self):
        """Test the Helen workout."""
        helen = FamousWODs.helen()
        
        assert helen.name == "Helen"
        assert helen.workout_type == WorkoutType.FOR_TIME
        assert len(helen.rounds) == 1
        
        # Check round structure (3 repetitions)
        round_obj = helen.rounds[0]
        assert round_obj.repetitions == 3
        assert len(round_obj.exercises) == 3
        
        # Check exercises
        exercises = round_obj.exercises
        assert exercises[0].name == "run"
        assert exercises[0].distance_m == 400
        assert exercises[1].name == "kettlebell-swing"
        assert exercises[1].reps == 21
        assert exercises[2].name == "pull-up"
        assert exercises[2].reps == 12
    
    def test_cindy_workout(self):
        """Test the Cindy workout."""
        cindy = FamousWODs.cindy()
        
        assert cindy.name == "Cindy"
        assert cindy.workout_type == WorkoutType.AMRAP
        assert cindy.time_cap_seconds == 1200  # 20 minutes
        assert len(cindy.rounds) == 1
        
        # Check exercises
        exercises = cindy.rounds[0].exercises
        assert len(exercises) == 3
        assert exercises[0].name == "pull-up"
        assert exercises[0].reps == 5
        assert exercises[1].name == "push-up"
        assert exercises[1].reps == 10
        assert exercises[2].name == "air-squat"
        assert exercises[2].reps == 15
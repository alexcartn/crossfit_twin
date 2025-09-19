"""
Unit tests for the Athlete module.
"""

import pytest
from crossfit_twin.athlete import Athlete


class TestAthlete:
    """Test cases for the Athlete class."""
    
    def test_athlete_creation_valid(self):
        """Test creating a valid athlete."""
        athlete = Athlete(
            name="Test Athlete",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        assert athlete.name == "Test Athlete"
        assert athlete.strength == 80.0
        assert athlete.endurance == 75.0
        assert athlete.fatigue_resistance == 70.0
        assert athlete.recovery_rate == 85.0
        assert athlete.weight_kg == 75.0
        assert athlete.experience_level == "intermediate"  # default
    
    def test_athlete_validation_strength_out_of_range(self):
        """Test that strength validation works."""
        with pytest.raises(ValueError, match="strength must be between 0 and 100"):
            Athlete(
                name="Invalid",
                strength=150.0,  # Too high
                endurance=75.0,
                fatigue_resistance=70.0,
                recovery_rate=85.0,
                weight_kg=75.0
            )
    
    def test_athlete_validation_negative_weight(self):
        """Test that weight validation works."""
        with pytest.raises(ValueError, match="weight_kg must be positive"):
            Athlete(
                name="Invalid",
                strength=80.0,
                endurance=75.0,
                fatigue_resistance=70.0,
                recovery_rate=85.0,
                weight_kg=-5.0  # Negative weight
            )
    
    def test_athlete_validation_invalid_experience_level(self):
        """Test that experience level validation works."""
        with pytest.raises(ValueError, match="experience_level must be one of"):
            Athlete(
                name="Invalid",
                strength=80.0,
                endurance=75.0,
                fatigue_resistance=70.0,
                recovery_rate=85.0,
                weight_kg=75.0,
                experience_level="master"  # Invalid level
            )
    
    def test_default_paces_set(self):
        """Test that default paces are set correctly."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        # Should have default paces for common exercises
        assert "thruster" in athlete.base_pace
        assert "pull-up" in athlete.base_pace
        assert "burpee" in athlete.base_pace
        assert athlete.base_pace["thruster"] > 0
    
    def test_experience_level_affects_pace(self):
        """Test that experience level affects base pace."""
        beginner = Athlete(
            name="Beginner",
            strength=50.0,
            endurance=50.0,
            fatigue_resistance=50.0,
            recovery_rate=50.0,
            weight_kg=70.0,
            experience_level="beginner"
        )
        
        elite = Athlete(
            name="Elite",
            strength=50.0,
            endurance=50.0,
            fatigue_resistance=50.0,
            recovery_rate=50.0,
            weight_kg=70.0,
            experience_level="elite"
        )
        
        # Elite should be faster than beginner
        assert elite.base_pace["thruster"] < beginner.base_pace["thruster"]
    
    def test_default_lifts_set(self):
        """Test that default max lifts are set based on bodyweight and strength."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=80.0  # 80kg athlete
        )
        
        # Should have default lifts
        assert "back-squat" in athlete.max_lifts
        assert "deadlift" in athlete.max_lifts
        assert athlete.max_lifts["back-squat"] > 0
        assert athlete.max_lifts["deadlift"] > athlete.max_lifts["back-squat"]  # DL > squat typically
    
    def test_get_rep_time_basic(self):
        """Test basic rep time calculation."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        # Fresh athlete doing bodyweight exercise
        rep_time = athlete.get_rep_time("thruster", weight_kg=None, fatigue=0.0)
        assert rep_time > 0
        assert rep_time == athlete.base_pace["thruster"]  # Should match base pace when fresh
    
    def test_get_rep_time_with_fatigue(self):
        """Test that fatigue increases rep time."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        fresh_time = athlete.get_rep_time("thruster", weight_kg=None, fatigue=0.0)
        fatigued_time = athlete.get_rep_time("thruster", weight_kg=None, fatigue=0.5)
        
        assert fatigued_time > fresh_time
    
    def test_get_rep_time_with_weight(self):
        """Test that heavier weights increase rep time."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        light_time = athlete.get_rep_time("thruster", weight_kg=20.0, fatigue=0.0)
        heavy_time = athlete.get_rep_time("thruster", weight_kg=50.0, fatigue=0.0)
        
        assert heavy_time > light_time
    
    def test_get_fatigue_per_rep(self):
        """Test fatigue accumulation per rep."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        fatigue = athlete.get_fatigue_per_rep("thruster", weight_kg=40.0)
        assert fatigue > 0
        assert fatigue < 1.0  # Should be reasonable
    
    def test_higher_fatigue_resistance_reduces_fatigue(self):
        """Test that higher fatigue resistance reduces fatigue per rep."""
        low_resistance = Athlete(
            name="Low",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=30.0,  # Low resistance
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        high_resistance = Athlete(
            name="High",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=90.0,  # High resistance
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        low_fatigue = low_resistance.get_fatigue_per_rep("thruster", weight_kg=40.0)
        high_fatigue = high_resistance.get_fatigue_per_rep("thruster", weight_kg=40.0)
        
        assert high_fatigue < low_fatigue
    
    def test_recover(self):
        """Test fatigue recovery during rest."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        initial_fatigue = 0.8
        recovered_fatigue = athlete.recover(10.0, initial_fatigue)  # 10 seconds rest
        
        assert recovered_fatigue < initial_fatigue
        assert recovered_fatigue >= 0.0  # Cannot go below 0
    
    def test_recover_no_negative_fatigue(self):
        """Test that fatigue cannot go below zero during recovery."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        recovered_fatigue = athlete.recover(100.0, 0.1)  # Long rest, low fatigue
        assert recovered_fatigue == 0.0
    
    def test_higher_recovery_rate_recovers_faster(self):
        """Test that higher recovery rate leads to faster recovery."""
        slow_recovery = Athlete(
            name="Slow",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=30.0,  # Slow recovery
            weight_kg=75.0
        )
        
        fast_recovery = Athlete(
            name="Fast",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=90.0,  # Fast recovery
            weight_kg=75.0
        )
        
        initial_fatigue = 0.8
        rest_time = 10.0
        
        slow_result = slow_recovery.recover(rest_time, initial_fatigue)
        fast_result = fast_recovery.recover(rest_time, initial_fatigue)
        
        assert fast_result < slow_result  # Fast recovery should have lower fatigue
    
    def test_clone_basic(self):
        """Test basic athlete cloning."""
        original = Athlete(
            name="Original",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        clone = original.clone(name="Clone")
        
        assert clone.name == "Clone"
        assert clone.strength == original.strength
        assert clone.endurance == original.endurance
        assert clone is not original  # Different objects
    
    def test_clone_with_modifications(self):
        """Test cloning with parameter modifications."""
        original = Athlete(
            name="Original",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        clone = original.clone(name="Stronger Clone", strength=90.0, endurance=80.0)
        
        assert clone.name == "Stronger Clone"
        assert clone.strength == 90.0  # Modified
        assert clone.endurance == 80.0  # Modified
        assert clone.fatigue_resistance == original.fatigue_resistance  # Unchanged
        assert clone.weight_kg == original.weight_kg  # Unchanged
    
    def test_clone_invalid_attribute(self):
        """Test that cloning with invalid attribute raises error."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        with pytest.raises(ValueError, match="Invalid attribute"):
            athlete.clone(invalid_attr=123)
    
    def test_clone_preserves_validation(self):
        """Test that cloning still validates parameters."""
        athlete = Athlete(
            name="Test",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        with pytest.raises(ValueError):
            athlete.clone(strength=150.0)  # Invalid strength
    
    def test_str_representation(self):
        """Test string representation of athlete."""
        athlete = Athlete(
            name="Test Athlete",
            strength=80.0,
            endurance=75.0,
            fatigue_resistance=70.0,
            recovery_rate=85.0,
            weight_kg=75.0
        )
        
        str_repr = str(athlete)
        assert "Test Athlete" in str_repr
        assert "strength=80.0" in str_repr
        assert "weight=75.0kg" in str_repr
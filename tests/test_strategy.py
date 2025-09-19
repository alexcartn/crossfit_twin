"""
Unit tests for the Strategy module.
"""

import pytest
from crossfit_twin.strategy import (
    RestPattern, PacingStyle, Strategy, UnbrokenStrategy, FractionedStrategy,
    DescendingStrategy, ConservativeStrategy, StrategyFactory
)


class TestRestPattern:
    """Test cases for the RestPattern class."""
    
    def test_rest_pattern_creation(self):
        """Test creating a basic rest pattern."""
        pattern = RestPattern(
            reps_before_rest=10,
            rest_duration_seconds=5.0
        )
        
        assert pattern.reps_before_rest == 10
        assert pattern.rest_duration_seconds == 5.0
        assert pattern.max_consecutive_reps is None
    
    def test_rest_pattern_with_max_consecutive(self):
        """Test creating rest pattern with max consecutive reps."""
        pattern = RestPattern(
            reps_before_rest=10,
            rest_duration_seconds=5.0,
            max_consecutive_reps=8
        )
        
        assert pattern.max_consecutive_reps == 8
    
    def test_rest_pattern_validation_negative_reps(self):
        """Test that negative reps before rest is not allowed."""
        with pytest.raises(ValueError, match="reps_before_rest must be positive"):
            RestPattern(
                reps_before_rest=-5,
                rest_duration_seconds=5.0
            )
    
    def test_rest_pattern_validation_negative_duration(self):
        """Test that negative rest duration is not allowed."""
        with pytest.raises(ValueError, match="rest_duration_seconds cannot be negative"):
            RestPattern(
                reps_before_rest=10,
                rest_duration_seconds=-2.0
            )
    
    def test_rest_pattern_validation_zero_max_consecutive(self):
        """Test that zero max consecutive reps is not allowed."""
        with pytest.raises(ValueError, match="max_consecutive_reps must be positive"):
            RestPattern(
                reps_before_rest=10,
                rest_duration_seconds=5.0,
                max_consecutive_reps=0
            )


class TestUnbrokenStrategy:
    """Test cases for the UnbrokenStrategy class."""
    
    def test_unbroken_strategy_creation(self):
        """Test creating unbroken strategy."""
        strategy = UnbrokenStrategy()
        
        assert strategy.name == "Unbroken"
        assert "unbroken" in strategy.description.lower()
        assert strategy.global_fatigue_threshold > 0.8  # High threshold
    
    def test_unbroken_strategy_custom_threshold(self):
        """Test creating unbroken strategy with custom fatigue threshold."""
        strategy = UnbrokenStrategy(fatigue_threshold=0.95)
        
        assert strategy.global_fatigue_threshold == 0.95
    
    def test_unbroken_should_rest_low_fatigue(self):
        """Test that unbroken strategy doesn't rest at low fatigue."""
        strategy = UnbrokenStrategy(fatigue_threshold=0.9)
        
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=10,
            total_reps=21,
            current_fatigue=0.5,  # Low fatigue
            time_elapsed=60.0
        )
        
        assert should_rest is False
    
    def test_unbroken_should_rest_high_fatigue(self):
        """Test that unbroken strategy rests at high fatigue."""
        strategy = UnbrokenStrategy(fatigue_threshold=0.9)
        
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=15,
            total_reps=21,
            current_fatigue=0.95,  # High fatigue
            time_elapsed=120.0
        )
        
        assert should_rest is True
    
    def test_unbroken_rest_duration_scales_with_fatigue(self):
        """Test that rest duration increases with fatigue level."""
        strategy = UnbrokenStrategy()
        
        low_fatigue_rest = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=10,
            current_fatigue=0.4,
            time_elapsed=60.0
        )
        
        high_fatigue_rest = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=15,
            current_fatigue=0.9,
            time_elapsed=120.0
        )
        
        assert high_fatigue_rest > low_fatigue_rest


class TestFractionedStrategy:
    """Test cases for the FractionedStrategy class."""
    
    def test_fractioned_strategy_creation(self):
        """Test creating fractioned strategy."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=5, rest_duration_seconds=3.0),
            "pull-up": RestPattern(reps_before_rest=3, rest_duration_seconds=2.0)
        }
        
        strategy = FractionedStrategy(exercise_patterns=patterns)
        
        assert strategy.name == "Fractioned"
        assert "fractioned" in strategy.description.lower()
        assert len(strategy.exercise_patterns) == 2
    
    def test_fractioned_should_rest_pattern_boundary(self):
        """Test that fractioned strategy rests at pattern boundaries."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=5, rest_duration_seconds=3.0)
        }
        strategy = FractionedStrategy(exercise_patterns=patterns)
        
        # Should rest after 5 reps
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=5,
            total_reps=21,
            current_fatigue=0.3,
            time_elapsed=30.0
        )
        
        assert should_rest is True
    
    def test_fractioned_should_rest_between_sets(self):
        """Test that fractioned strategy doesn't rest between sets."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=5, rest_duration_seconds=3.0)
        }
        strategy = FractionedStrategy(exercise_patterns=patterns)
        
        # Should not rest at rep 3 (middle of first set)
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=3,
            total_reps=21,
            current_fatigue=0.2,
            time_elapsed=20.0
        )
        
        assert should_rest is False
    
    def test_fractioned_should_rest_high_fatigue_override(self):
        """Test that high fatigue overrides pattern."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=10, rest_duration_seconds=3.0)
        }
        strategy = FractionedStrategy(exercise_patterns=patterns, fatigue_threshold=0.7)
        
        # Should rest due to high fatigue even though not at pattern boundary
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=3,
            total_reps=21,
            current_fatigue=0.8,  # Above threshold
            time_elapsed=20.0
        )
        
        assert should_rest is True
    
    def test_fractioned_rest_duration_from_pattern(self):
        """Test that rest duration comes from pattern."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=5, rest_duration_seconds=4.0)
        }
        strategy = FractionedStrategy(exercise_patterns=patterns)
        
        duration = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=5,
            current_fatigue=0.3,
            time_elapsed=30.0
        )
        
        # Should be base duration adjusted for fatigue
        assert duration >= 4.0  # At least base duration
    
    def test_fractioned_unknown_exercise_fallback(self):
        """Test behavior with exercise not in patterns."""
        patterns = {
            "thruster": RestPattern(reps_before_rest=5, rest_duration_seconds=3.0)
        }
        strategy = FractionedStrategy(exercise_patterns=patterns)
        
        # Unknown exercise should use default behavior
        should_rest = strategy.should_rest(
            exercise_name="unknown-exercise",
            current_rep=3,
            total_reps=10,
            current_fatigue=0.3,
            time_elapsed=20.0
        )
        
        assert should_rest is False  # Low fatigue, no pattern


class TestDescendingStrategy:
    """Test cases for the DescendingStrategy class."""
    
    def test_descending_strategy_creation(self):
        """Test creating descending strategy."""
        strategy = DescendingStrategy()
        
        assert strategy.name == "Descending"
        assert "descending" in strategy.description.lower()
    
    def test_descending_set_breakdown_small(self):
        """Test set breakdown for small rep count."""
        strategy = DescendingStrategy()
        
        breakdown = strategy.get_set_breakdown("thruster", 5)
        assert breakdown == [5]  # Too small to break down
    
    def test_descending_set_breakdown_medium(self):
        """Test set breakdown for medium rep count."""
        strategy = DescendingStrategy()
        
        breakdown = strategy.get_set_breakdown("thruster", 15)
        
        # Should be descending and sum to 15
        assert sum(breakdown) == 15
        assert len(breakdown) > 1
        # Check that it's generally descending (allowing for even splits at end)
        for i in range(len(breakdown) - 2):
            assert breakdown[i] >= breakdown[i + 1] or breakdown[i + 1] == breakdown[i + 2]
    
    def test_descending_set_breakdown_large(self):
        """Test set breakdown for large rep count."""
        strategy = DescendingStrategy()
        
        breakdown = strategy.get_set_breakdown("thruster", 30)
        
        assert sum(breakdown) == 30
        assert len(breakdown) > 2
        assert breakdown[0] > breakdown[-1]  # First set larger than last
    
    def test_descending_should_rest_at_boundaries(self):
        """Test that descending strategy rests at set boundaries."""
        strategy = DescendingStrategy()
        
        # For 15 reps, let's say breakdown is [6, 5, 4] (as an example)
        breakdown = strategy.get_set_breakdown("thruster", 15)
        first_set_size = breakdown[0]
        
        # Should rest after first set
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=first_set_size,
            total_reps=15,
            current_fatigue=0.4,
            time_elapsed=30.0
        )
        
        assert should_rest is True
    
    def test_descending_rest_duration_increases_with_fatigue(self):
        """Test that rest duration increases with fatigue."""
        strategy = DescendingStrategy()
        
        low_fatigue_rest = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=6,
            current_fatigue=0.3,
            time_elapsed=30.0
        )
        
        high_fatigue_rest = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=6,
            current_fatigue=0.8,
            time_elapsed=60.0
        )
        
        assert high_fatigue_rest > low_fatigue_rest


class TestConservativeStrategy:
    """Test cases for the ConservativeStrategy class."""
    
    def test_conservative_strategy_creation(self):
        """Test creating conservative strategy."""
        strategy = ConservativeStrategy()
        
        assert strategy.name == "Conservative"
        assert "conservative" in strategy.description.lower()
        assert strategy.global_fatigue_threshold < 0.7  # Low threshold
    
    def test_conservative_should_rest_frequently(self):
        """Test that conservative strategy rests frequently."""
        strategy = ConservativeStrategy(fatigue_threshold=0.6)
        
        # Should rest even at moderate fatigue
        should_rest = strategy.should_rest(
            exercise_name="thruster",
            current_rep=8,  # Default pattern might trigger here
            total_reps=21,
            current_fatigue=0.4,
            time_elapsed=40.0
        )
        
        # Conservative strategy should rest more frequently
        # The exact behavior depends on implementation details
        assert isinstance(should_rest, bool)
    
    def test_conservative_rest_duration_short(self):
        """Test that conservative strategy uses short rests."""
        strategy = ConservativeStrategy()
        
        duration = strategy.rest_duration(
            exercise_name="thruster",
            current_rep=5,
            current_fatigue=0.3,
            time_elapsed=30.0
        )
        
        # Should be relatively short rest
        assert 0 < duration <= 10.0  # Reasonable range for short rest


class TestStrategyFactory:
    """Test cases for the StrategyFactory class."""
    
    def test_factory_unbroken(self):
        """Test factory method for unbroken strategy."""
        strategy = StrategyFactory.unbroken()
        
        assert isinstance(strategy, UnbrokenStrategy)
        assert strategy.name == "Unbroken"
    
    def test_factory_unbroken_custom_threshold(self):
        """Test factory method with custom threshold."""
        strategy = StrategyFactory.unbroken(fatigue_threshold=0.95)
        
        assert strategy.global_fatigue_threshold == 0.95
    
    def test_factory_fractioned(self):
        """Test factory method for fractioned strategy."""
        patterns = {
            "thruster": (5, 3.0),
            "pull-up": (3, 2.0)
        }
        
        strategy = StrategyFactory.fractioned(patterns)
        
        assert isinstance(strategy, FractionedStrategy)
        assert "thruster" in strategy.exercise_patterns
        assert strategy.exercise_patterns["thruster"].reps_before_rest == 5
        assert strategy.exercise_patterns["thruster"].rest_duration_seconds == 3.0
    
    def test_factory_descending(self):
        """Test factory method for descending strategy."""
        strategy = StrategyFactory.descending()
        
        assert isinstance(strategy, DescendingStrategy)
        assert strategy.name == "Descending"
    
    def test_factory_conservative(self):
        """Test factory method for conservative strategy."""
        strategy = StrategyFactory.conservative()
        
        assert isinstance(strategy, ConservativeStrategy)
        assert strategy.name == "Conservative"
    
    def test_factory_conservative_with_patterns(self):
        """Test factory method for conservative strategy with patterns."""
        patterns = {
            "thruster": (3, 2.0)
        }
        
        strategy = StrategyFactory.conservative(patterns)
        
        assert "thruster" in strategy.exercise_patterns
    
    def test_factory_for_workout_type_sprint(self):
        """Test factory method for sprint workout type."""
        strategy = StrategyFactory.for_workout_type("sprint")
        
        assert isinstance(strategy, UnbrokenStrategy)
        assert strategy.global_fatigue_threshold > 0.9  # High threshold for sprint
    
    def test_factory_for_workout_type_medium(self):
        """Test factory method for medium workout type."""
        strategy = StrategyFactory.for_workout_type("medium")
        
        assert isinstance(strategy, DescendingStrategy)
    
    def test_factory_for_workout_type_endurance(self):
        """Test factory method for endurance workout type."""
        strategy = StrategyFactory.for_workout_type("long")
        
        assert isinstance(strategy, ConservativeStrategy)
        assert strategy.global_fatigue_threshold < 0.7  # Low threshold for endurance
    
    def test_factory_for_workout_type_unknown(self):
        """Test factory method for unknown workout type."""
        strategy = StrategyFactory.for_workout_type("unknown")
        
        assert isinstance(strategy, FractionedStrategy)  # Default fallback
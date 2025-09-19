"""
Example usage of the CrossFit Digital Twin library.

This script demonstrates how to use the library to:
1. Create athletes with different profiles
2. Define workouts
3. Test different pacing strategies
4. Run parameter experiments
5. Compare results
"""

from crossfit_twin import Athlete, WOD, Strategy, simulate
from crossfit_twin.workout import FamousWODs
from crossfit_twin.strategy import StrategyFactory
from crossfit_twin.utils import (
    AthleteCloneGenerator, PerformanceComparator, ExperimentRunner,
    quick_parameter_test, compare_all_strategies
)


def create_example_athletes():
    """Create a variety of example athletes for testing."""
    
    athletes = {}
    
    # Beginner athlete
    athletes["beginner"] = Athlete(
        name="Alex (Beginner)",
        strength=40.0,
        endurance=35.0,
        fatigue_resistance=30.0,
        recovery_rate=40.0,
        weight_kg=70.0,
        experience_level="beginner"
    )
    
    # Intermediate athlete (your typical CrossFit gym member)
    athletes["intermediate"] = Athlete(
        name="Sam (Intermediate)",
        strength=70.0,
        endurance=65.0,
        fatigue_resistance=60.0,
        recovery_rate=70.0,
        weight_kg=75.0,
        experience_level="intermediate"
    )
    
    # Advanced athlete
    athletes["advanced"] = Athlete(
        name="Jordan (Advanced)",
        strength=85.0,
        endurance=80.0,
        fatigue_resistance=85.0,
        recovery_rate=85.0,
        weight_kg=72.0,
        experience_level="advanced"
    )
    
    # Elite competitor
    athletes["elite"] = Athlete(
        name="Casey (Elite)",
        strength=95.0,
        endurance=90.0,
        fatigue_resistance=95.0,
        recovery_rate=95.0,
        weight_kg=68.0,
        experience_level="elite"
    )
    
    # Strength-biased athlete
    athletes["strength_focused"] = Athlete(
        name="Max (Strength Focus)",
        strength=90.0,
        endurance=55.0,
        fatigue_resistance=70.0,
        recovery_rate=60.0,
        weight_kg=85.0,
        experience_level="advanced"
    )
    
    # Endurance-biased athlete
    athletes["endurance_focused"] = Athlete(
        name="River (Endurance Focus)",
        strength=60.0,
        endurance=95.0,
        fatigue_resistance=85.0,
        recovery_rate=90.0,
        weight_kg=65.0,
        experience_level="advanced"
    )
    
    return athletes


def example_basic_simulation():
    """Demonstrate basic simulation usage."""
    print("=== BASIC SIMULATION EXAMPLE ===\n")
    
    # Create an athlete
    athlete = Athlete(
        name="Demo Athlete",
        strength=75.0,
        endurance=70.0,
        fatigue_resistance=65.0,
        recovery_rate=75.0,
        weight_kg=70.0
    )
    
    # Get a famous workout
    fran = FamousWODs.fran()
    
    # Create a strategy
    strategy = StrategyFactory.unbroken()
    
    # Run simulation
    result = simulate(fran, athlete, strategy, verbose=True)
    
    print(f"\n{result.get_summary()}\n")
    print("-" * 50)


def example_strategy_comparison():
    """Demonstrate comparing different strategies."""
    print("=== STRATEGY COMPARISON EXAMPLE ===\n")
    
    # Create athlete
    athlete = Athlete(
        name="Strategy Test Athlete",
        strength=80.0,
        endurance=75.0,
        fatigue_resistance=70.0,
        recovery_rate=80.0,
        weight_kg=75.0
    )
    
    # Get workout
    fran = FamousWODs.fran()
    
    # Compare all built-in strategies
    results = compare_all_strategies(athlete, fran)
    
    print(f"Strategy comparison for {fran.name}:")
    print(f"Athlete: {athlete.name}\n")
    
    for i, (strategy_name, time, completed) in enumerate(results, 1):
        status = "✅" if completed else "❌"
        print(f"{i}. {strategy_name}: {time:.1f}s {status}")
    
    print("\n" + "-" * 50)


def example_parameter_sweep():
    """Demonstrate parameter sweep experiment."""
    print("=== PARAMETER SWEEP EXAMPLE ===\n")
    
    # Base athlete
    base_athlete = Athlete(
        name="Base Athlete",
        strength=70.0,
        endurance=70.0,
        fatigue_resistance=70.0,
        recovery_rate=70.0,
        weight_kg=75.0
    )
    
    # Test how strength affects performance on Fran
    analysis = quick_parameter_test(
        athlete=base_athlete,
        workout=FamousWODs.fran(),
        strategy=StrategyFactory.descending(),
        parameter="strength",
        percentage_range=(-20.0, 20.0),
        steps=5
    )
    
    print("Testing strength parameter on Fran:")
    print(f"Base strength: {analysis['base_value']:.1f}")
    print(f"Optimal strength: {analysis['optimal_value']:.1f}")
    print(f"Optimal time: {analysis['optimal_performance']:.1f}s")
    print(f"Performance range: {analysis['performance_range']:.1f}s")
    print(f"Correlation: {analysis['correlation_with_performance']:.3f}")
    
    print("\nData points (strength, time):")
    for strength, time in analysis['data_points']:
        print(f"  {strength:.1f} → {time:.1f}s")
    
    print("\n" + "-" * 50)


def example_athlete_cloning():
    """Demonstrate athlete cloning and variations."""
    print("=== ATHLETE CLONING EXAMPLE ===\n")
    
    # Base athlete
    base_athlete = Athlete(
        name="Original Athlete",
        strength=75.0,
        endurance=70.0,
        fatigue_resistance=65.0,
        recovery_rate=75.0,
        weight_kg=70.0
    )
    
    # Create variations
    parameter_variations = {
        "strength": [65.0, 75.0, 85.0],
        "endurance": [60.0, 70.0, 80.0]
    }
    
    clones = AthleteCloneGenerator.create_parameter_variations(
        base_athlete, parameter_variations
    )
    
    print(f"Created {len(clones)} athlete clones:")
    for clone in clones:
        print(f"  {clone.name}")
        print(f"    Strength: {clone.strength:.1f}, Endurance: {clone.endurance:.1f}")
    
    # Test all clones on Helen
    helen = FamousWODs.helen()
    strategy = StrategyFactory.conservative()
    
    print(f"\nTesting all clones on {helen.name} with {strategy.name} strategy:")
    
    results = []
    for clone in clones:
        result = simulate(helen, clone, strategy)
        results.append(result)
        status = "✅" if result.completed else "❌"
        print(f"  {clone.name}: {result.total_time:.1f}s {status}")
    
    # Analyze results
    analysis = PerformanceComparator.compare_results(results)
    print(f"\nBest time: {analysis['best_time']:.1f}s ({analysis['best_result'].athlete_name})")
    print(f"Average time: {analysis['average_time']:.1f}s")
    print(f"Completion rate: {analysis['completion_rate']:.1%}")
    
    print("\n" + "-" * 50)


def example_custom_workout():
    """Demonstrate creating and testing custom workouts."""
    print("=== CUSTOM WORKOUT EXAMPLE ===\n")
    
    # Create a custom workout
    custom_wod = WOD.for_time(
        name="Custom Nasty",
        exercises=[
            ("thruster", 50, 35.0),
            ("burpee", 40, None),
            ("wall-ball", 30, 9.0),
            ("pull-up", 20, None),
            ("push-up", 10, None)
        ],
        time_cap_seconds=1200,  # 20 minute cap
        description="A grinding chipper workout"
    )
    
    print(f"Created custom workout:\n{custom_wod}\n")
    
    # Test with different athlete types
    athletes = create_example_athletes()
    strategy = StrategyFactory.fractioned({
        "thruster": (8, 5.0),
        "burpee": (6, 3.0),
        "wall-ball": (10, 4.0),
        "pull-up": (4, 3.0),
        "push-up": (5, 2.0)
    })
    
    print(f"Testing with {strategy.name} strategy:\n")
    
    for athlete_type, athlete in athletes.items():
        result = simulate(custom_wod, athlete, strategy)
        status = "✅" if result.completed else "❌"
        print(f"{athlete_type:15} ({athlete.name:20}): {result.total_time:6.1f}s {status}")
    
    print("\n" + "-" * 50)


def example_amrap_workout():
    """Demonstrate AMRAP workout simulation."""
    print("=== AMRAP WORKOUT EXAMPLE ===\n")
    
    # Create AMRAP workout
    amrap_wod = WOD.amrap(
        name="12 min AMRAP Test",
        time_cap_seconds=720,  # 12 minutes
        exercises=[
            ("thruster", 8, 35.0),
            ("chest-to-bar", 6, None),
            ("overhead-squat", 4, 35.0)
        ],
        description="12 min AMRAP: 8 Thrusters, 6 C2B, 4 OHS"
    )
    
    print(f"AMRAP Workout:\n{amrap_wod}\n")
    
    # Test with intermediate athlete
    athlete = create_example_athletes()["intermediate"]
    strategy = StrategyFactory.conservative()
    
    result = simulate(amrap_wod, athlete, strategy, verbose=True)
    
    print(f"\nAMRAP Results:")
    print(f"Rounds completed: {result.rounds_completed}")
    print(f"Total reps: {result.total_reps}")
    print(f"Time used: {result.total_time:.1f}s / {amrap_wod.time_cap_seconds:.0f}s")
    print(f"Final fatigue: {result.final_fatigue:.2f}")
    
    print("\n" + "-" * 50)


def main():
    """Run all examples."""
    print("CrossFit Digital Twin - Example Usage\n")
    print("=" * 60)
    
    # Run examples
    example_basic_simulation()
    example_strategy_comparison()
    example_parameter_sweep()
    example_athlete_cloning()
    example_custom_workout()
    example_amrap_workout()
    
    print("\nAll examples completed! 🎉")
    print("\nNext steps:")
    print("- Try modifying the athlete parameters")
    print("- Create your own workouts")
    print("- Experiment with different strategies")
    print("- Run parameter sweeps on different attributes")


if __name__ == "__main__":
    main()
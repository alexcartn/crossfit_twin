"""
Validation scenarios for the CrossFit Digital Twin library.

This script contains realistic scenarios with known performance ranges
to validate that the simulation produces reasonable results.
"""

from crossfit_twin import Athlete, simulate
from crossfit_twin.workout import FamousWODs, WOD
from crossfit_twin.strategy import StrategyFactory


def create_real_world_athletes():
    """Create athletes based on real-world CrossFit performance data."""
    
    athletes = {}
    
    # Elite male competitor (Games level)
    athletes["elite_male"] = Athlete(
        name="Elite Male Competitor",
        strength=95.0,
        endurance=90.0,
        fatigue_resistance=95.0,
        recovery_rate=95.0,
        weight_kg=82.0,
        experience_level="elite",
        max_lifts={
            "back-squat": 200.0,    # ~2.4x BW
            "deadlift": 250.0,      # ~3.0x BW  
            "clean": 150.0,         # ~1.8x BW
            "snatch": 125.0,        # ~1.5x BW
            "thruster": 80.0,       # ~1.0x BW
            "overhead-press": 100.0  # ~1.2x BW
        }
    )
    
    # Elite female competitor (Games level) 
    athletes["elite_female"] = Athlete(
        name="Elite Female Competitor",
        strength=85.0,
        endurance=95.0,
        fatigue_resistance=90.0,
        recovery_rate=90.0,
        weight_kg=64.0,
        experience_level="elite",
        max_lifts={
            "back-squat": 130.0,    # ~2.0x BW
            "deadlift": 160.0,      # ~2.5x BW
            "clean": 95.0,          # ~1.5x BW
            "snatch": 75.0,         # ~1.2x BW
            "thruster": 55.0,       # ~0.85x BW
            "overhead-press": 65.0   # ~1.0x BW
        }
    )
    
    # Regional level male
    athletes["regional_male"] = Athlete(
        name="Regional Male",
        strength=85.0,
        endurance=80.0,
        fatigue_resistance=80.0,
        recovery_rate=85.0,
        weight_kg=78.0,
        experience_level="advanced",
        max_lifts={
            "back-squat": 160.0,    # ~2.0x BW
            "deadlift": 200.0,      # ~2.5x BW
            "clean": 115.0,         # ~1.45x BW
            "snatch": 90.0,         # ~1.15x BW
            "thruster": 65.0,       # ~0.83x BW
            "overhead-press": 80.0   # ~1.0x BW
        }
    )
    
    # Regional level female
    athletes["regional_female"] = Athlete(
        name="Regional Female", 
        strength=75.0,
        endurance=85.0,
        fatigue_resistance=75.0,
        recovery_rate=80.0,
        weight_kg=62.0,
        experience_level="advanced",
        max_lifts={
            "back-squat": 105.0,    # ~1.7x BW
            "deadlift": 135.0,      # ~2.2x BW
            "clean": 75.0,          # ~1.2x BW
            "snatch": 60.0,         # ~0.95x BW
            "thruster": 45.0,       # ~0.73x BW
            "overhead-press": 50.0   # ~0.8x BW
        }
    )
    
    # Average CrossFit gym member (male)
    athletes["gym_male"] = Athlete(
        name="Average Gym Male",
        strength=65.0,
        endurance=60.0,
        fatigue_resistance=55.0,
        recovery_rate=65.0,
        weight_kg=80.0,
        experience_level="intermediate",
        max_lifts={
            "back-squat": 110.0,    # ~1.4x BW
            "deadlift": 140.0,      # ~1.75x BW
            "clean": 75.0,          # ~0.94x BW
            "snatch": 55.0,         # ~0.69x BW
            "thruster": 50.0,       # ~0.63x BW
            "overhead-press": 60.0   # ~0.75x BW
        }
    )
    
    # Average CrossFit gym member (female)
    athletes["gym_female"] = Athlete(
        name="Average Gym Female",
        strength=55.0,
        endurance=65.0,
        fatigue_resistance=50.0,
        recovery_rate=60.0,
        weight_kg=65.0,
        experience_level="intermediate",
        max_lifts={
            "back-squat": 75.0,     # ~1.15x BW
            "deadlift": 95.0,       # ~1.46x BW
            "clean": 50.0,          # ~0.77x BW
            "snatch": 40.0,         # ~0.62x BW
            "thruster": 35.0,       # ~0.54x BW
            "overhead-press": 40.0   # ~0.62x BW
        }
    )
    
    return athletes


def validate_fran_times():
    """Validate Fran simulation against known performance ranges."""
    print("=== FRAN VALIDATION ===\n")
    
    # Known Fran time ranges (approximately)
    expected_ranges = {
        "elite_male": (120, 180),      # 2:00 - 3:00
        "elite_female": (150, 210),    # 2:30 - 3:30  
        "regional_male": (180, 240),   # 3:00 - 4:00
        "regional_female": (210, 270), # 3:30 - 4:30
        "gym_male": (300, 480),        # 5:00 - 8:00
        "gym_female": (360, 540),      # 6:00 - 9:00
    }
    
    athletes = create_real_world_athletes()
    fran = FamousWODs.fran()
    strategy = StrategyFactory.descending()  # Realistic strategy for Fran
    
    print("Fran validation (21-15-9 Thrusters @ 42.5kg + Pull-ups):")
    print("Strategy: Descending sets\n")
    
    validation_passed = True
    
    for athlete_type, athlete in athletes.items():
        result = simulate(fran, athlete, strategy)
        expected_min, expected_max = expected_ranges[athlete_type]
        
        within_range = expected_min <= result.total_time <= expected_max
        status = "✅" if within_range else "❌"
        
        print(f"{athlete_type:15}: {result.total_time:6.1f}s "
              f"(expected: {expected_min:3.0f}-{expected_max:3.0f}s) {status}")
        
        if not within_range:
            validation_passed = False
    
    print(f"\nFran validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def validate_cindy_scores():
    """Validate Cindy simulation against known performance ranges."""
    print("=== CINDY VALIDATION ===\n")
    
    # Known Cindy round ranges (20 min AMRAP: 5 pull-ups, 10 push-ups, 15 air squats)
    expected_ranges = {
        "elite_male": (25, 35),        # 25-35 rounds
        "elite_female": (22, 30),      # 22-30 rounds
        "regional_male": (20, 28),     # 20-28 rounds
        "regional_female": (18, 25),   # 18-25 rounds
        "gym_male": (12, 20),          # 12-20 rounds
        "gym_female": (10, 18),        # 10-18 rounds
    }
    
    athletes = create_real_world_athletes()
    cindy = FamousWODs.cindy()
    strategy = StrategyFactory.conservative()  # Good for long AMRAPs
    
    print("Cindy validation (20 min AMRAP: 5 Pull-ups, 10 Push-ups, 15 Air Squats):")
    print("Strategy: Conservative pacing\n")
    
    validation_passed = True
    
    for athlete_type, athlete in athletes.items():
        result = simulate(cindy, athlete, strategy)
        expected_min, expected_max = expected_ranges[athlete_type]
        
        within_range = expected_min <= result.rounds_completed <= expected_max
        status = "✅" if within_range else "❌"
        
        print(f"{athlete_type:15}: {result.rounds_completed:2d} rounds "
              f"(expected: {expected_min:2d}-{expected_max:2d}) {status}")
        
        if not within_range:
            validation_passed = False
    
    print(f"\nCindy validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def validate_helen_times():
    """Validate Helen simulation against known performance ranges."""
    print("=== HELEN VALIDATION ===\n")
    
    # Known Helen time ranges (3 rounds: 400m run, 21 KB swings @ 24kg, 12 pull-ups)
    expected_ranges = {
        "elite_male": (420, 540),      # 7:00 - 9:00
        "elite_female": (480, 600),    # 8:00 - 10:00
        "regional_male": (540, 660),   # 9:00 - 11:00
        "regional_female": (600, 720), # 10:00 - 12:00
        "gym_male": (720, 960),        # 12:00 - 16:00
        "gym_female": (840, 1080),     # 14:00 - 18:00
    }
    
    athletes = create_real_world_athletes()
    helen = FamousWODs.helen()
    strategy = StrategyFactory.fractioned({
        "kettlebell-swing": (12, 3.0),
        "pull-up": (4, 2.0)
    })
    
    print("Helen validation (3 rounds: 400m Run, 21 KB Swings @ 24kg, 12 Pull-ups):")
    print("Strategy: Fractioned (12/9 KB swings, 4/4/4 pull-ups)\n")
    
    validation_passed = True
    
    for athlete_type, athlete in athletes.items():
        result = simulate(helen, athlete, strategy)
        expected_min, expected_max = expected_ranges[athlete_type]
        
        within_range = expected_min <= result.total_time <= expected_max
        status = "✅" if within_range else "❌"
        
        print(f"{athlete_type:15}: {result.total_time:6.1f}s "
              f"({result.total_time/60:.1f} min, expected: {expected_min/60:.1f}-{expected_max/60:.1f} min) {status}")
        
        if not within_range:
            validation_passed = False
    
    print(f"\nHelen validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def validate_strategy_differences():
    """Validate that different strategies produce meaningfully different results."""
    print("=== STRATEGY DIFFERENCES VALIDATION ===\n")
    
    athlete = create_real_world_athletes()["regional_male"]
    fran = FamousWODs.fran()
    
    strategies = [
        StrategyFactory.unbroken(),
        StrategyFactory.conservative(),
        StrategyFactory.descending(),
        StrategyFactory.fractioned({"thruster": (7, 4.0), "pull-up": (5, 3.0)})
    ]
    
    results = []
    print(f"Testing strategy differences on Fran with {athlete.name}:\n")
    
    for strategy in strategies:
        result = simulate(fran, athlete, strategy)
        results.append((strategy.name, result.total_time, result.final_fatigue))
        print(f"{strategy.name:15}: {result.total_time:6.1f}s (fatigue: {result.final_fatigue:.2f})")
    
    # Check that we have meaningful variation (at least 30s spread)
    times = [time for _, time, _ in results]
    time_spread = max(times) - min(times)
    
    validation_passed = time_spread >= 30.0  # At least 30 seconds difference
    
    print(f"\nTime spread: {time_spread:.1f}s")
    print(f"Strategy differences validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def validate_athlete_differences():
    """Validate that different athlete levels produce appropriate performance gaps."""
    print("=== ATHLETE DIFFERENCES VALIDATION ===\n")
    
    athletes = create_real_world_athletes()
    fran = FamousWODs.fran()
    strategy = StrategyFactory.descending()
    
    print(f"Testing athlete differences on Fran with {strategy.name} strategy:\n")
    
    results = []
    for athlete_type, athlete in athletes.items():
        result = simulate(fran, athlete, strategy)
        results.append((athlete_type, result.total_time))
        print(f"{athlete_type:15}: {result.total_time:6.1f}s")
    
    # Sort by performance
    results.sort(key=lambda x: x[1])
    
    # Check that elite performers are faster than average gym members
    elite_times = [time for name, time in results if "elite" in name]
    gym_times = [time for name, time in results if "gym" in name]
    
    avg_elite_time = sum(elite_times) / len(elite_times)
    avg_gym_time = sum(gym_times) / len(gym_times)
    
    performance_gap = avg_gym_time - avg_elite_time
    validation_passed = performance_gap >= 120.0  # At least 2 minutes faster
    
    print(f"\nAverage elite time: {avg_elite_time:.1f}s")
    print(f"Average gym time: {avg_gym_time:.1f}s")
    print(f"Performance gap: {performance_gap:.1f}s")
    print(f"Athlete differences validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def validate_fatigue_system():
    """Validate that the fatigue system behaves realistically."""
    print("=== FATIGUE SYSTEM VALIDATION ===\n")
    
    athlete = create_real_world_athletes()["gym_male"]
    
    # Create a very long workout to test fatigue accumulation
    long_workout = WOD.for_time(
        name="Fatigue Test",
        exercises=[("thruster", 100, 40.0)],  # 100 thrusters
        time_cap_seconds=1800  # 30 minute cap
    )
    
    strategies = [
        StrategyFactory.unbroken(fatigue_threshold=0.95),
        StrategyFactory.conservative(fatigue_threshold=0.5)
    ]
    
    print("Testing fatigue system with long workout (100 thrusters @ 40kg):\n")
    
    validation_passed = True
    
    for strategy in strategies:
        result = simulate(long_workout, athlete, strategy)
        
        # Extract fatigue progression
        fatigue_events = [(e.timestamp, e.fatigue_level) for e in result.events if e.fatigue_level > 0]
        
        if len(fatigue_events) >= 2:
            initial_fatigue = fatigue_events[0][1]
            final_fatigue = result.final_fatigue
            
            # Fatigue should increase over time
            fatigue_increased = final_fatigue > initial_fatigue
            
            # Conservative strategy should have lower final fatigue
            print(f"{strategy.name:15}: {result.total_time:6.1f}s, "
                  f"final fatigue: {final_fatigue:.2f}, "
                  f"fatigue increased: {fatigue_increased}")
            
            if not fatigue_increased:
                validation_passed = False
    
    print(f"\nFatigue system validation: {'PASSED' if validation_passed else 'FAILED'}")
    print("-" * 50)
    
    return validation_passed


def run_full_validation():
    """Run all validation scenarios."""
    print("CrossFit Digital Twin - Validation Scenarios\n")
    print("=" * 60)
    
    validations = [
        validate_fran_times(),
        validate_cindy_scores(),
        validate_helen_times(),
        validate_strategy_differences(),
        validate_athlete_differences(),
        validate_fatigue_system()
    ]
    
    passed_count = sum(validations)
    total_count = len(validations)
    
    print(f"\nVALIDATION SUMMARY:")
    print(f"Passed: {passed_count}/{total_count}")
    print(f"Success rate: {passed_count/total_count:.1%}")
    
    if passed_count == total_count:
        print("\n🎉 ALL VALIDATIONS PASSED! The simulation is producing realistic results.")
    else:
        print("\n⚠️  Some validations failed. Review the simulation parameters.")
    
    return passed_count == total_count


if __name__ == "__main__":
    run_full_validation()
"""
Example usage of CrossFit Digital Twin V2 system (Python 3.4 compatible).

Demonstrates the new concrete parameter system with RPE-based strategies.
"""

from crossfit_twin import (
    # V2 system
    UIBenchmarks,
    build_athlete_from_benchmarks,
    AthleteV2,
    ContextParams,
    DayState,
    create_rpe_strategy,
    RPELevel,

    # Legacy system (for WOD definitions)
    WOD,
    Exercise
)


def create_example_athlete():
    """Create an example athlete using the new benchmark system."""

    # Define athlete benchmarks (what user would input in UI)
    benchmarks = UIBenchmarks(
        # Weightlifting (kg)
        back_squat=140.0,
        front_squat=120.0,
        deadlift=170.0,
        clean=100.0,
        snatch=80.0,
        overhead_press=70.0,
        bench=110.0,

        # Gymnastics - max reps
        max_pullup=20,
        max_hspu=15,
        max_ttb=25,
        max_bmu=8,
        max_du=200,
        max_wb=40,

        # Gymnastics - timed sets (mm:ss format)
        t_20pu="1:30",      # 20 pull-ups in 1:30
        t_20hspu="2:15",    # 20 HSPU in 2:15
        t_60du="0:45",      # 60 DU in 45 seconds
        t_20wb="1:45",      # 20 wall balls in 1:45

        # Monostructural
        ftp_bike_w=280,     # 280W FTP on bike
        row_2k="7:15",      # 2k row in 7:15
        row_5k="19:30",     # 5k row in 19:30
        run_400m="1:25",    # 400m run in 1:25
        run_1600m="6:45",   # 1600m run in 6:45

        # CrossFit benchmarks
        fran="4:30",        # Fran in 4:30
        helen="11:45",      # Helen in 11:45
    )

    # Build athlete capabilities from benchmarks
    capabilities = build_athlete_from_benchmarks(
        name="Example Athlete",
        body_mass_kg=75.0,
        benchmarks=benchmarks,
        height_cm=175.0
    )

    # Set current context and day state
    context = ContextParams(
        temperature_c=25.0,     # Warm day
        humidity_pct=65.0,      # Humid
        altitude_m=0.0          # Sea level
    )

    day_state = DayState(
        sleep_h=7.0,            # 7 hours sleep
        sleep_quality=3,        # Average quality (1-5)
        water_l=1.5,            # 1.5L water so far
        body_mass_kg=75.0,      # Current weight
        rpe_intended=7          # Planning RPE 7 workout
    )

    # Create athlete with all components
    athlete = AthleteV2(
        name="Example Athlete",
        capabilities=capabilities,
        context=context,
        day_state=day_state
    )

    return athlete


def demonstrate_rpe_strategies():
    """Demonstrate different RPE strategies."""

    print("=== RPE Strategy Comparison ===\n")

    for rpe in [3, 5, 7, 9]:
        strategy = create_rpe_strategy(rpe)
        level = RPELevel.from_rpe(rpe)

        print("RPE {} - {}".format(rpe, level.description))
        print("  Max load: {:.0%} of 1RM".format(strategy.constraints.max_load_pct))
        print("  Set size: {:.0%} of max capacity".format(strategy.constraints.preferred_set_fraction))
        print("  Min rest: {:.0f}s between sets".format(strategy.constraints.min_rest_between_sets))
        print("  Cardio reserve: {:.0%} W'bal".format(strategy.constraints.cardio_reserve))
        print()


def demonstrate_athlete_capabilities(athlete):
    """Demonstrate athlete capabilities display."""

    print("=== Athlete Summary ===")
    summary = athlete.get_performance_summary()
    print("Name: {}".format(summary['name']))
    print("Body Mass: {}kg".format(summary['body_mass_kg']))
    if summary['relative_strength']:
        print("Relative Strength: {:.1f}x bodyweight".format(summary['relative_strength']))
    if summary['aerobic_capacity']:
        print("Estimated VO2 Max: {:.0f} ml/kg/min".format(summary['aerobic_capacity']))
    print("Intended RPE: {}".format(summary['intended_rpe']))
    print()

    # Show capabilities
    print("=== Key Capabilities ===")
    print("1RM Lifts:")
    for movement, weight in athlete.capabilities.one_rm.items():
        if weight > 0:
            ratio = weight / athlete.capabilities.body_mass_kg
            print("  {}: {:.0f}kg ({:.1f}x BW)".format(movement, weight, ratio))

    print("\nGym Skills:")
    for skill, profile in athlete.capabilities.gym_skills.items():
        print("  {}: {:.1f}s/rep, max {}".format(skill, profile.cycle_s, profile.unbroken_cap))

    print("\nCardio Profiles:")
    for modality, profile in athlete.capabilities.cardio_profiles.items():
        if modality in ['bike', 'row']:
            print("  {}: CP={:.0f}W, W'={:.0f}J".format(modality, profile.cp, profile.w_prime))
        else:
            print("  {}: CS={:.1f}m/s, D'={:.0f}m".format(modality, profile.cp, profile.w_prime))
    print()


def demonstrate_fatigue_tracking(athlete):
    """Demonstrate fatigue accumulation and recovery."""

    print("=== Fatigue Tracking Demonstration ===\n")

    # Reset fatigue
    athlete.reset_fatigue()

    print("Initial state:")
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:  # Only show non-zero fatigue
            print("  {}: {:.3f}".format(key, value))

    print("\nAfter 21 thrusters (43kg):")
    athlete.add_work('thruster', 21, 43.0)
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print("  {}: {:.3f}".format(key, value))

    print("\nAfter 21 pull-ups:")
    athlete.add_work('pull-up', 21)
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print("  {}: {:.3f}".format(key, value))

    print("\nAfter 2 minutes rest:")
    athlete.recover(120.0)  # 2 minutes
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print("  {}: {:.3f}".format(key, value))


def demonstrate_performance_effects(athlete):
    """Demonstrate how context and fatigue affect performance."""

    print("=== Performance Effects Demonstration ===\n")

    # Reset fatigue
    athlete.reset_fatigue()

    print("Pull-up times under different conditions:")

    # Fresh, optimal conditions
    fresh_time = athlete.get_rep_time('pull-up')
    print("  Fresh, 25C, 65% humidity: {:.2f}s".format(fresh_time))

    # Add fatigue
    athlete.add_work('pull-up', 20)
    fatigued_time = athlete.get_rep_time('pull-up')
    pct_slower = (fatigued_time/fresh_time-1)*100
    print("  After 20 reps: {:.2f}s ({:.1f}% slower)".format(fatigued_time, pct_slower))

    # Change temperature (hot)
    athlete.context.temperature_c = 35.0
    athlete._context_factors_cache = None  # Clear cache
    hot_time = athlete.get_rep_time('pull-up')
    pct_slower_hot = (hot_time/fresh_time-1)*100
    print("  Hot conditions (35C): {:.2f}s ({:.1f}% slower)".format(hot_time, pct_slower_hot))

    # Reset conditions, test dehydration
    athlete.context.temperature_c = 25.0
    athlete.day_state.water_l = 0.8  # Dehydrated
    athlete._context_factors_cache = None
    dehydrated_time = athlete.get_rep_time('pull-up')
    pct_slower_dehy = (dehydrated_time/fresh_time-1)*100
    print("  Dehydrated (0.8L): {:.2f}s ({:.1f}% slower)".format(dehydrated_time, pct_slower_dehy))


def main():
    """Main demonstration function."""

    print("CrossFit Digital Twin V2 - Concrete Parameter System")
    print("=" * 60)
    print()

    # Create athlete
    athlete = create_example_athlete()

    # Demonstrate different components
    demonstrate_athlete_capabilities(athlete)
    demonstrate_rpe_strategies()
    demonstrate_fatigue_tracking(athlete)
    demonstrate_performance_effects(athlete)

    print("\n" + "=" * 60)
    print("V2 System Benefits:")
    print("✓ Concrete, measurable parameters")
    print("✓ RPE-based strategy selection")
    print("✓ Physiological fatigue models")
    print("✓ Environmental context effects")
    print("✓ Easy integration with UI benchmarks")


if __name__ == "__main__":
    main()
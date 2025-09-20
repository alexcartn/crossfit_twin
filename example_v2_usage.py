"""
Example usage of CrossFit Digital Twin V2 system.

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


def create_example_athlete() -> AthleteV2:
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

        print(f"RPE {rpe} - {level.description}")
        print(f"  Max load: {strategy.constraints.max_load_pct:.0%} of 1RM")
        print(f"  Set size: {strategy.constraints.preferred_set_fraction:.0%} of max capacity")
        print(f"  Min rest: {strategy.constraints.min_rest_between_sets:.0f}s between sets")
        print(f"  Cardio reserve: {strategy.constraints.cardio_reserve:.0%} W'bal")
        print()


def simulate_fran_different_rpes(athlete: AthleteV2):
    """Simulate Fran at different RPE levels."""

    print("=== Fran Simulation at Different RPEs ===\n")

    # Define Fran workout
    fran = WOD(
        name="Fran",
        structure="for_time",
        rounds=[
            [Exercise("thruster", reps=21, weight_kg=43)],  # 95lb thrusters
            [Exercise("pull-up", reps=21)],
            [Exercise("thruster", reps=15, weight_kg=43)],
            [Exercise("pull-up", reps=15)],
            [Exercise("thruster", reps=9, weight_kg=43)],
            [Exercise("pull-up", reps=9)],
        ]
    )

    for target_rpe in [5, 7, 9]:
        # Reset athlete fatigue
        athlete.reset_fatigue()

        # Update intended RPE
        athlete.day_state.rpe_intended = target_rpe
        strategy = athlete.get_strategy_for_rpe()

        print(f"RPE {target_rpe} Strategy:")

        # Simulate first round (21 thrusters + 21 pull-ups)
        thruster_1rm = athlete.capabilities.get_one_rm('thruster')
        if thruster_1rm:
            load_pct = 43.0 / thruster_1rm
            print(f"  Thruster load: {load_pct:.0%} of 1RM ({43}kg / {thruster_1rm:.0f}kg)")

        # Get set scheme for 21 thrusters
        pullup_skill = athlete.capabilities.get_gym_skill('pull-up')
        if pullup_skill:
            thruster_scheme = strategy.calculate_set_scheme(
                exercise='thruster',
                total_reps=21,
                unbroken_capacity=15,  # Conservative estimate for weighted movement
                current_local_fatigue=0.0,
                one_rm_kg=thruster_1rm
            )

            pullup_scheme = strategy.calculate_set_scheme(
                exercise='pull-up',
                total_reps=21,
                unbroken_capacity=pullup_skill.unbroken_cap,
                current_local_fatigue=0.0
            )

            print(f"  Thruster sets: {thruster_scheme.reps_per_set}")
            print(f"  Pull-up sets: {pullup_scheme.reps_per_set}")
            print(f"  Rest between thruster sets: {[f'{r:.0f}s' for r in thruster_scheme.rest_between_sets]}")

        print()


def demonstrate_fatigue_tracking(athlete: AthleteV2):
    """Demonstrate fatigue accumulation and recovery."""

    print("=== Fatigue Tracking Demonstration ===\n")

    # Reset fatigue
    athlete.reset_fatigue()

    print("Initial state:")
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:  # Only show non-zero fatigue
            print(f"  {key}: {value:.3f}")

    print("\nAfter 21 thrusters (43kg):")
    athlete.add_work('thruster', 21, 43.0)
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print(f"  {key}: {value:.3f}")

    print("\nAfter 21 pull-ups:")
    athlete.add_work('pull-up', 21)
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print(f"  {key}: {value:.3f}")

    print("\nAfter 2 minutes rest:")
    athlete.recover(120.0)  # 2 minutes
    fatigue_summary = athlete.fatigue_manager.get_fatigue_summary()
    for key, value in fatigue_summary.items():
        if value > 0.01:
            print(f"  {key}: {value:.3f}")


def demonstrate_performance_effects(athlete: AthleteV2):
    """Demonstrate how context and fatigue affect performance."""

    print("=== Performance Effects Demonstration ===\n")

    # Reset fatigue
    athlete.reset_fatigue()

    print("Pull-up times under different conditions:")

    # Fresh, optimal conditions
    fresh_time = athlete.get_rep_time('pull-up')
    print(f"  Fresh, 25°C, 65% humidity: {fresh_time:.2f}s")

    # Add fatigue
    athlete.add_work('pull-up', 20)
    fatigued_time = athlete.get_rep_time('pull-up')
    print(f"  After 20 reps: {fatigued_time:.2f}s ({(fatigued_time/fresh_time-1)*100:.1f}% slower)")

    # Change temperature (hot)
    athlete.context.temperature_c = 35.0
    athlete._context_factors_cache = None  # Clear cache
    hot_time = athlete.get_rep_time('pull-up')
    print(f"  Hot conditions (35°C): {hot_time:.2f}s ({(hot_time/fresh_time-1)*100:.1f}% slower)")

    # Reset conditions, test dehydration
    athlete.context.temperature_c = 25.0
    athlete.day_state.water_l = 0.8  # Dehydrated
    athlete._context_factors_cache = None
    dehydrated_time = athlete.get_rep_time('pull-up')
    print(f"  Dehydrated (0.8L): {dehydrated_time:.2f}s ({(dehydrated_time/fresh_time-1)*100:.1f}% slower)")


def main():
    """Main demonstration function."""

    print("CrossFit Digital Twin V2 - Concrete Parameter System")
    print("=" * 60)
    print()

    # Create athlete
    athlete = create_example_athlete()

    # Show athlete summary
    print("=== Athlete Summary ===")
    summary = athlete.get_performance_summary()
    print(f"Name: {summary['name']}")
    print(f"Body Mass: {summary['body_mass_kg']}kg")
    if summary['relative_strength']:
        print(f"Relative Strength: {summary['relative_strength']:.1f}x bodyweight")
    if summary['aerobic_capacity']:
        print(f"Estimated VO2 Max: {summary['aerobic_capacity']:.0f} ml/kg/min")
    print(f"Intended RPE: {summary['intended_rpe']}")
    print()

    # Show capabilities
    print("=== Key Capabilities ===")
    print("1RM Lifts:")
    for movement, weight in athlete.capabilities.one_rm.items():
        if weight > 0:
            ratio = weight / athlete.capabilities.body_mass_kg
            print(f"  {movement}: {weight:.0f}kg ({ratio:.1f}x BW)")

    print("\nGym Skills:")
    for skill, profile in athlete.capabilities.gym_skills.items():
        print(f"  {skill}: {profile.cycle_s:.1f}s/rep, max {profile.unbroken_cap}")

    print("\nCardio Profiles:")
    for modality, profile in athlete.capabilities.cardio_profiles.items():
        if modality in ['bike', 'row']:
            print(f"  {modality}: CP={profile.cp:.0f}W, W'={profile.w_prime:.0f}J")
        else:
            print(f"  {modality}: CS={profile.cp:.1f}m/s, D'={profile.w_prime:.0f}m")
    print()

    # Demonstrate different components
    demonstrate_rpe_strategies()
    simulate_fran_different_rpes(athlete)
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
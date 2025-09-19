#!/usr/bin/env python3
"""
Validation script for the new concrete parameter system.
This script tests the key functionality without requiring Streamlit.
"""

try:
    # Test imports
    from crossfit_twin.athlete import Athlete, ContextParams, DayState
    from crossfit_twin.athlete import (
        freshness_factor, hydration_factor, 
        hot_humid_recovery_scale, cardio_drift_scale,
        u_shape_cycle_multiplier
    )
    from crossfit_twin.workout import FamousWODs
    from crossfit_twin.strategy import StrategyFactory
    from crossfit_twin import simulate
    print("✅ All imports successful")
    
    # Test concrete input athlete creation
    athlete = Athlete.from_concrete_inputs(
        name="Test Athlete",
        weight_kg=75.0,
        row_2k_time="7:30",
        row_5k_time="19:30", 
        t_thr_10=20.0,
        t_pu_10=15.0,
        t_bur_15=45.0,
        t_wb_15=35.0,
        bs_1rm=150.0,
        cj_1rm=110.0,
        sn_1rm=85.0
    )
    print(f"✅ Created athlete: {athlete.name}")
    print(f"  - Strength: {athlete.strength:.0f}/100")
    print(f"  - Endurance: {athlete.endurance:.0f}/100")
    print(f"  - Fatigue Resistance: {athlete.fatigue_resistance:.0f}/100")
    print(f"  - Recovery Rate: {athlete.recovery_rate:.0f}/100")
    
    # Test context and day state
    ctx = ContextParams(temperature_c=25.0, humidity_pct=60.0, altitude_m=0.0)
    day = DayState(sleep_h=7.5, sleep_quality=3, water_l=2.0, body_mass_kg=75.0)
    
    athlete.set_simulation_context(ctx, day)
    print("✅ Set simulation context and day state")
    
    # Test environmental factor calculations
    fresh_factor = freshness_factor(day.sleep_h, day.sleep_quality)
    hydro_factor = hydration_factor(day.water_l, day.body_mass_kg, ctx.temperature_c) 
    recovery_factor = hot_humid_recovery_scale(ctx.temperature_c, ctx.humidity_pct)
    cardio_factor = cardio_drift_scale(ctx.temperature_c, ctx.humidity_pct, ctx.altitude_m)
    
    print(f"✅ Environmental factors calculated:")
    print(f"  - Freshness: {fresh_factor:.3f}")
    print(f"  - Hydration: {hydro_factor:.3f}")
    print(f"  - Recovery: {recovery_factor:.3f}")
    print(f"  - Cardio drift: {cardio_factor:.3f}")
    
    # Test rep time calculation with context
    rep_time_fresh = athlete.get_rep_time("thruster", weight_kg=42.5, fatigue=0.0)
    rep_time_fatigued = athlete.get_rep_time("thruster", weight_kg=42.5, fatigue=0.5)
    print(f"✅ Rep time calculations:")
    print(f"  - Thruster (fresh): {rep_time_fresh:.2f}s")
    print(f"  - Thruster (fatigued): {rep_time_fatigued:.2f}s")
    
    # Test recovery calculation with context
    recovered_fatigue = athlete.recover(rest_duration_seconds=60.0, current_fatigue=0.5)
    print(f"✅ Recovery calculation:")
    print(f"  - Fatigue after 60s rest: {recovered_fatigue:.3f}")
    
    # Test simulation with context
    workout = FamousWODs.fran()
    strategy = StrategyFactory.unbroken()
    
    print("✅ Running simulation test...")
    result = simulate(workout, athlete, strategy, verbose=False)
    print(f"✅ Simulation completed:")
    print(f"  - Total time: {result.total_time:.1f}s")
    print(f"  - Completed: {result.completed}")
    print(f"  - Final fatigue: {result.final_fatigue:.3f}")
    
    print("\n🎉 All tests passed! The new concrete parameter system is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
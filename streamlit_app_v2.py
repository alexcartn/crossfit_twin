"""
Streamlit V2 web interface for CrossFit Digital Twin.

Enhanced UI supporting concrete benchmark inputs, RPE-based strategies,
and advanced fatigue visualization using the V2 system.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional
import time

# Import V2 system
from crossfit_twin import (
    # V2 system
    UIBenchmarks, AthleteCapabilities, AthleteV2, ContextParams, DayState,
    build_athlete_from_benchmarks, validate_benchmarks, estimate_missing_lifts,
    create_rpe_strategy, RPELevel, RPEStrategy,
    FatigueManager, MovementPattern,

    # Legacy system (for WODs)
    WOD, Exercise, simulate
)
from crossfit_twin.workout import FamousWODs

# Page configuration
st.set_page_config(
    page_title="CrossFit Digital Twin V2",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .v2-badge {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables for V2 system."""
    if 'v2_benchmarks' not in st.session_state:
        st.session_state.v2_benchmarks = UIBenchmarks()
    if 'v2_athlete' not in st.session_state:
        st.session_state.v2_athlete = None
    if 'v2_context' not in st.session_state:
        st.session_state.v2_context = ContextParams()
    if 'v2_day_state' not in st.session_state:
        st.session_state.v2_day_state = DayState()
    if 'v2_simulation_results' not in st.session_state:
        st.session_state.v2_simulation_results = []
    if 'current_workout' not in st.session_state:
        st.session_state.current_workout = None


def create_benchmark_input_form():
    """Create comprehensive benchmark input form."""
    st.subheader("📊 Benchmark Inputs")
    st.markdown('<span class="v2-badge">V2 System</span>', unsafe_allow_html=True)

    benchmarks = st.session_state.v2_benchmarks

    # Basic info
    with st.expander("👤 Basic Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Athlete Name", value="My Athlete")
            body_mass = st.number_input("Body Mass (kg)", 40.0, 150.0, 75.0, 0.1)
        with col2:
            height = st.number_input("Height (cm)", 140.0, 220.0, 175.0, 0.5)

    # Weightlifting benchmarks
    with st.expander("🏋️ Weightlifting Benchmarks (kg)", expanded=False):
        st.markdown("**Enter your 1RM or best known values:**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Squats:**")
            benchmarks.back_squat = st.number_input("Back Squat", 0.0, 400.0,
                                                   value=float(benchmarks.back_squat or 0), key="back_squat")
            benchmarks.front_squat = st.number_input("Front Squat", 0.0, 350.0,
                                                    value=float(benchmarks.front_squat or 0), key="front_squat")
            benchmarks.oh_squat = st.number_input("Overhead Squat", 0.0, 250.0,
                                                 value=float(benchmarks.oh_squat or 0), key="oh_squat")

        with col2:
            st.markdown("**Presses:**")
            benchmarks.strict_press = st.number_input("Strict Press", 0.0, 200.0,
                                                     value=float(benchmarks.strict_press or 0), key="strict_press")
            benchmarks.push_press = st.number_input("Push Press", 0.0, 250.0,
                                                   value=float(benchmarks.push_press or 0), key="push_press")
            benchmarks.push_jerk = st.number_input("Push Jerk", 0.0, 300.0,
                                                  value=float(benchmarks.push_jerk or 0), key="push_jerk")
            benchmarks.bench = st.number_input("Bench Press", 0.0, 300.0,
                                              value=float(benchmarks.bench or 0), key="bench")

        with col3:
            st.markdown("**Olympic & Other:**")
            benchmarks.deadlift = st.number_input("Deadlift", 0.0, 400.0,
                                                 value=float(benchmarks.deadlift or 0), key="deadlift")
            benchmarks.clean = st.number_input("Clean", 0.0, 250.0,
                                              value=float(benchmarks.clean or 0), key="clean")
            benchmarks.snatch = st.number_input("Snatch", 0.0, 200.0,
                                               value=float(benchmarks.snatch or 0), key="snatch")
            benchmarks.clean_and_jerk = st.number_input("Clean & Jerk", 0.0, 250.0,
                                                       value=float(benchmarks.clean_and_jerk or 0), key="clean_jerk")

    # Gymnastics benchmarks
    with st.expander("🤸 Gymnastics Benchmarks", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Max Unbroken Reps:**")
            benchmarks.max_pullup = st.number_input("Pull-ups", 0, 100,
                                                   value=int(benchmarks.max_pullup or 0), key="max_pullup")
            benchmarks.max_hspu = st.number_input("Handstand Push-ups", 0, 50,
                                                 value=int(benchmarks.max_hspu or 0), key="max_hspu")
            benchmarks.max_ttb = st.number_input("Toes to Bar", 0, 100,
                                                value=int(benchmarks.max_ttb or 0), key="max_ttb")
            benchmarks.max_bmu = st.number_input("Bar Muscle-ups", 0, 30,
                                                value=int(benchmarks.max_bmu or 0), key="max_bmu")
            benchmarks.max_rmu = st.number_input("Ring Muscle-ups", 0, 30,
                                                value=int(benchmarks.max_rmu or 0), key="max_rmu")
            benchmarks.max_wb = st.number_input("Wall Balls", 0, 100,
                                               value=int(benchmarks.max_wb or 0), key="max_wb")
            benchmarks.max_du = st.number_input("Double Unders", 0, 500,
                                               value=int(benchmarks.max_du or 0), key="max_du")

        with col2:
            st.markdown("**Timed Cycles (mm:ss):**")
            benchmarks.t_60du = st.text_input("60 Double Unders",
                                             value=benchmarks.t_60du or "", key="t_60du")
            benchmarks.t_20pu = st.text_input("20 Pull-ups",
                                             value=benchmarks.t_20pu or "", key="t_20pu")
            benchmarks.t_20hspu = st.text_input("20 Handstand Push-ups",
                                               value=benchmarks.t_20hspu or "", key="t_20hspu")
            benchmarks.t_20ttb = st.text_input("20 Toes to Bar",
                                              value=benchmarks.t_20ttb or "", key="t_20ttb")
            benchmarks.t_10bmu = st.text_input("10 Bar Muscle-ups",
                                              value=benchmarks.t_10bmu or "", key="t_10bmu")
            benchmarks.t_5rmu = st.text_input("5 Ring Muscle-ups",
                                             value=benchmarks.t_5rmu or "", key="t_5rmu")
            benchmarks.t_20wb = st.text_input("20 Wall Balls",
                                             value=benchmarks.t_20wb or "", key="t_20wb")
            benchmarks.t_hswalk_15m = st.text_input("15m Handstand Walk",
                                                   value=benchmarks.t_hswalk_15m or "", key="t_hswalk_15m")

    # Monostructural benchmarks
    with st.expander("🚴 Monostructural Benchmarks", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Bike:**")
            benchmarks.ftp_bike_w = st.number_input("FTP (watts)", 0, 600,
                                                   value=int(benchmarks.ftp_bike_w or 0), key="ftp_bike")

        with col2:
            st.markdown("**Rowing (mm:ss):**")
            benchmarks.row_500m = st.text_input("500m", value=benchmarks.row_500m or "", key="row_500m")
            benchmarks.row_2k = st.text_input("2k", value=benchmarks.row_2k or "", key="row_2k")
            benchmarks.row_5k = st.text_input("5k", value=benchmarks.row_5k or "", key="row_5k")

        with col3:
            st.markdown("**Running (mm:ss):**")
            benchmarks.run_400m = st.text_input("400m", value=benchmarks.run_400m or "", key="run_400m")
            benchmarks.run_1600m = st.text_input("1600m", value=benchmarks.run_1600m or "", key="run_1600m")
            benchmarks.run_5k = st.text_input("5k", value=benchmarks.run_5k or "", key="run_5k")

    # CrossFit benchmarks
    with st.expander("💪 CrossFit Benchmark WODs (mm:ss)", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            benchmarks.fran = st.text_input("Fran", value=benchmarks.fran or "", key="fran")
            benchmarks.helen = st.text_input("Helen", value=benchmarks.helen or "", key="helen")
            benchmarks.grace = st.text_input("Grace", value=benchmarks.grace or "", key="grace")
            benchmarks.isabel = st.text_input("Isabel", value=benchmarks.isabel or "", key="isabel")

        with col2:
            benchmarks.amanda = st.text_input("Amanda", value=benchmarks.amanda or "", key="amanda")
            benchmarks.diane = st.text_input("Diane", value=benchmarks.diane or "", key="diane")
            benchmarks.nancy = st.text_input("Nancy", value=benchmarks.nancy or "", key="nancy")
            benchmarks.mary = st.text_input("Mary", value=benchmarks.mary or "", key="mary")

        with col3:
            benchmarks.angie = st.text_input("Angie", value=benchmarks.angie or "", key="angie")
            benchmarks.murph_vest = st.text_input("Murph (w/ vest)", value=benchmarks.murph_vest or "", key="murph")
            benchmarks.filthy_50 = st.text_input("Filthy 50", value=benchmarks.filthy_50 or "", key="filthy_50")

    # Validate and create athlete
    if st.button("🔄 Create V2 Athlete", type="primary"):
        errors = validate_benchmarks(benchmarks)
        if errors:
            st.error("⚠️ Validation errors:")
            for field, error in errors.items():
                st.error(f"- {field}: {error}")
        else:
            try:
                # Build athlete capabilities
                capabilities = build_athlete_from_benchmarks(
                    name=name,
                    body_mass_kg=body_mass,
                    benchmarks=benchmarks,
                    height_cm=height if height > 0 else None
                )

                # Estimate missing lifts
                estimate_missing_lifts(capabilities)

                # Create V2 athlete
                athlete = AthleteV2(
                    name=name,
                    capabilities=capabilities,
                    context=st.session_state.v2_context,
                    day_state=st.session_state.v2_day_state
                )

                st.session_state.v2_athlete = athlete
                st.session_state.v2_benchmarks = benchmarks
                st.success("✅ V2 Athlete created successfully!")

                # Show summary
                with st.expander("📋 Athlete Summary", expanded=True):
                    summary = athlete.get_performance_summary()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Body Mass", f"{summary['body_mass_kg']}kg")
                        if summary['relative_strength']:
                            st.metric("Relative Strength", f"{summary['relative_strength']:.1f}x BW")
                    with col2:
                        if summary['aerobic_capacity']:
                            st.metric("Est. VO2 Max", f"{summary['aerobic_capacity']:.0f} ml/kg/min")
                        st.metric("Intended RPE", summary['intended_rpe'])
                    with col3:
                        st.metric("1RM Count", len(athlete.capabilities.one_rm))
                        st.metric("Gym Skills", len(athlete.capabilities.gym_skills))

            except Exception as e:
                st.error(f"❌ Error creating athlete: {str(e)}")


def create_context_day_form():
    """Create context and day state configuration."""
    st.subheader("🌡️ Context & Day State")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Environmental Context:**")
        temp = st.slider("Temperature (°C)", -10, 45, int(st.session_state.v2_context.temperature_c))
        humidity = st.slider("Humidity (%)", 10, 100, int(st.session_state.v2_context.humidity_pct))
        altitude = st.slider("Altitude (m)", 0, 3000, int(st.session_state.v2_context.altitude_m))

    with col2:
        st.markdown("**Daily State:**")
        sleep_h = st.slider("Sleep Hours", 4.0, 12.0, st.session_state.v2_day_state.sleep_h, 0.5)
        sleep_quality = st.slider("Sleep Quality (1-5)", 1, 5, st.session_state.v2_day_state.sleep_quality)
        water_l = st.slider("Water Intake (L)", 0.0, 5.0, st.session_state.v2_day_state.water_l, 0.1)
        rpe_intended = st.slider("Intended RPE (0-10)", 0, 10, st.session_state.v2_day_state.rpe_intended)

    # Update session state
    st.session_state.v2_context = ContextParams(
        temperature_c=float(temp),
        humidity_pct=float(humidity),
        altitude_m=float(altitude)
    )

    body_mass = st.session_state.v2_athlete.capabilities.body_mass_kg if st.session_state.v2_athlete else 75.0
    st.session_state.v2_day_state = DayState(
        sleep_h=sleep_h,
        sleep_quality=sleep_quality,
        water_l=water_l,
        body_mass_kg=body_mass,
        rpe_intended=rpe_intended
    )

    # Show RPE description
    rpe_level = RPELevel.from_rpe(rpe_intended)
    st.info(f"**RPE {rpe_intended}**: {rpe_level.description}")


def create_rpe_strategy_display():
    """Display RPE-based strategy information."""
    if not st.session_state.v2_athlete:
        st.warning("Please create an athlete first.")
        return

    st.subheader("⚡ RPE Strategy")

    strategy = st.session_state.v2_athlete.get_strategy_for_rpe()

    st.markdown(strategy.get_strategy_description())

    # Strategy constraints visualization
    constraints = strategy.constraints

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Load", f"{constraints.max_load_pct:.0%}")
        st.metric("Preferred Load", f"{constraints.preferred_load_pct:.0%}")
    with col2:
        st.metric("Max Set Size", f"{constraints.max_set_fraction:.0%}")
        st.metric("Preferred Set Size", f"{constraints.preferred_set_fraction:.0%}")
    with col3:
        st.metric("Min Rest (sets)", f"{constraints.min_rest_between_sets:.0f}s")
        st.metric("Min Rest (movements)", f"{constraints.min_rest_between_movements:.0f}s")


def create_fatigue_visualization():
    """Visualize current fatigue state."""
    if not st.session_state.v2_athlete:
        st.warning("Please create an athlete first.")
        return

    st.subheader("🔋 Fatigue State")

    fatigue_summary = st.session_state.v2_athlete.fatigue_manager.get_fatigue_summary()

    # Create fatigue chart
    local_fatigue = {k.replace('local_', ''): v for k, v in fatigue_summary.items() if k.startswith('local_')}
    cardio_fatigue = {k.replace('cardio_', ''): v for k, v in fatigue_summary.items() if k.startswith('cardio_')}

    if local_fatigue:
        fig = go.Figure()

        patterns = list(local_fatigue.keys())
        values = list(local_fatigue.values())

        fig.add_trace(go.Bar(
            x=patterns,
            y=values,
            name="Local Fatigue",
            marker_color="orange"
        ))

        fig.update_layout(
            title="Local Muscle Fatigue by Movement Pattern",
            yaxis_title="Fatigue Level",
            xaxis_title="Movement Pattern"
        )

        st.plotly_chart(fig, use_container_width=True)

    # Show cardio fatigue
    if cardio_fatigue:
        col1, col2, col3, col4 = st.columns(4)
        for i, (modality, fatigue) in enumerate(cardio_fatigue.items()):
            with [col1, col2, col3, col4][i % 4]:
                st.metric(f"{modality.title()} Fatigue", f"{fatigue:.2f}")


def create_workout_simulation():
    """Create workout simulation interface."""
    if not st.session_state.v2_athlete:
        st.warning("Please create an athlete first.")
        return

    st.subheader("🏃 Workout Simulation")

    # Workout selection
    workout_type = st.selectbox(
        "Choose workout type:",
        ["Famous WODs", "Custom WOD"]
    )

    if workout_type == "Famous WODs":
        wod_name = st.selectbox(
            "Select WOD:",
            ["Fran", "Helen", "Cindy", "Grace", "Isabel", "Amanda", "Diane"]
        )

        if st.button("🚀 Simulate Workout"):
            try:
                # Get the workout
                wod = getattr(FamousWODs, wod_name.upper())()

                # Reset athlete fatigue
                st.session_state.v2_athlete.reset_fatigue()

                # Update athlete context and day state
                st.session_state.v2_athlete.context = st.session_state.v2_context
                st.session_state.v2_athlete.day_state = st.session_state.v2_day_state

                # Get strategy
                strategy = st.session_state.v2_athlete.get_strategy_for_rpe()

                # Note: For now, using legacy simulate function
                # In a full implementation, we'd create a V2 simulator
                result = simulate(wod, st.session_state.v2_athlete, strategy)

                st.success(f"✅ {wod_name} completed!")

                # Display results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Time", f"{result.total_time:.1f}s")
                with col2:
                    st.metric("Final Fatigue", f"{result.final_fatigue:.2f}")
                with col3:
                    st.metric("Strategy", strategy.constraints.target_rpe)

                # Store result
                st.session_state.v2_simulation_results.append({
                    'workout': wod_name,
                    'time': result.total_time,
                    'rpe': strategy.constraints.target_rpe,
                    'athlete': st.session_state.v2_athlete.name
                })

            except Exception as e:
                st.error(f"❌ Simulation error: {str(e)}")

    # Show simulation history
    if st.session_state.v2_simulation_results:
        st.subheader("📊 Simulation History")
        df = pd.DataFrame(st.session_state.v2_simulation_results)
        st.dataframe(df, use_container_width=True)


def main():
    """Main application."""
    initialize_session_state()

    # Header
    st.markdown('<h1 class="main-header">🏋️ CrossFit Digital Twin V2</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <span class="v2-badge">Concrete Parameters</span>
        <span class="v2-badge">RPE Strategies</span>
        <span class="v2-badge">Advanced Fatigue</span>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        page = st.selectbox(
            "Choose a page:",
            [
                "🏠 Home",
                "👤 Athlete Builder",
                "🌡️ Context & Day",
                "⚡ RPE Strategy",
                "🔋 Fatigue Monitor",
                "🏃 Simulation",
                "📊 Comparison"
            ]
        )

    # Main content
    if page == "🏠 Home":
        st.markdown("""
        ## Welcome to CrossFit Digital Twin V2! 🎉

        ### 🆕 What's New in V2:

        **🎯 Concrete Parameters**
        - Real 1RM values (kg) instead of abstract scores
        - Cycle times (s/rep) for gymnastics movements
        - Critical Power/W' models for cardio

        **⚡ RPE-Based Strategies**
        - Rate of Perceived Exertion (0-10) drives workout intensity
        - Automatic set sizing and rest periods
        - Load constraints based on intended effort

        **🧠 Advanced Fatigue Modeling**
        - W'bal system for cardiovascular fatigue
        - Local muscle fatigue by movement pattern
        - Environmental and daily state effects

        **📊 Comprehensive Benchmarks**
        - Weightlifting: All major lifts
        - Gymnastics: Max reps + timed cycles
        - Monostructural: Bike, row, run, swim
        - MetCons: Famous CrossFit benchmarks

        ### 🚀 Getting Started:
        1. Go to **👤 Athlete Builder** to input your benchmarks
        2. Set **🌡️ Context & Day** parameters
        3. Review your **⚡ RPE Strategy**
        4. Run **🏃 Simulations** and monitor **🔋 Fatigue**

        ---
        *Built with the power of concrete physiological modeling* 💪
        """)

    elif page == "👤 Athlete Builder":
        create_benchmark_input_form()

    elif page == "🌡️ Context & Day":
        create_context_day_form()

    elif page == "⚡ RPE Strategy":
        create_rpe_strategy_display()

    elif page == "🔋 Fatigue Monitor":
        create_fatigue_visualization()

    elif page == "🏃 Simulation":
        create_workout_simulation()

    elif page == "📊 Comparison":
        st.subheader("📊 Performance Comparison")
        st.info("🚧 Comparison tools coming soon in V2.1!")

        if st.session_state.v2_simulation_results:
            df = pd.DataFrame(st.session_state.v2_simulation_results)

            # Simple time comparison chart
            if len(df) > 1:
                fig = px.bar(df, x='workout', y='time', color='rpe',
                           title="Workout Times by RPE")
                st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #666; margin-top: 2rem;">'
        'CrossFit Digital Twin V2 | Powered by Concrete Physiological Modeling'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
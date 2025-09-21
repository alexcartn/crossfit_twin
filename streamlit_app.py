"""
Streamlit web interface for CrossFit Digital Twin.

A comprehensive web application for creating athletes using concrete benchmarks,
testing RPE-based strategies, and analyzing performance with advanced fatigue modeling.
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

    # Advanced optimization features
    StrategySolver, OperationalAnalyzer, CloneOptimizer,
    _advanced_features_available,

    # Legacy system (for WODs)
    WOD, Exercise, simulate
)
from crossfit_twin.workout import FamousWODs

# Page configuration
st.set_page_config(
    page_title="CrossFit Digital Twin",
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
    .feature-badge {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: bold;
        margin: 0.25rem;
        display: inline-block;
    }
    .rpe-indicator {
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def get_dummy_benchmarks():
    """Get realistic dummy data for testing the app."""
    return UIBenchmarks(
        # Weightlifting - intermediate level athlete
        back_squat=120.0,
        front_squat=100.0,
        oh_squat=80.0,
        strict_press=65.0,
        push_press=75.0,
        push_jerk=85.0,
        bench=90.0,
        deadlift=140.0,
        clean=85.0,
        snatch=65.0,
        clean_and_jerk=85.0,

        # Gymnastics max reps
        max_pullup=15,
        max_hspu=8,
        max_ttb=12,
        max_bmu=3,
        max_rmu=2,
        max_wb=30,
        max_du=80,

        # Gymnastics timed cycles
        t_60du="1:45",
        t_20pu="2:00",
        t_20hspu="3:30",
        t_20ttb="2:30",
        t_10bmu="4:00",
        t_5rmu="2:45",
        t_20wb="1:45",
        t_hswalk_15m="1:15",

        # Cardio
        ftp_bike_w=220,
        row_500m="1:45",
        row_2k="7:45",
        row_5k="21:00",
        run_400m="1:35",
        run_1600m="7:00",
        run_5k="24:30",

        # CrossFit benchmarks
        fran="5:30",
        helen="12:45",
        grace="4:15",
        isabel="3:45",
        amanda="8:30",
        diane="6:15",
        nancy="14:30",
        mary="18:45",
        angie="22:15",
        murph_vest="52:30",
        filthy_50="32:45"
    )


def initialize_session_state():
    """Initialize session state variables."""
    if 'benchmarks' not in st.session_state:
        # Start with dummy data for easy testing
        st.session_state.benchmarks = get_dummy_benchmarks()
    if 'athlete' not in st.session_state:
        st.session_state.athlete = None
    if 'context' not in st.session_state:
        st.session_state.context = ContextParams()
    if 'day_state' not in st.session_state:
        st.session_state.day_state = DayState()
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = []
    if 'current_workout' not in st.session_state:
        st.session_state.current_workout = None
    if 'use_dummy_data' not in st.session_state:
        st.session_state.use_dummy_data = True


def create_benchmark_input_form():
    """Create comprehensive benchmark input form."""
    st.subheader("📊 Athlete Benchmark Input")
    st.markdown("Input your real performance data to create an accurate digital twin.")

    # Dummy data controls
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("💡 **Tip**: The app is pre-loaded with dummy data for easy testing!")
    with col2:
        if st.button("🎯 Use My Data", help="Clear dummy data and enter your own"):
            st.session_state.benchmarks = UIBenchmarks()
            st.session_state.use_dummy_data = False
            st.rerun()

        if st.button("🧪 Reset to Dummy", help="Restore dummy data for testing"):
            st.session_state.benchmarks = get_dummy_benchmarks()
            st.session_state.use_dummy_data = True
            st.rerun()

    benchmarks = st.session_state.benchmarks

    # Show data completeness
    if st.session_state.use_dummy_data:
        st.info("📊 Currently using dummy data - perfect for testing all features!")
    else:
        # Count non-empty fields for completeness indicator
        total_fields = 34  # Total benchmark fields
        filled_fields = sum(1 for field in [
            benchmarks.back_squat, benchmarks.front_squat, benchmarks.oh_squat,
            benchmarks.strict_press, benchmarks.push_press, benchmarks.push_jerk,
            benchmarks.bench, benchmarks.deadlift, benchmarks.clean, benchmarks.snatch,
            benchmarks.clean_and_jerk, benchmarks.max_pullup, benchmarks.max_hspu,
            benchmarks.max_ttb, benchmarks.max_bmu, benchmarks.max_rmu, benchmarks.max_wb,
            benchmarks.max_du, benchmarks.t_60du, benchmarks.t_20pu, benchmarks.t_20hspu,
            benchmarks.t_20ttb, benchmarks.t_10bmu, benchmarks.t_5rmu, benchmarks.t_20wb,
            benchmarks.t_hswalk_15m, benchmarks.ftp_bike_w, benchmarks.row_500m,
            benchmarks.row_2k, benchmarks.row_5k, benchmarks.run_400m, benchmarks.run_1600m,
            benchmarks.run_5k, benchmarks.fran
        ] if field and str(field).strip())

        completeness = filled_fields / total_fields
        if completeness > 0.7:
            st.success(f"📈 Data completeness: {completeness:.0%} - Excellent!")
        elif completeness > 0.4:
            st.warning(f"📊 Data completeness: {completeness:.0%} - Good for testing")
        else:
            st.info(f"📉 Data completeness: {completeness:.0%} - Missing data will be inferred")

    # Basic info
    with st.expander("👤 Basic Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Athlete Name", value="My Athlete")
            body_mass = st.number_input("Body Mass (kg)", 40.0, 150.0, 75.0, 0.1)
        with col2:
            height = st.number_input("Height (cm)", 140.0, 220.0, 175.0, 0.5)

    # Weightlifting benchmarks
    with st.expander("🏋️ Weightlifting Benchmarks (1RM in kg)", expanded=False):
        st.markdown("**Enter your one-rep max or best known values:**")

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
            st.markdown("**Olympic & Others:**")
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
            st.markdown("**Timed Cycles (mm:ss format):**")
            st.caption("Enter times for specific rep counts")
            benchmarks.t_60du = st.text_input("60 Double Unders",
                                             value=benchmarks.t_60du or "", key="t_60du",
                                             placeholder="e.g., 1:15")
            benchmarks.t_20pu = st.text_input("20 Pull-ups",
                                             value=benchmarks.t_20pu or "", key="t_20pu",
                                             placeholder="e.g., 1:30")
            benchmarks.t_20hspu = st.text_input("20 Handstand Push-ups",
                                               value=benchmarks.t_20hspu or "", key="t_20hspu",
                                               placeholder="e.g., 2:15")
            benchmarks.t_20ttb = st.text_input("20 Toes to Bar",
                                              value=benchmarks.t_20ttb or "", key="t_20ttb",
                                              placeholder="e.g., 1:45")
            benchmarks.t_10bmu = st.text_input("10 Bar Muscle-ups",
                                              value=benchmarks.t_10bmu or "", key="t_10bmu",
                                              placeholder="e.g., 2:30")
            benchmarks.t_5rmu = st.text_input("5 Ring Muscle-ups",
                                             value=benchmarks.t_5rmu or "", key="t_5rmu",
                                             placeholder="e.g., 1:45")
            benchmarks.t_20wb = st.text_input("20 Wall Balls",
                                             value=benchmarks.t_20wb or "", key="t_20wb",
                                             placeholder="e.g., 1:20")
            benchmarks.t_hswalk_15m = st.text_input("15m Handstand Walk",
                                                   value=benchmarks.t_hswalk_15m or "", key="t_hswalk_15m",
                                                   placeholder="e.g., 0:45")

    # Monostructural benchmarks
    with st.expander("🚴 Monostructural Benchmarks", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Bike:**")
            benchmarks.ftp_bike_w = st.number_input("FTP (watts)", 0, 600,
                                                   value=int(benchmarks.ftp_bike_w or 0), key="ftp_bike")

        with col2:
            st.markdown("**Rowing (mm:ss format):**")
            benchmarks.row_500m = st.text_input("500m", value=benchmarks.row_500m or "", key="row_500m",
                                               placeholder="e.g., 1:35")
            benchmarks.row_2k = st.text_input("2k", value=benchmarks.row_2k or "", key="row_2k",
                                             placeholder="e.g., 7:15")
            benchmarks.row_5k = st.text_input("5k", value=benchmarks.row_5k or "", key="row_5k",
                                             placeholder="e.g., 19:30")

        with col3:
            st.markdown("**Running (mm:ss format):**")
            benchmarks.run_400m = st.text_input("400m", value=benchmarks.run_400m or "", key="run_400m",
                                               placeholder="e.g., 1:25")
            benchmarks.run_1600m = st.text_input("1600m", value=benchmarks.run_1600m or "", key="run_1600m",
                                                placeholder="e.g., 6:45")
            benchmarks.run_5k = st.text_input("5k", value=benchmarks.run_5k or "", key="run_5k",
                                             placeholder="e.g., 22:30")

    # CrossFit benchmarks
    with st.expander("💪 CrossFit Benchmark WODs (mm:ss format)", expanded=False):
        st.markdown("**Enter your personal records for famous CrossFit workouts:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            benchmarks.fran = st.text_input("Fran", value=benchmarks.fran or "", key="fran",
                                           placeholder="e.g., 4:30")
            benchmarks.helen = st.text_input("Helen", value=benchmarks.helen or "", key="helen",
                                            placeholder="e.g., 11:45")
            benchmarks.grace = st.text_input("Grace", value=benchmarks.grace or "", key="grace",
                                            placeholder="e.g., 3:15")
            benchmarks.isabel = st.text_input("Isabel", value=benchmarks.isabel or "", key="isabel",
                                             placeholder="e.g., 2:45")

        with col2:
            benchmarks.amanda = st.text_input("Amanda", value=benchmarks.amanda or "", key="amanda",
                                             placeholder="e.g., 6:20")
            benchmarks.diane = st.text_input("Diane", value=benchmarks.diane or "", key="diane",
                                            placeholder="e.g., 4:45")
            benchmarks.nancy = st.text_input("Nancy", value=benchmarks.nancy or "", key="nancy",
                                            placeholder="e.g., 12:30")
            benchmarks.mary = st.text_input("Mary", value=benchmarks.mary or "", key="mary",
                                           placeholder="e.g., 15:20")

        with col3:
            benchmarks.angie = st.text_input("Angie", value=benchmarks.angie or "", key="angie",
                                            placeholder="e.g., 18:45")
            benchmarks.murph_vest = st.text_input("Murph (w/ vest)", value=benchmarks.murph_vest or "", key="murph",
                                                 placeholder="e.g., 45:30")
            benchmarks.filthy_50 = st.text_input("Filthy 50", value=benchmarks.filthy_50 or "", key="filthy_50",
                                                placeholder="e.g., 28:15")

    # Create athlete button
    if st.button("🔄 Create Digital Twin", type="primary", use_container_width=True):
        errors = validate_benchmarks(benchmarks)
        if errors:
            st.warning("⚠️ Found some data issues, but proceeding with intelligent fallbacks:")
            for field, error in errors.items():
                st.warning(f"• **{field.replace('_', ' ').title()}**: {error}")

        try:
            with st.spinner("Creating your digital twin..."):
                # Build athlete capabilities with robust fallback
                from crossfit_twin.builder import build_athlete_from_benchmarks_robust
                capabilities = build_athlete_from_benchmarks_robust(
                    name=name,
                    body_mass_kg=body_mass,
                    benchmarks=benchmarks,
                    height_cm=height if height > 0 else None
                )

                # Estimate missing lifts (for legacy compatibility)
                estimate_missing_lifts(capabilities)

                # Create athlete
                athlete = AthleteV2(
                    name=name,
                    capabilities=capabilities,
                    context=st.session_state.context,
                    day_state=st.session_state.day_state
                )

                st.session_state.athlete = athlete
                st.session_state.benchmarks = benchmarks

            st.success("✅ Digital twin created successfully!")

            # Show confidence score if available
            if hasattr(capabilities, 'completeness_score'):
                completeness = capabilities.completeness_score
                if completeness > 0.8:
                    st.success(f"🔬 Data confidence: {completeness:.0%} - Excellent!")
                elif completeness > 0.6:
                    st.info(f"🔬 Data confidence: {completeness:.0%} - Good with some inference")
                else:
                    st.warning(f"🔬 Data confidence: {completeness:.0%} - Heavy inference used")

            # Show athlete summary
            show_athlete_summary(athlete)

        except Exception as e:
            st.error(f"❌ Error creating athlete: {str(e)}")
            st.info("💡 The robust fallback system should handle missing data automatically.")


def show_athlete_summary(athlete):
    """Display athlete capability summary."""
    with st.expander("📋 Your Digital Twin Summary", expanded=True):
        summary = athlete.get_performance_summary()

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Body Mass", f"{summary['body_mass_kg']}kg")
        with col2:
            if summary['relative_strength']:
                st.metric("Relative Strength", f"{summary['relative_strength']:.1f}x BW")
            else:
                st.metric("Relative Strength", "Not calculated")
        with col3:
            if summary['aerobic_capacity']:
                st.metric("Est. VO2 Max", f"{summary['aerobic_capacity']:.0f} ml/kg/min")
            else:
                st.metric("Est. VO2 Max", "Not calculated")
        with col4:
            st.metric("Intended RPE", summary['intended_rpe'])

        # Provenance legend
        if hasattr(athlete.capabilities, 'provenance'):
            st.markdown("**📊 Data Quality:**")
            st.markdown("🧪 Measured | 🧩 Inferred | 💤 Default | 📊 Population Prior")

        # Detailed capabilities
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🏋️ Strength (1RM):**")
            if athlete.capabilities.one_rm:
                # Show provenance icons
                provenance_icons = {"measured": "🧪", "inferred": "🧩", "default": "💤", "prior": "📊"}

                for movement, weight in list(athlete.capabilities.one_rm.items())[:5]:
                    ratio = weight / athlete.capabilities.body_mass_kg

                    # Get provenance if available
                    icon = ""
                    if hasattr(athlete.capabilities, 'provenance'):
                        prov_key = f"1rm.{movement}"
                        source = athlete.capabilities.provenance.source.get(prov_key, "unknown")
                        icon = provenance_icons.get(source, "❓") + " "

                    st.text(f"{icon}{movement}: {weight:.0f}kg ({ratio:.1f}x)")

                if len(athlete.capabilities.one_rm) > 5:
                    st.text(f"... and {len(athlete.capabilities.one_rm) - 5} more")
            else:
                st.text("No strength data")

        with col2:
            st.markdown("**🤸 Gymnastics:**")
            if athlete.capabilities.gym_skills:
                for skill, profile in list(athlete.capabilities.gym_skills.items())[:5]:
                    st.text(f"{skill}: {profile.cycle_s:.1f}s/rep")
                if len(athlete.capabilities.gym_skills) > 5:
                    st.text(f"... and {len(athlete.capabilities.gym_skills) - 5} more")
            else:
                st.text("No gymnastics data")

        with col3:
            st.markdown("**🚴 Cardio:**")
            if athlete.capabilities.cardio_profiles:
                for modality, profile in athlete.capabilities.cardio_profiles.items():
                    if modality in ['bike', 'row']:
                        st.text(f"{modality}: {profile.cp:.0f}W CP")
                    else:
                        st.text(f"{modality}: {profile.cp:.1f}m/s CS")
            else:
                st.text("No cardio data")


def create_context_day_form():
    """Create context and day state configuration."""
    st.subheader("🌡️ Environment & Daily State")
    st.markdown("Configure environmental conditions and your daily readiness.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🌍 Environmental Context:**")
        temp = st.slider("Temperature (°C)", -10, 45, int(st.session_state.context.temperature_c))
        humidity = st.slider("Humidity (%)", 10, 100, int(st.session_state.context.humidity_pct))
        altitude = st.slider("Altitude (m)", 0, 3000, int(st.session_state.context.altitude_m))

        # Temperature guidance
        if temp < 10:
            st.info("🥶 Cold conditions may reduce flexibility and require longer warmup.")
        elif temp > 30:
            st.warning("🥵 Hot conditions will increase fatigue and reduce performance.")
        else:
            st.success("🌡️ Optimal temperature range for performance.")

    with col2:
        st.markdown("**💪 Daily Readiness:**")
        sleep_h = st.slider("Sleep Hours", 4.0, 12.0, st.session_state.day_state.sleep_h, 0.5)
        sleep_quality = st.slider("Sleep Quality (1-5)", 1, 5, st.session_state.day_state.sleep_quality)
        water_l = st.slider("Water Intake (L)", 0.0, 5.0, st.session_state.day_state.water_l, 0.1)
        rpe_intended = st.slider("Intended RPE (0-10)", 0, 10, st.session_state.day_state.rpe_intended)

        # Sleep guidance
        if sleep_h < 6:
            st.warning("😴 Low sleep will significantly impact performance.")
        elif sleep_h > 8:
            st.success("😴 Well-rested for optimal performance.")

    # Update session state
    st.session_state.context = ContextParams(
        temperature_c=float(temp),
        humidity_pct=float(humidity),
        altitude_m=float(altitude)
    )

    body_mass = st.session_state.athlete.capabilities.body_mass_kg if st.session_state.athlete else 75.0
    st.session_state.day_state = DayState(
        sleep_h=sleep_h,
        sleep_quality=sleep_quality,
        water_l=water_l,
        body_mass_kg=body_mass,
        rpe_intended=rpe_intended
    )

    # Show RPE description
    rpe_level = RPELevel.from_rpe(rpe_intended)
    st.markdown(f"""
    <div class="rpe-indicator">
        <h4>RPE {rpe_intended}: {rpe_level.description}</h4>
    </div>
    """, unsafe_allow_html=True)

    # Update athlete if exists
    if st.session_state.athlete:
        st.session_state.athlete.context = st.session_state.context
        st.session_state.athlete.day_state = st.session_state.day_state


def create_rpe_strategy_display():
    """Display RPE-based strategy information."""
    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("⚡ RPE-Based Strategy")
    st.markdown("Your personalized workout strategy based on intended effort level.")

    strategy = st.session_state.athlete.get_strategy_for_rpe()

    # Strategy overview
    st.markdown(f"### Current Strategy (RPE {strategy.constraints.target_rpe})")
    st.markdown(strategy.get_strategy_description())

    # Visual constraints
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**💪 Load Constraints**")
        st.metric("Max Load", f"{strategy.constraints.max_load_pct:.0%}", help="Maximum % of 1RM to use")
        st.metric("Preferred Load", f"{strategy.constraints.preferred_load_pct:.0%}", help="Target % for repeated efforts")

    with col2:
        st.markdown("**🎯 Set Size Constraints**")
        st.metric("Max Set Size", f"{strategy.constraints.max_set_fraction:.0%}", help="% of max capacity to use")
        st.metric("Preferred Set Size", f"{strategy.constraints.preferred_set_fraction:.0%}", help="Target % for sets")

    with col3:
        st.markdown("**⏰ Rest Constraints**")
        st.metric("Min Rest (sets)", f"{strategy.constraints.min_rest_between_sets:.0f}s", help="Between sets")
        st.metric("Min Rest (movements)", f"{strategy.constraints.min_rest_between_movements:.0f}s", help="Between exercises")

    # Strategy comparison
    with st.expander("📊 Compare RPE Levels", expanded=False):
        rpe_data = []
        for rpe in range(3, 11, 2):
            temp_strategy = create_rpe_strategy(rpe)
            rpe_data.append({
                'RPE': rpe,
                'Max Load': temp_strategy.constraints.max_load_pct,
                'Set Size': temp_strategy.constraints.preferred_set_fraction,
                'Rest (s)': temp_strategy.constraints.min_rest_between_sets
            })

        df = pd.DataFrame(rpe_data)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['RPE'], y=df['Max Load'], name='Max Load %', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=df['RPE'], y=df['Set Size'], name='Set Size %', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['RPE'], y=df['Rest (s)'] / 100, name='Rest Time (×100s)', line=dict(color='green')))

        fig.update_layout(
            title="RPE Strategy Comparison",
            xaxis_title="RPE Level",
            yaxis_title="Constraint Value",
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)


def create_fatigue_visualization():
    """Visualize current fatigue state."""
    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("🔋 Fatigue Monitoring")
    st.markdown("Real-time tracking of your digital twin's fatigue state.")

    fatigue_summary = st.session_state.athlete.fatigue_manager.get_fatigue_summary()

    # Overall fatigue status
    global_fatigue = fatigue_summary.get('global', 0)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Global Fatigue", f"{global_fatigue:.3f}", help="Overall accumulated fatigue")
    with col2:
        fatigue_status = "Fresh" if global_fatigue < 0.1 else "Moderate" if global_fatigue < 0.5 else "High"
        st.metric("Status", fatigue_status)
    with col3:
        if global_fatigue > 0:
            estimated_recovery = min(300, global_fatigue * 600)  # Rough estimate
            st.metric("Est. Recovery", f"{estimated_recovery:.0f}s")
        else:
            st.metric("Est. Recovery", "0s")

    # Local fatigue breakdown
    local_fatigue = {k.replace('local_', '').upper(): v for k, v in fatigue_summary.items() if k.startswith('local_')}

    if local_fatigue:
        st.markdown("**🎯 Local Muscle Fatigue by Movement Pattern:**")

        # Create fatigue chart
        fig = go.Figure(data=go.Bar(
            x=list(local_fatigue.keys()),
            y=list(local_fatigue.values()),
            marker_color=['orange' if v > 0.1 else 'lightblue' for v in local_fatigue.values()]
        ))

        fig.update_layout(
            title="Local Fatigue by Movement Pattern",
            yaxis_title="Fatigue Level",
            xaxis_title="Movement Pattern",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Movement pattern guide
        with st.expander("ℹ️ Movement Pattern Guide", expanded=False):
            st.markdown("""
            **Movement Patterns:**
            - **PULL**: Pull-ups, rows, muscle-ups
            - **PUSH**: Push-ups, HSPU, presses
            - **SQUAT**: Squats, wall-balls, box-jumps
            - **HINGE**: Deadlifts, KB swings, burpees
            - **CORE**: Sit-ups, toes-to-bar, L-sits
            - **GRIP**: Rope climbs, farmer's carries
            """)

    # Cardio fatigue (W'bal)
    cardio_fatigue = {k.replace('cardio_', '').title(): v for k, v in fatigue_summary.items() if k.startswith('cardio_')}

    if cardio_fatigue:
        st.markdown("**🚴 Cardiovascular Fatigue (W'bal):**")
        cardio_cols = st.columns(len(cardio_fatigue))
        for i, (modality, fatigue) in enumerate(cardio_fatigue.items()):
            with cardio_cols[i]:
                st.metric(f"{modality} Fatigue", f"{fatigue:.3f}")

    # Fatigue simulation
    st.markdown("**🧪 Fatigue Simulation:**")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Add 10 Pull-ups"):
            st.session_state.athlete.add_work("pull-up", 10)
            st.rerun()

    with col2:
        if st.button("Rest 60 seconds"):
            st.session_state.athlete.recover(60.0)
            st.rerun()


def create_workout_simulation():
    """Create workout simulation interface."""
    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("🏃 Workout Simulation")
    st.markdown("Test your digital twin on famous CrossFit workouts.")

    # Workout selection
    col1, col2 = st.columns([2, 1])

    with col1:
        workout_type = st.selectbox(
            "Choose workout type:",
            ["Famous WODs", "Custom WOD"]
        )

    with col2:
        if st.button("🔄 Reset Fatigue"):
            st.session_state.athlete.reset_fatigue()
            st.success("Fatigue reset!")

    if workout_type == "Famous WODs":
        wod_name = st.selectbox(
            "Select WOD:",
            ["Fran", "Helen", "Cindy", "Grace", "Isabel", "Amanda", "Diane"]
        )

        # Show WOD details
        try:
            wod = getattr(FamousWODs, wod_name.upper())()
            with st.expander(f"📋 {wod_name} Details", expanded=True):
                st.markdown(f"**Structure:** {wod.structure}")
                st.markdown("**Movements:**")
                for i, round_exercises in enumerate(wod.rounds):
                    round_text = f"Round {i+1}: "
                    exercises = []
                    for exercise in round_exercises:
                        if exercise.weight_kg:
                            exercises.append(f"{exercise.reps} {exercise.name} @ {exercise.weight_kg}kg")
                        else:
                            exercises.append(f"{exercise.reps} {exercise.name}")
                    st.text(round_text + ", ".join(exercises))
        except:
            st.error(f"Could not load {wod_name} details")

        if st.button("🚀 Simulate Workout", type="primary"):
            try:
                with st.spinner(f"Simulating {wod_name}..."):
                    # Get the workout
                    wod = getattr(FamousWODs, wod_name.upper())()

                    # Reset athlete fatigue
                    st.session_state.athlete.reset_fatigue()

                    # Update athlete context and day state
                    st.session_state.athlete.context = st.session_state.context
                    st.session_state.athlete.day_state = st.session_state.day_state

                    # Get strategy
                    strategy = st.session_state.athlete.get_strategy_for_rpe()

                    # Simulate (using legacy simulator for now)
                    result = simulate(wod, st.session_state.athlete, strategy)

                st.success(f"✅ {wod_name} simulation completed!")

                # Display results
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    minutes = int(result.total_time // 60)
                    seconds = int(result.total_time % 60)
                    st.metric("Total Time", f"{minutes}:{seconds:02d}")
                with col2:
                    st.metric("Final Fatigue", f"{result.final_fatigue:.2f}")
                with col3:
                    st.metric("RPE Used", strategy.constraints.target_rpe)
                with col4:
                    st.metric("Strategy", "RPE-Based")

                # Store result
                st.session_state.simulation_results.append({
                    'workout': wod_name,
                    'time_seconds': result.total_time,
                    'time_display': f"{minutes}:{seconds:02d}",
                    'final_fatigue': result.final_fatigue,
                    'rpe': strategy.constraints.target_rpe,
                    'athlete': st.session_state.athlete.name,
                    'conditions': f"{st.session_state.context.temperature_c}°C, {st.session_state.context.humidity_pct}% humidity"
                })

                # Show recent performance
                if result.events:
                    with st.expander("📊 Performance Timeline", expanded=False):
                        events_df = pd.DataFrame([
                            {
                                'Time': event.timestamp,
                                'Event': event.event_type,
                                'Details': f"{event.exercise} - {event.details if hasattr(event, 'details') else ''}"
                            }
                            for event in result.events[-20:]  # Last 20 events
                        ])
                        st.dataframe(events_df, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Simulation error: {str(e)}")
                st.info("💡 This might be due to missing benchmark data or system compatibility.")

    # Show simulation history
    if st.session_state.simulation_results:
        st.subheader("📊 Simulation History")

        # Create results dataframe
        df = pd.DataFrame(st.session_state.simulation_results)

        # Display table
        st.dataframe(df[[
            'workout', 'time_display', 'rpe', 'final_fatigue', 'conditions'
        ]].rename(columns={
            'workout': 'Workout',
            'time_display': 'Time',
            'rpe': 'RPE',
            'final_fatigue': 'Final Fatigue',
            'conditions': 'Conditions'
        }), use_container_width=True)

        # Performance visualization
        if len(df) > 1:
            fig = px.bar(
                df, x='workout', y='time_seconds', color='rpe',
                title="Workout Performance Comparison",
                labels={'time_seconds': 'Time (seconds)', 'workout': 'Workout'}
            )
            st.plotly_chart(fig, use_container_width=True)


def create_strategy_solver_page():
    """Create strategy solver interface for time-based objectives."""
    if not _advanced_features_available:
        st.error("❌ Advanced optimization features not available")
        st.info("The StrategySolver module could not be imported.")
        return

    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("🎯 Strategy Solver")
    st.markdown("Generate optimal strategies to hit specific time targets for workouts.")

    # Workout selection for strategy solving
    col1, col2 = st.columns([2, 1])

    with col1:
        target_workout = st.selectbox(
            "Choose workout for strategy optimization:",
            ["Fran", "Helen", "Grace", "Isabel", "Cindy", "Amanda", "Diane"]
        )

    with col2:
        target_time_input = st.text_input(
            "Target time (mm:ss):",
            placeholder="e.g., 3:30",
            help="Enter your goal time for this workout"
        )

    if target_time_input and st.button("🔍 Generate Strategy", type="primary"):
        try:
            # Parse target time
            if ":" in target_time_input:
                minutes, seconds = target_time_input.split(":")
                target_seconds = int(minutes) * 60 + int(seconds)
            else:
                target_seconds = float(target_time_input)

            with st.spinner(f"Generating strategy for {target_workout} in {target_time_input}..."):
                # Get the workout
                wod = getattr(FamousWODs, target_workout.upper())()

                # Create strategy solver
                solver = StrategySolver(st.session_state.athlete, wod)

                # Generate candidate strategies
                candidates = solver.generate_candidate_strategies()

                # Find strategies that meet target
                solutions = solver.solve_for_time_target(target_seconds, tolerance_seconds=30)

            if solutions:
                st.success(f"✅ Found {len(solutions)} viable strategies!")

                # Display best solution
                best_solution = solutions[0]
                st.markdown(f"### 🏆 Recommended Strategy")

                col1, col2, col3 = st.columns(3)
                with col1:
                    predicted_minutes = int(best_solution.predicted_time // 60)
                    predicted_seconds = int(best_solution.predicted_time % 60)
                    st.metric("Predicted Time", f"{predicted_minutes}:{predicted_seconds:02d}")

                with col2:
                    st.metric("Strategy Type", best_solution.strategy_type.value.replace("_", " ").title())

                with col3:
                    st.metric("Confidence", f"{best_solution.confidence_score:.1%}")

                # Show strategy details
                with st.expander("📋 Strategy Details", expanded=True):
                    st.markdown("**Rep Schemes:**")
                    for i, round_scheme in enumerate(best_solution.rep_schemes):
                        st.markdown(f"**Round {i+1}:**")
                        for rep_scheme in round_scheme:
                            breakdown = " + ".join(map(str, rep_scheme.set_breakdown))
                            rest_info = f"Rest: {rep_scheme.total_rest_time:.0f}s" if rep_scheme.total_rest_time > 0 else "Unbroken"
                            st.text(f"  {rep_scheme.exercise_name}: {breakdown} ({rest_info})")

                # Show all solutions
                if len(solutions) > 1:
                    with st.expander(f"📊 All {len(solutions)} Solutions", expanded=False):
                        solutions_data = []
                        for sol in solutions:
                            pred_time = f"{int(sol.predicted_time//60)}:{int(sol.predicted_time%60):02d}"
                            solutions_data.append({
                                "Strategy Type": sol.strategy_type.value.replace("_", " ").title(),
                                "Predicted Time": pred_time,
                                "Confidence": f"{sol.confidence_score:.1%}",
                                "Total Rest": f"{sum(sum(rs.total_rest_time for rs in round_schemes) for round_schemes in sol.rep_schemes):.0f}s"
                            })

                        df = pd.DataFrame(solutions_data)
                        st.dataframe(df, use_container_width=True)

            else:
                st.warning(f"⚠️ No viable strategies found for {target_time_input}")
                st.info("💡 Try a more realistic target time or adjust your athlete's capabilities.")

        except Exception as e:
            st.error(f"❌ Error generating strategy: {str(e)}")


def create_operational_analysis_page():
    """Create operational what-if analysis interface."""
    if not _advanced_features_available:
        st.error("❌ Advanced optimization features not available")
        st.info("The OperationalAnalyzer module could not be imported.")
        return

    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("🔍 Operational Analysis")
    st.markdown("Analyze how changes in cycle times, transitions, and micro-rest affect performance.")

    # Workout selection
    workout_name = st.selectbox(
        "Choose workout for analysis:",
        ["Fran", "Helen", "Grace", "Isabel", "Amanda", "Diane"]
    )

    # Parameter selection
    st.markdown("### 🎛️ Parameters to Analyze")

    col1, col2 = st.columns(2)

    with col1:
        analyze_cycle_times = st.checkbox("Cycle Times", value=True, help="How faster/slower reps affect performance")
        if analyze_cycle_times:
            cycle_variation = st.slider("Cycle time variation", -50, 50, 0, 5,
                                      format="%d%%", help="% change from baseline")

    with col2:
        analyze_transitions = st.checkbox("Transitions", value=True, help="Time between exercises")
        if analyze_transitions:
            transition_variation = st.slider("Transition time variation", -50, 100, 0, 10,
                                           format="%d%%", help="% change from baseline")

    # Micro-rest analysis
    analyze_microrest = st.checkbox("Micro-Rest Strategy", value=False,
                                   help="Add small rests within exercises")
    if analyze_microrest:
        microrest_duration = st.slider("Micro-rest duration", 5, 30, 10, help="Seconds of rest to add")
        microrest_frequency = st.slider("Micro-rest frequency", 5, 50, 20, help="Reps between micro-rests")

    if st.button("🔍 Run Analysis", type="primary"):
        try:
            with st.spinner(f"Analyzing {workout_name} performance variations..."):
                # Get the workout
                wod = getattr(FamousWODs, workout_name.upper())()

                # Create analyzer
                analyzer = OperationalAnalyzer(st.session_state.athlete, wod)

                # Run analysis based on selected parameters
                results = []

                if analyze_cycle_times:
                    cycle_result = analyzer.analyze_cycle_time_variation(cycle_variation / 100.0)
                    results.append(("Cycle Time", cycle_result))

                if analyze_transitions:
                    transition_result = analyzer.analyze_transition_variation(transition_variation / 100.0)
                    results.append(("Transition", transition_result))

                if analyze_microrest:
                    microrest_result = analyzer.analyze_microrest_strategy(
                        rest_duration_s=microrest_duration,
                        rest_frequency_reps=microrest_frequency
                    )
                    results.append(("Micro-Rest", microrest_result))

            # Display results
            if results:
                st.success("✅ Analysis completed!")

                # Summary metrics
                st.markdown("### 📊 Performance Impact Summary")

                baseline_time = None
                for param_name, result in results:
                    if baseline_time is None and hasattr(result, 'baseline_time'):
                        baseline_time = result.baseline_time

                if baseline_time:
                    baseline_min = int(baseline_time // 60)
                    baseline_sec = int(baseline_time % 60)
                    st.info(f"🎯 Baseline time: {baseline_min}:{baseline_sec:02d}")

                # Results table
                results_data = []
                for param_name, result in results:
                    if hasattr(result, 'modified_time'):
                        time_diff = result.modified_time - baseline_time if baseline_time else 0
                        modified_min = int(result.modified_time // 60)
                        modified_sec = int(result.modified_time % 60)

                        results_data.append({
                            "Parameter": param_name,
                            "Modified Time": f"{modified_min}:{modified_sec:02d}",
                            "Time Difference": f"{time_diff:+.1f}s",
                            "% Change": f"{(time_diff/baseline_time)*100:+.1f}%" if baseline_time else "N/A"
                        })

                if results_data:
                    df = pd.DataFrame(results_data)
                    st.dataframe(df, use_container_width=True)

                    # Visualization
                    if len(results_data) > 1:
                        fig = px.bar(
                            df, x="Parameter", y=[float(x.replace("s", "")) for x in df["Time Difference"]],
                            title="Performance Impact by Parameter",
                            labels={"y": "Time Difference (seconds)"}
                        )
                        st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Analysis error: {str(e)}")


def create_clone_optimization_page():
    """Create clone optimization interface."""
    if not _advanced_features_available:
        st.error("❌ Advanced optimization features not available")
        st.info("The CloneOptimizer module could not be imported.")
        return

    if not st.session_state.athlete:
        st.warning("⚠️ Please create an athlete first in the Athlete Builder.")
        return

    st.subheader("🧬 Clone Optimization")
    st.markdown("Test strategies across variations of your athlete to find robust solutions.")

    # Workout selection
    workout_name = st.selectbox(
        "Choose workout for optimization:",
        ["Fran", "Helen", "Grace", "Isabel", "Amanda", "Diane"]
    )

    # Parameter variations
    st.markdown("### 🔬 Parameter Variations")
    st.markdown("Define how much your capabilities might vary on competition day:")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Strength Variation:**")
        strength_var = st.slider("1RM variation", 0, 20, 10, help="±% variation in strength")

        st.markdown("**Cycle Time Variation:**")
        cycle_var = st.slider("Cycle time variation", 0, 30, 15, help="±% variation in movement speed")

    with col2:
        st.markdown("**Cardio Variation:**")
        cardio_var = st.slider("Cardio capacity variation", 0, 15, 8, help="±% variation in CP/W'")

        st.markdown("**Daily State:**")
        daily_var = st.slider("Daily readiness variation", 0, 20, 12, help="±% variation in daily form")

    # Optimization settings
    st.markdown("### ⚙️ Optimization Settings")

    col1, col2 = st.columns(2)
    with col1:
        target_time_input = st.text_input("Target time (mm:ss):", placeholder="e.g., 4:00")
        num_clones = st.slider("Number of clones", 10, 100, 50, help="More clones = more robust results")

    with col2:
        confidence_level = st.slider("Confidence level", 80, 99, 90, help="% of clones that should hit target")
        max_strategies = st.slider("Max strategies to test", 3, 10, 5)

    if target_time_input and st.button("🚀 Optimize Clones", type="primary"):
        try:
            # Parse target time
            if ":" in target_time_input:
                minutes, seconds = target_time_input.split(":")
                target_seconds = int(minutes) * 60 + int(seconds)
            else:
                target_seconds = float(target_time_input)

            with st.spinner(f"Optimizing {num_clones} clones for {workout_name}..."):
                # Get the workout
                wod = getattr(FamousWODs, workout_name.upper())()

                # Create optimizer
                optimizer = CloneOptimizer(st.session_state.athlete)

                # Define parameter variations
                variations = {
                    'strength': strength_var / 100.0,
                    'cycle_times': cycle_var / 100.0,
                    'cardio': cardio_var / 100.0,
                    'daily_state': daily_var / 100.0
                }

                # Run optimization
                optimization_result = optimizer.optimize_for_target(
                    wod=wod,
                    target_time_s=target_seconds,
                    parameter_variations=variations,
                    num_clones=num_clones,
                    confidence_level=confidence_level / 100.0,
                    max_strategies=max_strategies
                )

            # Display results
            if optimization_result and optimization_result.best_strategy:
                st.success("✅ Clone optimization completed!")

                # Best strategy summary
                st.markdown("### 🏆 Optimal Robust Strategy")

                col1, col2, col3 = st.columns(3)
                with col1:
                    success_rate = optimization_result.success_rate
                    st.metric("Success Rate", f"{success_rate:.1%}")

                with col2:
                    avg_time = optimization_result.average_time
                    avg_min = int(avg_time // 60)
                    avg_sec = int(avg_time % 60)
                    st.metric("Average Time", f"{avg_min}:{avg_sec:02d}")

                with col3:
                    time_std = optimization_result.time_std_dev
                    st.metric("Time Std Dev", f"±{time_std:.1f}s")

                # Strategy details
                with st.expander("📋 Robust Strategy Details", expanded=True):
                    best_strategy = optimization_result.best_strategy
                    st.markdown(f"**Strategy Type:** {best_strategy.strategy_type.value.replace('_', ' ').title()}")

                    # Show rep schemes for each round
                    for i, round_scheme in enumerate(best_strategy.rep_schemes):
                        st.markdown(f"**Round {i+1}:**")
                        for rep_scheme in round_scheme:
                            breakdown = " + ".join(map(str, rep_scheme.set_breakdown))
                            rest_info = f"Rest: {rep_scheme.total_rest_time:.0f}s" if rep_scheme.total_rest_time > 0 else "Unbroken"
                            st.text(f"  {rep_scheme.exercise_name}: {breakdown} ({rest_info})")

                # Performance distribution
                if hasattr(optimization_result, 'performance_distribution'):
                    st.markdown("### 📈 Performance Distribution")

                    times = optimization_result.performance_distribution
                    fig = px.histogram(
                        x=times, nbins=20,
                        title=f"Time Distribution Across {num_clones} Clones",
                        labels={"x": "Time (seconds)", "y": "Count"}
                    )
                    fig.add_vline(x=target_seconds, line_dash="dash", line_color="red",
                                annotation_text="Target")
                    st.plotly_chart(fig, use_container_width=True)

            else:
                st.warning("⚠️ No robust strategy found for the specified parameters")
                st.info("💡 Try adjusting the target time, confidence level, or parameter variations.")

        except Exception as e:
            st.error(f"❌ Optimization error: {str(e)}")


def main():
    """Main application."""
    initialize_session_state()

    # Header
    st.markdown('<h1 class="main-header">🏋️ CrossFit Digital Twin</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <span class="feature-badge">Concrete Parameters</span>
        <span class="feature-badge">RPE Strategies</span>
        <span class="feature-badge">Advanced Fatigue</span>
        <span class="feature-badge">Real Benchmarks</span>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        # Build navigation list with conditional advanced features
        nav_pages = [
            "🏠 Home",
            "👤 Athlete Builder",
            "🌡️ Environment & State",
            "⚡ RPE Strategy",
            "🔋 Fatigue Monitor",
            "🏃 Simulation",
            "📊 Performance Analysis"
        ]

        # Add advanced features if available
        if _advanced_features_available:
            nav_pages.extend([
                "🎯 Strategy Solver",
                "🔍 Operational Analysis",
                "🧬 Clone Optimization"
            ])

        page = st.selectbox("Choose a page:", nav_pages)

        # Show athlete status
        if st.session_state.athlete:
            st.markdown("---")
            st.markdown("### 👤 Current Athlete")
            st.success(f"✅ {st.session_state.athlete.name}")
            st.metric("RPE Intent", st.session_state.day_state.rpe_intended)
        else:
            st.markdown("---")
            st.markdown("### 👤 No Athlete")
            st.info("Create an athlete to get started!")

    # Main content
    if page == "🏠 Home":
        st.markdown("""
        ## Welcome to CrossFit Digital Twin! 🎉

        Transform your CrossFit training with the power of **concrete physiological modeling**.
        No more guessing – use real performance data to optimize your workouts.

        ### 🆕 Revolutionary Features:

        **🎯 Concrete Parameters**
        - Input real 1RM values, not abstract scores
        - Use actual cycle times and unbroken capacities
        - Critical Power/W' models for cardio performance

        **⚡ RPE-Based Strategies**
        - Rate of Perceived Exertion (0-10) drives workout intensity
        - Automatic load and set size constraints
        - Personalized rest periods and pacing

        **🧠 Advanced Fatigue Modeling**
        - W'bal system for cardiovascular fatigue tracking
        - Local muscle fatigue by movement pattern
        - Environmental and daily state effects

        **📊 Comprehensive Benchmarks**
        - All major weightlifting movements
        - Gymnastics max reps and timed cycles
        - Monostructural FTP, rowing, running, swimming
        - Famous CrossFit benchmark times

        ### 🚀 Getting Started:

        1. **👤 Athlete Builder** → Input your real performance benchmarks
        2. **🌡️ Environment & State** → Set conditions and daily readiness
        3. **⚡ RPE Strategy** → Review your personalized strategy
        4. **🏃 Simulation** → Test on famous CrossFit workouts
        5. **🔋 Fatigue Monitor** → Track performance changes

        ---

        ### 📈 Why This Matters:

        Traditional training relies on guesswork. Our system uses:
        - **Real physiological models** from exercise science
        - **Your actual performance data** for accuracy
        - **Adaptive strategies** based on daily readiness
        - **Environmental factors** that affect performance

        **Ready to create your digital twin?** Start with the Athlete Builder! 💪
        """)

    elif page == "👤 Athlete Builder":
        create_benchmark_input_form()

    elif page == "🌡️ Environment & State":
        create_context_day_form()

    elif page == "⚡ RPE Strategy":
        create_rpe_strategy_display()

    elif page == "🔋 Fatigue Monitor":
        create_fatigue_visualization()

    elif page == "🏃 Simulation":
        create_workout_simulation()

    elif page == "📊 Performance Analysis":
        st.subheader("📊 Performance Analysis")

        if st.session_state.simulation_results:
            df = pd.DataFrame(st.session_state.simulation_results)

            # Performance trends
            if len(df) > 1:
                st.markdown("### 📈 Performance Trends")

                # Time comparison by workout
                fig1 = px.bar(
                    df, x='workout', y='time_seconds', color='rpe',
                    title="Workout Times by RPE Level",
                    labels={'time_seconds': 'Time (seconds)', 'workout': 'Workout'}
                )
                st.plotly_chart(fig1, use_container_width=True)

                # Fatigue vs Performance
                fig2 = px.scatter(
                    df, x='final_fatigue', y='time_seconds', color='workout',
                    title="Fatigue vs Performance",
                    labels={'final_fatigue': 'Final Fatigue', 'time_seconds': 'Time (seconds)'}
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Summary statistics
            st.markdown("### 📋 Summary Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                avg_time = df['time_seconds'].mean()
                st.metric("Average Time", f"{int(avg_time//60)}:{int(avg_time%60):02d}")

            with col2:
                avg_rpe = df['rpe'].mean()
                st.metric("Average RPE", f"{avg_rpe:.1f}")

            with col3:
                total_workouts = len(df)
                st.metric("Total Workouts", total_workouts)

        else:
            st.info("🏃 Complete some simulations to see performance analysis!")

    elif page == "🎯 Strategy Solver":
        create_strategy_solver_page()

    elif page == "🔍 Operational Analysis":
        create_operational_analysis_page()

    elif page == "🧬 Clone Optimization":
        create_clone_optimization_page()

    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #666; margin-top: 2rem;">'
        'CrossFit Digital Twin | Powered by Concrete Physiological Modeling | '
        'Transform your training with real data 💪'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
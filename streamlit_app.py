"""
Streamlit web interface for CrossFit Digital Twin.

A user-friendly web application for creating athletes, defining workouts,
testing strategies, and analyzing performance results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any

# Import CrossFit Digital Twin library
from crossfit_twin import Athlete, WOD, simulate
from crossfit_twin.athlete import ContextParams, DayState
from crossfit_twin.workout import FamousWODs, Exercise, Round
from crossfit_twin.strategy import StrategyFactory
from crossfit_twin.utils import (
    AthleteCloneGenerator, PerformanceComparator, ExperimentRunner,
    quick_parameter_test, compare_all_strategies
)


# Page configuration
st.set_page_config(
    page_title="CrossFit Digital Twin",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize session state variables."""
    if 'current_athlete' not in st.session_state:
        st.session_state.current_athlete = None
    if 'current_workout' not in st.session_state:
        st.session_state.current_workout = None
    if 'current_context' not in st.session_state:
        st.session_state.current_context = ContextParams()
    if 'current_day_state' not in st.session_state:
        st.session_state.current_day_state = DayState()
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = []
    if 'experiment_results' not in st.session_state:
        st.session_state.experiment_results = []


def create_athlete_form():
    """Create athlete configuration form with concrete inputs."""
    st.subheader("👤 Athlete Profile")
    
    # A. Intrinsic Profile
    with st.expander("🧍 Profil intrinsèque", expanded=True):
        st.markdown("**Paramètres stables de l'athlète**")
        
        with st.form("intrinsic_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Nom de l'athlète", value="Mon Athlète")
                weight_kg = st.number_input("Poids (kg)", 40.0, 150.0, 78.0, 0.1)
                
                st.write("**Tests de répétitions chronométrées:**")
                t_thr_10 = st.number_input("10 Thrusters @ 20kg (s)", 10.0, 120.0, 20.0, 0.1)
                t_pu_10 = st.number_input("10 Kipping Pull-ups (s)", 5.0, 120.0, 15.0, 0.1)
                t_bur_15 = st.number_input("15 Burpees (s)", 10.0, 300.0, 45.0, 0.1)
                t_wb_15 = st.number_input("15 Wall-balls @ 9kg (s)", 10.0, 300.0, 35.0, 0.1)
            
            with col2:
                experience = st.selectbox(
                    "Niveau d'expérience",
                    ["beginner", "intermediate", "advanced", "elite"],
                    index=1
                )
                
                st.write("**Cardio de référence:**")
                row_2k = st.text_input("2k Row (mm:ss)", "7:30")
                row_5k = st.text_input("5k Row (mm:ss)", "19:30")
                
                st.write("**1RM (ou estimés):**")
                bs_1rm = st.number_input("Back Squat 1RM (kg)", 40.0, 300.0, 150.0, 1.0)
                cj_1rm = st.number_input("Clean & Jerk 1RM (kg)", 30.0, 250.0, 110.0, 1.0)
                sn_1rm = st.number_input("Snatch 1RM (kg)", 20.0, 200.0, 85.0, 1.0)
                
                # Recovery rate as simple slider for now
                recovery_rate = st.slider("Récupération générale", 0, 100, 70, 
                                        help="Capacité générale de récupération (0-100)")
            
            submitted = st.form_submit_button("Créer l'athlète")
            
            if submitted:
                try:
                    # Create athlete from concrete inputs
                    athlete = Athlete.from_concrete_inputs(
                        name=name,
                        weight_kg=weight_kg,
                        row_2k_time=row_2k,
                        row_5k_time=row_5k,
                        t_thr_10=t_thr_10,
                        t_pu_10=t_pu_10,
                        t_bur_15=t_bur_15,
                        t_wb_15=t_wb_15,
                        bs_1rm=bs_1rm,
                        cj_1rm=cj_1rm,
                        sn_1rm=sn_1rm,
                        experience_level=experience,
                        recovery_rate=recovery_rate
                    )
                    
                    st.session_state.current_athlete = athlete
                    st.success(f"✅ Athlète '{name}' créé avec succès!")
                    
                    # Show calculated parameters
                    st.info(f"**Paramètres calculés:** Force: {athlete.strength:.0f}/100, "
                           f"Endurance: {athlete.endurance:.0f}/100, "
                           f"Résistance fatigue: {athlete.fatigue_resistance:.0f}/100")
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erreur lors de la création de l'athlète: {e}")


def create_context_form():
    """Create environmental context form."""
    st.subheader("🌍 Contexte environnemental")
    st.markdown("**Conditions d'entraînement/compétition**")
    
    # Get current values from session state for persistence
    current_ctx = st.session_state.current_context
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        temp = st.number_input(
            "Température (°C)", 
            min_value=-10.0, 
            max_value=45.0, 
            value=current_ctx.temperature_c,
            step=0.1,
            help="Température ambiante",
            key="temp_input"
        )
    
    with col2:
        humidity = st.number_input(
            "Humidité (%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=current_ctx.humidity_pct,
            step=1.0,
            help="Humidité relative",
            key="humidity_input"
        )
    
    with col3:
        altitude = st.number_input(
            "Altitude (m)", 
            min_value=0.0, 
            max_value=4000.0, 
            value=current_ctx.altitude_m,
            step=1.0,
            help="Altitude au-dessus du niveau de la mer",
            key="altitude_input"
        )
    
    # Update context in session state whenever inputs change
    st.session_state.current_context = ContextParams(
        temperature_c=temp,
        humidity_pct=humidity,
        altitude_m=altitude
    )
    
    # Show environmental impact indicators
    from crossfit_twin.athlete import hot_humid_recovery_scale, cardio_drift_scale
    recovery_impact = hot_humid_recovery_scale(temp, humidity)
    cardio_impact = cardio_drift_scale(temp, humidity, altitude)
    
    col1, col2 = st.columns(2)
    with col1:
        impact_color = "🟢" if recovery_impact > 0.9 else "🟡" if recovery_impact > 0.8 else "🔴"
        st.write(f"{impact_color} Impact récupération: {recovery_impact:.1%}")
    with col2:
        cardio_color = "🟢" if cardio_impact < 1.1 else "🟡" if cardio_impact < 1.2 else "🔴"
        st.write(f"{cardio_color} Charge cardio: {cardio_impact:.1%}")


def create_day_state_form():
    """Create daily state form."""
    st.subheader("📅 État du jour")
    st.markdown("**Forme physique du jour**")
    
    # Get current values from session state for persistence
    current_day = st.session_state.current_day_state
    
    col1, col2 = st.columns(2)
    
    with col1:
        sleep_h = st.number_input(
            "Sommeil dernière nuit (h)", 
            min_value=0.0, 
            max_value=12.0, 
            value=current_day.sleep_h,
            step=0.1,
            help="Heures de sommeil",
            key="sleep_h_input"
        )
        sleep_quality = st.slider(
            "Qualité du sommeil", 
            min_value=1, 
            max_value=5, 
            value=current_day.sleep_quality,
            help="1=Très mauvais, 5=Excellent",
            key="sleep_quality_input"
        )
    
    with col2:
        water_l = st.number_input(
            "Eau bue depuis réveil (L)", 
            min_value=0.0, 
            max_value=8.0, 
            value=current_day.water_l,
            step=0.1,
            help="Litres d'eau consommés",
            key="water_input"
        )
        
        # Use athlete weight as default if available, otherwise use current day state
        default_weight = (
            st.session_state.current_athlete.weight_kg 
            if st.session_state.current_athlete 
            else current_day.body_mass_kg
        )
        mass_day = st.number_input(
            "Poids du jour (kg)", 
            min_value=40.0, 
            max_value=150.0, 
            value=default_weight,
            step=0.1,
            help="Poids actuel",
            key="mass_day_input"
        )
    
    # Update day state in session state whenever inputs change
    st.session_state.current_day_state = DayState(
        sleep_h=sleep_h,
        sleep_quality=sleep_quality,
        water_l=water_l,
        body_mass_kg=mass_day
    )
    
    # Show daily state impact indicators
    from crossfit_twin.athlete import freshness_factor, hydration_factor
    current_ctx = st.session_state.current_context
    fresh_impact = freshness_factor(sleep_h, sleep_quality)
    hydration_impact = hydration_factor(water_l, mass_day, current_ctx.temperature_c)
    
    col1, col2 = st.columns(2)
    with col1:
        fresh_color = "🟢" if fresh_impact > 0.95 else "🟡" if fresh_impact > 0.85 else "🔴"
        st.write(f"{fresh_color} Fraîcheur: {fresh_impact:.1%}")
    with col2:
        hydro_color = "🟢" if hydration_impact > 0.95 else "🟡" if hydration_impact > 0.85 else "🔴"
        st.write(f"{hydro_color} Hydratation: {hydration_impact:.1%}")


def display_athlete_stats():
    """Display current athlete statistics and environmental factors."""
    if st.session_state.current_athlete:
        athlete = st.session_state.current_athlete
        ctx = st.session_state.current_context
        day = st.session_state.current_day_state
        
        st.subheader(f"📊 {athlete.name} - Résumé complet")
        
        # Derived stats (calculated from concrete inputs)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Force", f"{athlete.strength:.0f}/100", help="Calculé depuis les 1RM")
            st.metric("Poids", f"{athlete.weight_kg:.0f} kg")
        
        with col2:
            st.metric("Endurance", f"{athlete.endurance:.0f}/100", help="Calculé depuis 2k/5k row")
            st.metric("Expérience", athlete.experience_level.title())
        
        with col3:
            st.metric("Résistance fatigue", f"{athlete.fatigue_resistance:.0f}/100", help="Calculé depuis W' critique")
            
        with col4:
            st.metric("Récupération", f"{athlete.recovery_rate:.0f}/100", help="Calculé depuis profil athlète")
        
        # Current environmental and daily summary
        st.write("**🌍 Conditions actuelles:**")
        st.write(f"🌡️ {ctx.temperature_c:.1f}°C, 💧 {ctx.humidity_pct:.0f}% HR, ⛰️ {ctx.altitude_m:.0f}m")
        st.write(f"😴 {day.sleep_h:.1f}h sommeil (qualité: {day.sleep_quality}/5), 💧 {day.water_l:.1f}L, ⚖️ {day.body_mass_kg:.1f}kg")
        
        # Performance indicators with context
        with st.expander("📈 Indicateurs de performance", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**💪 1RM principaux:**")
                key_lifts = ["back-squat", "clean", "snatch", "thruster"]
                for lift in key_lifts:
                    if lift in athlete.max_lifts:
                        ratio = athlete.max_lifts[lift] / athlete.weight_kg
                        st.write(f"• {lift.replace('-', ' ').title()}: {athlete.max_lifts[lift]:.0f}kg ({ratio:.1f}x BW)")
            
            with col2:
                st.write("**⏱️ Temps de base (par rep):**")
                key_exercises = ["thruster", "pull-up", "burpee", "wall-ball"]
                for ex in key_exercises:
                    if ex in athlete.base_pace:
                        st.write(f"• {ex.replace('-', ' ').title()}: {athlete.base_pace[ex]:.1f}s")
                        
            # Show row performance
            st.write("**🚣 Performances cardio:**")
            if hasattr(athlete, '_row_2k_time') and athlete._row_2k_time:
                st.write(f"• 2k Row: {athlete._row_2k_time}")
            if hasattr(athlete, '_row_5k_time') and athlete._row_5k_time:
                st.write(f"• 5k Row: {athlete._row_5k_time}")


def create_workout_selection():
    """Create workout selection interface."""
    st.subheader("🏋️ Workout Selection")
    
    workout_type = st.radio(
        "Choose workout type:",
        ["Famous WODs", "Custom Workout"],
        horizontal=True
    )
    
    if workout_type == "Famous WODs":
        famous_wods = {
            "Fran": "21-15-9 Thrusters (42.5kg) and Pull-ups",
            "Helen": "3 rounds: 400m Run, 21 KB Swings (24kg), 12 Pull-ups",
            "Cindy": "AMRAP 20 min: 5 Pull-ups, 10 Push-ups, 15 Air Squats"
        }
        
        selected_wod = st.selectbox(
            "Select a famous WOD:",
            list(famous_wods.keys()),
            format_func=lambda x: f"{x} - {famous_wods[x]}"
        )
        
        if st.button("Load WOD"):
            if selected_wod == "Fran":
                workout = FamousWODs.fran()
            elif selected_wod == "Helen":
                workout = FamousWODs.helen()
            elif selected_wod == "Cindy":
                workout = FamousWODs.cindy()
            
            st.session_state.current_workout = workout
            st.success(f"✅ Loaded {selected_wod}")
            st.rerun()
    
    else:  # Custom Workout
        with st.form("custom_workout_form"):
            workout_name = st.text_input("Workout Name", "My Custom WOD")
            
            workout_format = st.selectbox(
                "Workout Format",
                ["For Time", "AMRAP"],
                help="For Time: Complete all work as fast as possible. AMRAP: As many rounds as possible in time limit."
            )
            
            if workout_format == "AMRAP":
                time_cap_minutes = st.number_input("Time Cap (minutes)", 1, 60, 20)
            else:
                time_cap_minutes = st.number_input("Time Cap (minutes)", 0, 60, 0, help="Leave 0 for no time cap")
            
            st.write("**Exercises:**")
            num_exercises = st.number_input("Number of exercises", 1, 10, 2)
            
            exercises = []
            for i in range(num_exercises):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    exercise_name = st.text_input(f"Exercise {i+1}", f"exercise-{i+1}", key=f"ex_name_{i}")
                
                with col2:
                    reps = st.number_input(f"Reps {i+1}", 1, 200, 10, key=f"ex_reps_{i}")
                
                with col3:
                    weight = st.number_input(f"Weight (kg) {i+1}", 0, 200, 0, key=f"ex_weight_{i}")
                
                exercises.append((exercise_name, reps, weight if weight > 0 else None))
            
            submitted = st.form_submit_button("Create Custom WOD")
            
            if submitted:
                time_cap_seconds = time_cap_minutes * 60 if time_cap_minutes > 0 else None
                
                if workout_format == "AMRAP":
                    workout = WOD.amrap(
                        name=workout_name,
                        time_cap_seconds=time_cap_minutes * 60,
                        exercises=exercises
                    )
                else:
                    workout = WOD.for_time(
                        name=workout_name,
                        exercises=exercises,
                        time_cap_seconds=time_cap_seconds
                    )
                
                st.session_state.current_workout = workout
                st.success(f"✅ Created custom WOD '{workout_name}'")
                st.rerun()


def display_current_workout():
    """Display current workout details."""
    if st.session_state.current_workout:
        workout = st.session_state.current_workout
        
        st.subheader(f"🎯 Current Workout: {workout.name}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Type:** {workout.workout_type.value.replace('_', ' ').title()}")
            if workout.time_cap_seconds:
                st.write(f"**Time Cap:** {workout.time_cap_seconds/60:.0f} minutes")
            
            st.write("**Structure:**")
            for i, round_obj in enumerate(workout.rounds):
                st.write(f"Round {i+1}: {round_obj}")
        
        with col2:
            total_exercises = workout.get_total_exercises()
            st.metric("Total Exercises", total_exercises)
            
            if workout.workout_type.value == "for_time":
                try:
                    total_reps = workout.get_total_reps()
                    st.metric("Total Reps", total_reps)
                except:
                    st.metric("Total Reps", "N/A")


def create_strategy_selection():
    """Create strategy selection interface."""
    st.subheader("🎯 Strategy Selection")
    
    strategy_type = st.selectbox(
        "Choose pacing strategy:",
        ["Unbroken", "Fractioned", "Descending", "Conservative", "Custom"],
        help="Different approaches to pacing during the workout"
    )
    
    if strategy_type == "Unbroken":
        fatigue_threshold = st.slider(
            "Fatigue Threshold", 0.5, 1.0, 0.9, 0.05,
            help="Only rest when fatigue exceeds this level"
        )
        strategy = StrategyFactory.unbroken(fatigue_threshold)
        
    elif strategy_type == "Fractioned":
        st.write("**Rest Patterns (reps before rest, rest duration in seconds):**")
        
        # Common exercises
        exercises = ["thruster", "pull-up", "burpee", "wall-ball", "kettlebell-swing"]
        patterns = {}
        
        for exercise in exercises:
            col1, col2 = st.columns(2)
            with col1:
                reps_before = st.number_input(f"{exercise.title()} - Reps before rest", 1, 50, 5, key=f"frac_{exercise}_reps")
            with col2:
                rest_duration = st.number_input(f"{exercise.title()} - Rest duration (s)", 0.0, 30.0, 3.0, key=f"frac_{exercise}_rest")
            
            patterns[exercise] = (reps_before, rest_duration)
        
        strategy = StrategyFactory.fractioned(patterns)
        
    elif strategy_type == "Descending":
        fatigue_threshold = st.slider(
            "Fatigue Threshold", 0.5, 1.0, 0.75, 0.05,
            help="Rest when fatigue exceeds this level"
        )
        strategy = StrategyFactory.descending(fatigue_threshold)
        
    elif strategy_type == "Conservative":
        fatigue_threshold = st.slider(
            "Fatigue Threshold", 0.3, 0.8, 0.6, 0.05,
            help="Rest proactively at this fatigue level"
        )
        strategy = StrategyFactory.conservative(fatigue_threshold=fatigue_threshold)
        
    else:  # Custom
        st.info("Custom strategy builder coming soon!")
        strategy = StrategyFactory.descending()
    
    return strategy


def run_simulation():
    """Run workout simulation with context and day state."""
    if not st.session_state.current_athlete:
        st.error("Please create an athlete first!")
        return
    
    if not st.session_state.current_workout:
        st.error("Please select a workout first!")
        return
    
    strategy = create_strategy_selection()
    
    # Show performance preview with current conditions
    st.write("**🎯 Aperçu des conditions actuelles:**")
    ctx = st.session_state.current_context
    day = st.session_state.current_day_state
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"🌡️ {ctx.temperature_c:.1f}°C")
    with col2:
        st.write(f"😴 {day.sleep_h:.1f}h sommeil")
    with col3:
        st.write(f"💧 {day.water_l:.1f}L hydratation")
    
    if st.button("🚀 Run Simulation", type="primary"):
        with st.spinner("Running simulation..."):
            # Create a copy of the athlete with current context/day state
            athlete_copy = st.session_state.current_athlete.clone(name=f"{st.session_state.current_athlete.name}_sim")
            
            # Set context and day state for simulation
            athlete_copy.set_simulation_context(ctx, day)
            
            result = simulate(
                st.session_state.current_workout,
                athlete_copy,
                strategy,
                verbose=False
            )
            
            st.session_state.simulation_results.append(result)
            
            # Display result
            st.success("✅ Simulation completed!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Time", f"{result.total_time:.1f}s ({result.total_time/60:.1f} min)")
                st.metric("Status", "✅ Completed" if result.completed else "❌ Time Cap")
            
            with col2:
                st.metric("Total Reps", result.total_reps)
                st.metric("Final Fatigue", f"{result.final_fatigue:.2f}")
            
            # Detailed results
            with st.expander("📊 Detailed Results"):
                st.text(result.get_summary())
            
            # Performance chart
            if result.round_results:
                create_performance_chart(result)


def create_performance_chart(result):
    """Create performance visualization chart."""
    if not result.round_results:
        return
    
    # Round times chart
    round_data = pd.DataFrame([
        {
            "Round": r.round_number,
            "Duration (s)": r.duration,
            "Pace (s/rep)": r.pace_per_rep,
            "Max Fatigue": r.max_fatigue
        }
        for r in result.round_results
    ])
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["Round Times", "Pace per Rep", "Fatigue Progression", "Cumulative Time"],
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Round times
    fig.add_trace(
        go.Bar(x=round_data["Round"], y=round_data["Duration (s)"], name="Round Time"),
        row=1, col=1
    )
    
    # Pace per rep
    fig.add_trace(
        go.Scatter(x=round_data["Round"], y=round_data["Pace (s/rep)"], mode="lines+markers", name="Pace"),
        row=1, col=2
    )
    
    # Fatigue progression
    if result.fatigue_curve:
        fatigue_df = pd.DataFrame(result.fatigue_curve, columns=["Time", "Fatigue"])
        fig.add_trace(
            go.Scatter(x=fatigue_df["Time"], y=fatigue_df["Fatigue"], mode="lines", name="Fatigue"),
            row=2, col=1
        )
    
    # Cumulative time
    cumulative_time = np.cumsum([0] + [r.duration for r in result.round_results])
    fig.add_trace(
        go.Scatter(x=list(range(len(cumulative_time))), y=cumulative_time, mode="lines+markers", name="Cumulative"),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False, title_text="Performance Analysis")
    st.plotly_chart(fig, use_container_width=True)


def parameter_experiment_tab():
    """Tab for running parameter experiments."""
    st.header("🧪 Parameter Experiments")
    
    if not st.session_state.current_athlete or not st.session_state.current_workout:
        st.warning("Please create an athlete and select a workout first!")
        return
    
    experiment_type = st.selectbox(
        "Experiment Type",
        ["Single Parameter Test", "Strategy Comparison", "Multi-Parameter Sweep"]
    )
    
    if experiment_type == "Single Parameter Test":
        parameter = st.selectbox(
            "Parameter to test",
            ["strength", "endurance", "fatigue_resistance", "recovery_rate", "weight_kg"]
        )
        
        col1, col2 = st.columns(2)
        with col1:
            min_pct = st.number_input("Min % change", -50, 50, -20)
        with col2:
            max_pct = st.number_input("Max % change", -50, 50, 20)
        
        steps = st.number_input("Number of test points", 3, 10, 5)
        
        if st.button("Run Parameter Test"):
            with st.spinner("Running parameter experiment..."):
                strategy = StrategyFactory.descending()
                analysis = quick_parameter_test(
                    st.session_state.current_athlete,
                    st.session_state.current_workout,
                    strategy,
                    parameter,
                    (min_pct, max_pct),
                    steps
                )
                
                if "error" not in analysis:
                    st.success("✅ Parameter test completed!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Base Value", f"{analysis['base_value']:.1f}")
                        st.metric("Optimal Value", f"{analysis['optimal_value']:.1f}")
                    
                    with col2:
                        st.metric("Optimal Time", f"{analysis['optimal_performance']:.1f}s")
                        st.metric("Performance Range", f"{analysis['performance_range']:.1f}s")
                    
                    # Create chart
                    df = pd.DataFrame(analysis['data_points'], columns=[parameter.title(), 'Time (s)'])
                    fig = px.line(df, x=parameter.title(), y='Time (s)', 
                                  title=f"Impact of {parameter.title()} on Performance")
                    fig.add_vline(x=analysis['optimal_value'], line_dash="dash", line_color="green")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(analysis["error"])
    
    elif experiment_type == "Strategy Comparison":
        if st.button("Compare All Strategies"):
            with st.spinner("Comparing strategies..."):
                results = compare_all_strategies(
                    st.session_state.current_athlete,
                    st.session_state.current_workout
                )
                
                st.success("✅ Strategy comparison completed!")
                
                df = pd.DataFrame(results, columns=["Strategy", "Time (s)", "Completed"])
                df["Status"] = df["Completed"].apply(lambda x: "✅" if x else "❌")
                
                st.dataframe(df[["Strategy", "Time (s)", "Status"]], hide_index=True)
                
                # Chart
                completed_df = df[df["Completed"]]
                if not completed_df.empty:
                    fig = px.bar(completed_df, x="Strategy", y="Time (s)", 
                                title="Strategy Performance Comparison")
                    st.plotly_chart(fig, use_container_width=True)


def results_history_tab():
    """Tab for viewing simulation results history."""
    st.header("📈 Results History")
    
    if not st.session_state.simulation_results:
        st.info("No simulation results yet. Run some simulations first!")
        return
    
    # Results table
    results_data = []
    for i, result in enumerate(st.session_state.simulation_results):
        results_data.append({
            "Simulation": i + 1,
            "Athlete": result.athlete_name,
            "Workout": result.workout_name,
            "Strategy": result.strategy_name,
            "Time (s)": result.total_time,
            "Completed": "✅" if result.completed else "❌",
            "Reps": result.total_reps,
            "Final Fatigue": result.final_fatigue
        })
    
    df = pd.DataFrame(results_data)
    st.dataframe(df, hide_index=True)
    
    # Performance comparison chart
    if len(results_data) > 1:
        fig = px.bar(df, x="Simulation", y="Time (s)", color="Strategy",
                     title="Simulation Results Comparison",
                     hover_data=["Athlete", "Workout"])
        st.plotly_chart(fig, use_container_width=True)
    
    # Clear results button
    if st.button("Clear Results History"):
        st.session_state.simulation_results = []
        st.rerun()


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Title and description
    st.title("🏋️ CrossFit Digital Twin")
    st.markdown("""
    **Optimize your CrossFit performance with data-driven pacing strategies.**
    
    Create digital twins of athletes, test different pacing strategies, and find optimal approaches for any WOD.
    """)
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        
        # Current athlete status
        if st.session_state.current_athlete:
            st.success(f"👤 **Athlete:** {st.session_state.current_athlete.name}")
        else:
            st.warning("👤 **No athlete created**")
        
        # Current workout status
        if st.session_state.current_workout:
            st.success(f"🎯 **Workout:** {st.session_state.current_workout.name}")
        else:
            st.warning("🎯 **No workout selected**")
        
        st.divider()
        
        # Quick actions
        if st.button("🆕 Reset All"):
            st.session_state.current_athlete = None
            st.session_state.current_workout = None
            st.session_state.simulation_results = []
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏃 Simulation", "🧪 Experiments", "📈 Results", "ℹ️ About"])
    
    with tab1:
        # Three separate components in their own sections
        col1, col2 = st.columns([1, 1])
        
        with col1:
            create_athlete_form()
            display_athlete_stats()
        
        with col2:
            create_workout_selection()
            display_current_workout()
        
        st.divider()
        
        # Environmental context and daily state as separate sections
        col1, col2 = st.columns([1, 1])
        
        with col1:
            create_context_form()
        
        with col2:
            create_day_state_form()
            
        st.divider()
        run_simulation()
    
    with tab2:
        parameter_experiment_tab()
    
    with tab3:
        results_history_tab()
    
    with tab4:
        st.header("ℹ️ About CrossFit Digital Twin")
        st.markdown("""
        ### What is this?
        CrossFit Digital Twin is a simulation tool that creates virtual athletes to test pacing strategies for CrossFit workouts.
        
        ### How it works:
        1. **Create an Athlete**: Define physical parameters like strength, endurance, and fatigue resistance
        2. **Select a Workout**: Choose from famous WODs or create custom workouts
        3. **Choose a Strategy**: Pick how to pace the workout (unbroken, fractioned, etc.)
        4. **Simulate**: Run the simulation to see predicted performance
        5. **Optimize**: Test different parameters and strategies to find the best approach
        
        ### Key Features:
        - **Realistic Fatigue Modeling**: Accounts for fatigue accumulation and recovery
        - **Multiple Strategies**: Test different pacing approaches
        - **Parameter Experiments**: See how changes in athlete attributes affect performance
        - **Famous WODs**: Pre-loaded with benchmark CrossFit workouts
        - **Custom Workouts**: Create your own workout simulations
        
        ### Use Cases:
        - **Athletes**: Optimize pacing strategies for competitions
        - **Coaches**: Test different approaches for their athletes
        - **Programmers**: Understand workout intensity and volume effects
        - **Researchers**: Study CrossFit performance factors
        
        **Built with:** Python, Streamlit, Plotly
        """)


if __name__ == "__main__":
    main()
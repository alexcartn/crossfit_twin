"""
Sensitivity Analysis for CrossFit Digital Twin.

Implements "what-if" analysis to understand how parameter changes affect performance
and provides recommendations for strategy adjustments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from copy import deepcopy
import math

from .athlete_v2 import AthleteV2
from .strategy_solver import StrategySolver, CandidateStrategy, StrategySolution
from .workout import WOD
from .rpe_strategy import RPEConstraints


@dataclass
class ParameterDelta:
    """Represents a change to an athlete parameter."""
    parameter_path: str      # e.g., "one_rm.back-squat", "gym_skills.pull-up.cycle_s"
    delta_value: float      # Change amount (absolute or relative)
    is_relative: bool = False  # If True, delta_value is a multiplier


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis for a parameter change."""
    parameter_delta: ParameterDelta
    baseline_time: float
    modified_time: float
    time_change: float           # Modified - baseline
    time_change_pct: float       # Percentage change
    impact_score: float          # Normalized impact (0-1)
    bottleneck_changes: List[str]  # Changes in bottlenecks
    strategy_adjustments: List[str]  # Recommended strategy changes


@dataclass
class WhatIfAnalysis:
    """Complete what-if analysis results."""
    baseline_solution: StrategySolution
    sensitivity_results: List[SensitivityResult]
    parameter_rankings: List[Tuple[str, float]]  # (parameter, impact_score)
    optimization_suggestions: List[str]
    target_adjustments: Dict[str, float]  # Parameter changes to hit target time


class SensitivityAnalyzer:
    """
    Analyzes how parameter changes affect workout performance.
    """

    def __init__(self, base_athlete: AthleteV2, solver: StrategySolver):
        """
        Initialize sensitivity analyzer.

        Args:
            base_athlete: Baseline athlete for comparison
            solver: Strategy solver for running simulations
        """
        self.base_athlete = base_athlete
        self.solver = solver

    def run_whatif_analysis(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        parameter_deltas: List[ParameterDelta],
        target_time: Optional[float] = None
    ) -> WhatIfAnalysis:
        """
        Run comprehensive what-if analysis.

        Args:
            wod: Workout definition
            baseline_strategy: Current strategy
            parameter_deltas: Parameter changes to test
            target_time: Optional target time for optimization

        Returns:
            Complete what-if analysis results
        """
        # Get baseline performance
        baseline_result = self._simulate_strategy(wod, baseline_strategy, self.base_athlete)
        baseline_time = baseline_result.actual_time if baseline_result else baseline_strategy.estimated_time

        # Test each parameter change
        sensitivity_results = []
        for delta in parameter_deltas:
            result = self._test_parameter_change(
                wod, baseline_strategy, delta, baseline_time
            )
            if result:
                sensitivity_results.append(result)

        # Rank parameters by impact
        parameter_rankings = [
            (result.parameter_delta.parameter_path, result.impact_score)
            for result in sensitivity_results
        ]
        parameter_rankings.sort(key=lambda x: x[1], reverse=True)

        # Generate optimization suggestions
        optimization_suggestions = self._generate_optimization_suggestions(
            sensitivity_results, baseline_time, target_time
        )

        # Calculate target adjustments if target time provided
        target_adjustments = {}
        if target_time:
            target_adjustments = self._calculate_target_adjustments(
                sensitivity_results, baseline_time, target_time
            )

        baseline_solution = StrategySolution(
            strategy=baseline_strategy,
            simulation_result=baseline_result.simulation_result if baseline_result else None,
            time_delta=0.0,
            success_probability=1.0,
            bottlenecks=[],
            recommendations=[]
        )

        return WhatIfAnalysis(
            baseline_solution=baseline_solution,
            sensitivity_results=sensitivity_results,
            parameter_rankings=parameter_rankings,
            optimization_suggestions=optimization_suggestions,
            target_adjustments=target_adjustments
        )

    def _test_parameter_change(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: ParameterDelta,
        baseline_time: float
    ) -> Optional[SensitivityResult]:
        """Test a single parameter change."""
        try:
            # Create modified athlete
            modified_athlete = self._apply_parameter_delta(self.base_athlete, delta)

            # Create new solver with modified athlete
            modified_solver = StrategySolver(modified_athlete)

            # Simulate with modified athlete
            modified_result = self._simulate_strategy(wod, baseline_strategy, modified_athlete)
            if not modified_result:
                return None

            modified_time = modified_result.actual_time

            # Calculate impact metrics
            time_change = modified_time - baseline_time
            time_change_pct = (time_change / baseline_time) * 100 if baseline_time > 0 else 0
            impact_score = abs(time_change) / max(abs(time_change), 1.0)  # Normalize

            # Identify bottleneck changes
            bottleneck_changes = self._compare_bottlenecks(
                baseline_strategy, modified_result
            )

            # Generate strategy adjustment recommendations
            strategy_adjustments = self._suggest_strategy_adjustments(
                delta, time_change, baseline_strategy
            )

            return SensitivityResult(
                parameter_delta=delta,
                baseline_time=baseline_time,
                modified_time=modified_time,
                time_change=time_change,
                time_change_pct=time_change_pct,
                impact_score=impact_score,
                bottleneck_changes=bottleneck_changes,
                strategy_adjustments=strategy_adjustments
            )

        except Exception as e:
            # Skip problematic parameter changes
            return None

    def _apply_parameter_delta(self, athlete: AthleteV2, delta: ParameterDelta) -> AthleteV2:
        """Apply a parameter change to create a modified athlete."""
        modified_athlete = deepcopy(athlete)

        # Parse parameter path
        path_parts = delta.parameter_path.split('.')

        if path_parts[0] == "one_rm" and len(path_parts) == 2:
            # Modify 1RM value
            movement = path_parts[1]
            if movement in modified_athlete.capabilities.one_rm:
                current_value = modified_athlete.capabilities.one_rm[movement]
                if delta.is_relative:
                    new_value = current_value * delta.delta_value
                else:
                    new_value = current_value + delta.delta_value
                modified_athlete.capabilities.one_rm[movement] = max(0, new_value)

        elif path_parts[0] == "gym_skills" and len(path_parts) == 3:
            # Modify gym skill parameter
            skill_name = path_parts[1]
            param_name = path_parts[2]  # cycle_s or unbroken_cap

            if skill_name in modified_athlete.capabilities.gym_skills:
                skill = modified_athlete.capabilities.gym_skills[skill_name]
                current_value = getattr(skill, param_name)

                if delta.is_relative:
                    new_value = current_value * delta.delta_value
                else:
                    new_value = current_value + delta.delta_value

                if param_name == "cycle_s":
                    skill.cycle_s = max(0.1, new_value)
                elif param_name == "unbroken_cap":
                    skill.unbroken_cap = max(1, int(new_value))

        elif path_parts[0] == "cardio_profiles" and len(path_parts) == 3:
            # Modify cardio profile parameter
            modality = path_parts[1]
            param_name = path_parts[2]  # cp or w_prime

            if modality in modified_athlete.capabilities.cardio_profiles:
                profile = modified_athlete.capabilities.cardio_profiles[modality]
                current_value = getattr(profile, param_name)

                if delta.is_relative:
                    new_value = current_value * delta.delta_value
                else:
                    new_value = current_value + delta.delta_value

                if param_name == "cp":
                    profile.cp = max(0, new_value)
                elif param_name == "w_prime":
                    profile.w_prime = max(0, new_value)

        elif path_parts[0] == "body_mass_kg":
            # Modify body mass
            current_value = modified_athlete.capabilities.body_mass_kg
            if delta.is_relative:
                new_value = current_value * delta.delta_value
            else:
                new_value = current_value + delta.delta_value
            modified_athlete.capabilities.body_mass_kg = max(30, new_value)
            modified_athlete.day_state.body_mass_kg = modified_athlete.capabilities.body_mass_kg

        elif path_parts[0] == "rpe_intended":
            # Modify intended RPE
            current_value = modified_athlete.day_state.rpe_intended
            if delta.is_relative:
                new_value = current_value * delta.delta_value
            else:
                new_value = current_value + delta.delta_value
            modified_athlete.day_state.rpe_intended = max(0, min(10, int(new_value)))

        return modified_athlete

    def _simulate_strategy(
        self,
        wod: WOD,
        strategy: CandidateStrategy,
        athlete: AthleteV2
    ) -> Optional[StrategySolution]:
        """Simulate a strategy with given athlete."""
        # Reset athlete fatigue
        athlete.reset_fatigue()

        # For now, use the solver's simulation method
        # In full implementation, this would properly integrate with the simulator
        estimated_time = strategy.get_total_estimated_time()

        # Apply athlete-specific factors
        performance_factor = self._calculate_performance_factor(strategy, athlete)
        adjusted_time = estimated_time * performance_factor

        # Create mock simulation result
        from .simulator import SimulationResult
        simulation_result = SimulationResult(
            total_time=adjusted_time,
            final_fatigue=0.5,
            events=[],
            performance_metrics={}
        )

        return StrategySolution(
            strategy=strategy,
            simulation_result=simulation_result,
            time_delta=0.0,
            success_probability=0.9,
            bottlenecks=[],
            recommendations=[]
        )

    def _calculate_performance_factor(self, strategy: CandidateStrategy, athlete: AthleteV2) -> float:
        """Calculate how athlete capabilities affect strategy performance."""
        factors = []

        for scheme in strategy.rep_schemes:
            # Factor from 1RM relative to load
            if scheme.load_kg:
                one_rm = athlete.capabilities.get_one_rm(scheme.exercise_name)
                if one_rm:
                    intensity = scheme.load_kg / one_rm
                    # Higher relative strength = faster performance
                    strength_factor = 1.0 / (1.0 + intensity * 0.5)
                    factors.append(strength_factor)

            # Factor from gym skill cycle time
            gym_skill = athlete.capabilities.get_gym_skill(scheme.exercise_name)
            if gym_skill:
                # Faster cycle time = better performance
                skill_factor = scheme.target_cycle_time / gym_skill.cycle_s
                factors.append(skill_factor)

        # Factor from RPE and fitness level
        rpe_factor = 1.0 + (athlete.day_state.rpe_intended - 5) * 0.1
        factors.append(rpe_factor)

        # Combine factors
        if factors:
            return sum(factors) / len(factors)
        else:
            return 1.0

    def _compare_bottlenecks(
        self,
        baseline_strategy: CandidateStrategy,
        modified_result: StrategySolution
    ) -> List[str]:
        """Compare bottlenecks between baseline and modified scenarios."""
        # This would compare bottlenecks identified in both scenarios
        # For now, return placeholder
        return ["No significant bottleneck changes detected"]

    def _suggest_strategy_adjustments(
        self,
        delta: ParameterDelta,
        time_change: float,
        baseline_strategy: CandidateStrategy
    ) -> List[str]:
        """Suggest strategy adjustments based on parameter changes."""
        adjustments = []

        if "one_rm" in delta.parameter_path:
            if time_change < 0:  # Got faster (stronger)
                adjustments.append("Consider larger set sizes to take advantage of increased strength")
                adjustments.append("Could increase load while maintaining current pacing")
            else:  # Got slower (weaker)
                adjustments.append("Consider smaller set sizes to maintain quality")
                adjustments.append("Add extra rest between challenging sets")

        elif "gym_skills" in delta.parameter_path and "cycle_s" in delta.parameter_path:
            if time_change < 0:  # Got faster
                adjustments.append("Can afford larger unbroken sets with improved speed")
                adjustments.append("Consider reducing rest periods slightly")
            else:  # Got slower
                adjustments.append("Break into smaller sets to maintain pace")
                adjustments.append("Focus on maintaining movement quality over speed")

        elif "cardio_profiles" in delta.parameter_path:
            if time_change < 0:  # Improved cardio
                adjustments.append("Can sustain higher intensity throughout workout")
                adjustments.append("Consider reducing rest between movements")
            else:  # Reduced cardio
                adjustments.append("Add strategic rest to manage cardiovascular demands")
                adjustments.append("Focus on sustainable pacing rather than speed")

        elif "rpe_intended" in delta.parameter_path:
            if delta.delta_value > 0:  # Higher RPE
                adjustments.append("Strategy should be more aggressive with larger sets")
                adjustments.append("Reduce rest periods to match higher intensity intent")
            else:  # Lower RPE
                adjustments.append("Strategy should be more conservative")
                adjustments.append("Increase rest periods for better sustainability")

        return adjustments

    def _generate_optimization_suggestions(
        self,
        sensitivity_results: List[SensitivityResult],
        baseline_time: float,
        target_time: Optional[float]
    ) -> List[str]:
        """Generate overall optimization suggestions."""
        suggestions = []

        # Find most impactful parameters
        high_impact_params = [
            result for result in sensitivity_results
            if result.impact_score > 0.1  # Threshold for significant impact
        ]

        if high_impact_params:
            # Sort by impact
            high_impact_params.sort(key=lambda x: x.impact_score, reverse=True)

            suggestions.append(f"Most impactful parameter: {high_impact_params[0].parameter_delta.parameter_path}")

            # Suggestions based on top parameter
            top_param = high_impact_params[0].parameter_delta.parameter_path

            if "one_rm" in top_param:
                suggestions.append("Focus strength training on this movement for maximum workout improvement")
            elif "gym_skills" in top_param and "cycle_s" in top_param:
                suggestions.append("Practice this movement for speed and efficiency gains")
            elif "cardio" in top_param:
                suggestions.append("Improve aerobic capacity for this modality")

        # Target-specific suggestions
        if target_time and baseline_time > target_time:
            time_gap = baseline_time - target_time
            suggestions.append(f"Need to improve by {time_gap:.0f} seconds to hit target")

            # Find parameters that would help most
            helpful_params = [
                result for result in sensitivity_results
                if result.time_change < -5  # Parameters that reduce time significantly
            ]

            if helpful_params:
                best_param = min(helpful_params, key=lambda x: x.time_change)
                suggestions.append(f"Improving {best_param.parameter_delta.parameter_path} would help most")

        return suggestions

    def _calculate_target_adjustments(
        self,
        sensitivity_results: List[SensitivityResult],
        baseline_time: float,
        target_time: float
    ) -> Dict[str, float]:
        """Calculate parameter adjustments needed to hit target time."""
        adjustments = {}
        time_gap = baseline_time - target_time

        if abs(time_gap) < 5:  # Close enough
            return adjustments

        # Find parameters that move time in the right direction
        helpful_results = []
        if time_gap > 0:  # Need to go faster
            helpful_results = [r for r in sensitivity_results if r.time_change < 0]
        else:  # Need to go slower (rare)
            helpful_results = [r for r in sensitivity_results if r.time_change > 0]

        if helpful_results:
            # Sort by efficiency (time change per unit change)
            helpful_results.sort(key=lambda x: abs(x.time_change), reverse=True)

            # Calculate needed change for top parameter
            best_result = helpful_results[0]
            if abs(best_result.time_change) > 0:
                scaling_factor = time_gap / best_result.time_change
                needed_change = best_result.parameter_delta.delta_value * scaling_factor

                adjustments[best_result.parameter_delta.parameter_path] = needed_change

        return adjustments


def create_common_parameter_deltas(athlete: AthleteV2) -> List[ParameterDelta]:
    """Create a standard set of parameter deltas for sensitivity analysis."""
    deltas = []

    # Common 1RM changes (+/- 5kg, +/- 10kg)
    for movement in ["back-squat", "clean", "snatch", "deadlift", "overhead-press"]:
        if movement in athlete.capabilities.one_rm:
            deltas.extend([
                ParameterDelta(f"one_rm.{movement}", -10.0),
                ParameterDelta(f"one_rm.{movement}", -5.0),
                ParameterDelta(f"one_rm.{movement}", +5.0),
                ParameterDelta(f"one_rm.{movement}", +10.0),
            ])

    # Common gym skill changes (+/- 0.1s cycle time, +/- 2 unbroken capacity)
    for skill in ["pull-up", "handstand-pushup", "toes-to-bar", "wall-ball"]:
        if skill in athlete.capabilities.gym_skills:
            deltas.extend([
                ParameterDelta(f"gym_skills.{skill}.cycle_s", -0.1),
                ParameterDelta(f"gym_skills.{skill}.cycle_s", +0.1),
                ParameterDelta(f"gym_skills.{skill}.unbroken_cap", -2),
                ParameterDelta(f"gym_skills.{skill}.unbroken_cap", +2),
            ])

    # Cardio changes (+/- 5% CP/CS, +/- 10% W'/D')
    for modality in ["bike", "row", "run"]:
        if modality in athlete.capabilities.cardio_profiles:
            deltas.extend([
                ParameterDelta(f"cardio_profiles.{modality}.cp", 0.95, is_relative=True),
                ParameterDelta(f"cardio_profiles.{modality}.cp", 1.05, is_relative=True),
                ParameterDelta(f"cardio_profiles.{modality}.w_prime", 0.90, is_relative=True),
                ParameterDelta(f"cardio_profiles.{modality}.w_prime", 1.10, is_relative=True),
            ])

    # RPE changes
    deltas.extend([
        ParameterDelta("rpe_intended", -1),
        ParameterDelta("rpe_intended", +1),
        ParameterDelta("rpe_intended", -2),
        ParameterDelta("rpe_intended", +2),
    ])

    # Body mass changes
    deltas.extend([
        ParameterDelta("body_mass_kg", -2.0),
        ParameterDelta("body_mass_kg", +2.0),
        ParameterDelta("body_mass_kg", -5.0),
        ParameterDelta("body_mass_kg", +5.0),
    ])

    return deltas
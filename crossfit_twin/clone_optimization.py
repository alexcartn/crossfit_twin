"""
Clone Optimization for CrossFit Digital Twin.

Implements digital clone generation with parameter variations for robust strategy
optimization and risk assessment.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import random
import math
import statistics
from copy import deepcopy

from .athlete_v2 import AthleteV2, ContextParams, DayState
from .strategy_solver import StrategySolver, CandidateStrategy
from .operational_whatif import OperationalAnalyzer
from .workout import WOD


@dataclass
class ParameterVariation:
    """Defines how a parameter should vary in clone generation."""
    parameter_path: str          # e.g., "gym_skills.pull-up.cycle_s"
    variation_range: Tuple[float, float]  # (min_value, max_value) or (min_delta, max_delta)
    is_delta: bool = True       # If True, range is deltas from baseline
    distribution: str = "uniform"  # "uniform", "normal", "triangular"


@dataclass
class CloneResult:
    """Result from a single clone simulation."""
    clone_id: int
    parameter_values: Dict[str, float]
    completion_time: float
    success: bool               # Did the clone complete the workout
    bottlenecks: List[str]      # What limited performance
    strategy_effectiveness: float  # How well the strategy worked (0-1)


@dataclass
class CloneOptimization:
    """Results from clone-based optimization."""
    baseline_time: float
    clone_results: List[CloneResult]
    statistics: Dict[str, float]        # mean, median, std, p10, p90, etc.
    optimal_strategy: CandidateStrategy
    risk_assessment: Dict[str, float]   # Risk factors and probabilities
    robustness_score: float             # How robust is the strategy (0-1)
    recommendations: List[str]


class CloneOptimizer:
    """
    Generates and analyzes digital clones for robust strategy optimization.
    """

    def __init__(self, base_athlete: AthleteV2):
        """Initialize with baseline athlete."""
        self.base_athlete = base_athlete
        self.solver = StrategySolver(base_athlete)

    def generate_parameter_variations(
        self,
        wod: WOD,
        uncertainty_level: str = "moderate"
    ) -> List[ParameterVariation]:
        """
        Generate realistic parameter variations for the given WOD.

        Args:
            wod: Workout definition
            uncertainty_level: "conservative", "moderate", "aggressive"

        Returns:
            List of parameter variations to test
        """
        variations = []

        # Define uncertainty ranges based on level
        uncertainty_factors = {
            "conservative": 0.05,  # ±5% variation
            "moderate": 0.10,      # ±10% variation
            "aggressive": 0.15     # ±15% variation
        }

        factor = uncertainty_factors.get(uncertainty_level, 0.10)

        # Extract movements from WOD
        movements = set()
        for round_exercises in wod.rounds:
            for exercise in round_exercises:
                movements.add(exercise.name)

        # Cycle time variations (day-of performance variation)
        for movement in movements:
            gym_skill = self.base_athlete.capabilities.get_gym_skill(movement)
            if gym_skill:
                base_cycle = gym_skill.cycle_s
                delta_range = base_cycle * factor

                variations.append(ParameterVariation(
                    parameter_path=f"gym_skills.{movement}.cycle_s",
                    variation_range=(-delta_range, delta_range),
                    is_delta=True,
                    distribution="normal"  # Performance usually normally distributed
                ))

        # Fatigue resistance variations
        for movement in movements:
            gym_skill = self.base_athlete.capabilities.get_gym_skill(movement)
            if gym_skill:
                base_slope = gym_skill.fatigue_slope
                delta_range = base_slope * factor

                variations.append(ParameterVariation(
                    parameter_path=f"gym_skills.{movement}.fatigue_slope",
                    variation_range=(-delta_range, delta_range),
                    is_delta=True,
                    distribution="uniform"
                ))

        # Unbroken capacity variations (more discrete)
        for movement in movements:
            gym_skill = self.base_athlete.capabilities.get_gym_skill(movement)
            if gym_skill and gym_skill.unbroken_cap > 5:
                cap_delta = max(1, int(gym_skill.unbroken_cap * factor))

                variations.append(ParameterVariation(
                    parameter_path=f"gym_skills.{movement}.unbroken_cap",
                    variation_range=(-cap_delta, cap_delta),
                    is_delta=True,
                    distribution="triangular"  # Most likely near baseline
                ))

        # Environmental variations
        variations.extend([
            ParameterVariation(
                parameter_path="context.temperature_c",
                variation_range=(-5.0, 5.0),
                is_delta=True,
                distribution="uniform"
            ),
            ParameterVariation(
                parameter_path="context.humidity_pct",
                variation_range=(-10.0, 10.0),
                is_delta=True,
                distribution="uniform"
            )
        ])

        # Daily state variations
        variations.extend([
            ParameterVariation(
                parameter_path="day_state.sleep_h",
                variation_range=(-1.0, 1.0),
                is_delta=True,
                distribution="normal"
            ),
            ParameterVariation(
                parameter_path="day_state.water_l",
                variation_range=(-0.5, 0.5),
                is_delta=True,
                distribution="uniform"
            )
        ])

        return variations

    def generate_clones(
        self,
        variations: List[ParameterVariation],
        n_clones: int = 64,
        seed: Optional[int] = None
    ) -> List[AthleteV2]:
        """
        Generate clone athletes with parameter variations.

        Args:
            variations: Parameter variations to apply
            n_clones: Number of clones to generate
            seed: Random seed for reproducibility

        Returns:
            List of clone athletes
        """
        if seed is not None:
            random.seed(seed)

        clones = []

        for i in range(n_clones):
            clone = deepcopy(self.base_athlete)
            clone.name = f"{self.base_athlete.name}_clone_{i}"

            # Apply random variations
            for variation in variations:
                value = self._sample_variation(variation)
                self._apply_parameter_value(clone, variation.parameter_path, value, variation.is_delta)

            clones.append(clone)

        return clones

    def _sample_variation(self, variation: ParameterVariation) -> float:
        """Sample a value from the parameter variation."""
        min_val, max_val = variation.variation_range

        if variation.distribution == "uniform":
            return random.uniform(min_val, max_val)
        elif variation.distribution == "normal":
            # Use range as ±2 standard deviations
            mean = (min_val + max_val) / 2
            std = (max_val - min_val) / 4
            return random.gauss(mean, std)
        elif variation.distribution == "triangular":
            # Most likely value is the midpoint
            mode = (min_val + max_val) / 2
            return random.triangular(min_val, max_val, mode)
        else:
            return random.uniform(min_val, max_val)

    def _apply_parameter_value(
        self,
        athlete: AthleteV2,
        parameter_path: str,
        value: float,
        is_delta: bool
    ) -> None:
        """Apply a parameter value to an athlete clone."""
        path_parts = parameter_path.split('.')

        if path_parts[0] == "gym_skills" and len(path_parts) == 3:
            skill_name = path_parts[1]
            param_name = path_parts[2]

            if skill_name in athlete.capabilities.gym_skills:
                skill = athlete.capabilities.gym_skills[skill_name]
                current_value = getattr(skill, param_name)

                if is_delta:
                    new_value = current_value + value
                else:
                    new_value = value

                if param_name == "cycle_s":
                    skill.cycle_s = max(0.1, new_value)
                elif param_name == "fatigue_slope":
                    skill.fatigue_slope = max(0.0, new_value)
                elif param_name == "unbroken_cap":
                    skill.unbroken_cap = max(1, int(new_value))

        elif path_parts[0] == "context":
            param_name = path_parts[1]
            current_value = getattr(athlete.context, param_name)

            if is_delta:
                new_value = current_value + value
            else:
                new_value = value

            # Apply bounds
            if param_name == "temperature_c":
                new_value = max(-10, min(45, new_value))
            elif param_name == "humidity_pct":
                new_value = max(10, min(100, new_value))
            elif param_name == "altitude_m":
                new_value = max(0, min(5000, new_value))

            setattr(athlete.context, param_name, new_value)

        elif path_parts[0] == "day_state":
            param_name = path_parts[1]
            current_value = getattr(athlete.day_state, param_name)

            if is_delta:
                new_value = current_value + value
            else:
                new_value = value

            # Apply bounds
            if param_name == "sleep_h":
                new_value = max(4.0, min(12.0, new_value))
            elif param_name == "water_l":
                new_value = max(0.5, min(5.0, new_value))
            elif param_name == "rpe_intended":
                new_value = max(0, min(10, int(new_value)))

            setattr(athlete.day_state, param_name, new_value)

    def run_clone_optimization(
        self,
        wod: WOD,
        strategy_candidates: List[CandidateStrategy],
        variations: List[ParameterVariation],
        n_clones: int = 64,
        seed: Optional[int] = None
    ) -> CloneOptimization:
        """
        Run complete clone optimization analysis.

        Args:
            wod: Workout definition
            strategy_candidates: Strategy options to test
            variations: Parameter variations for clones
            n_clones: Number of clones per strategy
            seed: Random seed

        Returns:
            Complete optimization results
        """
        # Generate clones
        clones = self.generate_clones(variations, n_clones, seed)

        # Test each strategy across all clones
        best_strategy = None
        best_score = float('inf')
        all_results = {}

        for strategy in strategy_candidates:
            results = []

            for i, clone in enumerate(clones):
                result = self._simulate_clone_strategy(wod, strategy, clone, i)
                if result:
                    results.append(result)

            if results:
                # Calculate strategy performance
                times = [r.completion_time for r in results if r.success]
                if times:
                    median_time = statistics.median(times)
                    success_rate = len([r for r in results if r.success]) / len(results)

                    # Combined score: median time + penalty for failures
                    score = median_time + (1 - success_rate) * 300  # 5min penalty per failure

                    if score < best_score:
                        best_score = score
                        best_strategy = strategy

                    all_results[strategy.strategy_type.value] = results

        # Analyze best strategy results
        if best_strategy and best_strategy.strategy_type.value in all_results:
            best_results = all_results[best_strategy.strategy_type.value]

            # Calculate statistics
            successful_times = [r.completion_time for r in best_results if r.success]
            baseline_time = self._simulate_baseline(wod, best_strategy)

            stats = {}
            if successful_times:
                stats = {
                    'mean': statistics.mean(successful_times),
                    'median': statistics.median(successful_times),
                    'std': statistics.stdev(successful_times) if len(successful_times) > 1 else 0,
                    'min': min(successful_times),
                    'max': max(successful_times),
                    'p10': self._percentile(successful_times, 10),
                    'p90': self._percentile(successful_times, 90),
                    'success_rate': len(successful_times) / len(best_results)
                }

            # Risk assessment
            risk_assessment = self._calculate_risk_assessment(best_results, baseline_time)

            # Robustness score
            robustness_score = self._calculate_robustness_score(best_results, stats)

            # Recommendations
            recommendations = self._generate_clone_recommendations(best_results, stats, risk_assessment)

            return CloneOptimization(
                baseline_time=baseline_time,
                clone_results=best_results,
                statistics=stats,
                optimal_strategy=best_strategy,
                risk_assessment=risk_assessment,
                robustness_score=robustness_score,
                recommendations=recommendations
            )

        # Fallback if no good strategy found
        return CloneOptimization(
            baseline_time=0,
            clone_results=[],
            statistics={},
            optimal_strategy=strategy_candidates[0] if strategy_candidates else None,
            risk_assessment={},
            robustness_score=0,
            recommendations=["No viable strategy found with current parameters"]
        )

    def _simulate_clone_strategy(
        self,
        wod: WOD,
        strategy: CandidateStrategy,
        clone: AthleteV2,
        clone_id: int
    ) -> Optional[CloneResult]:
        """Simulate a strategy with a specific clone."""
        try:
            # Reset clone fatigue
            clone.reset_fatigue()

            # Create solver for this clone
            clone_solver = StrategySolver(clone)

            # Estimate performance (simplified simulation)
            estimated_time = strategy.get_total_estimated_time()

            # Apply clone-specific performance factors
            performance_factor = self._calculate_clone_performance_factor(strategy, clone)
            actual_time = estimated_time * performance_factor

            # Determine success based on realistic thresholds
            success = True
            bottlenecks = []

            # Check for failure conditions
            for scheme in strategy.rep_schemes:
                gym_skill = clone.capabilities.get_gym_skill(scheme.exercise_name)
                if gym_skill:
                    max_set = max(scheme.set_breakdown)
                    current_fatigue = clone.fatigue_manager.get_movement_fatigue(scheme.exercise_name)
                    effective_cap = gym_skill.effective_unbroken_cap(current_fatigue)

                    if max_set > effective_cap * 1.5:  # Significantly exceeds capacity
                        success = False
                        bottlenecks.append(f"Set size {max_set} exceeds {scheme.exercise_name} capacity")

            # Strategy effectiveness (how well strategy matched clone capabilities)
            effectiveness = min(1.0, 1.0 / performance_factor) if performance_factor > 0 else 0.0

            # Extract parameter values for analysis
            parameter_values = self._extract_clone_parameters(clone)

            return CloneResult(
                clone_id=clone_id,
                parameter_values=parameter_values,
                completion_time=actual_time,
                success=success,
                bottlenecks=bottlenecks,
                strategy_effectiveness=effectiveness
            )

        except Exception:
            return None

    def _calculate_clone_performance_factor(self, strategy: CandidateStrategy, clone: AthleteV2) -> float:
        """Calculate performance factor for this clone relative to baseline."""
        factors = []

        for scheme in strategy.rep_schemes:
            gym_skill = clone.capabilities.get_gym_skill(scheme.exercise_name)
            if gym_skill:
                # Factor from cycle time
                base_skill = self.base_athlete.capabilities.get_gym_skill(scheme.exercise_name)
                if base_skill:
                    cycle_factor = gym_skill.cycle_s / base_skill.cycle_s
                    factors.append(cycle_factor)

        # Environmental factors
        if clone.context.temperature_c != self.base_athlete.context.temperature_c:
            temp_delta = abs(clone.context.temperature_c - 20)  # Optimal temp
            base_temp_delta = abs(self.base_athlete.context.temperature_c - 20)
            temp_factor = (1 + temp_delta * 0.01) / (1 + base_temp_delta * 0.01)
            factors.append(temp_factor)

        # Daily state factors
        if clone.day_state.sleep_h != self.base_athlete.day_state.sleep_h:
            sleep_factor = clone.day_state.sleep_h / self.base_athlete.day_state.sleep_h
            sleep_factor = max(0.8, min(1.2, sleep_factor))  # Bound the effect
            factors.append(sleep_factor)

        return statistics.mean(factors) if factors else 1.0

    def _extract_clone_parameters(self, clone: AthleteV2) -> Dict[str, float]:
        """Extract key parameter values from clone for analysis."""
        params = {}

        # Extract key gym skills
        for skill_name, skill in clone.capabilities.gym_skills.items():
            params[f"{skill_name}_cycle_s"] = skill.cycle_s
            params[f"{skill_name}_fatigue_slope"] = skill.fatigue_slope
            params[f"{skill_name}_unbroken_cap"] = skill.unbroken_cap

        # Extract context
        params["temperature_c"] = clone.context.temperature_c
        params["humidity_pct"] = clone.context.humidity_pct

        # Extract day state
        params["sleep_h"] = clone.day_state.sleep_h
        params["water_l"] = clone.day_state.water_l

        return params

    def _simulate_baseline(self, wod: WOD, strategy: CandidateStrategy) -> float:
        """Get baseline time for comparison."""
        return strategy.get_total_estimated_time()

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_data) - 1)
        weight = index - lower_index
        return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight

    def _calculate_risk_assessment(self, results: List[CloneResult], baseline_time: float) -> Dict[str, float]:
        """Calculate risk factors from clone results."""
        if not results:
            return {}

        successful_results = [r for r in results if r.success]
        failure_rate = 1 - (len(successful_results) / len(results))

        risk_factors = {
            'failure_probability': failure_rate,
            'time_variability': 0.0,
            'performance_degradation_risk': 0.0
        }

        if successful_results:
            times = [r.completion_time for r in successful_results]
            mean_time = statistics.mean(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0

            risk_factors['time_variability'] = std_time / mean_time if mean_time > 0 else 0
            risk_factors['performance_degradation_risk'] = max(0, (mean_time - baseline_time) / baseline_time)

        return risk_factors

    def _calculate_robustness_score(self, results: List[CloneResult], stats: Dict[str, float]) -> float:
        """Calculate overall robustness score (0-1, higher is better)."""
        if not results or not stats:
            return 0.0

        # Factors contributing to robustness
        success_rate = stats.get('success_rate', 0)

        # Low variability is good
        cv = stats.get('std', 0) / stats.get('mean', 1) if stats.get('mean', 0) > 0 else 1
        variability_score = max(0, 1 - cv)

        # Combine factors
        robustness = (success_rate * 0.6 + variability_score * 0.4)

        return min(1.0, robustness)

    def _generate_clone_recommendations(
        self,
        results: List[CloneResult],
        stats: Dict[str, float],
        risk_assessment: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on clone analysis."""
        recommendations = []

        success_rate = stats.get('success_rate', 0)
        if success_rate < 0.8:
            recommendations.append(f"Strategy has {(1-success_rate)*100:.0f}% failure risk - consider more conservative approach")

        time_variability = risk_assessment.get('time_variability', 0)
        if time_variability > 0.15:
            recommendations.append("High time variability - focus on consistency in key movements")

        # Analyze parameter sensitivity
        if results:
            # Find which parameters correlate with poor performance
            fast_results = [r for r in results if r.success and r.completion_time < stats.get('median', 0)]
            slow_results = [r for r in results if r.success and r.completion_time > stats.get('median', 0)]

            if fast_results and slow_results:
                # Compare parameter values (simplified analysis)
                recommendations.append("Consider additional movement efficiency training for consistency")

        if risk_assessment.get('failure_probability', 0) > 0.2:
            recommendations.append("High failure risk - ensure adequate preparation and consider backup strategies")

        return recommendations
"""
Utilities module for CrossFit Digital Twin.

Contains utility functions for athlete cloning, performance comparison, and analysis.
"""

from typing import List, Dict, Tuple, Optional, Any, Union
import itertools
import statistics
from dataclasses import asdict

from .athlete import Athlete
from .workout import WOD
from .strategy import Strategy, StrategyFactory
from .simulator import simulate, SimulationResult


class AthleteCloneGenerator:
    """
    Utility class for generating athlete clones with parameter variations.
    """
    
    @staticmethod
    def create_parameter_variations(
        base_athlete: Athlete,
        parameter_variations: Dict[str, List[float]],
        clone_name_prefix: Optional[str] = None
    ) -> List[Athlete]:
        """
        Create multiple athlete clones with different parameter values.
        
        Args:
            base_athlete: The base athlete to clone
            parameter_variations: Dict mapping parameter names to lists of values to try
            clone_name_prefix: Prefix for clone names (default: base athlete name)
            
        Returns:
            List of athlete clones with varied parameters
        """
        if not parameter_variations:
            return [base_athlete]
        
        prefix = clone_name_prefix or base_athlete.name
        clones = []
        
        # Generate all combinations of parameter values
        param_names = list(parameter_variations.keys())
        param_value_lists = list(parameter_variations.values())
        
        for i, combination in enumerate(itertools.product(*param_value_lists)):
            modifications = dict(zip(param_names, combination))
            
            # Create descriptive name
            mod_strs = [f"{param}={value}" for param, value in modifications.items()]
            clone_name = f"{prefix}_clone_{i+1}_({','.join(mod_strs)})"
            
            # Create clone with modifications
            clone = base_athlete.clone(name=clone_name, **modifications)
            clones.append(clone)
        
        return clones
    
    @staticmethod
    def create_percentage_variations(
        base_athlete: Athlete,
        parameters: List[str],
        percentage_range: Tuple[float, float] = (-10.0, 10.0),
        steps: int = 5
    ) -> List[Athlete]:
        """
        Create athlete clones with percentage-based parameter variations.
        
        Args:
            base_athlete: The base athlete to clone
            parameters: List of parameter names to vary
            percentage_range: Tuple of (min_percent, max_percent) to vary
            steps: Number of steps in the percentage range
            
        Returns:
            List of athlete clones with percentage variations
        """
        # Generate percentage values
        min_pct, max_pct = percentage_range
        if steps == 1:
            percentages = [0.0]
        else:
            step_size = (max_pct - min_pct) / (steps - 1)
            percentages = [min_pct + i * step_size for i in range(steps)]
        
        # Create variations dict
        variations = {}
        for param in parameters:
            base_value = getattr(base_athlete, param)
            variations[param] = [
                max(0.0, base_value * (1 + pct / 100.0)) 
                for pct in percentages
            ]
        
        return AthleteCloneGenerator.create_parameter_variations(
            base_athlete, variations
        )
    
    @staticmethod
    def create_focused_variations(
        base_athlete: Athlete,
        focus_parameter: str,
        variation_range: Tuple[float, float],
        steps: int = 5
    ) -> List[Athlete]:
        """
        Create athlete clones varying only one parameter across a range.
        
        Args:
            base_athlete: The base athlete to clone
            focus_parameter: The parameter to vary
            variation_range: Tuple of (min_value, max_value)
            steps: Number of steps in the range
            
        Returns:
            List of athlete clones with focused parameter variation
        """
        min_val, max_val = variation_range
        if steps == 1:
            values = [(min_val + max_val) / 2]
        else:
            step_size = (max_val - min_val) / (steps - 1)
            values = [min_val + i * step_size for i in range(steps)]
        
        variations = {focus_parameter: values}
        return AthleteCloneGenerator.create_parameter_variations(
            base_athlete, variations
        )


class PerformanceComparator:
    """
    Utility class for comparing and analyzing simulation results.
    """
    
    @staticmethod
    def compare_results(results: List[SimulationResult]) -> Dict[str, Any]:
        """
        Compare multiple simulation results and generate analysis.
        
        Args:
            results: List of simulation results to compare
            
        Returns:
            Dictionary containing comparison metrics and analysis
        """
        if not results:
            return {}
        
        # Basic statistics
        times = [r.total_time for r in results if r.completed]
        all_times = [r.total_time for r in results]
        
        comparison = {
            "total_simulations": len(results),
            "completed_simulations": len(times),
            "completion_rate": len(times) / len(results) if results else 0.0,
            "best_time": min(times) if times else None,
            "worst_time": max(times) if times else None,
            "average_time": statistics.mean(times) if times else None,
            "median_time": statistics.median(times) if times else None,
            "time_std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
            "best_result": None,
            "worst_result": None,
            "results_by_strategy": {},
            "results_by_athlete": {},
        }
        
        # Find best and worst results
        if times:
            comparison["best_result"] = min(results, key=lambda r: r.total_time if r.completed else float('inf'))
            comparison["worst_result"] = max(results, key=lambda r: r.total_time if r.completed else 0.0)
        
        # Group by strategy
        strategy_groups: Dict[str, List[SimulationResult]] = {}
        for result in results:
            strategy = result.strategy_name
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(result)
        
        for strategy, strategy_results in strategy_groups.items():
            strategy_times = [r.total_time for r in strategy_results if r.completed]
            comparison["results_by_strategy"][strategy] = {
                "count": len(strategy_results),
                "completed": len(strategy_times),
                "best_time": min(strategy_times) if strategy_times else None,
                "average_time": statistics.mean(strategy_times) if strategy_times else None,
            }
        
        # Group by athlete
        athlete_groups: Dict[str, List[SimulationResult]] = {}
        for result in results:
            athlete = result.athlete_name
            if athlete not in athlete_groups:
                athlete_groups[athlete] = []
            athlete_groups[athlete].append(result)
        
        for athlete, athlete_results in athlete_groups.items():
            athlete_times = [r.total_time for r in athlete_results if r.completed]
            comparison["results_by_athlete"][athlete] = {
                "count": len(athlete_results),
                "completed": len(athlete_times),
                "best_time": min(athlete_times) if athlete_times else None,
                "average_time": statistics.mean(athlete_times) if athlete_times else None,
            }
        
        return comparison
    
    @staticmethod
    def rank_results(
        results: List[SimulationResult],
        metric: str = "total_time"
    ) -> List[Tuple[int, SimulationResult]]:
        """
        Rank simulation results by a specific metric.
        
        Args:
            results: List of simulation results
            metric: Metric to rank by ("total_time", "total_reps", "avg_pace")
            
        Returns:
            List of (rank, result) tuples, sorted by rank
        """
        if metric == "total_time":
            # For time, lower is better, but only consider completed workouts
            completed_results = [r for r in results if r.completed]
            sorted_results = sorted(completed_results, key=lambda r: r.total_time)
        elif metric == "total_reps":
            # For reps, higher is better
            sorted_results = sorted(results, key=lambda r: r.total_reps, reverse=True)
        elif metric == "avg_pace":
            # For pace, lower is better
            results_with_pace = [r for r in results if r.avg_pace > 0]
            sorted_results = sorted(results_with_pace, key=lambda r: r.avg_pace)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        return [(i + 1, result) for i, result in enumerate(sorted_results)]
    
    @staticmethod
    def analyze_parameter_impact(
        base_athlete: Athlete,
        results: List[SimulationResult],
        parameter_name: str
    ) -> Dict[str, Any]:
        """
        Analyze the impact of a specific parameter on performance.
        
        Args:
            base_athlete: The base athlete (for reference values)
            results: Results from parameter variation experiments
            parameter_name: Name of the parameter that was varied
            
        Returns:
            Analysis of parameter impact
        """
        # Extract parameter values and corresponding performance
        data_points = []
        base_value = getattr(base_athlete, parameter_name)
        
        for result in results:
            # Try to extract parameter value from athlete name (if it follows our naming convention)
            if f"{parameter_name}=" in result.athlete_name:
                try:
                    # Parse parameter value from name like "athlete_clone_1_(strength=85.0)"
                    param_part = result.athlete_name.split(f"{parameter_name}=")[1]
                    param_value = float(param_part.split(",")[0].split(")")[0])
                    
                    if result.completed:
                        data_points.append((param_value, result.total_time))
                except (ValueError, IndexError):
                    continue
        
        if not data_points:
            return {"error": "No valid data points found for parameter analysis"}
        
        # Sort by parameter value
        data_points.sort(key=lambda x: x[0])
        
        param_values = [x[0] for x in data_points]
        performance_values = [x[1] for x in data_points]
        
        # Calculate correlation coefficient (simplified)
        if len(data_points) > 1:
            mean_param = statistics.mean(param_values)
            mean_perf = statistics.mean(performance_values)
            
            numerator = sum((p - mean_param) * (t - mean_perf) for p, t in data_points)
            param_variance = sum((p - mean_param) ** 2 for p in param_values)
            perf_variance = sum((t - mean_perf) ** 2 for t in performance_values)
            
            correlation = numerator / (param_variance * perf_variance) ** 0.5 if param_variance > 0 and perf_variance > 0 else 0.0
        else:
            correlation = 0.0
        
        # Find optimal value
        best_point = min(data_points, key=lambda x: x[1])
        worst_point = max(data_points, key=lambda x: x[1])
        
        return {
            "parameter_name": parameter_name,
            "base_value": base_value,
            "data_points": data_points,
            "correlation_with_performance": correlation,
            "optimal_value": best_point[0],
            "optimal_performance": best_point[1],
            "worst_value": worst_point[0],
            "worst_performance": worst_point[1],
            "performance_range": worst_point[1] - best_point[1],
            "parameter_range": (min(param_values), max(param_values)),
        }


class ExperimentRunner:
    """
    Utility class for running systematic experiments with multiple variations.
    """
    
    @staticmethod
    def run_parameter_sweep(
        base_athlete: Athlete,
        workout: WOD,
        strategy: Strategy,
        parameter_variations: Dict[str, List[float]],
        verbose: bool = False
    ) -> Tuple[List[SimulationResult], Dict[str, Any]]:
        """
        Run a parameter sweep experiment.
        
        Args:
            base_athlete: Base athlete to create variations from
            workout: Workout to simulate
            strategy: Strategy to use
            parameter_variations: Parameters and values to test
            verbose: Whether to print progress
            
        Returns:
            Tuple of (results_list, analysis_dict)
        """
        # Generate athlete clones
        clones = AthleteCloneGenerator.create_parameter_variations(
            base_athlete, parameter_variations
        )
        
        if verbose:
            print(f"Running parameter sweep with {len(clones)} athlete variations...")
        
        # Run simulations
        results = []
        for i, clone in enumerate(clones):
            if verbose:
                print(f"  Simulating {i+1}/{len(clones)}: {clone.name}")
            
            result = simulate(workout, clone, strategy, verbose=False)
            results.append(result)
        
        # Analyze results
        analysis = PerformanceComparator.compare_results(results)
        
        if verbose:
            print(f"\nParameter sweep complete:")
            print(f"  Total simulations: {analysis['total_simulations']}")
            print(f"  Completion rate: {analysis['completion_rate']:.1%}")
            if analysis['best_time']:
                print(f"  Best time: {analysis['best_time']:.1f}s ({analysis['best_result'].athlete_name})")
        
        return results, analysis
    
    @staticmethod
    def run_strategy_comparison(
        athlete: Athlete,
        workout: WOD,
        strategies: List[Strategy],
        verbose: bool = False
    ) -> Tuple[List[SimulationResult], Dict[str, Any]]:
        """
        Compare multiple strategies on the same athlete and workout.
        
        Args:
            athlete: Athlete to use
            workout: Workout to simulate
            strategies: List of strategies to compare
            verbose: Whether to print progress
            
        Returns:
            Tuple of (results_list, analysis_dict)
        """
        if verbose:
            print(f"Comparing {len(strategies)} strategies on {workout.name}...")
        
        results = []
        for i, strategy in enumerate(strategies):
            if verbose:
                print(f"  Testing strategy {i+1}/{len(strategies)}: {strategy.name}")
            
            result = simulate(workout, athlete, strategy, verbose=False)
            results.append(result)
        
        # Analyze and rank results
        analysis = PerformanceComparator.compare_results(results)
        ranked_results = PerformanceComparator.rank_results(results, "total_time")
        
        if verbose:
            print(f"\nStrategy comparison complete:")
            for rank, result in ranked_results[:3]:  # Show top 3
                status = "✅" if result.completed else "❌"
                print(f"  {rank}. {result.strategy_name}: {result.total_time:.1f}s {status}")
        
        return results, analysis


# Convenience functions for common experiments
def quick_parameter_test(
    athlete: Athlete,
    workout: WOD,
    strategy: Strategy,
    parameter: str,
    percentage_range: Tuple[float, float] = (-20.0, 20.0),
    steps: int = 5
) -> Dict[str, Any]:
    """
    Quick test of how a single parameter affects performance.
    
    Args:
        athlete: Base athlete
        workout: Workout to test
        strategy: Strategy to use
        parameter: Parameter name to vary
        percentage_range: Percentage range to test
        steps: Number of test points
        
    Returns:
        Analysis results
    """
    clones = AthleteCloneGenerator.create_percentage_variations(
        athlete, [parameter], percentage_range, steps
    )
    
    results = [simulate(workout, clone, strategy) for clone in clones]
    analysis = PerformanceComparator.analyze_parameter_impact(athlete, results, parameter)
    
    return analysis


def compare_all_strategies(
    athlete: Athlete,
    workout: WOD
) -> List[Tuple[str, float, bool]]:
    """
    Compare all built-in strategies on a workout.
    
    Args:
        athlete: Athlete to use
        workout: Workout to test
        
    Returns:
        List of (strategy_name, time, completed) tuples, sorted by performance
    """
    strategies = [
        StrategyFactory.unbroken(),
        StrategyFactory.conservative(),
        StrategyFactory.descending(),
        StrategyFactory.fractioned({"thruster": (5, 5.0), "pull-up": (3, 3.0)}),
    ]
    
    results = [simulate(workout, athlete, strategy) for strategy in strategies]
    
    # Sort by time (completed workouts first)
    results.sort(key=lambda r: (not r.completed, r.total_time))
    
    return [(r.strategy_name, r.total_time, r.completed) for r in results]
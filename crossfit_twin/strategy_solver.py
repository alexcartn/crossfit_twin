"""
Strategy Solver for CrossFit Digital Twin.

Implements goal-based strategy generation, candidate filtering, and optimization
to find optimal pacing strategies for specific time targets.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import math
import itertools
from copy import deepcopy

from .athlete_v2 import AthleteV2
from .rpe_strategy import RPEStrategy, RPEConstraints
from .workout import WOD, Exercise
from .simulator import simulate, SimulationResult


class StrategyType(Enum):
    """Strategy archetype for candidate generation."""
    UNBROKEN_AMBITIOUS = "unbroken_ambitious"
    FRACTIONED_STABLE = "fractioned_stable"
    CONSERVATIVE_NEGATIVE_SPLIT = "conservative_negative_split"
    BURST_MICRO_REST = "burst_micro_rest"
    STEADY_PACE = "steady_pace"


@dataclass
class RepScheme:
    """Repetition scheme for a single exercise within a round."""
    exercise_name: str
    total_reps: int
    set_breakdown: List[int]              # Reps per set: [21] or [12, 9] or [8, 7, 6]
    rest_after_sets: List[float]          # Rest after each set (seconds)
    load_kg: Optional[float] = None       # Load for weighted exercises
    target_cycle_time: float = 1.5       # Target seconds per rep

    @property
    def total_sets(self) -> int:
        return len(self.set_breakdown)

    @property
    def total_rest_time(self) -> float:
        return sum(self.rest_after_sets)

    @property
    def estimated_work_time(self) -> float:
        return self.total_reps * self.target_cycle_time

    @property
    def estimated_total_time(self) -> float:
        return self.estimated_work_time + self.total_rest_time


@dataclass
class CandidateStrategy:
    """Complete strategy candidate with rep schemes and metadata."""
    strategy_type: StrategyType
    rep_schemes: List[RepScheme]          # One per exercise in the WOD
    transition_rests: List[float]         # Rest between exercises
    rpe_policy: RPEConstraints
    risk_score: float = 0.0              # 0-1, higher = more risky
    estimated_time: float = 0.0          # Total estimated time
    feasibility_notes: List[str] = field(default_factory=list)

    def get_total_estimated_time(self) -> float:
        """Calculate total estimated time including transitions."""
        work_time = sum(scheme.estimated_total_time for scheme in self.rep_schemes)
        transition_time = sum(self.transition_rests)
        return work_time + transition_time


@dataclass
class StrategySolution:
    """Solution with strategy, simulation result, and analysis."""
    strategy: CandidateStrategy
    simulation_result: Optional[SimulationResult]
    time_delta: float                     # Difference from target time
    success_probability: float            # 0-1 estimated success rate
    bottlenecks: List[str]               # Where strategy might fail
    recommendations: List[str]            # How to improve

    @property
    def actual_time(self) -> float:
        return self.simulation_result.total_time if self.simulation_result else self.strategy.estimated_time


class StrategySolver:
    """
    Main solver for generating and optimizing workout strategies.
    """

    def __init__(self, athlete: AthleteV2):
        """
        Initialize solver with athlete capabilities.

        Args:
            athlete: AthleteV2 instance with capabilities and current state
        """
        self.athlete = athlete

    def generate_candidate_strategies(
        self,
        wod: WOD,
        rpe_constraints: RPEConstraints,
        max_candidates: int = 50
    ) -> List[CandidateStrategy]:
        """
        Generate multiple strategy candidates of different types.

        Args:
            wod: Workout definition
            rpe_constraints: RPE-based constraints
            max_candidates: Maximum number of candidates to generate

        Returns:
            List of candidate strategies
        """
        candidates = []

        # Generate candidates for each strategy type
        for strategy_type in StrategyType:
            type_candidates = self._generate_type_candidates(
                wod, rpe_constraints, strategy_type, max_candidates // len(StrategyType)
            )
            candidates.extend(type_candidates)

        # Filter for feasibility
        feasible_candidates = []
        for candidate in candidates:
            if self._check_feasibility(candidate):
                feasible_candidates.append(candidate)

        # Sort by estimated risk and time
        feasible_candidates.sort(key=lambda c: (c.risk_score, c.estimated_time))

        return feasible_candidates[:max_candidates]

    def _generate_type_candidates(
        self,
        wod: WOD,
        rpe_constraints: RPEConstraints,
        strategy_type: StrategyType,
        max_count: int
    ) -> List[CandidateStrategy]:
        """Generate candidates for a specific strategy type."""
        candidates = []

        # Generate rep schemes for ALL exercises across ALL rounds in the workout
        all_rep_schemes = []
        all_transition_rests = []

        for round_idx, round_obj in enumerate(wod.rounds):
            for exercise_idx, exercise in enumerate(round_obj.exercises):
                # Generate rep scheme variations
                schemes = self._generate_rep_schemes(exercise, rpe_constraints, strategy_type)

                if not schemes:
                    # Use a default scheme if generation fails
                    default_scheme = RepScheme(
                        exercise_name=exercise.name,
                        total_reps=exercise.reps,
                        set_breakdown=[exercise.reps],  # Do all unbroken as fallback
                        rest_after_sets=[],
                        load_kg=exercise.weight_kg,
                        target_cycle_time=2.0
                    )
                    all_rep_schemes.append(default_scheme)
                else:
                    # Take first scheme for now (could expand to combinations)
                    all_rep_schemes.append(schemes[0])

                # Add transition rest between exercises (but not after last exercise in round)
                if exercise_idx < len(round_obj.exercises) - 1:
                    all_transition_rests.append(rpe_constraints.min_rest_between_movements)

            # Add rest between rounds (but not after last round)
            if round_idx < len(wod.rounds) - 1:
                all_transition_rests.append(wod.rest_between_rounds)

        # Create one candidate for the entire workout
        if all_rep_schemes:
            candidate = CandidateStrategy(
                strategy_type=strategy_type,
                rep_schemes=all_rep_schemes,
                transition_rests=all_transition_rests,
                rpe_policy=rpe_constraints
            )

            # Calculate risk score and estimated time
            candidate.risk_score = self._calculate_risk_score(candidate)
            candidate.estimated_time = candidate.get_total_estimated_time()

            candidates.append(candidate)

        return candidates[:max_count]

    def _generate_rep_schemes(
        self,
        exercise: Exercise,
        rpe_constraints: RPEConstraints,
        strategy_type: StrategyType
    ) -> List[RepScheme]:
        """Generate rep schemes for a single exercise."""
        # Get athlete capabilities for this exercise
        gym_skill = self.athlete.capabilities.get_gym_skill(exercise.name)
        one_rm = self.athlete.capabilities.get_one_rm(exercise.name)

        # Determine load
        load_kg = None
        if exercise.weight_kg:
            load_kg = exercise.weight_kg
        elif one_rm:
            # Use RPE constraints to set load
            load_kg = one_rm * rpe_constraints.preferred_load_pct

        # Get cycle time
        target_cycle_time = 2.0  # Default
        if gym_skill:
            target_cycle_time = gym_skill.cycle_s
        elif one_rm and load_kg:
            target_cycle_time = self.athlete.capabilities.barbell_profile.rep_time(load_kg, one_rm)

        # Get unbroken capacity
        unbroken_cap = exercise.reps  # Default: do all reps
        if gym_skill:
            current_fatigue = self.athlete.fatigue_manager.get_movement_fatigue(exercise.name)
            effective_cap = gym_skill.effective_unbroken_cap(current_fatigue)
            unbroken_cap = min(exercise.reps, int(effective_cap * rpe_constraints.max_set_fraction))

        # Generate set breakdowns based on strategy type
        set_breakdowns = self._get_set_breakdowns(
            exercise.reps, unbroken_cap, strategy_type, rpe_constraints
        )

        schemes = []
        for breakdown in set_breakdowns:
            # Calculate rest periods
            rest_after_sets = self._calculate_rest_periods(
                breakdown, rpe_constraints, strategy_type
            )

            scheme = RepScheme(
                exercise_name=exercise.name,
                total_reps=exercise.reps,
                set_breakdown=breakdown,
                rest_after_sets=rest_after_sets,
                load_kg=load_kg,
                target_cycle_time=target_cycle_time
            )

            schemes.append(scheme)

        return schemes

    def _get_set_breakdowns(
        self,
        total_reps: int,
        unbroken_cap: int,
        strategy_type: StrategyType,
        rpe_constraints: RPEConstraints
    ) -> List[List[int]]:
        """Generate set breakdown patterns based on strategy type."""
        breakdowns = []

        if strategy_type == StrategyType.UNBROKEN_AMBITIOUS:
            # Try to do all unbroken if possible
            if total_reps <= unbroken_cap:
                breakdowns.append([total_reps])
            else:
                # Large sets with minimal breaking
                big_set = min(unbroken_cap, int(total_reps * 0.6))
                remaining = total_reps - big_set
                if remaining <= unbroken_cap:
                    breakdowns.append([big_set, remaining])
                else:
                    # Split remaining
                    mid_set = remaining // 2
                    breakdowns.append([big_set, mid_set, remaining - mid_set])

        elif strategy_type == StrategyType.FRACTIONED_STABLE:
            # Even set sizes, conservative approach
            target_set_size = min(unbroken_cap, int(total_reps * rpe_constraints.preferred_set_fraction))
            target_set_size = max(1, target_set_size)

            num_sets = math.ceil(total_reps / target_set_size)

            # Distribute reps evenly
            base_reps = total_reps // num_sets
            extra_reps = total_reps % num_sets

            breakdown = [base_reps] * num_sets
            for i in range(extra_reps):
                breakdown[i] += 1

            breakdowns.append(breakdown)

        elif strategy_type == StrategyType.CONSERVATIVE_NEGATIVE_SPLIT:
            # Start small, build up (negative split)
            if total_reps <= 6:
                breakdowns.append([total_reps])
            else:
                # 3-4 sets, increasing size
                if total_reps <= 15:
                    # Example: 21 → [5, 6, 10] or 15 → [3, 5, 7]
                    small = max(1, total_reps // 5)
                    medium = max(1, total_reps // 3)
                    large = total_reps - small - medium
                    if large > 0:
                        breakdowns.append([small, medium, large])
                    else:
                        breakdowns.append([small, total_reps - small])
                else:
                    # Larger totals: 4 sets
                    sets = [
                        max(1, int(total_reps * 0.15)),
                        max(1, int(total_reps * 0.25)),
                        max(1, int(total_reps * 0.30)),
                    ]
                    sets.append(total_reps - sum(sets))
                    breakdowns.append(sets)

        elif strategy_type == StrategyType.BURST_MICRO_REST:
            # Many small sets with short rests
            small_set_size = min(unbroken_cap // 2, max(1, total_reps // 8))
            small_set_size = max(1, small_set_size)

            num_sets = math.ceil(total_reps / small_set_size)
            base_reps = total_reps // num_sets
            extra_reps = total_reps % num_sets

            breakdown = [base_reps] * num_sets
            for i in range(extra_reps):
                breakdown[i] += 1

            breakdowns.append(breakdown)

        elif strategy_type == StrategyType.STEADY_PACE:
            # Moderate, consistent set sizes
            ideal_set_size = min(unbroken_cap, max(3, total_reps // 4))
            num_sets = max(1, math.ceil(total_reps / ideal_set_size))

            base_reps = total_reps // num_sets
            extra_reps = total_reps % num_sets

            breakdown = [base_reps] * num_sets
            for i in range(extra_reps):
                breakdown[i] += 1

            breakdowns.append(breakdown)

        # Ensure all breakdowns are valid
        valid_breakdowns = []
        for breakdown in breakdowns:
            if sum(breakdown) == total_reps and all(reps > 0 for reps in breakdown):
                valid_breakdowns.append(breakdown)

        return valid_breakdowns if valid_breakdowns else [[total_reps]]

    def _calculate_rest_periods(
        self,
        set_breakdown: List[int],
        rpe_constraints: RPEConstraints,
        strategy_type: StrategyType
    ) -> List[float]:
        """Calculate rest periods between sets."""
        if len(set_breakdown) <= 1:
            return [0.0]

        base_rest = rpe_constraints.min_rest_between_sets

        rest_periods = []
        for i in range(len(set_breakdown)):
            if i == len(set_breakdown) - 1:
                # No rest after last set
                rest_periods.append(0.0)
            else:
                rest_time = base_rest

                # Adjust based on strategy type
                if strategy_type == StrategyType.BURST_MICRO_REST:
                    rest_time = max(2.0, base_rest * 0.5)  # Very short rests
                elif strategy_type == StrategyType.UNBROKEN_AMBITIOUS:
                    rest_time = base_rest * 0.7  # Shorter rests, aggressive
                elif strategy_type == StrategyType.CONSERVATIVE_NEGATIVE_SPLIT:
                    rest_time = base_rest * 1.5  # Longer rests, build up energy

                # Scale based on set size (larger sets need more rest)
                set_factor = 1.0 + (set_breakdown[i] / 20.0) * 0.3
                rest_time *= set_factor

                rest_periods.append(rest_time)

        return rest_periods

    def _check_feasibility(self, candidate: CandidateStrategy) -> bool:
        """Check if a strategy candidate is physiologically feasible."""
        feasible = True
        notes = []

        for scheme in candidate.rep_schemes:
            # Check set sizes against unbroken capacity
            gym_skill = self.athlete.capabilities.get_gym_skill(scheme.exercise_name)
            if gym_skill:
                current_fatigue = self.athlete.fatigue_manager.get_movement_fatigue(scheme.exercise_name)
                effective_cap = gym_skill.effective_unbroken_cap(current_fatigue)

                for set_size in scheme.set_breakdown:
                    if set_size > effective_cap * 1.2:  # Allow 20% overage
                        feasible = False
                        notes.append(f"{scheme.exercise_name}: Set size {set_size} exceeds capacity {effective_cap:.0f}")

            # Check load against 1RM
            if scheme.load_kg:
                one_rm = self.athlete.capabilities.get_one_rm(scheme.exercise_name)
                if one_rm:
                    intensity = scheme.load_kg / one_rm
                    if intensity > candidate.rpe_policy.max_load_pct:
                        feasible = False
                        notes.append(f"{scheme.exercise_name}: Load {intensity:.0%} exceeds RPE limit {candidate.rpe_policy.max_load_pct:.0%}")

        candidate.feasibility_notes = notes
        return feasible

    def _calculate_risk_score(self, candidate: CandidateStrategy) -> float:
        """Calculate risk score (0-1) for a strategy candidate."""
        risk_factors = []

        for scheme in candidate.rep_schemes:
            # Risk from large set sizes
            gym_skill = self.athlete.capabilities.get_gym_skill(scheme.exercise_name)
            if gym_skill:
                current_fatigue = self.athlete.fatigue_manager.get_movement_fatigue(scheme.exercise_name)
                effective_cap = gym_skill.effective_unbroken_cap(current_fatigue)

                max_set_ratio = max(scheme.set_breakdown) / max(1, effective_cap)
                risk_factors.append(max(0, max_set_ratio - 0.8))  # Risk if >80% capacity

            # Risk from high load
            if scheme.load_kg:
                one_rm = self.athlete.capabilities.get_one_rm(scheme.exercise_name)
                if one_rm:
                    intensity = scheme.load_kg / one_rm
                    risk_factors.append(max(0, intensity - 0.7))  # Risk if >70% 1RM

            # Risk from insufficient rest
            if scheme.rest_after_sets:
                positive_rests = [rest for rest in scheme.rest_after_sets if rest > 0]
                if positive_rests:
                    min_rest = min(positive_rests)
                    if min_rest < candidate.rpe_policy.min_rest_between_sets:
                        risk_factors.append(0.2)  # Fixed risk for insufficient rest

        # Combine risk factors
        return min(1.0, sum(risk_factors) / len(risk_factors) if risk_factors else 0.0)

    def solve_for_target_time(
        self,
        wod: WOD,
        target_seconds: float,
        rpe_constraints: RPEConstraints,
        top_k: int = 5
    ) -> List[StrategySolution]:
        """
        Find optimal strategies for a target time.

        Args:
            wod: Workout definition
            target_seconds: Target completion time
            rpe_constraints: RPE-based constraints
            top_k: Number of top solutions to return

        Returns:
            List of strategy solutions sorted by fitness to target
        """
        # Generate candidate strategies
        candidates = self.generate_candidate_strategies(wod, rpe_constraints, max_candidates=50)

        solutions = []

        for candidate in candidates:
            # Simulate the strategy
            try:
                # Create a temporary strategy object for simulation
                # (This would need adaptation to work with existing simulator)
                simulation_result = self._simulate_candidate(wod, candidate)

                # Calculate time delta
                actual_time = simulation_result.total_time if simulation_result else candidate.estimated_time
                time_delta = abs(actual_time - target_seconds)

                # Estimate success probability
                success_prob = self._estimate_success_probability(candidate, simulation_result)

                # Identify bottlenecks
                bottlenecks = self._identify_bottlenecks(candidate, simulation_result)

                # Generate recommendations
                recommendations = self._generate_recommendations(candidate, target_seconds, actual_time)

                solution = StrategySolution(
                    strategy=candidate,
                    simulation_result=simulation_result,
                    time_delta=time_delta,
                    success_probability=success_prob,
                    bottlenecks=bottlenecks,
                    recommendations=recommendations
                )

                solutions.append(solution)

            except Exception as e:
                # Skip problematic candidates
                continue

        # Sort by fitness (time delta, then success probability)
        solutions.sort(key=lambda s: (s.time_delta, -s.success_probability))

        return solutions[:top_k]

    def _simulate_candidate(self, wod: WOD, candidate: CandidateStrategy) -> Optional[SimulationResult]:
        """
        Simulate a candidate strategy.

        Note: This is a placeholder that would need integration with the actual simulator.
        """
        # For now, return estimated time as a simple simulation
        # In full implementation, this would convert candidate to Strategy object
        # and run through the existing simulate() function

        # Placeholder simulation result
        from .simulator import SimulationResult

        estimated_time = candidate.get_total_estimated_time()

        # Add some variability based on risk
        time_variance = estimated_time * candidate.risk_score * 0.1
        final_time = estimated_time + time_variance

        return SimulationResult(
            total_time=final_time,
            final_fatigue=candidate.risk_score,
            events=[],  # Would be populated in real simulation
            performance_metrics={}
        )

    def _estimate_success_probability(
        self,
        candidate: CandidateStrategy,
        simulation_result: Optional[SimulationResult]
    ) -> float:
        """Estimate probability of successfully completing the strategy."""
        # Base probability from risk score
        base_prob = 1.0 - candidate.risk_score

        # Adjust based on simulation results
        if simulation_result:
            # Lower probability if final fatigue is very high
            fatigue_penalty = min(0.3, simulation_result.final_fatigue * 0.2)
            base_prob -= fatigue_penalty

        return max(0.1, min(1.0, base_prob))

    def _identify_bottlenecks(
        self,
        candidate: CandidateStrategy,
        simulation_result: Optional[SimulationResult]
    ) -> List[str]:
        """Identify potential failure points in the strategy."""
        bottlenecks = []

        for scheme in candidate.rep_schemes:
            # Check for large sets
            if max(scheme.set_breakdown) > 15:
                bottlenecks.append(f"Large {scheme.exercise_name} set ({max(scheme.set_breakdown)} reps)")

            # Check for high load
            if scheme.load_kg:
                one_rm = self.athlete.capabilities.get_one_rm(scheme.exercise_name)
                if one_rm and (scheme.load_kg / one_rm) > 0.8:
                    intensity = scheme.load_kg / one_rm
                    bottlenecks.append(f"High {scheme.exercise_name} load ({intensity:.0%} 1RM)")

            # Check for insufficient rest
            if scheme.rest_after_sets:
                positive_rests = [rest for rest in scheme.rest_after_sets if rest > 0]
                if positive_rests and min(positive_rests) < 5:
                    bottlenecks.append(f"Short rest after {scheme.exercise_name}")

        return bottlenecks

    def _generate_recommendations(
        self,
        candidate: CandidateStrategy,
        target_time: float,
        actual_time: float
    ) -> List[str]:
        """Generate recommendations for improving the strategy."""
        recommendations = []

        time_diff = actual_time - target_time

        if time_diff > 30:  # Too slow
            recommendations.append("Consider larger set sizes to reduce transition time")
            recommendations.append("Check if load can be reduced while maintaining workout intent")
            recommendations.append("Reduce rest periods between sets")
        elif time_diff < -30:  # Too fast (may be unsustainable)
            recommendations.append("Consider smaller set sizes for better sustainability")
            recommendations.append("Add more rest to maintain quality throughout")
            recommendations.append("Check if current pacing is realistic for your fitness level")

        # RPE-specific recommendations
        if candidate.rpe_policy.target_rpe <= 5:
            recommendations.append("Conservative approach - focus on consistent pacing")
        elif candidate.rpe_policy.target_rpe >= 8:
            recommendations.append("High intensity - ensure adequate warmup and pacing practice")

        return recommendations
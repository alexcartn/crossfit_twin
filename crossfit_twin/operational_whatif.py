"""
Operational What-If Analysis for CrossFit Digital Twin.

Focuses on day-of-competition operational parameters that actually impact performance:
- Cycle times and movement efficiency
- Transitions and micro-rest management
- Set breakdown strategies
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from copy import deepcopy
from enum import Enum

from .athlete_v2 import AthleteV2
from .strategy_solver import CandidateStrategy, StrategySolution
from .workout import WOD


class OperationalLever(Enum):
    """Types of operational improvements that affect performance."""
    MOVEMENT_EFFICIENCY = "movement_efficiency"     # Better technique → faster cycle time
    FATIGUE_RESISTANCE = "fatigue_resistance"       # Less degradation under fatigue
    TRANSITION_SPEED = "transition_speed"           # Faster setup/breakdown
    REST_OPTIMIZATION = "rest_optimization"         # Better micro-rest management
    SET_STRATEGY = "set_strategy"                   # Smarter rep breakdown


@dataclass
class OperationalParameter:
    """Represents an operational parameter that can be adjusted."""
    name: str
    description: str
    lever_type: OperationalLever
    movement: Optional[str] = None          # Specific movement or None for general
    baseline_value: float = 0.0             # Current value
    min_delta: float = -1.0                 # Minimum improvement (usually negative)
    max_delta: float = 1.0                  # Maximum improvement (usually positive)
    unit: str = "seconds"


@dataclass
class OperationalDelta:
    """A specific change to an operational parameter."""
    parameter: OperationalParameter
    delta_value: float                      # Change amount
    feasibility: float = 1.0               # 0-1, how realistic this change is
    training_required: str = "None"        # What practice/training is needed


@dataclass
class OperationalImpact:
    """Impact assessment of an operational change."""
    delta: OperationalDelta
    time_savings: float                     # Seconds saved (negative = time lost)
    impact_per_rep: float                   # Time change per rep
    total_reps_affected: int                # How many reps benefit
    bottleneck_relief: float                # 0-1, how much this relieves bottlenecks
    implementation_difficulty: str          # "Easy", "Moderate", "Hard"
    confidence: float                       # 0-1, confidence in this estimate


@dataclass
class OperationalStrategy:
    """Complete operational improvement strategy."""
    improvements: List[OperationalImpact]
    total_time_savings: float
    implementation_plan: List[str]
    risk_factors: List[str]
    training_priorities: List[str]


class OperationalAnalyzer:
    """
    Analyzes operational improvements for day-of-competition performance gains.
    """

    def __init__(self, athlete: AthleteV2):
        """Initialize with baseline athlete."""
        self.athlete = athlete

    def identify_operational_parameters(self, wod: WOD) -> List[OperationalParameter]:
        """
        Identify relevant operational parameters for a specific WOD.

        Args:
            wod: Workout definition

        Returns:
            List of operational parameters that could impact this WOD
        """
        parameters = []

        # Extract movements from WOD
        movements = set()
        for round_exercises in wod.rounds:
            for exercise in round_exercises:
                movements.add(exercise.name)

        # Movement-specific cycle time parameters
        for movement in movements:
            gym_skill = self.athlete.capabilities.get_gym_skill(movement)
            if gym_skill:
                # Cycle time improvement through technique
                parameters.append(OperationalParameter(
                    name=f"{movement}_cycle_efficiency",
                    description=f"Improved {movement} technique reducing cycle time",
                    lever_type=OperationalLever.MOVEMENT_EFFICIENCY,
                    movement=movement,
                    baseline_value=gym_skill.cycle_s,
                    min_delta=-0.3,  # Can improve up to 0.3s per rep
                    max_delta=0.1,   # Could get slower if tired/sloppy
                    unit="s/rep"
                ))

                # Fatigue resistance improvement
                parameters.append(OperationalParameter(
                    name=f"{movement}_fatigue_resistance",
                    description=f"Reduced {movement} degradation under fatigue",
                    lever_type=OperationalLever.FATIGUE_RESISTANCE,
                    movement=movement,
                    baseline_value=gym_skill.fatigue_slope,
                    min_delta=-0.15,  # Better fatigue resistance
                    max_delta=0.1,    # Could get worse if unpracticed
                    unit="degradation_rate"
                ))

        # Barbell transition parameters
        barbell_movements = {mv for mv in movements if self.athlete.capabilities.get_one_rm(mv)}
        if barbell_movements:
            parameters.extend([
                OperationalParameter(
                    name="barbell_setup_speed",
                    description="Faster bar setup, chalk, positioning",
                    lever_type=OperationalLever.TRANSITION_SPEED,
                    baseline_value=3.0,  # Default setup time
                    min_delta=-2.0,      # Can save up to 2s
                    max_delta=2.0,       # Could lose time if disorganized
                    unit="s/transition"
                ),
                OperationalParameter(
                    name="no_drop_technique",
                    description="Keeping bar in hands vs dropping",
                    lever_type=OperationalLever.TRANSITION_SPEED,
                    baseline_value=1.5,  # Time to drop and re-setup
                    min_delta=-1.5,      # Eliminate if no-drop
                    max_delta=0.5,       # Could add time if struggling
                    unit="s/set"
                )
            ])

        # Micro-rest optimization
        parameters.extend([
            OperationalParameter(
                name="controlled_breathing",
                description="Efficient breathing technique during micro-rests",
                lever_type=OperationalLever.REST_OPTIMIZATION,
                baseline_value=5.0,   # Default micro-rest time
                min_delta=-2.0,       # More efficient recovery
                max_delta=3.0,        # Could need more time if inefficient
                unit="s/micro_rest"
            ),
            OperationalParameter(
                name="strategic_positioning",
                description="Optimal positioning between exercises",
                lever_type=OperationalLever.TRANSITION_SPEED,
                baseline_value=2.0,   # Walking/positioning time
                min_delta=-1.5,       # Pre-position equipment
                max_delta=2.0,        # Poor gym layout/prep
                unit="s/transition"
            )
        ])

        # Set strategy parameters
        for movement in movements:
            gym_skill = self.athlete.capabilities.get_gym_skill(movement)
            if gym_skill and gym_skill.unbroken_cap > 5:  # Only for movements with meaningful capacity
                parameters.append(OperationalParameter(
                    name=f"{movement}_set_strategy",
                    description=f"Optimal {movement} set breakdown vs aggressive",
                    lever_type=OperationalLever.SET_STRATEGY,
                    movement=movement,
                    baseline_value=0.7,  # Default set fraction
                    min_delta=-0.3,      # More conservative
                    max_delta=0.2,       # More aggressive
                    unit="set_fraction"
                ))

        return parameters

    def calculate_operational_impacts(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        deltas: List[OperationalDelta]
    ) -> List[OperationalImpact]:
        """
        Calculate the impact of operational changes.

        Args:
            wod: Workout definition
            baseline_strategy: Current strategy
            deltas: Proposed operational changes

        Returns:
            List of impact assessments
        """
        impacts = []

        for delta in deltas:
            impact = self._calculate_single_impact(wod, baseline_strategy, delta)
            if impact:
                impacts.append(impact)

        return impacts

    def _calculate_single_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> Optional[OperationalImpact]:
        """Calculate impact of a single operational change."""

        param = delta.parameter

        if param.lever_type == OperationalLever.MOVEMENT_EFFICIENCY:
            return self._calculate_cycle_time_impact(wod, baseline_strategy, delta)
        elif param.lever_type == OperationalLever.FATIGUE_RESISTANCE:
            return self._calculate_fatigue_resistance_impact(wod, baseline_strategy, delta)
        elif param.lever_type == OperationalLever.TRANSITION_SPEED:
            return self._calculate_transition_impact(wod, baseline_strategy, delta)
        elif param.lever_type == OperationalLever.REST_OPTIMIZATION:
            return self._calculate_rest_impact(wod, baseline_strategy, delta)
        elif param.lever_type == OperationalLever.SET_STRATEGY:
            return self._calculate_set_strategy_impact(wod, baseline_strategy, delta)

        return None

    def _calculate_cycle_time_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> OperationalImpact:
        """Calculate impact of improved cycle time."""

        # Count total reps for this movement
        total_reps = 0
        for round_exercises in wod.rounds:
            for exercise in round_exercises:
                if exercise.name == delta.parameter.movement:
                    total_reps += exercise.reps

        # Time savings = reps × cycle time improvement
        time_savings = total_reps * (-delta.delta_value)  # Negative delta = improvement

        # Implementation difficulty based on change magnitude
        difficulty = "Easy"
        if abs(delta.delta_value) > 0.15:
            difficulty = "Moderate"
        if abs(delta.delta_value) > 0.25:
            difficulty = "Hard"

        # Confidence based on movement type and change size
        confidence = 0.9
        if abs(delta.delta_value) > 0.2:
            confidence = 0.7
        if delta.parameter.movement in ["muscle-up", "handstand-pushup"]:
            confidence *= 0.8  # Technical movements harder to predict

        return OperationalImpact(
            delta=delta,
            time_savings=time_savings,
            impact_per_rep=-delta.delta_value,
            total_reps_affected=total_reps,
            bottleneck_relief=0.8 if total_reps > 20 else 0.5,
            implementation_difficulty=difficulty,
            confidence=confidence
        )

    def _calculate_fatigue_resistance_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> OperationalImpact:
        """Calculate impact of improved fatigue resistance."""

        # Count reps for this movement
        total_reps = 0
        for round_exercises in wod.rounds:
            for exercise in round_exercises:
                if exercise.name == delta.parameter.movement:
                    total_reps += exercise.reps

        # Fatigue resistance mainly helps later in workout
        # Estimate average fatigue level during this movement
        avg_fatigue_level = min(1.0, total_reps / 30.0)  # Rough estimate

        # Time savings from reduced degradation
        gym_skill = self.athlete.capabilities.get_gym_skill(delta.parameter.movement)
        base_cycle = gym_skill.cycle_s if gym_skill else 2.0

        # Current degradation vs improved degradation
        current_degradation = avg_fatigue_level * delta.parameter.baseline_value
        improved_degradation = avg_fatigue_level * (delta.parameter.baseline_value + delta.delta_value)

        degradation_savings = current_degradation - improved_degradation
        time_savings = total_reps * base_cycle * degradation_savings

        return OperationalImpact(
            delta=delta,
            time_savings=time_savings,
            impact_per_rep=base_cycle * degradation_savings,
            total_reps_affected=total_reps,
            bottleneck_relief=0.6,  # Helps but less direct than cycle time
            implementation_difficulty="Moderate",  # Requires conditioning
            confidence=0.7
        )

    def _calculate_transition_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> OperationalImpact:
        """Calculate impact of improved transitions."""

        param_name = delta.parameter.name

        if "barbell_setup" in param_name:
            # Count barbell transitions
            barbell_transitions = 0
            for round_exercises in wod.rounds:
                for exercise in round_exercises:
                    if self.athlete.capabilities.get_one_rm(exercise.name):
                        # Each barbell exercise has setup
                        barbell_transitions += 1

            time_savings = barbell_transitions * (-delta.delta_value)

            return OperationalImpact(
                delta=delta,
                time_savings=time_savings,
                impact_per_rep=0,  # Per transition, not per rep
                total_reps_affected=0,
                bottleneck_relief=0.4,  # Moderate impact
                implementation_difficulty="Easy",
                confidence=0.9
            )

        elif "no_drop" in param_name:
            # Count sets where no-drop could apply
            applicable_sets = 0
            for scheme in baseline_strategy.rep_schemes:
                if self.athlete.capabilities.get_one_rm(scheme.exercise_name):
                    applicable_sets += len(scheme.set_breakdown) - 1  # Don't count last set

            time_savings = applicable_sets * (-delta.delta_value)

            return OperationalImpact(
                delta=delta,
                time_savings=time_savings,
                impact_per_rep=0,
                total_reps_affected=0,
                bottleneck_relief=0.7,  # High impact when applicable
                implementation_difficulty="Moderate",  # Requires strength endurance
                confidence=0.8
            )

        elif "strategic_positioning" in param_name:
            # Count exercise transitions
            total_transitions = sum(len(exercises) - 1 for exercises in wod.rounds)
            total_transitions += len(wod.rounds) - 1  # Round transitions

            time_savings = total_transitions * (-delta.delta_value)

            return OperationalImpact(
                delta=delta,
                time_savings=time_savings,
                impact_per_rep=0,
                total_reps_affected=0,
                bottleneck_relief=0.3,  # Lower impact but easy
                implementation_difficulty="Easy",
                confidence=0.95
            )

        return OperationalImpact(
            delta=delta,
            time_savings=0,
            impact_per_rep=0,
            total_reps_affected=0,
            bottleneck_relief=0,
            implementation_difficulty="Easy",
            confidence=0.5
        )

    def _calculate_rest_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> OperationalImpact:
        """Calculate impact of optimized rest periods."""

        # Count rest periods in strategy
        total_rest_periods = 0
        for scheme in baseline_strategy.rep_schemes:
            total_rest_periods += sum(1 for rest in scheme.rest_after_sets if rest > 0)

        # Time savings from more efficient recovery
        time_savings = total_rest_periods * (-delta.delta_value)

        # But check if this might hurt performance
        confidence = 0.8
        if delta.delta_value < -1.5:  # Very aggressive rest reduction
            confidence = 0.6
            time_savings *= 0.7  # Discount for potential performance loss

        return OperationalImpact(
            delta=delta,
            time_savings=time_savings,
            impact_per_rep=0,
            total_reps_affected=0,
            bottleneck_relief=0.5,
            implementation_difficulty="Moderate",  # Requires practice
            confidence=confidence
        )

    def _calculate_set_strategy_impact(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        delta: OperationalDelta
    ) -> OperationalImpact:
        """Calculate impact of different set breakdown strategy."""

        # This is complex - changing set strategy affects both cycle times and rest
        # For now, estimate based on whether we're going more conservative or aggressive

        movement = delta.parameter.movement
        total_reps = 0
        for round_exercises in wod.rounds:
            for exercise in round_exercises:
                if exercise.name == movement:
                    total_reps += exercise.reps

        # More conservative (negative delta) usually saves time through consistency
        # More aggressive (positive delta) might save transitions but risk breakdown

        if delta.delta_value < 0:  # More conservative
            # Fewer transitions, more consistent pace
            estimated_savings = abs(delta.delta_value) * total_reps * 0.05  # Small per-rep benefit
            confidence = 0.8
            difficulty = "Easy"
        else:  # More aggressive
            # Risk of breakdown, but fewer transitions
            estimated_savings = -delta.delta_value * total_reps * 0.02  # Potential loss
            confidence = 0.6
            difficulty = "Hard"

        return OperationalImpact(
            delta=delta,
            time_savings=estimated_savings,
            impact_per_rep=estimated_savings / max(1, total_reps),
            total_reps_affected=total_reps,
            bottleneck_relief=0.6,
            implementation_difficulty=difficulty,
            confidence=confidence
        )

    def generate_operational_strategy(
        self,
        wod: WOD,
        baseline_strategy: CandidateStrategy,
        target_time_savings: float = 30.0
    ) -> OperationalStrategy:
        """
        Generate a comprehensive operational improvement strategy.

        Args:
            wod: Workout definition
            baseline_strategy: Current strategy
            target_time_savings: Desired time improvement (seconds)

        Returns:
            Complete operational strategy with prioritized improvements
        """

        # Get all relevant parameters
        parameters = self.identify_operational_parameters(wod)

        # Generate reasonable deltas for each parameter
        deltas = []
        for param in parameters:
            # Create multiple delta options (conservative, moderate, aggressive)
            delta_values = []

            if param.lever_type == OperationalLever.MOVEMENT_EFFICIENCY:
                delta_values = [-0.05, -0.10, -0.15]  # Cycle time improvements
            elif param.lever_type == OperationalLever.FATIGUE_RESISTANCE:
                delta_values = [-0.05, -0.10, -0.15]  # Fatigue slope improvements
            elif param.lever_type == OperationalLever.TRANSITION_SPEED:
                delta_values = [-0.5, -1.0, -1.5]    # Transition time savings
            elif param.lever_type == OperationalLever.REST_OPTIMIZATION:
                delta_values = [-0.5, -1.0, -2.0]    # Rest time reductions
            elif param.lever_type == OperationalLever.SET_STRATEGY:
                delta_values = [-0.1, -0.2, 0.1]     # Set strategy changes

            for delta_val in delta_values:
                if param.min_delta <= delta_val <= param.max_delta:
                    # Assess feasibility
                    feasibility = 1.0
                    training_required = "Minimal"

                    if abs(delta_val) > abs(param.min_delta) * 0.7:
                        feasibility = 0.7
                        training_required = "Moderate"
                    if abs(delta_val) > abs(param.min_delta) * 0.9:
                        feasibility = 0.5
                        training_required = "Significant"

                    deltas.append(OperationalDelta(
                        parameter=param,
                        delta_value=delta_val,
                        feasibility=feasibility,
                        training_required=training_required
                    ))

        # Calculate impacts
        impacts = self.calculate_operational_impacts(wod, baseline_strategy, deltas)

        # Sort by time savings and feasibility
        impacts.sort(key=lambda x: x.time_savings * x.delta.feasibility, reverse=True)

        # Select best combination to reach target
        selected_improvements = []
        total_savings = 0.0

        for impact in impacts:
            if total_savings < target_time_savings and impact.time_savings > 0:
                # Check for conflicts (same parameter type)
                conflict = False
                for existing in selected_improvements:
                    if (existing.delta.parameter.name == impact.delta.parameter.name or
                        (existing.delta.parameter.movement == impact.delta.parameter.movement and
                         existing.delta.parameter.lever_type == impact.delta.parameter.lever_type)):
                        conflict = True
                        break

                if not conflict:
                    selected_improvements.append(impact)
                    total_savings += impact.time_savings

        # Generate implementation plan
        implementation_plan = self._create_implementation_plan(selected_improvements)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(selected_improvements)

        # Create training priorities
        training_priorities = self._create_training_priorities(selected_improvements)

        return OperationalStrategy(
            improvements=selected_improvements,
            total_time_savings=total_savings,
            implementation_plan=implementation_plan,
            risk_factors=risk_factors,
            training_priorities=training_priorities
        )

    def _create_implementation_plan(self, improvements: List[OperationalImpact]) -> List[str]:
        """Create step-by-step implementation plan."""
        plan = []

        # Group by difficulty and time to implement
        easy_wins = [imp for imp in improvements if imp.implementation_difficulty == "Easy"]
        moderate = [imp for imp in improvements if imp.implementation_difficulty == "Moderate"]
        hard = [imp for imp in improvements if imp.implementation_difficulty == "Hard"]

        if easy_wins:
            plan.append("PHASE 1 - Quick Wins (implement immediately):")
            for imp in easy_wins:
                plan.append(f"  • {imp.delta.parameter.description}")

        if moderate:
            plan.append("PHASE 2 - Moderate Changes (1-2 weeks practice):")
            for imp in moderate:
                plan.append(f"  • {imp.delta.parameter.description}")

        if hard:
            plan.append("PHASE 3 - Advanced Changes (ongoing training):")
            for imp in hard:
                plan.append(f"  • {imp.delta.parameter.description}")

        return plan

    def _identify_risk_factors(self, improvements: List[OperationalImpact]) -> List[str]:
        """Identify risks associated with the improvements."""
        risks = []

        # Check for aggressive changes
        aggressive_changes = [imp for imp in improvements if imp.confidence < 0.7]
        if aggressive_changes:
            risks.append("Some changes have lower confidence - test thoroughly in training")

        # Check for multiple fatigue-related changes
        fatigue_changes = [imp for imp in improvements
                          if imp.delta.parameter.lever_type == OperationalLever.FATIGUE_RESISTANCE]
        if len(fatigue_changes) > 2:
            risks.append("Multiple fatigue-related changes may compound - implement gradually")

        # Check for rest reductions
        rest_reductions = [imp for imp in improvements
                          if imp.delta.parameter.lever_type == OperationalLever.REST_OPTIMIZATION
                          and imp.delta.delta_value < -1.0]
        if rest_reductions:
            risks.append("Significant rest reductions may impact performance quality")

        return risks

    def _create_training_priorities(self, improvements: List[OperationalImpact]) -> List[str]:
        """Create training priority list."""
        priorities = []

        # Sort by time savings and training requirements
        movement_improvements = {}

        for imp in improvements:
            if imp.delta.parameter.movement:
                movement = imp.delta.parameter.movement
                if movement not in movement_improvements:
                    movement_improvements[movement] = []
                movement_improvements[movement].append(imp)

        # Prioritize movements with highest total impact
        sorted_movements = sorted(
            movement_improvements.items(),
            key=lambda x: sum(imp.time_savings for imp in x[1]),
            reverse=True
        )

        for movement, imps in sorted_movements:
            total_savings = sum(imp.time_savings for imp in imps)
            priorities.append(f"{movement.title()}: {total_savings:.1f}s potential savings")

            for imp in imps:
                if imp.delta.training_required != "Minimal":
                    priorities.append(f"  - {imp.delta.parameter.description} ({imp.delta.training_required} training)")

        return priorities
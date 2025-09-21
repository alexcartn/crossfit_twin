"""
Fallback system for missing athlete data.

Implements comprehensive inference rules and provenance tracking to ensure
simulations never fail due to missing data.
"""

from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import math
from .benchmarks import UIBenchmarks, parse_time_string


@dataclass
class DataProvenance:
    """Track the source and confidence of each data point."""
    source: Dict[str, str] = field(default_factory=dict)  # "measured" | "inferred" | "default" | "prior"
    confidence: Dict[str, float] = field(default_factory=dict)  # 0.0 - 1.0

    def add(self, key: str, source: str, confidence: float = 1.0):
        """Add provenance information for a data point."""
        self.source[key] = source
        self.confidence[key] = confidence

    def get_completeness_score(self) -> float:
        """Calculate overall data completeness score."""
        if not self.source:
            return 0.0

        weights = {"measured": 1.0, "inferred": 0.7, "default": 0.4, "prior": 0.3}
        total_weight = sum(weights.get(source, 0.5) for source in self.source.values())
        max_weight = len(self.source) * 1.0
        return total_weight / max_weight if max_weight > 0 else 0.0


# Default values for population priors
DEFAULT_1RM_KG = {
    # Intermediate level athlete defaults
    'back_squat': 120.0,
    'front_squat': 100.0,
    'oh_squat': 80.0,
    'strict_press': 65.0,
    'push_press': 75.0,
    'push_jerk': 85.0,
    'bench': 90.0,
    'deadlift': 140.0,
    'clean': 85.0,
    'snatch': 65.0,
    'clean_and_jerk': 85.0,
    'thruster': 70.0,
    'wall_ball': 25.0,
}

DEFAULT_CYCLE_TIMES = {
    # Conservative cycle times (seconds per rep)
    'pull_up': 2.0,
    'hspu': 2.5,
    'ttb': 2.2,
    'bmu': 8.0,
    'rmu': 10.0,
    'wb': 2.8,
    'du': 0.50,
    'su': 0.25,
    'burpee': 4.0,
    'box_jump': 2.0,
}

DEFAULT_CARDIO_PROFILES = {
    # Conservative cardio profiles
    'bike': {'cp': 200.0, 'w_prime': 12000.0},
    'row': {'cp': 180.0, 'w_prime': 10000.0},
    'run': {'cs': 3.2, 'd_prime': 300.0},  # m/s, meters
    'swim': {'cs': 1.2, 'd_prime': 100.0},
}


class InferenceEngine:
    """Implements smart inference rules for missing data."""

    @staticmethod
    def infer_1rm_from_relationships(benchmarks: UIBenchmarks, provenance: DataProvenance) -> Dict[str, float]:
        """Infer missing 1RM values using known relationships."""
        one_rm = {}

        # Helper to safely get and track source
        def safe_get_1rm(lift: str, fallback_fn=None) -> float:
            value = getattr(benchmarks, lift, None)
            if value and value > 0:
                provenance.add(f"1rm.{lift}", "measured", 1.0)
                return float(value)

            if fallback_fn:
                inferred = fallback_fn()
                if inferred:
                    provenance.add(f"1rm.{lift}", "inferred", 0.7)
                    return inferred

            default_val = DEFAULT_1RM_KG.get(lift, 80.0)
            provenance.add(f"1rm.{lift}", "default", 0.4)
            return default_val

        # Start with measured values
        back_squat = safe_get_1rm('back_squat')
        front_squat = safe_get_1rm('front_squat',
                                  lambda: back_squat * 0.85 if back_squat else None)
        oh_squat = safe_get_1rm('oh_squat',
                              lambda: front_squat * 0.80 if front_squat else None)

        strict_press = safe_get_1rm('strict_press')
        push_press = safe_get_1rm('push_press',
                                lambda: strict_press * 1.15 if strict_press else None)
        push_jerk = safe_get_1rm('push_jerk',
                               lambda: strict_press * 1.25 if strict_press else None)

        deadlift = safe_get_1rm('deadlift',
                              lambda: back_squat * 1.20 if back_squat else None)
        clean = safe_get_1rm('clean',
                           lambda: back_squat * 0.80 if back_squat else None)
        snatch = safe_get_1rm('snatch',
                            lambda: back_squat * 0.62 if back_squat else None)

        bench = safe_get_1rm('bench')
        clean_and_jerk = safe_get_1rm('clean_and_jerk',
                                    lambda: clean if clean else None)

        # Derived movements
        thruster_from_front = front_squat * 0.90 if front_squat else None
        thruster_from_press = strict_press * 1.15 if strict_press else None
        thruster = min(filter(None, [thruster_from_front, thruster_from_press])) if any([thruster_from_front, thruster_from_press]) else DEFAULT_1RM_KG['thruster']
        if thruster_from_front or thruster_from_press:
            provenance.add("1rm.thruster", "inferred", 0.7)
        else:
            provenance.add("1rm.thruster", "default", 0.4)

        return {
            'back_squat': back_squat,
            'front_squat': front_squat,
            'oh_squat': oh_squat,
            'strict_press': strict_press,
            'push_press': push_press,
            'push_jerk': push_jerk,
            'bench': bench,
            'deadlift': deadlift,
            'clean': clean,
            'snatch': snatch,
            'clean_and_jerk': clean_and_jerk,
            'thruster': thruster,
            'wall_ball': DEFAULT_1RM_KG['wall_ball'],  # Usually not 1RM based
        }

    @staticmethod
    def infer_gym_cycles(benchmarks: UIBenchmarks, provenance: DataProvenance) -> Dict[str, float]:
        """Infer gymnastics cycle times from available data."""
        cycles = {}

        def safe_get_cycle(movement: str, timed_field: str = None, max_field: str = None) -> float:
            # Try timed cycle first
            if timed_field:
                time_str = getattr(benchmarks, timed_field, None)
                if time_str and time_str.strip():
                    try:
                        total_seconds = parse_time_string(time_str)
                        reps = int(timed_field.split('_')[1].replace('du', '').replace('pu', '').replace('hspu', '').replace('ttb', '').replace('bmu', '').replace('rmu', '').replace('wb', ''))
                        cycle_time = total_seconds / reps
                        provenance.add(f"gym.{movement}.cycle", "measured", 1.0)
                        return cycle_time
                    except:
                        pass

            # Try to infer from max unbroken
            if max_field:
                max_reps = getattr(benchmarks, max_field, None)
                if max_reps and max_reps > 0:
                    # Formula: cycle ≈ clamp(1.0, 3.0, 30/max_reps)
                    inferred_cycle = max(1.0, min(3.0, 30.0 / max_reps))
                    provenance.add(f"gym.{movement}.cycle", "inferred", 0.6)
                    return inferred_cycle

            # Use default
            default_cycle = DEFAULT_CYCLE_TIMES.get(movement, 2.0)
            provenance.add(f"gym.{movement}.cycle", "default", 0.4)
            return default_cycle

        cycles['pull_up'] = safe_get_cycle('pull_up', 't_20pu', 'max_pullup')
        cycles['hspu'] = safe_get_cycle('hspu', 't_20hspu', 'max_hspu')
        cycles['ttb'] = safe_get_cycle('ttb', 't_20ttb', 'max_ttb')
        cycles['bmu'] = safe_get_cycle('bmu', 't_10bmu', 'max_bmu')
        cycles['rmu'] = safe_get_cycle('rmu', 't_5rmu', 'max_rmu')
        cycles['wb'] = safe_get_cycle('wb', 't_20wb', 'max_wb')
        cycles['du'] = safe_get_cycle('du', 't_60du', 'max_du')

        # Additional movements with defaults
        cycles['burpee'] = DEFAULT_CYCLE_TIMES['burpee']
        cycles['box_jump'] = DEFAULT_CYCLE_TIMES['box_jump']
        cycles['su'] = DEFAULT_CYCLE_TIMES['su']

        for movement in ['burpee', 'box_jump', 'su']:
            provenance.add(f"gym.{movement}.cycle", "default", 0.4)

        return cycles

    @staticmethod
    def infer_cardio_profiles(benchmarks: UIBenchmarks, provenance: DataProvenance) -> Dict[str, Dict[str, float]]:
        """Infer cardio CP/W' profiles from available data."""
        profiles = {}

        # Bike
        ftp = benchmarks.ftp_bike_w
        if ftp and ftp > 0:
            cp = ftp / 0.95  # FTP ≈ 95% of CP
            w_prime = 12000.0  # Default W' for bike
            profiles['bike'] = {'cp': cp, 'w_prime': w_prime}
            provenance.add("cardio.bike.cp", "measured", 0.9)
            provenance.add("cardio.bike.w_prime", "default", 0.4)
        else:
            profiles['bike'] = DEFAULT_CARDIO_PROFILES['bike'].copy()
            provenance.add("cardio.bike.cp", "default", 0.4)
            provenance.add("cardio.bike.w_prime", "default", 0.4)

        # Row
        row_500m = benchmarks.row_500m
        row_2k = benchmarks.row_2k

        if row_2k and row_2k.strip():
            try:
                time_2k = parse_time_string(row_2k)
                # Rough power estimation: P ≈ 2.8 / (time_per_500m)^3
                time_per_500 = time_2k / 4.0
                power_avg = 2.8 / (time_per_500 / 60.0) ** 3 * 100  # Watts
                cp = power_avg * 0.85  # 2k pace ≈ 115% of CP
                w_prime = 10000.0
                profiles['row'] = {'cp': cp, 'w_prime': w_prime}
                provenance.add("cardio.row.cp", "inferred", 0.7)
                provenance.add("cardio.row.w_prime", "default", 0.4)
            except:
                profiles['row'] = DEFAULT_CARDIO_PROFILES['row'].copy()
                provenance.add("cardio.row.cp", "default", 0.4)
                provenance.add("cardio.row.w_prime", "default", 0.4)
        else:
            profiles['row'] = DEFAULT_CARDIO_PROFILES['row'].copy()
            provenance.add("cardio.row.cp", "default", 0.4)
            provenance.add("cardio.row.w_prime", "default", 0.4)

        # Run
        run_400m = benchmarks.run_400m
        run_1600m = benchmarks.run_1600m

        if run_400m and run_1600m and run_400m.strip() and run_1600m.strip():
            try:
                time_400 = parse_time_string(run_400m)
                time_1600 = parse_time_string(run_1600m)

                speed_400 = 400.0 / time_400  # m/s
                speed_1600 = 1600.0 / time_1600  # m/s

                # Two-point CS/D' estimation
                # Using P = CS + D'/t model, where P is speed
                if time_400 != time_1600:
                    cs = (speed_400 * time_400 - speed_1600 * time_1600) / (time_400 - time_1600)
                    d_prime = (speed_400 - cs) * time_400

                    cs = max(2.0, min(6.0, cs))  # Clamp to reasonable range
                    d_prime = max(50.0, min(500.0, d_prime))

                    profiles['run'] = {'cs': cs, 'd_prime': d_prime}
                    provenance.add("cardio.run.cs", "inferred", 0.8)
                    provenance.add("cardio.run.d_prime", "inferred", 0.7)
                else:
                    profiles['run'] = DEFAULT_CARDIO_PROFILES['run'].copy()
                    provenance.add("cardio.run.cs", "default", 0.4)
                    provenance.add("cardio.run.d_prime", "default", 0.4)
            except:
                profiles['run'] = DEFAULT_CARDIO_PROFILES['run'].copy()
                provenance.add("cardio.run.cs", "default", 0.4)
                provenance.add("cardio.run.d_prime", "default", 0.4)
        else:
            profiles['run'] = DEFAULT_CARDIO_PROFILES['run'].copy()
            provenance.add("cardio.run.cs", "default", 0.4)
            provenance.add("cardio.run.d_prime", "default", 0.4)

        # Swim (defaults only for now)
        profiles['swim'] = DEFAULT_CARDIO_PROFILES['swim'].copy()
        provenance.add("cardio.swim.cs", "default", 0.4)
        provenance.add("cardio.swim.d_prime", "default", 0.4)

        return profiles


def apply_confidence_based_adjustments(capabilities: 'AthleteCapabilities', provenance: DataProvenance) -> 'AthleteCapabilities':
    """Apply conservative adjustments based on data confidence."""
    # For low-confidence data, make capabilities slightly more conservative
    # This prevents unrealistic strategies for uncertain parameters

    adjusted_caps = capabilities

    # Check 1RM confidence
    for movement, confidence in provenance.confidence.items():
        if movement.startswith("1rm.") and confidence < 0.6:
            lift_name = movement.replace("1rm.", "")
            if lift_name in adjusted_caps.one_rm:
                # Reduce by 5% for low confidence
                adjusted_caps.one_rm[lift_name] *= 0.95

    # Check gym cycle confidence
    for movement, confidence in provenance.confidence.items():
        if movement.startswith("gym.") and movement.endswith(".cycle") and confidence < 0.6:
            skill_name = movement.replace("gym.", "").replace(".cycle", "")
            if skill_name in adjusted_caps.gym_skills:
                # Increase cycle time by 10% for low confidence (slower = more conservative)
                adjusted_caps.gym_skills[skill_name].cycle_s *= 1.1

    # Check cardio confidence
    for movement, confidence in provenance.confidence.items():
        if movement.startswith("cardio.") and confidence < 0.6:
            parts = movement.split(".")
            if len(parts) >= 3:
                modality = parts[1]
                param = parts[2]
                if modality in adjusted_caps.cardio_profiles:
                    if param == "cp" and modality in ["bike", "row"]:
                        # Reduce CP by 5% for low confidence
                        adjusted_caps.cardio_profiles[modality].cp *= 0.95
                    elif param == "cs" and modality in ["run", "swim"]:
                        # Reduce CS by 5% for low confidence
                        adjusted_caps.cardio_profiles[modality].cp *= 0.95  # cs stored as cp

    return adjusted_caps


def is_low_confidence_movement(movement: str, provenance: DataProvenance) -> bool:
    """Check if a movement has low confidence data."""
    relevant_keys = [
        f"1rm.{movement}",
        f"gym.{movement}.cycle",
        f"cardio.{movement}.cp",
        f"cardio.{movement}.cs"
    ]

    confidences = [provenance.confidence.get(key, 0.0) for key in relevant_keys if key in provenance.confidence]

    if not confidences:
        return True  # No data = low confidence

    avg_confidence = sum(confidences) / len(confidences)
    return avg_confidence < 0.6
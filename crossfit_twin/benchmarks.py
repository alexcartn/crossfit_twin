"""
UI Benchmarks module for CrossFit Digital Twin.

Contains dataclasses for capturing user benchmark inputs and converting them
to athlete capabilities with concrete, measurable parameters.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import re


@dataclass
class UIBenchmarks:
    """
    User interface benchmarks capturing all performance inputs.
    All times should be in "mm:ss" format, weights in kg, distances in meters.
    """

    # === WEIGHTLIFTING BENCHMARKS (kg) ===
    back_squat: Optional[float] = None
    front_squat: Optional[float] = None
    oh_squat: Optional[float] = None
    strict_press: Optional[float] = None
    push_press: Optional[float] = None
    push_jerk: Optional[float] = None
    bench: Optional[float] = None
    deadlift: Optional[float] = None
    power_snatch: Optional[float] = None
    snatch: Optional[float] = None
    power_clean: Optional[float] = None
    clean: Optional[float] = None
    clean_and_jerk: Optional[float] = None

    # === GYMNASTICS BENCHMARKS ===
    # Max unbroken reps
    max_hspu: Optional[int] = None
    max_pullup: Optional[int] = None
    max_ttb: Optional[int] = None
    max_bmu: Optional[int] = None
    max_rmu: Optional[int] = None
    max_wb: Optional[int] = None
    max_du: Optional[int] = None

    # Time trials for set rep counts (format: "mm:ss")
    t_60du: Optional[str] = None        # 60 double unders
    t_20wb: Optional[str] = None        # 20 wall balls
    t_20pu: Optional[str] = None        # 20 pull-ups
    t_20ttb: Optional[str] = None       # 20 toes to bar
    t_10bmu: Optional[str] = None       # 10 bar muscle ups
    t_5rmu: Optional[str] = None        # 5 ring muscle ups
    t_20hspu: Optional[str] = None      # 20 handstand push ups
    t_hswalk_15m: Optional[str] = None  # 15m handstand walk

    # === MONOSTRUCTURAL BENCHMARKS ===
    # Bike
    ftp_bike_w: Optional[int] = None    # FTP in watts

    # Rowing (format: "mm:ss")
    row_500m: Optional[str] = None
    row_2k: Optional[str] = None
    row_5k: Optional[str] = None

    # Running (format: "mm:ss")
    run_100m: Optional[str] = None
    run_400m: Optional[str] = None
    run_1600m: Optional[str] = None
    run_5k: Optional[str] = None

    # Swimming (format: "mm:ss")
    swim_50m: Optional[str] = None
    swim_100m: Optional[str] = None
    swim_200m: Optional[str] = None

    # === CROSSFIT METCON BENCHMARKS (format: "mm:ss") ===
    fran: Optional[str] = None
    amanda: Optional[str] = None
    diane: Optional[str] = None
    helen: Optional[str] = None
    angie: Optional[str] = None
    cindy: Optional[int] = None         # rounds in 20 minutes
    grace: Optional[str] = None
    isabel: Optional[str] = None
    nancy: Optional[str] = None
    mary: Optional[str] = None
    murph_vest: Optional[str] = None    # with vest
    nate: Optional[int] = None          # rounds in 20 minutes
    fight_gone_bad: Optional[int] = None # total points
    filthy_50: Optional[str] = None


def parse_time_string(time_str: Optional[str]) -> Optional[float]:
    """
    Parse time string in various formats to seconds.

    Supports:
    - "mm:ss" (e.g., "7:30" -> 450.0)
    - "mm:ss.cc" (e.g., "7:30.50" -> 450.5)
    - "ss" or "ss.cc" (e.g., "45.2" -> 45.2)

    Args:
        time_str: Time string to parse

    Returns:
        Time in seconds, or None if invalid/empty
    """
    if not time_str or not time_str.strip():
        return None

    time_str = time_str.strip()

    # Handle mm:ss or mm:ss.cc format
    if ':' in time_str:
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return None
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60.0 + seconds
        except (ValueError, IndexError):
            return None

    # Handle pure seconds format
    try:
        return float(time_str)
    except ValueError:
        return None


def validate_benchmarks(benchmarks: UIBenchmarks) -> Dict[str, str]:
    """
    Validate benchmark inputs and return any errors found.

    Args:
        benchmarks: UIBenchmarks instance to validate

    Returns:
        Dictionary mapping field names to error messages
    """
    errors = {}

    # Validate weights are positive
    weight_fields = [
        'back_squat', 'front_squat', 'oh_squat', 'strict_press', 'push_press',
        'push_jerk', 'bench', 'deadlift', 'power_snatch', 'snatch',
        'power_clean', 'clean', 'clean_and_jerk'
    ]

    for field in weight_fields:
        value = getattr(benchmarks, field)
        if value is not None and value <= 0:
            errors[field] = f"{field} must be positive"

    # Validate rep counts are positive integers
    rep_fields = [
        'max_hspu', 'max_pullup', 'max_ttb', 'max_bmu', 'max_rmu',
        'max_wb', 'max_du', 'cindy', 'nate', 'fight_gone_bad'
    ]

    for field in rep_fields:
        value = getattr(benchmarks, field)
        if value is not None and (not isinstance(value, int) or value <= 0):
            errors[field] = f"{field} must be a positive integer"

    # Validate time strings can be parsed
    time_fields = [
        't_60du', 't_20wb', 't_20pu', 't_20ttb', 't_10bmu', 't_5rmu',
        't_20hspu', 't_hswalk_15m', 'row_500m', 'row_2k', 'row_5k',
        'run_100m', 'run_400m', 'run_1600m', 'run_5k', 'swim_50m',
        'swim_100m', 'swim_200m', 'fran', 'amanda', 'diane', 'helen',
        'angie', 'grace', 'isabel', 'nancy', 'mary', 'murph_vest', 'filthy_50'
    ]

    for field in time_fields:
        time_str = getattr(benchmarks, field)
        if time_str is not None:
            parsed_time = parse_time_string(time_str)
            if parsed_time is None:
                errors[field] = f"{field} has invalid time format (use mm:ss or seconds)"
            elif parsed_time <= 0:
                errors[field] = f"{field} time must be positive"

    # Validate FTP is positive
    if benchmarks.ftp_bike_w is not None and benchmarks.ftp_bike_w <= 0:
        errors['ftp_bike_w'] = "FTP must be positive"

    # Cross-validation: related lifts should be in logical order
    if benchmarks.power_clean and benchmarks.clean:
        if benchmarks.power_clean > benchmarks.clean:
            errors['clean'] = "Clean should be >= Power Clean"

    if benchmarks.power_snatch and benchmarks.snatch:
        if benchmarks.power_snatch > benchmarks.snatch:
            errors['snatch'] = "Snatch should be >= Power Snatch"

    if benchmarks.front_squat and benchmarks.back_squat:
        if benchmarks.front_squat > benchmarks.back_squat:
            errors['back_squat'] = "Back Squat should be >= Front Squat"

    return errors


def get_benchmark_summary(benchmarks: UIBenchmarks) -> str:
    """
    Generate a human-readable summary of provided benchmarks.

    Args:
        benchmarks: UIBenchmarks instance

    Returns:
        Formatted summary string
    """
    summary_lines = []

    # Count provided benchmarks by category
    weightlifting_count = sum(1 for field in [
        'back_squat', 'front_squat', 'oh_squat', 'strict_press', 'push_press',
        'push_jerk', 'bench', 'deadlift', 'power_snatch', 'snatch',
        'power_clean', 'clean', 'clean_and_jerk'
    ] if getattr(benchmarks, field) is not None)

    gymnastics_count = sum(1 for field in [
        'max_hspu', 'max_pullup', 'max_ttb', 'max_bmu', 'max_rmu', 'max_wb',
        'max_du', 't_60du', 't_20wb', 't_20pu', 't_20ttb', 't_10bmu',
        't_5rmu', 't_20hspu', 't_hswalk_15m'
    ] if getattr(benchmarks, field) is not None)

    monostructural_count = sum(1 for field in [
        'ftp_bike_w', 'row_500m', 'row_2k', 'row_5k', 'run_100m', 'run_400m',
        'run_1600m', 'run_5k', 'swim_50m', 'swim_100m', 'swim_200m'
    ] if getattr(benchmarks, field) is not None)

    metcon_count = sum(1 for field in [
        'fran', 'amanda', 'diane', 'helen', 'angie', 'cindy', 'grace',
        'isabel', 'nancy', 'mary', 'murph_vest', 'nate', 'fight_gone_bad', 'filthy_50'
    ] if getattr(benchmarks, field) is not None)

    summary_lines.append(f"Benchmark Summary:")
    summary_lines.append(f"  Weightlifting: {weightlifting_count} benchmarks")
    summary_lines.append(f"  Gymnastics: {gymnastics_count} benchmarks")
    summary_lines.append(f"  Monostructural: {monostructural_count} benchmarks")
    summary_lines.append(f"  MetCons: {metcon_count} benchmarks")
    summary_lines.append(f"  Total: {weightlifting_count + gymnastics_count + monostructural_count + metcon_count} benchmarks")

    return "\n".join(summary_lines)
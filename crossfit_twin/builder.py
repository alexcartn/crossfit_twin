"""
Builder module for converting UI benchmarks to athlete capabilities.

Transforms user benchmark inputs into concrete physiological models.
"""

from typing import Dict, Optional, Tuple, List
import math
from .benchmarks import UIBenchmarks, parse_time_string
from .capabilities import AthleteCapabilities, BarbellProfile, CPProfile, GymSkill


def ftp_to_critical_power(ftp_watts: float) -> float:
    """
    Convert FTP (Functional Threshold Power) to Critical Power.

    Args:
        ftp_watts: FTP in watts

    Returns:
        Estimated Critical Power in watts
    """
    # FTP is typically ~95% of CP for 1-hour duration
    return ftp_watts / 0.95


def two_point_cp_estimation(
    duration1_s: float, power1_w: float,
    duration2_s: float, power2_w: float
) -> Tuple[float, float]:
    """
    Estimate CP and W' from two power-duration points.

    Uses the hyperbolic model: P = CP + W'/t

    Args:
        duration1_s: First duration in seconds
        power1_w: First power in watts
        duration2_s: Second duration in seconds
        power2_w: Second power in watts

    Returns:
        Tuple of (CP in watts, W' in joules)
    """
    if duration1_s == duration2_s:
        return power1_w, 0.0

    # Solve linear system:
    # P1 = CP + W'/t1
    # P2 = CP + W'/t2
    # CP = (P1*t1 - P2*t2) / (t1 - t2)
    # W' = (P2 - P1) * t1 * t2 / (t1 - t2)

    cp = (power1_w * duration1_s - power2_w * duration2_s) / (duration1_s - duration2_s)
    w_prime = (power2_w - power1_w) * duration1_s * duration2_s / (duration1_s - duration2_s)

    return max(0, cp), max(0, w_prime)


def two_point_cs_estimation(
    distance1_m: float, time1_s: float,
    distance2_m: float, time2_s: float
) -> Tuple[float, float]:
    """
    Estimate CS (Critical Speed) and D' from two distance-time points.

    Uses the hyperbolic model: t = d/CS + D'/CS

    Args:
        distance1_m: First distance in meters
        time1_s: First time in seconds
        distance2_m: Second distance in meters
        time2_s: Second time in seconds

    Returns:
        Tuple of (CS in m/s, D' in meters)
    """
    if time1_s == time2_s:
        return distance1_m / time1_s, 0.0

    # Solve for CS and D':
    # t1 = d1/CS + D'/CS
    # t2 = d2/CS + D'/CS
    # CS = (d2 - d1) / (t2 - t1)
    # D' = CS * (t1 - d1/CS)

    cs = (distance2_m - distance1_m) / (time2_s - time1_s)
    if cs <= 0:
        return 0.1, 0.0  # Fallback for invalid data

    d_prime = cs * time1_s - distance1_m

    return cs, max(0, d_prime)


def estimate_rowing_power(distance_m: float, time_s: float, body_mass_kg: float) -> float:
    """
    Estimate rowing power from distance and time.

    Uses simplified Concept2 power calculation.

    Args:
        distance_m: Distance rowed in meters
        time_s: Time taken in seconds
        body_mass_kg: Body mass in kg

    Returns:
        Estimated average power in watts
    """
    if time_s <= 0:
        return 0.0

    # Concept2 pace to power relationship (simplified)
    # P = 2.8 / (pace/500)^3 where pace is seconds per 500m
    pace_per_500m = time_s * 500.0 / distance_m
    power = 2.8 / ((pace_per_500m / 500.0) ** 3)

    # Rough scaling factor
    return power * 1000.0  # Convert to watts (approximate)


def build_weightlifting_capabilities(benchmarks: UIBenchmarks) -> Dict[str, float]:
    """
    Build 1RM dictionary from benchmark inputs.

    Args:
        benchmarks: UI benchmark inputs

    Returns:
        Dictionary mapping movement names to 1RM values in kg
    """
    one_rm = {}

    # Direct 1RM inputs
    if benchmarks.back_squat:
        one_rm['back-squat'] = benchmarks.back_squat
    if benchmarks.front_squat:
        one_rm['front-squat'] = benchmarks.front_squat
    if benchmarks.oh_squat:
        one_rm['overhead-squat'] = benchmarks.oh_squat
    if benchmarks.strict_press:
        one_rm['overhead-press'] = benchmarks.strict_press
    if benchmarks.push_press:
        one_rm['push-press'] = benchmarks.push_press
    if benchmarks.push_jerk:
        one_rm['push-jerk'] = benchmarks.push_jerk
    if benchmarks.bench:
        one_rm['bench-press'] = benchmarks.bench
    if benchmarks.deadlift:
        one_rm['deadlift'] = benchmarks.deadlift
    if benchmarks.power_snatch:
        one_rm['power-snatch'] = benchmarks.power_snatch
    if benchmarks.snatch:
        one_rm['snatch'] = benchmarks.snatch
    if benchmarks.power_clean:
        one_rm['power-clean'] = benchmarks.power_clean
    if benchmarks.clean:
        one_rm['clean'] = benchmarks.clean
    if benchmarks.clean_and_jerk:
        one_rm['clean-and-jerk'] = benchmarks.clean_and_jerk

    return one_rm


def build_gymnastics_capabilities(benchmarks: UIBenchmarks) -> Dict[str, GymSkill]:
    """
    Build gymnastics capabilities from benchmark inputs.

    Args:
        benchmarks: UI benchmark inputs

    Returns:
        Dictionary mapping skill names to GymSkill profiles
    """
    gym_skills = {}

    # Helper function to calculate cycle time from timed set
    def calculate_cycle_time(time_str: Optional[str], rep_count: int, fallback_s: float) -> float:
        if time_str:
            total_time = parse_time_string(time_str)
            if total_time and total_time > 0:
                return total_time / rep_count
        return fallback_s

    # Pull-ups
    cycle_time = calculate_cycle_time(benchmarks.t_20pu, 20, 1.5)
    unbroken_cap = benchmarks.max_pullup or 12
    gym_skills['pull-up'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Toes to Bar
    cycle_time = calculate_cycle_time(benchmarks.t_20ttb, 20, 2.0)
    unbroken_cap = benchmarks.max_ttb or 10
    gym_skills['toes-to-bar'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Handstand Push-ups
    cycle_time = calculate_cycle_time(benchmarks.t_20hspu, 20, 2.5)
    unbroken_cap = benchmarks.max_hspu or 8
    gym_skills['handstand-pushup'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Bar Muscle-ups
    cycle_time = calculate_cycle_time(benchmarks.t_10bmu, 10, 3.0)
    unbroken_cap = benchmarks.max_bmu or 5
    gym_skills['bar-muscle-up'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Ring Muscle-ups
    cycle_time = calculate_cycle_time(benchmarks.t_5rmu, 5, 4.0)
    unbroken_cap = benchmarks.max_rmu or 3
    gym_skills['ring-muscle-up'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Double Unders
    cycle_time = calculate_cycle_time(benchmarks.t_60du, 60, 0.5)
    unbroken_cap = benchmarks.max_du or 100
    gym_skills['double-under'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Wall Balls
    cycle_time = calculate_cycle_time(benchmarks.t_20wb, 20, 2.2)
    unbroken_cap = benchmarks.max_wb or 25
    gym_skills['wall-ball'] = GymSkill(cycle_s=cycle_time, unbroken_cap=unbroken_cap)

    # Handstand Walk (special case - distance based)
    if benchmarks.t_hswalk_15m:
        total_time = parse_time_string(benchmarks.t_hswalk_15m)
        if total_time and total_time > 0:
            speed_ms = 15.0 / total_time  # m/s
            gym_skills['handstand-walk'] = GymSkill(
                cycle_s=1.0 / speed_ms,  # seconds per meter
                unbroken_cap=15
            )

    return gym_skills


def build_cardio_capabilities(benchmarks: UIBenchmarks, body_mass_kg: float) -> Dict[str, CPProfile]:
    """
    Build cardio capabilities from benchmark inputs.

    Args:
        benchmarks: UI benchmark inputs
        body_mass_kg: Body mass in kg

    Returns:
        Dictionary mapping modality names to CPProfile
    """
    cardio_profiles = {}

    # === BIKE ===
    if benchmarks.ftp_bike_w:
        cp_watts = ftp_to_critical_power(benchmarks.ftp_bike_w)
        # Estimate W' based on typical values (12-25 kJ for trained athletes)
        w_prime = 15000.0  # 15 kJ default
        cardio_profiles['bike'] = CPProfile(cp=cp_watts, w_prime=w_prime)

    # === ROWING ===
    # Try to estimate CP/W' from multiple rowing distances
    row_times = {}
    if benchmarks.row_500m:
        row_times[500] = parse_time_string(benchmarks.row_500m)
    if benchmarks.row_2k:
        row_times[2000] = parse_time_string(benchmarks.row_2k)
    if benchmarks.row_5k:
        row_times[5000] = parse_time_string(benchmarks.row_5k)

    # Use 2k and 5k for CP estimation if both available
    if 2000 in row_times and 5000 in row_times and row_times[2000] and row_times[5000]:
        power_2k = estimate_rowing_power(2000, row_times[2000], body_mass_kg)
        power_5k = estimate_rowing_power(5000, row_times[5000], body_mass_kg)

        cp, w_prime = two_point_cp_estimation(
            row_times[2000], power_2k,
            row_times[5000], power_5k
        )

        if cp > 0:
            cardio_profiles['row'] = CPProfile(cp=cp, w_prime=w_prime)

    # === RUNNING ===
    # Try different distance combinations for CS/D' estimation
    run_times = {}
    distances = {
        'run_100m': 100,
        'run_400m': 400,
        'run_1600m': 1600,
        'run_5k': 5000
    }

    for attr, distance in distances.items():
        time_str = getattr(benchmarks, attr)
        if time_str:
            parsed_time = parse_time_string(time_str)
            if parsed_time:
                run_times[distance] = parsed_time

    # Prefer 400m and 1600m for CS estimation (good anaerobic vs aerobic split)
    if 400 in run_times and 1600 in run_times:
        cs, d_prime = two_point_cs_estimation(
            400, run_times[400],
            1600, run_times[1600]
        )
    elif 1600 in run_times and 5000 in run_times:
        cs, d_prime = two_point_cs_estimation(
            1600, run_times[1600],
            5000, run_times[5000]
        )
    else:
        cs, d_prime = None, None

    if cs and cs > 0:
        cardio_profiles['run'] = CPProfile(cp=cs, w_prime=d_prime)

    # === SWIMMING ===
    swim_times = {}
    swim_distances = {
        'swim_50m': 50,
        'swim_100m': 100,
        'swim_200m': 200
    }

    for attr, distance in swim_distances.items():
        time_str = getattr(benchmarks, attr)
        if time_str:
            parsed_time = parse_time_string(time_str)
            if parsed_time:
                swim_times[distance] = parsed_time

    # Use 100m and 200m for swimming CS estimation
    if 100 in swim_times and 200 in swim_times:
        cs, d_prime = two_point_cs_estimation(
            100, swim_times[100],
            200, swim_times[200]
        )

        if cs and cs > 0:
            cardio_profiles['swim'] = CPProfile(cp=cs, w_prime=d_prime)

    return cardio_profiles


def build_athlete_from_benchmarks(
    name: str,
    body_mass_kg: float,
    benchmarks: UIBenchmarks,
    height_cm: Optional[float] = None,
    barbell_profile: Optional[BarbellProfile] = None
) -> AthleteCapabilities:
    """
    Build complete athlete capabilities from UI benchmarks.

    Args:
        name: Athlete name
        body_mass_kg: Body mass in kg
        benchmarks: UI benchmark inputs
        height_cm: Height in cm (optional)
        barbell_profile: Custom barbell profile (optional)

    Returns:
        AthleteCapabilities with all available data
    """
    # Build components
    one_rm = build_weightlifting_capabilities(benchmarks)
    gym_skills = build_gymnastics_capabilities(benchmarks)
    cardio_profiles = build_cardio_capabilities(benchmarks, body_mass_kg)

    # Use provided barbell profile or default
    if barbell_profile is None:
        barbell_profile = BarbellProfile()

    return AthleteCapabilities(
        body_mass_kg=body_mass_kg,
        height_cm=height_cm,
        one_rm=one_rm,
        barbell_profile=barbell_profile,
        gym_skills=gym_skills,
        cardio_profiles=cardio_profiles
    )


def estimate_missing_lifts(capabilities: AthleteCapabilities) -> None:
    """
    Estimate missing 1RM values based on available lifts and typical ratios.

    Modifies the capabilities object in place.

    Args:
        capabilities: AthleteCapabilities object to modify
    """
    # Typical strength ratios relative to back squat
    squat_ratios = {
        'front-squat': 0.85,
        'overhead-squat': 0.65,
        'deadlift': 1.2,
        'clean': 0.8,
        'snatch': 0.65,
        'overhead-press': 0.5,
        'bench-press': 0.9,
        'thruster': 0.6,
    }

    # If we have back squat, estimate others
    if 'back-squat' in capabilities.one_rm:
        back_squat = capabilities.one_rm['back-squat']
        for movement, ratio in squat_ratios.items():
            if movement not in capabilities.one_rm:
                capabilities.one_rm[movement] = back_squat * ratio

    # Alternative base movements for estimation
    if 'clean' in capabilities.one_rm and 'back-squat' not in capabilities.one_rm:
        clean = capabilities.one_rm['clean']
        # Estimate back squat from clean (clean is typically ~80% of back squat)
        estimated_back_squat = clean / 0.8
        capabilities.one_rm['back-squat'] = estimated_back_squat

        # Now estimate others from back squat
        for movement, ratio in squat_ratios.items():
            if movement not in capabilities.one_rm:
                capabilities.one_rm[movement] = estimated_back_squat * ratio
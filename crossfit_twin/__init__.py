"""
CrossFit Digital Twin Library

A Python library for simulating CrossFit athlete performance and optimizing pacing strategies.

V2 Features:
- Concrete physiological parameters (1RM, CP/W', cycle times)
- RPE-based strategy selection
- Advanced fatigue modeling (W'bal + local muscle fatigue)
- Environmental context effects
"""

# Legacy system (v1)
from .athlete import Athlete
from .workout import WOD, Exercise
from .strategy import Strategy
from .simulator import simulate, SimulationResult

# New system (v2) - recommended
from .benchmarks import UIBenchmarks, parse_time_string, validate_benchmarks
from .capabilities import AthleteCapabilities, BarbellProfile, CPProfile, GymSkill
from .builder import build_athlete_from_benchmarks, estimate_missing_lifts
from .athlete_v2 import AthleteV2, ContextParams, DayState
from .fatigue_models import FatigueManager, MovementPattern
from .rpe_strategy import RPEStrategy, create_rpe_strategy, RPELevel

# Advanced optimization features
from .strategy_solver import StrategySolver, StrategySolution, CandidateStrategy
from .operational_whatif import OperationalAnalyzer, OperationalParameter, WhatIfResult
from .clone_optimization import CloneOptimizer, ParameterVariation, CloneOptimization
from .sensitivity_analysis import SensitivityAnalyzer, SensitivityResult

__version__ = "0.2.0"

# Legacy exports
__all__ = [
    "Athlete",
    "WOD",
    "Exercise",
    "Strategy",
    "simulate",
    "SimulationResult",
]

# V2 exports
__all__.extend([
    # Data input
    "UIBenchmarks",
    "parse_time_string",
    "validate_benchmarks",

    # Capabilities
    "AthleteCapabilities",
    "BarbellProfile",
    "CPProfile",
    "GymSkill",

    # Builder
    "build_athlete_from_benchmarks",
    "estimate_missing_lifts",

    # New athlete system
    "AthleteV2",
    "ContextParams",
    "DayState",

    # Fatigue models
    "FatigueManager",
    "MovementPattern",

    # RPE strategy
    "RPEStrategy",
    "create_rpe_strategy",
    "RPELevel",

    # Advanced optimization
    "StrategySolver",
    "StrategySolution",
    "CandidateStrategy",
    "OperationalAnalyzer",
    "OperationalParameter",
    "WhatIfResult",
    "CloneOptimizer",
    "ParameterVariation",
    "CloneOptimization",
    "SensitivityAnalyzer",
    "SensitivityResult",
])
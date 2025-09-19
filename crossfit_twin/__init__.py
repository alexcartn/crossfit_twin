"""
CrossFit Digital Twin Library

A Python library for simulating CrossFit athlete performance and optimizing pacing strategies.
"""

from .athlete import Athlete
from .workout import WOD, Exercise
from .strategy import Strategy
from .simulator import simulate, SimulationResult

__version__ = "0.1.0"
__all__ = [
    "Athlete",
    "WOD", 
    "Exercise",
    "Strategy",
    "simulate",
    "SimulationResult",
]
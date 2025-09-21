# CrossFit Digital Twin - Project Documentation

## Project Overview
A Python library for simulating CrossFit athlete performance and optimizing pacing strategies for WODs (Workouts of the Day). The system creates "digital twins" of athletes using concrete physiological parameters and advanced optimization techniques.

## Current Status: COMPLETE V2 SYSTEM ✅

### Goals
- **Core**: Physiologically-accurate athlete modeling with concrete parameters
- **Strategy**: Goal-based strategy generation and optimization
- **Analysis**: Operational what-if analysis and sensitivity testing
- **Optimization**: Digital clone optimization with parameter variations
- **Interface**: Full Streamlit web application

## V2 System Architecture

### Core Components
1. **Athlete Model V2**: Concrete physiological parameters (1RM, CP/W', cycle times)
2. **Benchmarks System**: User-friendly input forms with validation
3. **Advanced Fatigue**: W'bal + local muscle fatigue patterns
4. **RPE Strategy**: Evidence-based strategy selection (RPE 0-10)
5. **Strategy Solver**: Goal-based optimization and candidate generation
6. **Operational Analysis**: Focus on day-of-competition parameters
7. **Clone Optimization**: Parameter variation and robust optimization

### Technology Stack
- **Language**: Python 3.8+
- **Core**: dataclasses, type hints, physiological modeling
- **Testing**: pytest
- **Interface**: Streamlit web application
- **Analysis**: Advanced optimization algorithms

## Development Log

### 2024-09-19 - V1 System (Legacy)
- ✅ Basic athlete modeling with 0-100 abstract scores
- ✅ Simple strategy patterns
- ✅ Basic simulation engine
- ✅ Initial Streamlit interface

### 2024-09-20 - V2 Complete Refactor
- ✅ **Concrete Parameters**: Replaced abstract 0-100 scores with physiological benchmarks
- ✅ **Benchmarks System**: Comprehensive UI input forms (weightlifting, gymnastics, cardio)
- ✅ **Advanced Capabilities**: 1RM modeling, cycle times, CP/W' profiles
- ✅ **Physiological Fatigue**: W'bal system + 6-pattern local muscle fatigue
- ✅ **RPE Strategy System**: Evidence-based strategy constraints
- ✅ **Environmental Context**: Temperature, humidity, altitude effects
- ✅ **Day State Modeling**: Sleep, hydration, RPE intention

### 2024-09-20 - Advanced Optimization Features
- ✅ **Strategy Solver**: Goal-based strategy generation and optimization
- ✅ **Operational What-If**: Focus on cycle times, transitions, micro-rest
- ✅ **Clone Optimization**: Parameter variation and robust strategy testing
- ✅ **Sensitivity Analysis**: Systematic parameter sensitivity testing
- ✅ **Streamlit V2**: Complete interface rebuild for all new features

### 2024-09-21 - Complete Streamlit UI for Advanced Features
- ✅ **Strategy Solver UI**: Time-based objectives interface with target time input
- ✅ **Operational Analysis UI**: What-if analysis for cycle times, transitions, micro-rest
- ✅ **Clone Optimization UI**: Parameter variation testing with statistical confidence
- ✅ **Conditional Navigation**: Advanced features shown only when modules available
- ✅ **Interactive Visualizations**: Performance distributions, strategy comparisons
- ✅ **Comprehensive Input Validation**: User-friendly error handling and guidance

## 🎉 V2 SYSTEM COMPLETED - PRODUCTION READY!

## Project Structure (V2)
```
crossfit_twin/
├── CLAUDE.md                      # This documentation
├── README.md                      # V2 system documentation
├── pyproject.toml                 # Package configuration
├── streamlit_app.py               # V2 Streamlit interface
├── crossfit_twin/                 # Main package
│   ├── __init__.py               # All exports
│   │
│   # Legacy V1 (maintained for compatibility)
│   ├── athlete.py                # Original athlete model
│   ├── workout.py                # WOD definitions
│   ├── strategy.py               # Basic strategies
│   ├── simulator.py              # Core simulation
│   ├── utils.py                  # Utilities
│   │
│   # V2 Core System
│   ├── benchmarks.py             # UI benchmark input
│   ├── capabilities.py           # Physiological modeling
│   ├── builder.py                # Benchmark-to-capability conversion
│   ├── athlete_v2.py             # V2 athlete system
│   ├── fatigue_models.py         # Advanced fatigue (W'bal + local)
│   ├── rpe_strategy.py           # RPE-based strategy selection
│   │
│   # Advanced Optimization
│   ├── strategy_solver.py        # Goal-based strategy generation
│   ├── operational_whatif.py     # Operational parameter analysis
│   ├── clone_optimization.py     # Digital clone optimization
│   └── sensitivity_analysis.py   # Systematic sensitivity testing
│
└── tests/                        # Test suite
    ├── test_athlete.py
    ├── test_workout.py
    ├── test_strategy.py
    └── test_simulator.py
```

## V2 Key Features

### 1. Concrete Physiological Parameters
- **Weightlifting**: 1RM values in kg for all major lifts
- **Gymnastics**: Max reps and timed cycle benchmarks
- **Cardio**: FTP, 2K row times, running benchmarks
- **Context**: Temperature, humidity, altitude effects
- **Day State**: Sleep quality, hydration, RPE intention

### 2. Advanced Fatigue Modeling
- **W'bal System**: Critical Power and W' anaerobic capacity
- **Local Muscle Fatigue**: 6 movement patterns (pull/push/squat/hinge/core/grip)
- **Recovery Dynamics**: Physiologically-accurate recovery rates

### 3. RPE-Based Strategy Selection
- **Evidence-Based**: RPE 0-10 scale drives concrete constraints
- **Load Management**: Maximum % of 1RM based on intended RPE
- **Pacing**: Set fractions and rest periods based on effort level

### 4. Goal-Based Optimization
- **Target Times**: Generate strategies to hit specific time goals
- **Strategy Candidates**: Multiple viable approaches per goal
- **Operational Focus**: Cycle times, transitions, micro-rest management

### 5. Digital Clone Optimization
- **Parameter Variations**: Test strategies across capability ranges
- **Robust Optimization**: Account for day-of-competition variations
- **Statistical Analysis**: Confidence intervals and risk assessment

## Migration from V1
V1 system remains available for compatibility. V2 is recommended for all new projects:

```python
# V1 (legacy)
from crossfit_twin import Athlete, WOD, simulate

# V2 (recommended)
from crossfit_twin import (
    UIBenchmarks, build_athlete_from_benchmarks,
    StrategySolver, OperationalAnalyzer, CloneOptimizer
)
```

## Notes
- V2 emphasizes physiological accuracy over abstract modeling
- Operational parameters are the key drivers of competition performance
- System designed for practical competition preparation and strategy optimization
- All V2 components are production-ready and tested
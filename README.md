# CrossFit Digital Twin 🏋️

A comprehensive Python library for simulating CrossFit athlete performance and optimizing pacing strategies for WODs (Workouts of the Day).

## Overview

This project creates "digital twins" of CrossFit athletes that can be used to:
- **Simulate performance** on different WODs with realistic fatigue modeling
- **Test pacing strategies** (unbroken, fractioned, descending, conservative)
- **Find optimal approaches** through parameter variations and athlete cloning
- **Compare different scenarios** with comprehensive performance analysis
- **Validate training decisions** with data-driven insights

## 🚀 Features

### Core Simulation Engine
- **Realistic Fatigue Modeling**: Sophisticated fatigue accumulation and recovery
- **Multiple WOD Types**: For Time, AMRAP, with extensibility for EMOM and others
- **Comprehensive Event Tracking**: Detailed simulation logs and performance metrics
- **Strategy-Based Pacing**: Intelligent rest decisions based on fatigue and strategy

### Athlete Modeling
- **Physical Parameters**: Strength, endurance, fatigue resistance, recovery rate
- **Experience Levels**: Beginner to elite with automatic performance adjustments
- **Custom Max Lifts**: Personalized strength standards for accurate simulation
- **Cloning System**: Generate variations to test different scenarios

### Pacing Strategies
- **Unbroken**: Go all-out until forced to rest
- **Fractioned**: Planned rest breaks with customizable patterns
- **Descending**: Decreasing set sizes to manage fatigue
- **Conservative**: Proactive rest to maintain consistent pace
- **Custom**: Extensible strategy system for specialized approaches

### Analysis Tools
- **Parameter Sweeps**: Test how athlete attributes affect performance
- **Strategy Comparison**: Find optimal pacing for specific WODs
- **Performance Analytics**: Statistical analysis and visualization
- **Experiment Framework**: Systematic testing with comprehensive results

### User Interface
- **Streamlit Web App**: User-friendly interface for non-programmers
- **Interactive Visualizations**: Performance charts and fatigue curves
- **Famous WODs**: Pre-loaded benchmark workouts (Fran, Helen, Cindy)
- **Custom WOD Builder**: Create and test your own workouts

## 📦 Installation

### From Source (Development)
```bash
git clone https://github.com/yourusername/crossfit-twin.git
cd crossfit-twin
pip install -e .
```

### Dependencies
```bash
pip install -r requirements-dev.txt  # For development
pip install streamlit plotly          # For web interface
```

## 🚀 Quick Start

### Basic Simulation
```python
from crossfit_twin import Athlete, simulate
from crossfit_twin.workout import FamousWODs
from crossfit_twin.strategy import StrategyFactory

# Create an athlete
athlete = Athlete(
    name="Demo Athlete",
    strength=75.0,
    endurance=70.0,
    fatigue_resistance=65.0,
    recovery_rate=75.0,
    weight_kg=70.0
)

# Get a famous workout
fran = FamousWODs.fran()

# Choose a strategy
strategy = StrategyFactory.descending()

# Run simulation
result = simulate(fran, athlete, strategy, verbose=True)
print(f"Completed in: {result.total_time:.1f} seconds")
```

### Strategy Comparison
```python
from crossfit_twin.utils import compare_all_strategies

# Compare all strategies on Fran
results = compare_all_strategies(athlete, fran)
for strategy_name, time, completed in results:
    status = "✅" if completed else "❌"
    print(f"{strategy_name}: {time:.1f}s {status}")
```

### Parameter Experiments
```python
from crossfit_twin.utils import quick_parameter_test

# Test how strength affects Fran performance
analysis = quick_parameter_test(
    athlete=athlete,
    workout=fran,
    strategy=strategy,
    parameter="strength",
    percentage_range=(-20.0, 20.0),
    steps=5
)

print(f"Optimal strength: {analysis['optimal_value']:.1f}")
print(f"Best time: {analysis['optimal_performance']:.1f}s")
```

### Custom Workouts
```python
from crossfit_twin import WOD

# Create a custom For Time workout
custom_wod = WOD.for_time(
    name="Custom Grinder",
    exercises=[
        ("thruster", 50, 35.0),
        ("burpee", 40, None),
        ("pull-up", 30, None)
    ],
    time_cap_seconds=1200  # 20 minutes
)

result = simulate(custom_wod, athlete, strategy)
```

### AMRAP Workouts
```python
# Create an AMRAP workout
amrap = WOD.amrap(
    name="12 min AMRAP",
    time_cap_seconds=720,
    exercises=[
        ("thruster", 8, 35.0),
        ("pull-up", 6, None),
        ("burpee", 4, None)
    ]
)

result = simulate(amrap, athlete, strategy)
print(f"Completed {result.rounds_completed} rounds")
```

## 🖥️ Web Interface

Launch the Streamlit web application:

```bash
streamlit run streamlit_app.py
```

Features:
- **Athlete Builder**: Create athletes with sliders and forms
- **Workout Library**: Access famous WODs or build custom ones
- **Strategy Tester**: Compare different pacing approaches
- **Parameter Experiments**: Visual analysis of attribute effects
- **Results Dashboard**: Track and compare simulation results

## 🧪 Examples and Validation

### Run Examples
```bash
python examples/example_usage.py
```

### Validate Simulation Accuracy
```bash
python examples/validation_scenarios.py
```

The validation script tests the simulation against known CrossFit performance ranges to ensure realistic results.

## 🧪 Testing

Run the comprehensive test suite:

```bash
pytest tests/ -v --cov=crossfit_twin
```

The library includes 90+ unit tests covering all core functionality.

## 📚 Documentation

### Project Structure
```
crossfit_twin/
├── crossfit_twin/           # Main library
│   ├── athlete.py          # Athlete modeling
│   ├── workout.py          # WOD and exercise definitions
│   ├── strategy.py         # Pacing strategies
│   ├── simulator.py        # Core simulation engine
│   └── utils.py            # Analysis and utilities
├── tests/                  # Unit tests
├── examples/               # Usage examples and validation
├── streamlit_app.py        # Web interface
└── docs/                   # Additional documentation
```

### Key Classes

- **`Athlete`**: Models athlete with physical parameters and performance characteristics
- **`WOD`**: Represents workouts with exercises, rounds, and timing
- **`Strategy`**: Defines pacing approaches and rest patterns
- **`WorkoutSimulator`**: Core engine that runs simulations
- **`SimulationResult`**: Comprehensive results with performance metrics

### Advanced Usage

See the [examples directory](examples/) for comprehensive usage patterns:
- **Parameter sweeps**: Systematic testing of athlete attributes
- **Strategy optimization**: Finding optimal pacing for specific WODs
- **Athlete profiling**: Comparing different athlete types
- **Custom strategies**: Building specialized pacing approaches

## 🤝 Contributing

This project follows professional development practices:

- **Clean Architecture**: Modular design with clear separation of concerns
- **Type Safety**: Full type hints throughout the codebase
- **Comprehensive Testing**: 90+ unit tests with high coverage
- **Documentation**: Detailed docstrings and examples
- **Code Quality**: Black formatting, flake8 linting, mypy type checking

## 📊 Use Cases

### For Athletes
- **Competition Prep**: Test pacing strategies before major events
- **Weakness Analysis**: Identify limiting factors in performance
- **Training Planning**: Understand how improvements affect results
- **Goal Setting**: Predict performance targets with specific adaptations

### For Coaches
- **Athlete Profiling**: Understand individual strengths and weaknesses
- **Strategy Development**: Find optimal approaches for different athletes
- **Programming**: Design workouts with predictable stimulus
- **Performance Prediction**: Estimate competition results

### For Researchers
- **Performance Modeling**: Study factors affecting CrossFit performance
- **Training Analysis**: Quantify the impact of different attributes
- **Strategy Research**: Compare pacing approaches scientifically
- **Fatigue Studies**: Understand fatigue patterns in multi-modal exercise

## 🏆 Validation

The simulation has been validated against real-world CrossFit performance data:

- **Fran times**: Elite (2-3 min) to beginner (8-12 min)
- **Cindy rounds**: Elite (25-35) to beginner (10-18)
- **Helen times**: Elite (7-9 min) to beginner (14-18 min)
- **Strategy differences**: Meaningful performance gaps between approaches
- **Athlete scaling**: Appropriate performance differences between levels

## 📈 Performance Characteristics

The simulation captures realistic CrossFit performance patterns:
- **Fatigue accumulation** that slows performance over time
- **Strategy impact** on overall times (20-60s differences)
- **Athlete scaling** across experience levels
- **Exercise specificity** with different fatigue patterns
- **Recovery dynamics** during planned and forced rest

## 🛠️ Technical Details

- **Language**: Python 3.8+
- **Dependencies**: NumPy, Pandas for data handling
- **UI Framework**: Streamlit with Plotly visualizations
- **Testing**: pytest with coverage reporting
- **Code Quality**: Black, flake8, mypy

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [CLAUDE.md](CLAUDE.md) - Detailed development log
- **Examples**: [examples/](examples/) - Usage patterns and validation
- **Tests**: [tests/](tests/) - Comprehensive test suite
- **Web App**: `streamlit run streamlit_app.py` - Interactive interface

---

**Built with ❤️ for the CrossFit community**

*Optimize your performance with data-driven insights*
# CrossFit Digital Twin V2 🏋️

## ⚡ Revolutionary Performance Modeling with Concrete Parameters

A comprehensive Python library for simulating CrossFit athlete performance using **real physiological data** instead of abstract scores. V2 introduces concrete benchmarks, RPE-based strategies, and advanced fatigue modeling.

---

## 🆕 What's New in V2

### 🎯 **Concrete Parameter System**
- **No more abstract 0-100 scores!**
- **Weightlifting**: Real 1RM values (kg) with physiological rep-time models
- **Gymnastics**: Cycle times (s/rep) + unbroken capacities (max reps)
- **Cardio**: Critical Power/W' model (watts, m/s) for bike, row, run, swim
- **Context**: Actual temperature, humidity, altitude values

### ⚡ **RPE-Based Strategy Selection**
- **Rate of Perceived Exertion (0-10)** drives workout intensity
- Automatic load constraints (% of 1RM based on RPE)
- Dynamic set sizing and rest periods
- Cardiovascular reserve management

### 🧠 **Advanced Fatigue Modeling**
- **W'bal System**: Cardiovascular fatigue tracking per modality
- **Local Muscle Fatigue**: 6 movement pattern buckets (pull/push/squat/hinge/core/grip)
- **Environmental Effects**: Temperature, altitude, humidity impact
- **Daily State**: Sleep, hydration, and readiness effects

### 📊 **Comprehensive UI Benchmarks**
- **Weightlifting**: All major lifts (squat, deadlift, clean, snatch, presses)
- **Gymnastics**: Max reps + timed cycles (20 pull-ups, 60 DU, etc.)
- **Monostructural**: FTP, rowing times, running PRs, swimming times
- **MetCons**: Famous CrossFit benchmarks (Fran, Helen, Grace, etc.)

---

## 🚀 Quick Start

### Installation
```bash
git clone https://github.com/alexcartn/crossfit_twin.git
cd crossfit_twin
pip install -e .
```

### V2 Basic Usage
```python
from crossfit_twin import UIBenchmarks, build_athlete_from_benchmarks, AthleteV2

# 1. Define athlete benchmarks (what user inputs in UI)
benchmarks = UIBenchmarks(
    # Weightlifting (kg)
    back_squat=140.0,
    clean=100.0,
    snatch=80.0,

    # Gymnastics
    max_pullup=20,
    t_20pu="1:30",  # 20 pull-ups in 1:30

    # Cardio
    row_2k="7:15",
    ftp_bike_w=280
)

# 2. Build athlete capabilities
capabilities = build_athlete_from_benchmarks(
    name="My Athlete",
    body_mass_kg=75.0,
    benchmarks=benchmarks
)

# 3. Create V2 athlete with context
athlete = AthleteV2(
    name="My Athlete",
    capabilities=capabilities,
    context=ContextParams(temperature_c=25.0, humidity_pct=65.0),
    day_state=DayState(sleep_h=7.0, rpe_intended=7)
)

# 4. Get RPE-based strategy and simulate
strategy = athlete.get_strategy_for_rpe(7)  # RPE 7 workout
# result = simulate_v2(wod, athlete, strategy)  # Coming in V2.1
```

### Streamlit V2 Web App
```bash
streamlit run streamlit_app_v2.py
```

---

## 📊 V2 System Architecture

### **Data Flow**
```
UI Benchmarks → AthleteCapabilities → AthleteV2 → RPE Strategy → Simulation
```

### **Core Components**

#### 1. **UIBenchmarks** - Data Input
```python
@dataclass
class UIBenchmarks:
    # Weightlifting (kg)
    back_squat: Optional[float] = None
    clean: Optional[float] = None
    # ... all major lifts

    # Gymnastics
    max_pullup: Optional[int] = None
    t_20pu: Optional[str] = None  # "mm:ss"
    # ... all gym movements

    # Monostructural
    row_2k: Optional[str] = None
    ftp_bike_w: Optional[int] = None
    # ... all cardio modalities
```

#### 2. **AthleteCapabilities** - Physiological Models
```python
@dataclass
class AthleteCapabilities:
    one_rm: Dict[str, float]                    # 1RM per movement (kg)
    gym_skills: Dict[str, GymSkill]             # Cycle times + capacities
    cardio_profiles: Dict[str, CPProfile]       # CP/W' per modality
    barbell_profile: BarbellProfile             # Rep-time model
```

#### 3. **Fatigue Models** - Advanced Tracking
```python
# Cardiovascular fatigue (W'bal)
wbal_state.update(power_demand, cp, duration)

# Local muscle fatigue (6 patterns)
fatigue_manager.add_local_fatigue("pull-up", load_factor, reps)
```

#### 4. **RPE Strategy** - Intelligent Constraints
```python
# RPE 7 constraints example
constraints = RPEConstraints(
    max_load_pct=0.88,           # 88% of 1RM max
    preferred_set_fraction=0.60,  # 60% of max capacity
    min_rest_between_sets=8.0,    # 8 seconds minimum
    cardio_reserve=0.25          # Keep 25% W'bal
)
```

---

## 🎯 Real-World Examples

### Example 1: Elite vs Recreational Athlete
```python
# Elite athlete benchmarks
elite_benchmarks = UIBenchmarks(
    back_squat=180.0, clean=130.0, snatch=110.0,
    max_pullup=35, t_20pu="1:15", row_2k="6:30"
)

# Recreational athlete benchmarks
rec_benchmarks = UIBenchmarks(
    back_squat=100.0, clean=70.0, snatch=55.0,
    max_pullup=12, t_20pu="2:30", row_2k="8:45"
)

# Compare Fran performance at RPE 8
# Elite: Likely unbroken thrusters, small pull-up sets
# Recreational: Fractioned strategy, longer rest periods
```

### Example 2: Environmental Impact
```python
# Hot, humid conditions
hot_context = ContextParams(temperature_c=35.0, humidity_pct=85.0)

# Cold, dry conditions
cold_context = ContextParams(temperature_c=5.0, humidity_pct=30.0)

# Same athlete, different performance in each condition
```

### Example 3: RPE-Driven Training
```python
# Easy day (RPE 5): Conservative loads, longer rest
easy_strategy = create_rpe_strategy(5)

# Competition day (RPE 9): Near-maximal effort
comp_strategy = create_rpe_strategy(9)
```

---

## 📈 Performance Comparison: V1 vs V2

| Aspect | V1 (Abstract) | V2 (Concrete) |
|--------|---------------|---------------|
| **Strength** | 0-100 score | 1RM values (kg) |
| **Endurance** | 0-100 score | CP/W' model (watts, m/s) |
| **Fatigue** | Simple accumulation | W'bal + local patterns |
| **Strategy** | Fixed parameters | RPE-driven constraints |
| **Input** | Manual tuning | Real benchmark data |
| **Interpretation** | Abstract | Physiologically meaningful |

---

## 🛠️ V2 Module Reference

### **Core Modules**
- `benchmarks.py` - UI data capture and validation
- `capabilities.py` - Physiological models (1RM, CP/W', gym skills)
- `builder.py` - Benchmark → capability conversion
- `athlete_v2.py` - New athlete system
- `fatigue_models.py` - W'bal + local muscle fatigue
- `rpe_strategy.py` - RPE-based strategy selection

### **Legacy Compatibility**
- V1 system still available via original imports
- Gradual migration path from abstract to concrete parameters
- Existing WOD and simulator infrastructure reused

---

## 🔬 Scientific Basis

### **Physiological Models Used**
1. **Critical Power Model**: P = CP + W'/t (Monod & Scherrer, 1965)
2. **W'bal Tracking**: Skiba et al. (2012) model for anaerobic capacity
3. **Barbell Velocity-Load**: Load-dependent rep time scaling
4. **Movement Pattern Fatigue**: Local vs global fatigue interactions
5. **Environmental Physiology**: Temperature, altitude, humidity effects

### **RPE Integration**
- Based on Borg CR10 scale (0-10)
- Translates perceived exertion to concrete workout constraints
- Accounts for individual RPE-load relationships

---

## 🌐 Web Interface (V2)

### **Streamlit V2 Features**
- **Comprehensive Benchmark Input**: All movement categories
- **Real-time Validation**: Immediate feedback on input errors
- **Visual Strategy Display**: RPE constraints and recommendations
- **Fatigue Monitoring**: Live fatigue state visualization
- **Performance Comparison**: Multi-athlete, multi-RPE analysis

### **Navigation**
- 🏠 **Home**: V2 overview and getting started
- 👤 **Athlete Builder**: Complete benchmark input forms
- 🌡️ **Context & Day**: Environmental and daily state settings
- ⚡ **RPE Strategy**: Strategy visualization and tuning
- 🔋 **Fatigue Monitor**: Real-time fatigue tracking
- 🏃 **Simulation**: Workout testing and analysis

---

## 🚧 Roadmap

### **V2.1 (Coming Soon)**
- [ ] New V2 simulator with full fatigue integration
- [ ] Advanced clone comparison tools
- [ ] Competition planning features
- [ ] Training load periodization

### **V2.2 (Future)**
- [ ] Machine learning athlete profiling
- [ ] Biomechanical efficiency factors
- [ ] Nutrition and recovery modeling
- [ ] Team/gym management features

---

## 🤝 Contributing

We welcome contributions! V2 opens many opportunities:

### **Priority Areas**
1. **Physiological Model Refinement**: Better CP/W' estimation, movement-specific fatigue
2. **UI/UX Improvements**: Enhanced Streamlit interface, mobile responsiveness
3. **Validation Studies**: Real athlete data collection and model validation
4. **New Features**: Additional movement patterns, advanced strategies

### **Development Setup**
```bash
# Clone and setup development environment
git clone https://github.com/alexcartn/crossfit_twin.git
cd crossfit_twin
pip install -e ".[dev]"

# Run tests
pytest tests/

# Check V2 example
python example_v2_usage.py
```

---

## 📚 Documentation

- **V1 Documentation**: Original abstract system (still supported)
- **V2 Migration Guide**: `docs/v2_migration.md`
- **API Reference**: Complete module documentation
- **Examples**: Real-world usage patterns

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🙏 Acknowledgments

- **Sport Science Community**: For physiological models and validation
- **CrossFit Community**: For workout structure and benchmark data
- **Open Source Contributors**: For making this project possible

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/alexcartn/crossfit_twin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/alexcartn/crossfit_twin/discussions)
- **Email**: [Support Email]

---

*Built with the power of concrete physiological modeling* 💪

**Version 2.0.0** | **Python 3.8+** | **MIT License**
# CrossFit Digital Twin 🏋️

## ⚡ Revolutionary Performance Modeling with Concrete Parameters

A comprehensive Python library for simulating CrossFit athlete performance using **real physiological data** instead of abstract scores. Features concrete benchmarks, RPE-based strategies, and advanced fatigue modeling.

---

## 🚀 Features

### 🎯 **Concrete Parameter System**
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

### 🎨 **Professional Web Interface**
- **Streamlit Application**: User-friendly interface with comprehensive benchmark forms
- **Real-time Validation**: Input validation with helpful error messages
- **Visual Analytics**: RPE strategies, fatigue monitoring, performance comparison
- **Multi-page Navigation**: Organized workflow from athlete creation to simulation

---

## 📦 Installation

### From Source
```bash
git clone https://github.com/alexcartn/crossfit_twin.git
cd crossfit_twin
pip install -e .
```

### Dependencies
- Python 3.8+
- NumPy, Pandas for data handling
- Streamlit for web interface
- Plotly for visualizations

---

## 🚀 Quick Start

### Basic Usage
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

# 3. Create athlete with context
athlete = AthleteV2(
    name="My Athlete",
    capabilities=capabilities,
    context=ContextParams(temperature_c=25.0, humidity_pct=65.0),
    day_state=DayState(sleep_h=7.0, rpe_intended=7)
)

# 4. Get RPE-based strategy and simulate
strategy = athlete.get_strategy_for_rpe(7)  # RPE 7 workout
# result = simulate(wod, athlete, strategy)
```

### Web Interface
```bash
streamlit run streamlit_app.py
```

---

## 📊 System Architecture

### **Data Flow**
```
UI Benchmarks → AthleteCapabilities → AthleteV2 → RPE Strategy → Simulation
```

### **Core Components**

#### 1. **UIBenchmarks** - Data Input
Captures all real performance data:
- **Weightlifting**: Back/front/OH squat, presses, deadlift, Olympic lifts
- **Gymnastics**: Max unbroken reps + timed cycles for all movements
- **Monostructural**: Bike FTP, rowing times, running PRs, swimming times
- **MetCons**: Famous CrossFit benchmark times (Fran, Helen, etc.)

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
- **W'bal System**: Cardiovascular fatigue per modality (bike/row/run/swim)
- **Local Muscle Fatigue**: 6 movement patterns with specific recovery
- **Environmental Effects**: Temperature, humidity, altitude impact

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

# Compare performance at same RPE level
```

### Example 2: Environmental Impact
```python
# Hot, humid conditions
hot_context = ContextParams(temperature_c=35.0, humidity_pct=85.0)

# Cold, dry conditions
cold_context = ContextParams(temperature_c=5.0, humidity_pct=30.0)

# Same athlete performs differently in each condition
```

### Example 3: RPE-Driven Training
```python
# Easy day (RPE 5): Conservative loads, longer rest
easy_strategy = create_rpe_strategy(5)

# Competition day (RPE 9): Near-maximal effort
comp_strategy = create_rpe_strategy(9)
```

---

## 🌐 Web Interface

### **Streamlit Application Features**

#### 🏠 **Home Page**
- System overview and getting started guide
- Feature highlights and benefits
- Navigation to all application sections

#### 👤 **Athlete Builder**
- **Comprehensive Benchmark Forms**: All movement categories with validation
- **Real-time Feedback**: Immediate validation and error checking
- **Capability Summary**: Generated athlete profile with key metrics
- **Estimation Tools**: Auto-fill missing lifts based on provided data

#### 🌡️ **Context & Day State**
- **Environmental Controls**: Temperature, humidity, altitude sliders
- **Daily Readiness**: Sleep, hydration, RPE intention settings
- **Real-time Effects**: Visual feedback on performance impact

#### ⚡ **RPE Strategy**
- **Strategy Visualization**: Concrete constraints display
- **RPE Scale Guide**: Detailed descriptions for each level
- **Dynamic Updates**: Strategy changes based on athlete state

#### 🔋 **Fatigue Monitor**
- **Live Fatigue Tracking**: Visual display of all fatigue systems
- **Movement Pattern Breakdown**: Local fatigue by muscle groups
- **Recovery Visualization**: Real-time recovery progress

#### 🏃 **Simulation**
- **Famous WODs**: Pre-loaded benchmark workouts
- **Custom Workouts**: Build and test your own WODs
- **Performance Analysis**: Detailed results and comparison
- **Strategy Testing**: Compare different RPE approaches

#### 📊 **Performance Comparison**
- **Multi-athlete Analysis**: Compare different athlete profiles
- **RPE Comparison**: Same athlete at different effort levels
- **Historical Tracking**: Performance trends over time

---

## 🔬 Scientific Basis

### **Physiological Models**
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

## 📈 Benefits Over Traditional Methods

| Traditional Approach | CrossFit Digital Twin |
|---------------------|----------------------|
| Generic workout plans | Personalized based on real benchmarks |
| Trial and error pacing | RPE-driven strategy optimization |
| Simple fatigue tracking | Advanced physiological models |
| Fixed strategies | Dynamic adaptation to athlete state |
| Abstract parameters | Concrete, measurable inputs |

---

## 🛠️ Module Reference

### **Core Modules**
- `benchmarks.py` - UI data capture and validation
- `capabilities.py` - Physiological models (1RM, CP/W', gym skills)
- `builder.py` - Benchmark → capability conversion
- `athlete_v2.py` - Main athlete system
- `fatigue_models.py` - W'bal + local muscle fatigue
- `rpe_strategy.py` - RPE-based strategy selection

### **Legacy Support**
- Original simulation engine still available
- Gradual migration from abstract to concrete parameters
- Backward compatibility maintained

---

## 🚧 Development Roadmap

### **Upcoming Features**
- [ ] Enhanced V2 simulator with full fatigue integration
- [ ] Machine learning athlete profiling
- [ ] Competition planning tools
- [ ] Training periodization features
- [ ] Mobile-responsive interface
- [ ] Advanced analytics dashboard

### **Research Areas**
- [ ] Real athlete data validation studies
- [ ] Biomechanical efficiency modeling
- [ ] Nutrition and recovery integration
- [ ] Team/gym management features

---

## 🤝 Contributing

We welcome contributions! Areas of interest:

### **Priority Development**
1. **Model Validation**: Real athlete data collection and comparison
2. **UI/UX Enhancement**: Mobile responsiveness, accessibility
3. **Feature Expansion**: New movement patterns, advanced strategies
4. **Performance Optimization**: Algorithm improvements, caching

### **Getting Started**
```bash
# Clone and setup development environment
git clone https://github.com/alexcartn/crossfit_twin.git
cd crossfit_twin
pip install -e ".[dev]"

# Run tests
pytest tests/

# Check examples
python example_v2_usage.py
```

### **Contribution Guidelines**
- Fork the repository and create feature branches
- Add tests for new functionality
- Follow existing code style and documentation patterns
- Submit pull requests with clear descriptions

---

## 📚 Documentation

- **Migration Guide**: `V2_MIGRATION_GUIDE.md`
- **API Reference**: Complete module documentation
- **Examples**: `example_v2_usage.py` - Comprehensive usage examples
- **Scientific References**: Physiological model citations

---

## 🙏 Acknowledgments

- **Sport Science Community**: For physiological models and research
- **CrossFit Community**: For workout structures and benchmark data
- **Open Source Contributors**: For libraries and development tools
- **Beta Testers**: For feedback and validation

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/alexcartn/crossfit_twin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/alexcartn/crossfit_twin/discussions)
- **Documentation**: Complete guides and API reference
- **Examples**: Working code samples and tutorials

---

*Transform your CrossFit training with the power of concrete physiological modeling* 💪

**Latest Version** | **Python 3.8+** | **MIT License**
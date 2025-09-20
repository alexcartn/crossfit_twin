# CrossFit Digital Twin V2 Migration Guide 🔄

## Overview

This guide helps you migrate from the abstract V1 system to the concrete V2 parameter system. V2 introduces real physiological data instead of 0-100 scores, providing more accurate and interpretable performance modeling.

---

## 🆚 Key Differences: V1 vs V2

### **Athlete Modeling**

| Aspect | V1 (Abstract) | V2 (Concrete) |
|--------|---------------|---------------|
| **Strength** | `strength: 75` (0-100) | `one_rm: {"back-squat": 140.0}` (kg) |
| **Endurance** | `endurance: 80` (0-100) | `cardio_profiles: {"row": CPProfile(cp=280, w_prime=15000)}` |
| **Gymnastics** | `base_pace: {"pull-up": 1.5}` | `gym_skills: {"pull-up": GymSkill(cycle_s=1.3, unbroken_cap=20)}` |
| **Input Method** | Manual parameter tuning | Real benchmark data from UI |

### **Strategy Selection**

| V1 | V2 |
|----|-----|
| Fixed strategy parameters | RPE-driven constraints (0-10) |
| `target_intensity: 0.8` | `rpe_intended: 7 → concrete load/set constraints` |
| Generic rest patterns | Fatigue-aware, movement-specific rest |

### **Fatigue Modeling**

| V1 | V2 |
|----|-----|
| Simple accumulation | W'bal + local muscle fatigue |
| Single fatigue value | 6 movement patterns + cardio modalities |
| Basic recovery | Context-aware recovery (temp, hydration, sleep) |

---

## 🚀 Migration Strategies

### **Strategy 1: Direct Benchmark Input (Recommended)**

If you have real performance data:

```python
# V1 - Abstract parameters
athlete_v1 = Athlete(
    name="John",
    strength=75,
    endurance=80,
    fatigue_resistance=70,
    recovery_rate=75,
    weight_kg=75.0
)

# V2 - Real benchmarks
benchmarks = UIBenchmarks(
    back_squat=140.0,      # Actual 1RM
    clean=100.0,           # Actual 1RM
    max_pullup=20,         # Actual max reps
    t_20pu="1:30",         # Actual time for 20 reps
    row_2k="7:15",         # Actual 2k time
    ftp_bike_w=280         # Actual FTP
)

capabilities = build_athlete_from_benchmarks("John", 75.0, benchmarks)
athlete_v2 = AthleteV2("John", capabilities)
```

### **Strategy 2: Convert Existing V1 Parameters**

If you only have V1 abstract parameters:

```python
def convert_v1_to_benchmarks(athlete_v1: Athlete) -> UIBenchmarks:
    """Convert V1 athlete to approximate V2 benchmarks."""

    # Estimate 1RMs from strength score and body weight
    strength_multiplier = athlete_v1.strength / 100.0

    # Conservative estimates - user should refine with real data
    estimated_benchmarks = UIBenchmarks(
        back_squat=athlete_v1.weight_kg * (1.0 + strength_multiplier * 1.0),
        clean=athlete_v1.weight_kg * (0.6 + strength_multiplier * 0.6),
        snatch=athlete_v1.weight_kg * (0.4 + strength_multiplier * 0.6),

        # Estimate cardio from endurance score
        row_2k="8:30" if athlete_v1.endurance < 50 else "7:30" if athlete_v1.endurance < 80 else "6:45",

        # Estimate gym capacity
        max_pullup=int(5 + (athlete_v1.strength / 100.0) * 25),

        # Conservative FTP estimate
        ftp_bike_w=int(150 + (athlete_v1.endurance / 100.0) * 200)
    )

    return estimated_benchmarks

# Usage
v1_athlete = Athlete(name="John", strength=75, endurance=80, ...)
estimated_benchmarks = convert_v1_to_benchmarks(v1_athlete)

# User should then refine these estimates with real data
print("Estimated benchmarks - please verify and update:")
print(f"Back Squat: {estimated_benchmarks.back_squat}kg")
print(f"Max Pull-ups: {estimated_benchmarks.max_pullup}")
# ... etc
```

### **Strategy 3: Gradual Migration**

Use both systems during transition:

```python
# Keep V1 for existing workflows
athlete_v1 = Athlete(...)
result_v1 = simulate(wod, athlete_v1, strategy_v1)

# Add V2 for new features
benchmarks = UIBenchmarks(...)  # Collect real data over time
athlete_v2 = AthleteV2(...)
strategy_v2 = athlete_v2.get_strategy_for_rpe(7)

# Compare results during transition
print(f"V1 time: {result_v1.total_time}")
# print(f"V2 time: {result_v2.total_time}")  # When V2 simulator ready
```

---

## 📊 Data Collection Guide

### **Essential Benchmarks to Collect**

#### **Priority 1: Core Strength**
```python
# Most important for strength modeling
required_lifts = {
    "back_squat": "Your actual 1RM or best 3RM",
    "deadlift": "Your actual 1RM",
    "clean": "Your best clean (not C&J)"
}
```

#### **Priority 2: Cardio Base**
```python
# Critical for endurance modeling
required_cardio = {
    "row_2k": "Your best 2k row time (mm:ss)",
    "run_400m": "Your best 400m time",
    "ftp_bike_w": "20-min FTP test result (watts)"
}
```

#### **Priority 3: Gymnastics**
```python
# For bodyweight movement modeling
required_gym = {
    "max_pullup": "Max unbroken kipping pull-ups",
    "t_20pu": "Time for 20 pull-ups (mm:ss)",
    "max_du": "Max unbroken double unders"
}
```

### **Data Collection Workflow**

1. **Start with what you know**: Input any existing PR data
2. **Test missing elements**: Schedule testing sessions for gaps
3. **Use estimation**: Let the system estimate missing lifts from relatives
4. **Refine over time**: Update benchmarks as you hit new PRs

### **Example Testing Session Plan**

```
Week 1: Strength Testing
- Day 1: Back squat 1RM, Front squat 1RM
- Day 3: Deadlift 1RM, Strict press 1RM
- Day 5: Clean 1RM, Snatch 1RM

Week 2: Cardio Testing
- Day 1: 2k row for time
- Day 3: 400m run for time
- Day 5: 20-min FTP test (bike)

Week 3: Gymnastics Testing
- Day 1: Max unbroken pull-ups, 20 pull-ups for time
- Day 3: Max unbroken HSPU, 20 HSPU for time
- Day 5: Max DU, 60 DU for time
```

---

## 🔧 Code Migration Examples

### **Basic Athlete Creation**

```python
# V1 - Abstract
def create_v1_athlete():
    return Athlete(
        name="Athlete",
        strength=75,
        endurance=80,
        fatigue_resistance=70,
        recovery_rate=75,
        weight_kg=75.0,
        experience_level="intermediate"
    )

# V2 - Concrete
def create_v2_athlete():
    benchmarks = UIBenchmarks(
        back_squat=140.0,
        clean=100.0,
        row_2k="7:15",
        max_pullup=20,
        t_20pu="1:30"
    )

    capabilities = build_athlete_from_benchmarks(
        "Athlete", 75.0, benchmarks
    )

    return AthleteV2("Athlete", capabilities)
```

### **Strategy Selection**

```python
# V1 - Fixed strategy
def get_v1_strategy():
    return StrategyFactory.fractioned(
        target_intensity=0.8,
        global_fatigue_threshold=1.2
    )

# V2 - RPE-driven
def get_v2_strategy(athlete_v2, rpe=7):
    # RPE automatically determines intensity and thresholds
    return athlete_v2.get_strategy_for_rpe(rpe)
```

### **Simulation with Context**

```python
# V1 - Manual context application
def simulate_v1_with_context():
    athlete = create_v1_athlete()

    # Context was applied internally in get_rep_time()
    context = ContextParams(temperature_c=30.0, humidity_pct=80.0)
    day_state = DayState(sleep_h=6.0, water_l=1.0)

    athlete.set_simulation_context(context, day_state)

    strategy = get_v1_strategy()
    return simulate(wod, athlete, strategy)

# V2 - Integrated context system
def simulate_v2_with_context():
    athlete = create_v2_athlete()

    # Context and day state are part of athlete
    athlete.context = ContextParams(temperature_c=30.0, humidity_pct=80.0)
    athlete.day_state = DayState(sleep_h=6.0, water_l=1.0, rpe_intended=7)

    strategy = athlete.get_strategy_for_rpe()  # Uses day_state.rpe_intended
    return simulate(wod, athlete, strategy)  # Will use V2 simulator when ready
```

---

## 🎯 RPE Integration Guide

### **Understanding RPE Mapping**

```python
# RPE to constraint mapping
rpe_examples = {
    3: "Easy recovery - 60% loads, 30% set sizes, long rest",
    5: "Moderate - 70% loads, 45% set sizes, moderate rest",
    7: "Vigorous - 84% loads, 60% set sizes, short rest",
    9: "Very hard - 92% loads, 85% set sizes, minimal rest"
}

# Using RPE in practice
def plan_workout_by_feel():
    if feeling_tired:
        return create_rpe_strategy(4)  # Easy day
    elif competition_day:
        return create_rpe_strategy(9)  # All out
    else:
        return create_rpe_strategy(7)  # Normal training
```

### **RPE Strategy Customization**

```python
# Custom RPE constraints
def create_custom_rpe_strategy():
    constraints = RPEConstraints(
        target_rpe=7,
        max_load_pct=0.85,           # Custom max load
        preferred_set_fraction=0.65,  # Custom set sizing
        min_rest_between_sets=10.0,   # Custom rest periods
        cardio_reserve=0.30          # Custom W'bal reserve
    )

    return RPEStrategy(constraints)
```

---

## 🧪 Testing and Validation

### **Validate V2 Conversion**

```python
def validate_v2_conversion(athlete_v1: Athlete, athlete_v2: AthleteV2):
    """Compare V1 vs V2 performance on simple movements."""

    # Test basic rep times
    v1_pullup_time = athlete_v1.get_rep_time("pull-up")
    v2_pullup_time = athlete_v2.get_rep_time("pull-up")

    print(f"Pull-up time - V1: {v1_pullup_time:.2f}s, V2: {v2_pullup_time:.2f}s")

    # Test fatigue accumulation
    athlete_v1_copy = athlete_v1.clone()
    athlete_v2_copy = athlete_v2.clone()

    # Simulate 20 pull-ups
    for _ in range(20):
        fatigue_v1 = athlete_v1_copy.get_fatigue_per_rep("pull-up")
        athlete_v2_copy.add_work("pull-up", 1)

    print(f"After 20 pull-ups:")
    print(f"V1 fatigue accumulation: {fatigue_v1 * 20:.2f}")
    print(f"V2 fatigue summary: {athlete_v2_copy.fatigue_manager.get_fatigue_summary()}")
```

### **Benchmark Validation**

```python
def validate_benchmarks():
    """Check if benchmark inputs produce reasonable capabilities."""

    benchmarks = UIBenchmarks(back_squat=140.0, body_mass_kg=75.0)

    # Validate relative strength
    relative_strength = 140.0 / 75.0  # 1.87x bodyweight

    if relative_strength < 1.0:
        print("⚠️ Warning: Back squat seems low")
    elif relative_strength > 3.0:
        print("⚠️ Warning: Back squat seems very high")
    else:
        print("✅ Back squat looks reasonable")
```

---

## ⚠️ Common Migration Issues

### **Issue 1: Missing Benchmark Data**

```python
# Problem: Don't have all benchmark data
benchmarks = UIBenchmarks(back_squat=140.0)  # Only one data point

# Solution: Use estimation + gradual refinement
capabilities = build_athlete_from_benchmarks("Athlete", 75.0, benchmarks)
estimate_missing_lifts(capabilities)  # Fills in estimates

# Then refine over time as you collect real data
```

### **Issue 2: Unrealistic Benchmark Values**

```python
# Problem: Input validation errors
benchmarks = UIBenchmarks(back_squat=400.0, body_mass_kg=60.0)  # 6.7x BW!

# Solution: Use validation function
errors = validate_benchmarks(benchmarks)
if errors:
    print("Please correct these issues:")
    for field, error in errors.items():
        print(f"- {field}: {error}")
```

### **Issue 3: Strategy Feels Too Easy/Hard**

```python
# Problem: RPE 7 strategy feels wrong
athlete = AthleteV2(...)
athlete.day_state.rpe_intended = 7
strategy = athlete.get_strategy_for_rpe()

# Solution: Adjust RPE or create custom constraints
if strategy_too_easy:
    athlete.day_state.rpe_intended = 8  # Bump up RPE
elif strategy_too_hard:
    athlete.day_state.rpe_intended = 6  # Dial back RPE

# Or create custom constraints
custom_strategy = RPEStrategy(
    RPEConstraints(target_rpe=7, max_load_pct=0.90)  # Higher loads
)
```

---

## 📋 Migration Checklist

### **Phase 1: Preparation**
- [ ] Install V2 system (`git pull` latest version)
- [ ] Review current V1 athlete parameters
- [ ] Identify available real benchmark data
- [ ] Plan data collection for missing benchmarks

### **Phase 2: Data Collection**
- [ ] Collect priority 1 benchmarks (strength)
- [ ] Collect priority 2 benchmarks (cardio)
- [ ] Collect priority 3 benchmarks (gymnastics)
- [ ] Validate benchmark inputs

### **Phase 3: Migration**
- [ ] Create UIBenchmarks object
- [ ] Build AthleteCapabilities
- [ ] Create AthleteV2 instance
- [ ] Test basic functionality (rep times, fatigue)
- [ ] Compare with V1 baseline results

### **Phase 4: Integration**
- [ ] Update context and day state handling
- [ ] Implement RPE-based strategy selection
- [ ] Test fatigue visualization
- [ ] Validate simulation results

### **Phase 5: Optimization**
- [ ] Refine benchmarks based on testing
- [ ] Customize RPE constraints if needed
- [ ] Update documentation and workflows
- [ ] Train team on V2 system

---

## 🎓 Best Practices

### **Data Quality**
1. **Use recent data**: Benchmarks should be from last 3-6 months
2. **Consistent conditions**: Test in similar environmental conditions
3. **Proper warmup**: Ensure adequate warmup for max efforts
4. **Multiple attempts**: Take best of 2-3 attempts for reliability

### **System Usage**
1. **Start conservative**: Use slightly lower RPE initially
2. **Monitor fatigue**: Watch fatigue visualizations during transition
3. **Iterative refinement**: Update benchmarks as you collect better data
4. **Context awareness**: Pay attention to environmental and daily state effects

### **Validation**
1. **Compare known workouts**: Test on workouts you know well
2. **Cross-check results**: Compare V1 vs V2 on simple movements
3. **Real-world validation**: Test predictions against actual performance
4. **Community feedback**: Share results with other users for validation

---

## 🤝 Getting Help

### **Resources**
- **GitHub Issues**: Report bugs or migration problems
- **Example Code**: Check `example_v2_usage.py` for complete examples
- **Documentation**: Refer to module docstrings for detailed API info

### **Community Support**
- Share migration experiences with other users
- Contribute benchmark data for model validation
- Report edge cases or unexpected behaviors

---

## 🚀 Next Steps

Once migrated to V2:

1. **Explore new features**: RPE strategies, fatigue visualization
2. **Collect more data**: Expand benchmark coverage over time
3. **Experiment with RPE**: Try different RPE levels for various workouts
4. **Contribute back**: Share insights and improvements with the community

---

*Happy migrating! The V2 system opens up much more accurate and interpretable performance modeling.* 💪
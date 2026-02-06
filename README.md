# F1 Race Engineer Agent 🏎️

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastF1](https://img.shields.io/badge/FastF1-enabled-red.svg)](https://github.com/theOehrly/Fast-F1)
[![LangChain](https://img.shields.io/badge/LangChain-powered-green.svg)](https://www.langchain.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An intelligent F1 data analysis agent powered by LangChain, FastF1, OpenF1 API, and LLM technology.

- 🚀 **28 Total Tools** (4 new quick lookup tools!)
- ⚡ **Complete OpenF1 API Coverage** (100% of endpoints)
- 📊 **Instant Record Lookups** (< 1ms response time)
- 🔄 **Smart Multi-Level Caching** (60-70% cache hit rate)
- 🎯 **100% Proactive** - Agent fetches data, never just suggests!
- 🎮 **Interactive Race Replay** - Visual race playback with telemetry

## 📑 Table of Contents

- [What Can It Do?](#-what-can-it-do)
- [Quick Start](#-quick-start)
- [Features](#-what-makes-this-special)
- [Project Structure](#-project-structure)
- [All Tools](#-all-28-tools)
- [Usage Examples](#-usage-examples)
- [Performance](#-performance)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

## 🎯 What Can It Do?

Ask anything about F1 and get instant, comprehensive answers:

### 🏆 Historical Records (Instant)
- "List of all race winners in 2023"
- "Who has the most pole positions?"
- "F1 world champions since 2000"
- "Constructor championships by team"

### 📊 Race Analysis
- "Compare Verstappen vs Hamilton at Monaco 2024"
- "Tire strategy for the last race"
- "Championship standings after round 10"
- "Pit stop analysis for Red Bull"

### 🔴 Live Data
- "Current weather at the track"
- "Live race positions and gaps"
- "Is DRS active?"
- "Verstappen's current speed"

### 🎮 Interactive Features
- "Replay Monaco 2023 race" (visual animation!)
- "Interactive telemetry comparison"
- "Strategy Gantt chart for all drivers"



## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/F1_agent.git
cd F1_agent

# Install dependencies
pip install -r requirements.txt

# Install Ollama (if not already installed)
# Visit: https://ollama.ai

# Pull LLM model
ollama pull qwen2.5:7b

# Run the agent
python main.py
```

Then ask away:
```
You: List of all race winners in 2023

Engineer: [Fetches all 22 races]
=== 2023 F1 Season - Race Winners ===

Round 1: Bahrain Grand Prix (Sakhir) - 2023-03-05
  Winner: Max Verstappen (Red Bull Racing)

Round 2: Saudi Arabian Grand Prix (Jeddah) - 2023-03-19
  Winner: Sergio Perez (Red Bull Racing)

... [all races]

=== Season Summary ===
Most Wins by Driver:
  Max Verstappen: 19 wins
  Sergio Perez: 2 wins
  Carlos Sainz: 1 win
```

### Prerequisites

- Python 3.10 or higher
- Ollama (for local LLM)
- 8GB RAM minimum (16GB recommended)

### Quick Install

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

## ✨ What Makes This Special?

### ⚡ Instant Lookups
- World champions: < 1ms
- Pole positions: < 1ms
- Fastest laps: < 1ms
- Constructor titles: < 1ms
- Race winners: Instant (cached) or ~2min (first fetch)

### 📊 Comprehensive Analysis
Every response includes:
- Main data requested
- Summary statistics
- Relevant insights
- Source information

### 🎮 Interactive Visualization
- Live race replay with car positions
- Telemetry data visualization
- Strategy Gantt charts
- Circuit maps with sector times

## 📁 Project Structure

```
F1_agent/
├── main.py                   # Main entry point
├── replay_ui.py              # Interactive race replay
├── rag_engine.py            # FIA regulations RAG
├── setup.py                  # Package setup
├── requirements.txt          # Dependencies
│
├── config/                   # Configuration
│   ├── settings.py          # Main settings
│   └── ui_settings.py       # UI constants
│
├── core/                     # Core functionality
│   ├── fastf1_adapter.py   # FastF1 wrapper
│   ├── api_client.py        # OpenF1 API client
│   ├── session_resolver.py  # Session resolver
│   ├── analytics.py         # Analytics engine
│   └── monitor.py           # Live monitoring
│
├── tools/                    # F1 analysis tools (28 tools)
│   ├── reference_tools.py   # Historical records
│   ├── analysis_tools.py    # Race analysis
│   ├── live_tools.py        # Real-time data
│   ├── advanced_tools.py    # Detailed analytics
│   ├── predictive_tools.py  # Predictions
│   ├── visualization_tools.py # Charts
│   └── replay_tools.py      # Race replay
│
├── utils/                    # Utilities
│   ├── validators.py        # Input validation
│   ├── cache_manager.py     # Caching system
│   ├── async_tools.py       # Async wrapper
│   └── quick_lookup.py      # Quick lookups
│
├── data/                     # Static data
├── docs/                     # Documentation
│   ├── SETUP.md            # Setup guide
│   └── architecture.py      # Architecture diagram
│
├── examples/                 # Example scripts
└── f1_rules_db/             # RAG database
```

## 🛠️ All 28 Tools

### 📚 Reference Tools (6)
1. **f1_champions_quick_lookup** - World champions
2. **f1_season_race_winners** - Race winners by season
3. **f1_fastest_lap_records** - Fastest lap statistics
4. **f1_pole_position_records** - Pole position records
5. **f1_constructor_champions** - Team championships
6. **f1_wikipedia_lookup** - General F1 knowledge

### 📊 Analysis Tools (6)
7. **f1_schedule** - Race calendar
8. **f1_session_results** - Race/Qualifying/Sprint results
9. **f1_telemetry_plot** - Driver comparison charts
10. **f1_tire_strategy** - Tire strategy analysis
11. **f1_championship_calculator** - Championship standings
12. **f1_race_weekend_summary** - Complete weekend report

### 🔴 Live Tools (3)
13. **f1_live_weather** - Current weather
14. **f1_live_position_map** - Track position visualization
15. **f1_live_intervals** - Live timing gaps

### 🔬 Advanced Tools (8)
16. **f1_live_car_telemetry** - Real-time car data
17. **f1_driver_info** - Driver information
18. **f1_pit_stop_analysis** - Pit stop performance
19. **f1_race_control_messages** - Race control events
20. **f1_position_changes** - Position tracking
21. **f1_stint_analysis** - Tire stint breakdown
22. **f1_team_radio_log** - Radio communications
23. **f1_lap_analysis** - Lap time analysis

### 🔮 Predictive Tools (2)
24. **f1_predict_tire_life** - Tire degradation prediction
25. **f1_predict_overtake** - Overtake possibility

### 📈 Visualization Tools (2)
26. **f1_plot_telemetry_interactive** - Interactive telemetry
27. **f1_plot_strategy_gantt** - Strategy Gantt chart

### 🎮 Replay Tools (1)
28. **f1_race_replay** - Interactive race animation

## 🎯 Usage Examples

```bash
python main.py
```

```
# Historical Records (Instant)
> Who has the most pole positions?
> List of F1 champions since 2010
> All race winners in 2023

# Live Data
> Current weather at the track
> Live race positions
> What's Verstappen's current speed?

# Analysis
> Compare VER vs HAM at Monaco 2024
> Tire strategy for the last race
> Championship standings after round 10

# Predictions
> Will Hamilton catch Verstappen?
> How are Leclerc's tires holding up?

# Replay
> Replay Monaco 2023 race
```

## 📊 Performance

| Query Type | Response Time | Example |
|------------|---------------|---------|
| Quick Lookup | < 1ms | "F1 champions" |
| Cached Data | < 1s | Previous queries |
| Live API | 1-3s | "Current weather" |
| Analysis | 5-15s | Telemetry plot |
| Race Replay | 1-3 min | Visual animation |

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_YEAR=2024
```

### Application Settings

Edit `config/settings.py`:

```python
DATA_DEFAULT_YEAR = 2024      # Default season
LLM_MODEL = "qwen2.5:7b"      # LLM model
API_TIMEOUT = 15               # API timeout
```

## 📦 Dependencies

- **LangChain & LangGraph** - Agent framework
- **FastF1** - Historical F1 data
- **OpenF1 API** - Live F1 data
- **Ollama** - Local LLM
- **Pandas & NumPy** - Data processing
- **Matplotlib** - Visualization
- **Arcade** - Race replay visualization
- **FAISS** - Regulation search

## 🐛 Troubleshooting

### Common Issues

**Agent not responding?**
- Check Ollama is running: `ollama list`
- Verify model is installed: `ollama pull qwen2.5:7b`

**No data for recent races?**
- FastF1 data available for 2018+
- Live data requires active session

**Slow first query?**
- First fetch downloads and caches data
- Subsequent queries use cache (instant)

**See logs**: `f1_agent.log`

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🙏 Acknowledgments

- **FastF1** - Excellent F1 data library
- **OpenF1** - Comprehensive F1 API
- **LangChain** - Agent framework
- **FIA** - Regulation documents

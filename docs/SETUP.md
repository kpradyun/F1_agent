# Setup Guide - F1 Race Engineer Agent

Complete installation and setup instructions for the F1 Race Engineer Agent.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Ollama Setup](#ollama-setup)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.10 or higher**
  ```bash
  python --version  # Should show 3.10+
  ```

- **Git** (for cloning the repository)
  ```bash
  git --version
  ```

- **Ollama** (for local LLM)
  - Download from [ollama.ai](https://ollama.ai)
  - Supports Linux, macOS, and Windows

### System Requirements

- **Memory**: 8GB RAM minimum (16GB recommended for larger models)
- **Storage**: 10GB free space (for cache and models)
- **Internet**: Required for initial data downloads

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/F1_agent.git
cd F1_agent
```

### 2. Create Virtual Environment

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- LangChain & LangGraph (Agent framework)
- FastF1 (Historical F1 data)
- Pandas & NumPy (Data processing)
- Matplotlib (Visualization)
- Arcade (Race replay UI)
- FAISS (Vector database)
- And more...

### 4. Verify Installation

```bash
python -c "import fastf1; import arcade; import langchain; print('✓ All packages installed')"
```

## Ollama Setup

### 1. Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download installer from [ollama.ai](https://ollama.ai)

### 2. Start Ollama Service

```bash
ollama serve
```

Leave this running in a separate terminal.

### 3. Pull the Model

**Recommended - Qwen 2.5 7B** (Good balance of speed and quality):
```bash
ollama pull qwen2.5:7b
```

**Alternative Models:**

- **Faster, less accurate:**
  ```bash
  ollama pull qwen2.5:3b
  ```

- **Slower, more accurate:**
  ```bash
  ollama pull qwen2.5:32b
  ```

### 4. Verify Ollama

```bash
ollama list
# Should show qwen2.5:7b (or your chosen model)
```

## Configuration

### 1. Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# LLM Configuration
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# API Configuration
OPENF1_API_TIMEOUT=15

# Data Configuration
DEFAULT_YEAR=2024
```

### 2. Application Settings

Edit `config/settings.py` for advanced configuration:

```python
# Default season
DATA_DEFAULT_YEAR = 2024

# LLM model
LLM_MODEL = "qwen2.5:7b"

# API timeout
API_TIMEOUT = 15

# Cache settings
CACHE_TTL_LIVE = 10      # 10 seconds for live data
CACHE_TTL_SESSION = 300  # 5 minutes for session data
CACHE_TTL_STATIC = 3600  # 1 hour for static data
```

### 3. Data Storage

The agent creates these directories automatically:
- `cache/` - FastF1 telemetry cache
- `plots/` - Generated charts and visualizations
- `f1_rules_db/` - FIA regulations vector database

## First Run

### 1. Start the Agent

```bash
python main.py
```

You should see:
```
╭───────────────────────────── F1 RACE ENGINEER ─────────────────────────────╮
│ F1 Hybrid Agent Online                                                     │
│ Date: 2024-02-04                                                          │
│ Model: qwen2.5:7b                                                         │
│ Type 'quit', 'exit', or '/stats' to check performance                    │
╰────────────────────────────────────────────────────────────────────────────╯
```

### 2. Try Simple Queries

Start with quick lookups (instant response):

```
You: List of F1 champions

You: Who has the most pole positions?

You: F1 world champions since 2020
```

### 3. Try Data Queries

These might take longer on first run (data download):

```
You: Results for Monaco 2023

You: Compare Verstappen vs Hamilton at Silverstone 2023

You: Tire strategy for the last Bahrain race
```

### 4. Try Live Features

```
You: Current weather at the track

You: Show me the 2024 race schedule
```

### 5. Try Interactive Replay

```
You: Replay Monaco 2023 race
```

This launches an interactive visualization window!

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "Cannot connect to Ollama"

**Solution**: 
1. Check Ollama is running: `ollama list`
2. Start Ollama: `ollama serve`
3. Verify model is installed: `ollama pull qwen2.5:7b`

### Issue: "No data for recent races"

**Solution**: 
- FastF1 data is available for 2018-2024 (current year may have delays)
- First query downloads data (can take 1-2 minutes)
- Subsequent queries use cache (instant)

### Issue: "Slow responses"

**Causes & Solutions**:
1. **First data fetch**: Normal, builds cache
2. **Large model**: Try smaller model like `qwen2.5:3b`
3. **Low RAM**: Close other applications
4. **No internet**: Check connection (needed for data downloads)

### Issue: "Replay window crashes"

**Solution**:
```bash
# Reinstall arcade
pip uninstall arcade
pip install arcade --upgrade

# Check Python version (needs 3.10+)
python --version
```

### Issue: "API timeout errors"

**Solution**: Edit `config/settings.py`:
```python
API_TIMEOUT = 30  # Increase timeout
```

### Check Logs

All errors are logged to `f1_agent.log`:
```bash
tail -f f1_agent.log
```

## Performance Tips

### 1. Cache Warming

On first run, execute common queries to build cache:
```bash
You: 2023 race schedule
You: Championship standings 2023
You: List of champions
```

### 2. Model Selection

| Model | Speed | Accuracy | RAM |
|-------|-------|----------|-----|
| qwen2.5:3b | Fast | Good | 4GB |
| qwen2.5:7b | Medium | Better | 8GB |
| qwen2.5:32b | Slow | Best | 20GB |

### 3. Internet Connection

- **Initial setup**: Requires internet
- **Cached queries**: Works offline
- **Live data**: Requires internet

## Advanced Configuration

### Custom Cache Directory

Edit `core/fastf1_adapter.py`:
```python
fastf1.Cache.enable_cache('/path/to/custom/cache')
```

### Change Default Year

Edit `config/settings.py`:
```python
DATA_DEFAULT_YEAR = 2023  # Change default year
```

### Add Custom Tools

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guide on adding new F1 analysis tools.

## Getting Help

1. **Check logs**: `f1_agent.log`
2. **GitHub Issues**: Report bugs or ask questions
3. **Documentation**: See README.md and other docs

## Next Steps

Once setup is complete:
- Explore [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for top queries
- Check [EXAMPLE_QUERIES.md](EXAMPLE_QUERIES.md) for 100+ examples
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) to add features

---

**Happy Racing! 🏁**

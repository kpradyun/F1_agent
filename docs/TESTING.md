# Testing Guide

This project now includes a quick smoke-test script for local validation.

## 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Run smoke tests

```bash
python scripts/smoke_test.py
```

This performs:
- recursive compile checks
- module import smoke checks for core/tool/UI entry points
- config sanity checks (including Tavily key presence warning)

## 3) Optional manual checks

### Agent startup

```bash
python main.py
```

### Replay UI startup

```bash
python replay_ui.py
```

### Tool-level quick checks (example)

```bash
python - <<'PY'
import asyncio
from tools.analysis_tools import f1_telemetry_plot

async def run():
    # Single-driver telemetry mode
    result = await f1_telemetry_plot.ainvoke({
        "driver1": "VER",
        "grand_prix": "Monza",
        "year": 2024,
        "session": "Race"
    })
    print(result)

asyncio.run(run())
PY
```

## 4) Radio download check

```bash
python - <<'PY'
import asyncio
from tools.advanced_tools import f1_team_radio_download

async def run():
    result = await f1_team_radio_download.ainvoke({
        "session_key": "latest",
        "limit": 3
    })
    print(result)

asyncio.run(run())
PY
```

Downloaded clips are saved under `plots/team_radio/`.

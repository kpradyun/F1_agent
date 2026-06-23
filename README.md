# F1 Race Engineer Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastF1](https://img.shields.io/badge/FastF1-enabled-red.svg)](https://github.com/theOehrly/Fast-F1)
[![LangChain](https://img.shields.io/badge/LangChain-powered-green.svg)](https://www.langchain.com/)
[![Tests](https://img.shields.io/badge/tests-36%20passing-brightgreen)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent Formula 1 data analysis agent powered by LangChain, FastF1, OpenF1 API, and local LLM technology via Ollama. Ask natural-language questions and get data-driven F1 insights — from 1950 historical records to live race telemetry, with FIA regulation lookup via RAG.

---

## What This Project Demonstrates

- **LangChain agent** with 25+ specialized tools, tool-calling, and session memory
- **Retrieval-Augmented Generation** (FAISS + HuggingFace) over official FIA regulations
- **Dual data sources**: FastF1 (historical, cached) + OpenF1 API (live/real-time)
- **Multi-level caching** for fast repeated queries
- **Local LLM inference** via Ollama with optional Gemini cloud fallback
- **Interactive race replay** via Arcade (2D animated visualization)
- Graceful degradation when Ollama, internet, or the regulations DB are unavailable

---

## Core Capabilities

| Capability | Latency | Source |
|---|---|---|
| Quick Lookup (champions, records) | < 1ms | Local metadata |
| Cached historical data | < 1s | FastF1 cache |
| FIA Regulations RAG | 1–2s | FAISS / HuggingFace |
| Live telemetry & weather | 1–3s | OpenF1 API |
| Deep telemetry analysis | 5–15s | FastF1 + Pandas |
| Race replay animation | 1–3 min | Arcade engine |

---

## Project Structure

```
F1_agent/
├── main.py              # Entry point & interactive chat loop
├── rag_engine.py        # FIA regulations RAG (FAISS + HuggingFace)
├── replay_ui.py         # Arcade-based race replay engine
├── core/                # Session resolution, search, RAG setup
├── tools/               # 25+ specialized analysis tools
├── ui/                  # Replay UI components
├── data/                # Static historical datasets
├── f1_rules_db/         # FAISS vector DB (auto-rebuilt if missing)
├── utils/               # Caching, logging, validation
├── config/              # Settings, environment, UI config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.10 or higher |
| [Ollama](https://ollama.com) | Local LLM runner — must be running before `python main.py` |
| RAM | 8 GB minimum, 16 GB recommended |
| Internet | Required for live data and first-run FastF1 downloads |
| Disk | ~2–5 GB for model weights + FastF1 session cache |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/kpradyun/F1_agent.git
cd F1_agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install and start Ollama (if not already installed)
# macOS:   brew install ollama
# Linux:   curl -fsSL https://ollama.com/install.sh | sh
# Windows: download from https://ollama.com/download

# 5. Pull the LLM (one-time download ~2–4 GB)
ollama pull llama3.2:latest

# 6. (Optional) Configure settings
cp .env.example .env
# Edit .env to customize OLLAMA_MODEL, DEFAULT_YEAR, LOG_LEVEL

# 7. Run the agent
python main.py
```

---

## Configuration

Settings can be adjusted via `.env` or `config/settings.py`:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` (local) or `gemini` (cloud — needs `GEMINI_API_KEY`) |
| `OLLAMA_MODEL` | `llama3.2:latest` | LLM model to use via Ollama |
| `GEMINI_API_KEY` | _(empty)_ | Gemini API key for cloud fallback |
| `DEFAULT_YEAR` | `2025` | Fallback season for data queries |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

---

## Example Queries

Once the agent is running, try:

```
> Who won the 2023 Formula 1 World Championship?
> Compare Verstappen and Hamilton's lap times at Silverstone 2023
> What does the FIA 2026 technical regulation say about ground effect?
> Show me the tire strategy for the 2024 Monaco Grand Prix
> What is the current track temperature? (requires live session)
> Replay the 2023 Abu Dhabi Grand Prix
```

---

## Toolset

The agent uses **30 specialized tools** across seven categories:

- **Reference (12):** World champions, pole positions, all-time records, head-to-head, career stats, circuit guide, reliability analysis, diagnostics
- **Analysis (6):** Schedule, race results, lap telemetry, tire strategy Gantt chart, championship calculator, weekend summary
- **Session (6):** Testing summaries, weather logs, race control messages, telemetry breakdown, tyre analysis, sector comparison
- **Live (4):** Real-time weather, track position map, timing intervals, leaderboard (via OpenF1 API)
- **Media (1):** Team radio downloads (mp3)
- **Replay (1):** Interactive Arcade race replay with telemetry overlay
- **RAG (1):** 2026 FIA Technical, Sporting, and Financial regulation search

---

## FIA Regulations RAG

The agent includes a FAISS vector database built from the official 2026 FIA regulations:

- Technical Regulations (chassis, power unit, aerodynamics)
- Sporting Regulations (race procedures, penalties, flags)
- Financial Regulations (cost cap, accounting)

If `f1_rules_db/` is missing, the agent **automatically rebuilds** it on the first RAG query using the source documents in `data/`. This takes 1–2 minutes on first run.

---

## Testing

```bash
pip install pytest
pytest tests/ -v
```

36 tests covering config validation, quick lookup pattern matching, year range checks, and tool composition — all run without any network calls or LLM.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Error: Ollama not running` | Run `ollama serve` in a separate terminal |
| `Model not found` | Run `ollama pull llama3.2:latest` (or set `LLM_PROVIDER=gemini` in `.env`) |
| `ollama list` shows no models | Pull the model first (see above) |
| First query is slow | FastF1 downloads session data on first access; subsequent calls use cache |
| `f1_rules_db` missing | The agent rebuilds it automatically on first RAG query |
| Historical data before 2018 | Telemetry data is limited pre-2018; metadata queries still work |
| Replay crashes | Ensure `arcade` is installed and a display is available |
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` inside the venv |

---

## Known Limitations

- **Ollama default:** Ollama is the default LLM. If Ollama isn't running, set `LLM_PROVIDER=gemini` in `.env` and provide a `GEMINI_API_KEY` to use the Gemini cloud fallback instead.
- **Live data:** OpenF1 live endpoints only work during active Formula 1 sessions
- **Replay graphics:** `arcade` requires a graphical display — not available in headless/SSH environments
- **Telemetry coverage:** High-resolution lap telemetry available from 2018 onwards

---

## Acknowledgments

- [FastF1](https://github.com/theOehrly/Fast-F1) — Historical F1 data
- [OpenF1](https://openf1.org) — Real-time F1 API
- [LangChain](https://www.langchain.com/) — Agentic framework
- [Ollama](https://ollama.com) — Local LLM inference
- [Arcade](https://api.arcade.academy/) — Race replay engine

---

## License

MIT © [kpradyun](https://github.com/kpradyun)

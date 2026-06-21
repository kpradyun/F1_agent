# F1 Race Engineer Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastF1](https://img.shields.io/badge/FastF1-enabled-red.svg)](https://github.com/theOehrly/Fast-F1)
[![LangChain](https://img.shields.io/badge/LangChain-powered-green.svg)](https://www.langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent Formula 1 data analysis agent powered by LangChain, FastF1, OpenF1 API, and local LLM technology via Ollama. Ask natural-language questions and get data-driven F1 insights — from 1950 historical records to live race telemetry, with FIA regulation lookup via RAG.

---

## What This Project Demonstrates

- **LangChain agent** with 25+ specialized tools, tool-calling, and session memory
- **Retrieval-Augmented Generation** (FAISS + HuggingFace) over official FIA regulations
- **Dual data sources**: FastF1 (historical, cached) + OpenF1 API (live/real-time)
- **Multi-level caching** for fast repeated queries
- **Local LLM inference** via Ollama (no cloud API keys required)
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

# 5. Pull the LLM (one-time download ~4 GB)
ollama pull qwen2.5:7b

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
| `OLLAMA_MODEL` | `qwen2.5:7b` | LLM model to use via Ollama |
| `DEFAULT_YEAR` | `2024` | Fallback season for data queries |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `CACHE_DIR` | `~/.cache/fastf1` | FastF1 data cache location |

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

The agent uses **25+ specialized tools** across six categories:

- **Reference (10):** World champions, pole positions, fastest laps, head-to-head records, season winners
- **Analysis (6):** Race results, lap telemetry, tire strategy, pit stop metrics
- **Session (4):** Testing summaries, weather logs, race control messages
- **Live (3):** Real-time weather, track positions, timing intervals (via OpenF1)
- **Media (1):** Team radio downloads
- **RAG (1):** 2026 FIA Technical, Sporting, and Financial regulation search

---

## FIA Regulations RAG

The agent includes a FAISS vector database built from the official 2026 FIA regulations:

- Technical Regulations (chassis, power unit, aerodynamics)
- Sporting Regulations (race procedures, penalties, flags)
- Financial Regulations (cost cap, accounting)

If `f1_rules_db/` is missing, the agent **automatically rebuilds** it on the first RAG query using the source documents in `data/`. This takes 1–2 minutes on first run.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Error: Ollama not running` | Run `ollama serve` in a separate terminal |
| `Model not found` | Run `ollama pull qwen2.5:7b` |
| `ollama list` shows no models | Pull the model first (see above) |
| First query is slow | FastF1 downloads session data on first access; subsequent calls use cache |
| `f1_rules_db` missing | The agent rebuilds it automatically on first RAG query |
| Historical data before 2018 | Telemetry data is limited pre-2018; metadata queries still work |
| Replay crashes | Ensure `arcade` is installed and a display is available |
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` inside the venv |

---

## Known Limitations

- **Ollama required:** No cloud LLM fallback — Ollama must be running locally
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

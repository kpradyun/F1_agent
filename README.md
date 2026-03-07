# F1 Race Engineer Agent

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastF1](https://img.shields.io/badge/FastF1-enabled-red.svg)](https://github.com/theOehrly/Fast-F1)
[![LangChain](https://img.shields.io/badge/LangChain-powered-green.svg)](https://www.langchain.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) 
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent Formula 1 data analysis agent powered by LangChain, FastF1, OpenF1 API, and LLM technology. This system provides real-time telemetry, historical record lookups, interactive race visualizations, and a RAG engine for FIA regulations.

## Core Capabilities

The agent processes natural language queries to provide data-driven insights:

* **Historical Records:** Instant access to world champions, pole positions, and race winners from 1950 to the present.
* **Race Analysis:** Comparative driver telemetry, tire strategy breakdowns, and pit stop performance metrics.
* **Live Data:** Real-time weather, DRS status, car speeds, and track positions via OpenF1 API integration.
* **FIA Regulations RAG:** Smart lookup for 2026 Technical, Sporting, and Financial regulations using FAISS vector storage.
* **Interactive Visualization:** 2D Arcade-based animated race replays, strategy Gantt charts, and telemetry plots.

## Performance Metrics

| Query Type | Latency | Technology |
| :--- | :--- | :--- |
| **Quick Lookup** | < 1ms | Local Metadata |
| **Cached Data** | < 1s | Multi-level Cache |
| **Regulations RAG** | 1–2s | FAISS / HuggingFace |
| **Live API** | 1–3s | OpenF1 Integration |
| **Deep Analysis** | 5–15s | FastF1 / Pandas |
| **Race Replay** | 1–3 min | Arcade Engine |

## Project Structure

```text
F1_agent/
├── main.py                # Main entry point & Chat Loop
├── replay_ui.py           # Interactive race replay engine (Arcade)
├── rag_engine.py          # FIA regulations RAG tool interface
├── core/                  # Core logic: RAG setup, Search, Session resolution
├── tools/                 # 25+ specialized analysis tools
├── ui/                    # Replay UI components and design system
├── data/                  # Static historical datasets and metadata
├── f1_rules_db/           # FAISS vector database for regulations
├── utils/                 # Caching, logging, and validation logic
└── config/                # Environment, UI, and Tool settings
```

## Installation

### Prerequisites
* **Python:** 3.10 or higher
* **Ollama:** Local LLM runner (installed and running)
* **Hardware:** 8GB RAM minimum (16GB recommended)

### Setup
```bash
# Clone the repository
git clone https://github.com/kpradyun/F1_agent.git
cd F1_agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Pull the required LLM
ollama pull llama3.2:latest 

# Run the agent
python main.py
```

## Toolset Overview

The agent utilizes a suite of **~25 specialized tools** categorized by function:

* **Reference Tools (10):** World champions, season winners, fastest laps, head-to-head comparisons, and more.
* **Analysis Tools (6):** Schedules, results, lap-by-lap telemetry, and tire strategy.
* **Session Tools (4):** Testing summaries, detailed weather, and race control logs.
* **Live Tools (3):** Real-time weather, track positions, and timing intervals.
* **Media Tools (1):** Team radio downloads and processing.
* **RAG Tool (1):** Deep search across 2026 FIA Technical, Sporting, and Financial regulations.

## FIA Regulations RAG

The agent includes a dedicated RAG (Retrieval-Augmented Generation) system for official FIA regulations. It uses **FAISS** for vector storage and **HuggingFace Embeddings** (`all-MiniLM-L6-v2`) to provide precise answers about:
- 2026 Technical specifications (Chassis & Power Unit)
- Sporting procedures and penalties
- Financial regulations and Cost Cap details

---

## Configuration

Custom settings can be managed via `.env` or `config/settings.py`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| **OLLAMA_MODEL** | The specific LLM to use via Ollama | `qwen2.5:7b` |
| **DEFAULT_YEAR** | The fallback season for data queries | `2024` |
| **LOG_LEVEL** | Detail level for logging | `INFO` |

---

## Troubleshooting

* **Model Connectivity:** Ensure the Ollama service is active (`ollama list`).
* **Data Limits:** High-resolution telemetry is generally available from **2018 onwards**.
* **First-Run Latency:** The initial fetch for a session involves large downloads; subsequent queries are cached.
* **Vector DB:** If `f1_rules_db` is missing, the agent will automatically attempt to rebuild it on first RAG query.

---

## Acknowledgments

* **FastF1:** Robust historical data processing.
* **OpenF1:** Comprehensive real-time API coverage.
* **LangChain:** Agentic framework and tool-calling logic.
* **Arcade:** Powering the interactive race replay engine.


# F1 Race Engineer Agent

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[![FastF1](https://img.shields.io/badge/FastF1-enabled-red.svg)](https://github.com/theOehrly/Fast-F1)

[![LangChain](https://img.shields.io/badge/LangChain-powered-green.svg)](https://www.langchain.com/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) 

An intelligent Formula 1 data analysis agent powered by LangChain, FastF1, OpenF1 API, and LLM technology. This system provides real-time telemetry, historical record lookups, and interactive race visualizations.

## Core Capabilities

The agent processes natural language queries to provide data-driven insights:

* **Historical Records:** Instant access to world champions, pole positions, and race winners from 1950 to the present.
* **Race Analysis:** Comparative driver telemetry, tire strategy breakdowns, and pit stop performance metrics.
* **Live Data:** Real-time weather, DRS status, car speeds, and track positions via OpenF1 API integration.
* **Interactive Visualization:** Animated race replays, strategy Gantt charts, and interactive telemetry plots.

## Performance Metrics

| Query Type | Latency | Technology |
| :--- | :--- | :--- |
| **Quick Lookup** | < 1ms | Local Metadata |
| **Cached Data** | < 1s | Multi-level Cache |
| **Live API** | 1–3s | OpenF1 Integration |
| **Deep Analysis** | 5–15s | FastF1 / Pandas |
| **Race Replay** | 1–3 min | Arcade Engine |

## Project Structure

```text
F1_agent/
├── main.py                # Main entry point
├── replay_ui.py           # Interactive race replay engine
├── rag_engine.py          # FIA regulations RAG (FAISS)
├── core/                  # API clients and session resolution
├── tools/                 # 28 specialized analysis tools
├── utils/                 # Caching and validation logic
└── config/                # Environment and UI settings
```

## Installation

### Prerequisites
* **Python:** 3.10 or higher
* **Ollama:** Local LLM runner (installed and running)
* **Hardware:** 8GB RAM minimum (16GB recommended)

### Setup
```bash
# Clone the repository
git clone [https://github.com/YOUR_USERNAME/F1_agent.git](https://github.com/YOUR_USERNAME/F1_agent.git)
cd F1_agent

# Install dependencies
pip install -r requirements.txt

# Pull the required LLM
ollama pull qwen2.5:7b

# Run the agent
python main.py
```

## Toolset Overview

The agent utilizes a suite of **28 specialized tools** categorized by function:

* **Reference Tools:** Access to world champions, season winners, fastest lap records, team championships, and Tavily-powered web/news lookups.
* **Analysis Tools:** Schedule/event metadata, next-race lookup, session control feeds (track/race control/weather), telemetry plotting, and tire strategy analysis.
* **Live Tools:** Real-time weather monitoring, track position maps, and timing intervals.
* **Advanced Tools:** In-depth pit stop analysis, radio logs, and car-specific telemetry.
* **Predictive & Visual:** Tire life degradation models and interactive race animations.



---

## Configuration

Custom settings can be managed via environment variables or by editing `config/settings.py`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| **OLLAMA_MODEL** | The specific LLM to use via Ollama | `qwen2.5:7b` |
| **DEFAULT_YEAR** | The fallback season for data queries | `2024` |
| **API_TIMEOUT** | Maximum duration for live data requests | `15s` |

---

## Troubleshooting

* **Model Connectivity:** Ensure the Ollama service is active. You can verify this by running `ollama list` in your terminal before launching `main.py`.
* **Data Limits:** While historical records go back to 1950, high-resolution telemetry and advanced lap data are generally only available for the **2018 season onwards**.
* **First-Run Latency:** The initial fetch for a new race session involves downloading large datasets. Subsequent queries are served instantly from the local multi-level cache.

---

## Acknowledgments

* **FastF1:** For the robust historical data processing.
* **OpenF1:** For the comprehensive real-time API coverage.
* **LangChain:** For the agentic framework and tool-calling logic.

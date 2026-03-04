# Improvement Roadmap

This project is already feature-rich. To make it more production-grade and easier to maintain, prioritize the following:

## 1) Reliability and Validation (Highest ROI)
- Add CI checks for:
  - dependency resolution (`pip install -r requirements.txt`)
  - static compilation (`python -m compileall .`)
  - smoke imports (`core.agent`, `tools.analysis_tools`, `rag_engine`)
- Add runtime health-check command that validates:
  - OpenF1 connectivity
  - FastF1 cache writable path
  - FAISS index availability
- Add structured error categories in tools so user-facing failures are actionable.

## 2) Test Coverage
- Add unit tests for:
  - session type normalization and cache behavior in `core/fastf1_adapter.py`
  - session key resolution in `core/session_resolver.py`
  - deterministic formatting helpers (`ui/helpers.py`)
- Add one integration smoke test for agent startup with a mocked toolset.

## 3) Dependency Hygiene
- Keep `langchain-huggingface==0.2.1` aligned with the current `langchain-core 0.3.x` ecosystem.
- Create a `constraints.txt` file for reproducible installs across machines.
- Split requirements into optional groups (`core`, `ui`, `rag`) if you want lighter installs.

## 4) Replay UI UX
- Add click-to-seek on the progress bar.
- Add lap marker ticks and optional sector split labels on the progress bar.
- Add compact mode for smaller resolutions.
- Add telemetry smoothing toggle for high-density sessions.

## 5) FastF1/OpenF1 Data Strategy
- Keep heavy telemetry lazy-loaded where possible.
- Reuse cached sessions across tools in the same process (already started).
- Add explicit cache hit/miss logging counters for profiling.

## 6) Observability
- Emit latency metrics per tool call (start/end timestamps).
- Track cache hit ratios and API error rates.
- Add a debug mode to dump tool inputs/outputs (without secrets).

## 7) Documentation and Developer Experience
- Add a short “architecture quickstart” diagram in docs.
- Add a one-command bootstrap script (`make setup` / `./scripts/bootstrap.sh`).
- Add troubleshooting section for dependency resolver and proxy/index issues.

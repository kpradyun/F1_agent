"""
F1 Agent - Architecture Visualization
Generate a visual diagram of the optimized architecture
"""

architecture_diagram = """
┌─────────────────────────────────────────────────────────────────┐
│                     F1 RACE ENGINEER AGENT v2.0                 │
│                      (Optimized Architecture)                    │
└─────────────────────────────────────────────────────────────────┘

                              [USER]
                                 │
                                 ▼
                        ┌────────────────┐
                        │ main_refactored│
                        │     .py        │
                        └────────┬───────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌───────────┐    ┌──────────┐    ┌──────────┐
        │  LangChain│    │  Config  │    │   RAG    │
        │   Agent   │    │ Settings │    │  Engine  │
        └─────┬─────┘    └──────────┘    └──────────┘
              │
              │ Uses Tools
              ▼
    ┌─────────────────────┐
    │   TOOLS PACKAGE     │
    ├─────────────────────┤
    │ • live_tools.py     │──┐
    │ • analysis_tools.py │  │
    │ • replay_tools.py   │  │
    └─────────────────────┘  │
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │  CORE PACKAGE   │          │ UTILS PACKAGE   │
    ├─────────────────┤          ├─────────────────┤
    │ • api_client.py │◄─────────┤ • validators.py │
    │   (Singleton)   │          └─────────────────┘
    │                 │
    │ • session_      │
    │   resolver.py   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   OpenF1 API    │
    │  (External)     │
    └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       DATA PROCESSING FLOW                       │
└─────────────────────────────────────────────────────────────────┘

[User Query] 
     │
     ▼
[Agent Routes to Tool]
     │
     ├─► LIVE DATA ──► api_client ──► OpenF1 API
     │                                     │
     │                                     ▼
     │                              [Weather/Positions]
     │
     ├─► ANALYSIS ──► f1_data_miner ──► FastF1
     │                                     │
     │                                     ▼
     │                              [Telemetry/Strategy]
     │
     ├─► RULES ──► rag_engine ──► Vector DB
     │                                │
     │                                ▼
     │                         [FIA Regulations]
     │
     └─► REPLAY ──► replay_ui ──► Arcade Window
                                    │
                                    ▼
                              [Interactive UI]

┌─────────────────────────────────────────────────────────────────┐
│                      OPTIMIZATION FEATURES                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│ Singleton Pattern│         │   LRU Caching    │
│  (API Client)    │         │  (RAG Queries)   │
│                  │         │                  │
│  ✓ Single        │         │  ✓ Avoids        │
│    instance      │         │    redundant     │
│  ✓ Shared state  │         │    lookups       │
│  ✓ Less memory   │         │  ✓ Fast access   │
└──────────────────┘         └──────────────────┘

┌──────────────────┐         ┌──────────────────┐
│ Backoff Retry    │         │   Type Hints     │
│  (All APIs)      │         │  (All modules)   │
│                  │         │                  │
│  ✓ Exponential   │         │  ✓ IDE support   │
│    backoff       │         │  ✓ Error         │
│  ✓ Auto-retry    │         │    detection     │
└──────────────────┘         └──────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        MODULE DIAGRAM                            │
└─────────────────────────────────────────────────────────────────┘

config/
  └── settings.py
       │
       ├── DATA_DEFAULT_YEAR = 2025
       ├── OPENF1_BASE_URL = "..."
       ├── API_TIMEOUT = 60
       └── [All Configuration]
       
core/
  ├── api_client.py
  │    │
  │    ├── class OpenF1Client
  │    │    ├── get_sessions()
  │    │    ├── get_weather()
  │    │    ├── get_location()
  │    │    └── get_intervals()
  │    │
  │    └── get_client() → Singleton
  │
  └── session_resolver.py
       │
       ├── class SessionResolver
       │    ├── _extract_year()
       │    ├── _get_meaningful_tokens()
       │    ├── _match_session()
       │    └── resolve()
       │
       └── get_resolver() → Singleton

tools/
  ├── live_tools.py
  │    ├── @tool f1_live_weather()
  │    ├── @tool f1_live_position_map()
  │    ├── @tool f1_live_intervals()
  │    └── get_live_tools()
  │
  ├── analysis_tools.py
  │    ├── @tool f1_schedule()
  │    ├── @tool f1_session_results()
  │    ├── @tool f1_telemetry_plot()
  │    ├── @tool f1_tire_strategy()
  │    ├── @tool f1_championship_calculator()
  │    ├── @tool f1_race_weekend_summary()
  │    └── get_analysis_tools()
  │
  └── replay_tools.py
       ├── @tool f1_race_replay()
       └── get_replay_tools()

utils/
  └── validators.py
       ├── validate_year()
       ├── validate_driver()
       └── validate_session_type()

┌─────────────────────────────────────────────────────────────────┐
│                      BEFORE vs AFTER                             │
└─────────────────────────────────────────────────────────────────┘

BEFORE:                          AFTER:
┌──────────────────┐            ┌──────────────────┐
│    main.py       │            │ main_refactored  │
│   (595 lines)    │            │   (224 lines)    │
│                  │            └────────┬─────────┘
│ ├─ Imports       │                     │
│ ├─ Config        │            ┌────────┴─────────┐
│ ├─ API calls     │            │                  │
│ ├─ Tools         │            ▼                  ▼
│ ├─ Agent setup   │      ┌──────────┐      ┌──────────┐
│ └─ Main loop     │      │  config/ │      │   core/  │
│                  │      │  tools/  │      │  utils/  │
│ [MONOLITHIC]     │      └──────────┘      └──────────┘
└──────────────────┘
                               [MODULAR]

┌─────────────────────────────────────────────────────────────────┐
│                     BENEFITS ACHIEVED                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ✅ ORGANIZATION: Clear module boundaries                         │
│ ✅ PERFORMANCE: Singleton + Caching + Retry logic                │
│ ✅ MAINTAINABILITY: Easy to find and modify code                 │
│ ✅ EXTENSIBILITY: Simple to add new tools                        │
│ ✅ TESTABILITY: Isolated, mockable modules                       │
│ ✅ TYPE SAFETY: Full type hints with Python 3.10+                │
│ ✅ DOCUMENTATION: Comprehensive docstrings                        │
│ ✅ COMPATIBILITY: Original code still works!                     │
└─────────────────────────────────────────────────────────────────┘
"""

if __name__ == "__main__":
    print(architecture_diagram)

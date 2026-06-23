"""
F1 Agent Configuration Settings
Centralized configuration for all modules
"""
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === API Configuration ===
OPENF1_BASE_URL = "https://api.openf1.org/v1"
# Jolpica: community-maintained Ergast mirror with current-season data
JOLPICA_BASE_URL = "https://api.jolpi.ca/ergast/f1"
API_TIMEOUT = 30
API_MAX_RETRIES = 3

# === Data Configuration ===
DATA_DEFAULT_YEAR = datetime.now().year
MIN_REPLAY_YEAR = 2018  # Telemetry data availability

# === Directory Structure ===
CACHE_DIR = "cache"
PLOTS_DIR = "plots"
DATA_DIR = "data"
RAG_DB_DIR = "f1_rules_db"
LOG_FILE = "f1_agent.log"

# === FastF1 Configuration ===
FASTF1_MIN_YEAR = 2018
FASTF1_MAX_YEAR = datetime.now().year

# === LLM Configuration ===
# LLM_PROVIDER: "gemini" (cloud, preferred when key is set) or "ollama" (local fallback)
# Auto-detects: if GEMINI_API_KEY is present, uses Gemini Flash by default.
# Override with LLM_PROVIDER=ollama in .env to force local model.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_default_provider = "gemini" if GEMINI_API_KEY else "ollama"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", _default_provider).lower()
LLM_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE = 0.3

# === Logging Configuration ===
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# === Date ===
TODAY = datetime.now().strftime("%Y-%m-%d")

# === 2026 F1 Grid ===
GRID_CONTEXT = """
BASELINE 2026 F1 GRID (11 TEAMS, 22 DRIVERS):
1. McLaren: Lando Norris & Oscar Piastri
2. Ferrari: Charles Leclerc & Lewis Hamilton
3. Red Bull: Max Verstappen & Isack Hadjar
4. Mercedes: George Russell & Kimi Antonelli
5. Aston Martin: Fernando Alonso & Lance Stroll
6. Alpine: Pierre Gasly & Franco Colapinto
7. Williams: Alex Albon & Carlos Sainz
8. Racing Bulls (VCARB): Liam Lawson & Arvid Lindblad
9. Haas: Esteban Ocon & Oliver Bearman
10. Audi (ex-Sauber): Nico Hulkenberg & Gabriel Bortoleto
11. Cadillac (NEW): Sergio Perez & Valtteri Bottas
"""

# === Ensure directories exist ===
def ensure_directories():
    """Create required directories if they don't exist"""
    for directory in [CACHE_DIR, PLOTS_DIR, DATA_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

# Auto-create directories on import
ensure_directories()

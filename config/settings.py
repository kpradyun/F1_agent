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
API_TIMEOUT = 60
API_MAX_RETRIES = 3

# === Data Configuration ===
DATA_DEFAULT_YEAR = 2025
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

# === UI Configuration ===
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 30

# === LLM Configuration ===
LLM_MODEL = "qwen2.5:7b"  # Fast model that fits in 8GB RAM (2x faster than llama3.1)
LLM_TEMPERATURE = 0.3  # Faster generation while still accurate for tool calling

# === Logging Configuration ===
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# === API Keys ===
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

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

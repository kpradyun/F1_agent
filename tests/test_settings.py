"""Tests for config/settings.py — no network required."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime


def test_today_is_valid_date():
    from config.settings import TODAY
    parsed = datetime.strptime(TODAY, "%Y-%m-%d")
    assert parsed.year >= 2024


def test_llm_provider_is_valid():
    from config.settings import LLM_PROVIDER
    assert LLM_PROVIDER in ("ollama", "gemini")


def test_llm_model_is_set():
    from config.settings import LLM_MODEL
    assert LLM_MODEL
    assert isinstance(LLM_MODEL, str)


def test_default_year_in_range():
    from config.settings import DATA_DEFAULT_YEAR
    assert 2018 <= DATA_DEFAULT_YEAR <= datetime.now().year + 1


def test_grid_context_has_all_teams():
    from config.settings import GRID_CONTEXT
    expected_teams = ["McLaren", "Ferrari", "Red Bull", "Mercedes", "Aston Martin",
                      "Alpine", "Williams", "Racing Bulls", "Haas", "Audi", "Cadillac"]
    for team in expected_teams:
        assert team in GRID_CONTEXT, f"Missing team in GRID_CONTEXT: {team}"


def test_grid_context_has_expected_drivers():
    from config.settings import GRID_CONTEXT
    expected_drivers = ["Norris", "Piastri", "Leclerc", "Hamilton",
                        "Verstappen", "Russell", "Alonso"]
    for driver in expected_drivers:
        assert driver in GRID_CONTEXT, f"Missing driver in GRID_CONTEXT: {driver}"


def test_directories_created_on_import():
    from config.settings import CACHE_DIR, PLOTS_DIR
    assert os.path.isdir(CACHE_DIR)
    assert os.path.isdir(PLOTS_DIR)


def test_openf1_base_url():
    from config.settings import OPENF1_BASE_URL
    assert OPENF1_BASE_URL.startswith("https://")
    assert "openf1" in OPENF1_BASE_URL

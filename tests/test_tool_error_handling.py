"""
Tests that tool functions return error strings (not raise exceptions)
when given invalid or impossible inputs.
All FastF1/network calls are mocked to isolate the error-path logic.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


# ── helpers ──────────────────────────────────────────────────────────────────

def run(coro):
    """Run an async coroutine in a test (compatible with pytest-asyncio auto mode)."""
    return asyncio.run(coro)


# ── analysis_tools ────────────────────────────────────────────────────────────

class TestAnalysisToolErrors:
    def test_session_results_bad_gp_returns_string(self):
        """f1_session_results returns a string when session cannot be loaded."""
        with patch("core.fastf1_adapter.load_session", return_value=None):
            from tools.analysis_tools import f1_session_results
            result = run(f1_session_results.ainvoke({
                "grand_prix": "FAKE_GP_THAT_DOESNT_EXIST",
                "year": 2024,
                "session": "Race"
            }))
        assert isinstance(result, str)
        assert "Failed" in result or "not found" in result.lower()

    def test_lap_chart_no_session_returns_string(self):
        """f1_lap_chart returns a descriptive string when session fails to load."""
        with patch("core.fastf1_adapter.load_session", return_value=None):
            from tools.analysis_tools import f1_lap_chart
            result = run(f1_lap_chart.ainvoke({
                "grand_prix": "NONEXISTENT",
                "year": 2024,
            }))
        assert isinstance(result, str)
        assert "Could not load" in result or "error" in result.lower()


# ── reference_tools ───────────────────────────────────────────────────────────

class TestReferenceToolErrors:
    def test_driver_career_invalid_name_returns_string(self):
        """f1_driver_career_summary returns a string for a nonexistent driver."""
        mock_client = MagicMock()
        mock_client.search_driver_id.return_value = None
        with patch("core.api_client.get_jolpica_client", return_value=mock_client):
            from tools.reference_tools import f1_driver_career_summary
            result = run(f1_driver_career_summary.ainvoke({
                "driver_query": "xzxzxzNobodyxzxzxz"
            }))
        assert isinstance(result, str)
        assert "Could not find" in result or "Error" in result

    def test_all_time_records_invalid_category_returns_string(self):
        """f1_all_time_records returns a string for an unsupported category."""
        from tools.reference_tools import f1_all_time_records
        result = run(f1_all_time_records.ainvoke({"category": "INVALID_CATEGORY"}))
        assert isinstance(result, str)
        assert "not supported" in result.lower() or "Error" in result


# ── live_tools ────────────────────────────────────────────────────────────────

class TestLiveToolErrors:
    def test_live_weather_with_no_session_returns_string(self):
        """f1_live_weather returns a descriptive string when no live session exists."""
        with patch("tools.live_tools.verify_live_session", side_effect=Exception("No active sessions")):
            from tools.live_tools import f1_live_weather
            result = run(f1_live_weather.ainvoke({"session_key": "latest"}))
        assert isinstance(result, str)
        # Should NOT raise; should contain a user-friendly message
        assert "session" in result.lower() or "error" in result.lower() or "No" in result


# ── advanced_tools ────────────────────────────────────────────────────────────

class TestAdvancedToolErrors:
    def test_bad_year_sector_analysis_returns_string(self):
        """Tools with invalid year should return a string, not raise."""
        with patch("core.fastf1_adapter.load_session", return_value=None):
            from tools.session_tools import f1_sector_analysis
            result = run(f1_sector_analysis.ainvoke({
                "driver1": "HAM",
                "driver2": "VER",
                "grand_prix": "Fake GP",
                "year": 1800,  # Way out of valid range
            }))
        assert isinstance(result, str)

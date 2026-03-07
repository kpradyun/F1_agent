"""
Session Tools
High-resolution analysis tools for specific F1 sessions (telemetry, weather, etc.)
"""
import logging
from langchain_core.tools import tool
from config.settings import DATA_DEFAULT_YEAR
from core.fastf1_adapter import (
    get_testing_summary,
    get_weather_analysis,
    get_race_control_messages,
    analyze_telemetry,
    get_tyre_summary,
    get_sector_analysis
)
from utils.async_tools import get_async_wrapper

logger = logging.getLogger("SessionTools")

@tool
async def f1_testing_summary(year: int, test_number: int = 1, day: int = 1) -> str:
    """
    Returns a summary of an F1 testing session (Pre-season or Mid-season).
    Includes top lap times and lap counts per driver/team.
    Use when user asks about: testing, winter testing, Bahrain test, lap times in testing.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_testing_summary, year, test_number, day)
    except Exception as e:
        logger.error(f"Testing summary failed: {e}")
        return f"Error: {e}"

@tool
async def f1_weather_report(grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Provides a detailed weather report for a COMPLETED F1 session.
    Includes air/track temperatures, humidity, and rainfall status/trends.
    Use ONLY for historical analysis or when session is finished.
    Do NOT use for "live", "now", or "current" weather (use f1_live_weather instead).
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_weather_analysis, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Weather report failed: {e}")
        return f"Error: {e}"

@tool
async def f1_race_control_report(grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Lists all official race control messages from a COMPLETED session.
    Includes Safety Cars, VSC, Red Flags, Investigations, and Penalties.
    Use ONLY for historical analysis or when session is finished.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_race_control_messages, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Race control report failed: {e}")
        return f"Error: {e}"

@tool
async def f1_telemetry_breakdown(driver: str, grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Provides a technical telemetry breakdown for a driver's fastest lap.
    Includes max speed, gear usage, and braking intensity.
    Use when user asks about: technical analysis, gear ratios, driver style, telemetry.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(analyze_telemetry, driver, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Telemetry breakdown failed: {e}")
        return f"Error: {e}"

@tool
async def f1_tyre_summary(grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Detailed tyre strategy and life analysis.
    Shows compounds used, stint lengths, and current tyre age for all drivers.
    Use when user asks about: tyre life, strategy, how old are the tyres, stints.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_tyre_summary, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Tyre summary failed: {e}")
        return f"Error: {e}"

@tool
async def f1_sector_analysis(grand_prix: str, driver1: str, driver2: str = None, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Detailed sector-by-sector performance analysis for a SPECIFIC session.
    Compare best sector times between two drivers or analyze one driver's sectors.
    Use when user asks about: sector times, S1/S2/S3, where is he faster in a race.
    NOTE: For season-long driver comparisons, use f1_head_to_head instead.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_sector_analysis, year, grand_prix, session, driver1, driver2)
    except Exception as e:
        logger.error(f"Sector analysis failed: {e}")
        return f"Error: {e}"

def get_session_tools() -> list:
    """Returns a list of all session-specific analysis tools."""
    return [
        f1_testing_summary,
        f1_weather_report,
        f1_race_control_report,
        f1_telemetry_breakdown,
        f1_tyre_summary,
        f1_sector_analysis
    ]

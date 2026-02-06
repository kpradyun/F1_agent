"""
Replay Tools
Interactive race replay functionality
"""
import logging
import threading
from langchain_core.tools import tool
from config.settings import DATA_DEFAULT_YEAR, MIN_REPLAY_YEAR
from core.fastf1_adapter import prepare_replay_data
from replay_ui import run_replay_threaded
from rich.console import Console

logger = logging.getLogger("ReplayTools")
console = Console()

@tool
async def f1_race_replay(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    Launches the ADVANCED INTERACTIVE REPLAY WINDOW.
    Features: Real-time telemetry, sector lines, DNF status tracking.
    UPDATED: Now supports Sprint and Qualifying sessions.
    
    Parameters:
        grand_prix: Name of the GP (e.g., "Bahrain", "Monaco")
        year: Year of the race (e.g., 2024)
        session: "Race", "Qualifying", "Sprint"
        
    Returns:
        Status message about the replay window.
    """
    # The repository relies on detailed telemetry, usually best after 2018
    if year < MIN_REPLAY_YEAR:
        return f"Replay available for {MIN_REPLAY_YEAR}+ only (telemetry data limitation)."

    try:
        console.print(
            f"[cyan]Initializing Advanced Replay for {grand_prix} {year} ({session})...[/cyan]"
        )
        console.print("[dim]Loading session data (this may take 10-20s)...[/dim]")
        
        # 1. Fetch and prepare data (heavy CPU/IO operation)
        # We use the wrapper to run the sync FastF1 code in a thread to not block the chat
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()
        
        # This calls the 'prepare_replay_data' we defined in fastf1_adapter.py
        ui_data = await wrapper.run_sync_tool(prepare_replay_data, year, grand_prix, session)
        
        if not ui_data:
            return "Failed to prepare replay data. Check if session exists and has telemetry."

        # 2. Launch Arcade Window in separate thread
        # This keeps the agent responsive while you watch the replay
        run_replay_threaded(ui_data)
        
        return f"🏁 Replay launched for {grand_prix} {year}! Check the popup window.\n(Controls: Space=Pause, Arrows=Seek/Speed, L=Toggle Names)"

    except Exception as e:
        logger.error(f"Replay failed: {e}")
        return f"Replay failed: {e}"

def get_replay_tools() -> list:
    """Get all replay tools."""
    return [f1_race_replay]
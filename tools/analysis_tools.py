"""
Analysis Tools
F1 advanced analysis tools for telemetry, strategy, and championship calculations
"""
import logging
from langchain_core.tools import tool
from config.settings import DATA_DEFAULT_YEAR, MIN_REPLAY_YEAR
from core.fastf1_adapter import (
    get_schedule,
    get_event_details,
    get_testing_schedule,
    get_next_event,
    get_session_results,
    get_session_status_summary,
    plot_driver_comparison,
    analyze_telemetry,
    get_tire_strategy_gantt,
    get_tire_strategy_analysis,
    calculate_championship_standings
)
from utils.async_tools import get_async_wrapper

logger = logging.getLogger("AnalysisTools")


@tool
async def f1_schedule(year: int = DATA_DEFAULT_YEAR) -> str:
    """
    Returns the complete F1 race calendar for a specific year.
    Use when user asks about: schedule, calendar, next race, upcoming races,
    race dates, when is the race, what races are coming up.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_schedule, year)
    except Exception as e:
        logger.error(f"Schedule fetch failed: {e}")
        return f"Failed to fetch schedule: {e}"


@tool
async def f1_session_results(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    Returns full classification/results for a specific session.
    UPDATED: Now supports Sprint and Qualifying sessions.
    Use when user asks about: race results, who won, final positions, points scored,
    qualifying results, sprint results, DNFs, race classification.
    Session types: 'Race', 'Qualifying', 'Sprint', 'Sprint Qualifying', 'FP1', 'FP2', 'FP3'
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_session_results, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Results fetch failed: {e}")
        return f"Failed to fetch results: {e}"


@tool
async def f1_event_details(
    grand_prix: str = "",
    year: int = DATA_DEFAULT_YEAR,
    round_number: int = 0
) -> str:
    """
    Event metadata using FastF1 event APIs (get_event/get_event_schedule).
    Use when user asks about event format, venue details, or session dates.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(
            get_event_details,
            year,
            grand_prix if grand_prix else None,
            round_number if round_number > 0 else None
        )
    except Exception as e:
        logger.error(f"Event details fetch failed: {e}")
        return f"Failed to fetch event details: {e}"


@tool
async def f1_testing_schedule(year: int = DATA_DEFAULT_YEAR) -> str:
    """
    Pre-season testing schedule from FastF1 get_testing_event_schedule API.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_testing_schedule, year)
    except Exception as e:
        logger.error(f"Testing schedule fetch failed: {e}")
        return f"Failed to fetch testing schedule: {e}"


@tool
async def f1_next_event(year: int = DATA_DEFAULT_YEAR) -> str:
    """
    Next remaining event using FastF1 get_events_remaining API.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_next_event, year)
    except Exception as e:
        logger.error(f"Next event fetch failed: {e}")
        return f"Failed to fetch next event: {e}"


@tool
async def f1_session_control_summary(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    Session control/ops feed from FastF1 APIs: track status, session status,
    race control messages and weather snapshot.
    """
    try:
        wrapper = get_async_wrapper()
        return await wrapper.run_sync_tool(get_session_status_summary, year, grand_prix, session)
    except Exception as e:
        logger.error(f"Session control summary failed: {e}")
        return f"Session control summary failed: {e}"


@tool
async def f1_telemetry_plot(
    driver1: str,
    grand_prix: str,
    driver2: str = "",
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    Telemetry tool that works for one or two drivers.

    - If one driver is provided, returns detailed telemetry breakdown.
    - If two drivers are provided, creates speed comparison + time delta plot.
    """
    try:
        wrapper = get_async_wrapper()

        if not driver2:
            return await wrapper.run_sync_tool(
                analyze_telemetry, driver1, year, grand_prix, session
            )

        result = await wrapper.run_sync_tool(
            plot_driver_comparison, driver1, driver2, year, grand_prix, session
        )

        if result.startswith("plots/"):
            return f"Telemetry comparison saved: {result}"
        return result

    except Exception as e:
        logger.error(f"Telemetry plot failed: {e}")
        return f"Telemetry plot error: {e}"


@tool
async def f1_tire_strategy(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    NEW: Visual Gantt Chart for tire strategies.
    Creates a color-coded bar chart showing:
    - Tire compounds (Red=Soft, Yellow=Medium, White=Hard)
    - Stint lengths and pit stop timing
    - Strategy comparison across all drivers
    Use when user asks about: tire strategy, pit stops, compounds, race strategy.
    """
    try:
        wrapper = get_async_wrapper()
        # Run detailed operations in thread pool
        gantt_result = await wrapper.run_sync_tool(
            get_tire_strategy_gantt, year, grand_prix, session
        )
        text_result = await wrapper.run_sync_tool(
            get_tire_strategy_analysis, year, grand_prix, session
        )
        
        if gantt_result.startswith("plots/"):
            return f"Tire strategy Gantt chart saved: {gantt_result}\n\n{text_result}"
        else:
            return f"{gantt_result}\n\n{text_result}"
            
    except Exception as e:
        logger.error(f"Tire strategy failed: {e}")
        return f"Tire strategy error: {e}"


@tool
async def f1_championship_calculator(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR
) -> str:
    """
    Championship Standings Calculator.
    Projects updated Driver and Constructor standings after a specific race.
    Shows current points, position changes, and championship implications.
    Use when user asks about: championship standings, points, who's leading, title fight.
    """
    try:
        wrapper = get_async_wrapper()
        result = await wrapper.run_sync_tool(
            calculate_championship_standings, year, grand_prix
        )
        return result
    except Exception as e:
        logger.error(f"Championship calculation failed: {e}")
        return f"Championship calculation error: {e}"


@tool
async def f1_race_weekend_summary(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR
) -> str:
    """
    Comprehensive weekend report combining multiple data sources.
    Includes: results, strategy, and track positions.
    """
    from core.session_resolver import get_resolver
    from tools.live_tools import f1_live_position_map
    
    output = f"=== {grand_prix.upper()} {year} - RACE WEEKEND SUMMARY ===\n\n"
    wrapper = get_async_wrapper()
    
    try:
        results = await wrapper.run_sync_tool(get_session_results, year, grand_prix, "Race")
        output += f"{results}\n\n"
    except Exception as e:
        output += f"[RESULTS] Failed to fetch: {e}\n\n"

    try:
        strategy = await wrapper.run_sync_tool(get_tire_strategy_analysis, year, grand_prix, "Race")
        output += f"{strategy}\n\n"
    except Exception as e:
        output += f"[STRATEGY] Failed to fetch: {e}\n\n"
    
    try:
        resolver = get_resolver()
        # Resolver is lightweight/singleton, safe to run sync
        session_key = resolver.resolve(year, grand_prix, "Race")
        
        # Use ainvoke for async tool call
        map_result = await f1_live_position_map.ainvoke({"session_key": session_key})
        output += f"[TRACK POSITIONS]\n{map_result}\n\n"
    except Exception as e:
        output += f"[TRACK POSITIONS] Failed: {e}\n\n"

    if year >= MIN_REPLAY_YEAR and grand_prix != "latest":
        try:
            session_results = await wrapper.run_sync_tool(get_session_results, year, grand_prix, "Race")
            lines = session_results.split('\n')[1:3]
            
            if len(lines) >= 2:
                driver1 = lines[0].split('(')[0].strip().split('. ')[1]
                driver2 = lines[1].split('(')[0].strip().split('. ')[1]
                
                # Use ainvoke for async tool call
                telem_result = await f1_telemetry_plot.ainvoke({
                    "driver1": driver1,
                    "driver2": driver2,
                    "grand_prix": grand_prix,
                    "year": year,
                    "session": "Race"
                })
                output += f"[TELEMETRY - Top 2 Drivers]\n{telem_result}\n\n"
        except Exception as e:
            output += f"[TELEMETRY] Failed: {e}\n\n"
    
    return output


def get_analysis_tools() -> list:
    """
    Get all analysis tools.
    
    Returns:
        List of analysis tool functions
    """
    return [
        f1_schedule,
        f1_next_event,
        f1_event_details,
        f1_testing_schedule,
        f1_session_results,
        f1_session_control_summary,
        f1_telemetry_plot,
        f1_tire_strategy,
        f1_championship_calculator,
        f1_race_weekend_summary
    ]

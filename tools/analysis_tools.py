"""
Analysis Tools
F1 advanced analysis tools for telemetry, strategy, and championship calculations
"""
import logging
import os
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from config.settings import DATA_DEFAULT_YEAR, FASTF1_MIN_YEAR, PLOTS_DIR
from core.fastf1_adapter import (
    get_schedule,
    get_session_results,
    plot_driver_comparison,
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
async def f1_telemetry_plot(
    driver1: str,
    driver2: str,
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR,
    session: str = "Race"
) -> str:
    """
    NEW: Enhanced with Delta Trace.
    Creates speed comparison + time delta plot between two drivers in a SPECIFIC session.
    Use when user asks to: compare drivers in a race, telemetry, speed trace, lap analysis.
    Shows where time was gained/lost over the lap distance.
    NOTE: For season-long headcount/points comparison, use f1_head_to_head instead.
    Session types: 'Race', 'Qualifying', 'Sprint', 'Sprint Qualifying'
    """
    try:
        wrapper = get_async_wrapper()
        result = await wrapper.run_sync_tool(
            plot_driver_comparison, driver1, driver2, year, grand_prix, session
        )
        
        if result.startswith("plots/"):
            return f"Telemetry comparison saved: {result}"
        else:
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
        
        if gantt_result.startswith("plots/"):
            return f"Tire strategy Gantt chart saved: {gantt_result}"
        else:
            return gantt_result
            
    except Exception as e:
        logger.error(f"Tire strategy failed: {e}")
        return f"Tire strategy error: {e}"


@tool
async def f1_championship_calculator(
    grand_prix: str,
    year: int = DATA_DEFAULT_YEAR
) -> str:
    """
    Championship Standings Calculator for COMPLETED races.
    Projects updated Driver and Constructor standings after a specific race.
    Use ONLY when the race is finished.
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

    if year >= FASTF1_MIN_YEAR and grand_prix != "latest":
        try:
            from core.fastf1_adapter import load_session
            race_session = await wrapper.run_sync_tool(load_session, year, grand_prix, "Race")
            if race_session is not None:
                res = race_session.results
                if res is not None and not res.empty and len(res) >= 2:
                    driver1 = str(res.iloc[0].get('Abbreviation', ''))
                    driver2 = str(res.iloc[1].get('Abbreviation', ''))
                    if driver1 and driver2:
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


@tool
async def f1_lap_chart(grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Creates a position-by-lap line chart for all drivers showing how positions changed
    throughout the race. Visualizes overtakes, pit stop effects, and safety car periods.
    Use when user asks about: lap chart, position changes by lap, overtake visualization,
    who was where on lap N, position history through the race.
    """
    try:
        from core.fastf1_adapter import load_session
        import pandas as pd

        wrapper = get_async_wrapper()
        session_obj = await wrapper.run_sync_tool(load_session, year, grand_prix, session)
        if session_obj is None:
            return f"Could not load session data for {grand_prix} {year}."

        laps = session_obj.laps
        if laps.empty:
            return "No lap data available for this session."

        drivers = laps['Driver'].unique()
        fig, ax = plt.subplots(figsize=(16, 9))
        fig.patch.set_facecolor('#1E1E1E')
        ax.set_facecolor('#1E1E1E')

        import fastf1.plotting
        for driver in drivers:
            d_laps = laps.pick_drivers(driver)[['LapNumber', 'Position']].dropna()
            if d_laps.empty:
                continue
            try:
                color = fastf1.plotting.get_driver_color(driver, session=session_obj)
            except Exception:
                color = '#AAAAAA'
            ax.plot(d_laps['LapNumber'], d_laps['Position'],
                    color=color, linewidth=1.5, alpha=0.85)
            last = d_laps.iloc[-1]
            ax.annotate(driver, (last['LapNumber'], last['Position']),
                        color=color, fontsize=7, va='center',
                        xytext=(3, 0), textcoords='offset points')

        ax.set_xlabel('Lap', color='white')
        ax.set_ylabel('Position', color='white')
        ax.set_title(f'Lap Chart — {grand_prix} {year} {session}', color='white', fontsize=14)
        ax.invert_yaxis()
        ax.set_yticks(range(1, len(drivers) + 1))
        ax.tick_params(colors='white')
        ax.grid(axis='both', alpha=0.2, color='gray')
        plt.tight_layout()

        filename = f"{PLOTS_DIR}/{year}_{grand_prix.replace(' ', '_')}_lap_chart.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#1E1E1E')
        plt.close()

        return f"Lap chart saved: {filename}"
    except Exception as e:
        logger.error(f"Lap chart failed: {e}")
        return f"Lap chart error: {e}"


@tool
async def f1_gap_evolution(grand_prix: str, year: int = DATA_DEFAULT_YEAR, session: str = "Race") -> str:
    """
    Creates a gap-to-leader chart showing how the gap between each driver and
    the race leader evolved over every lap. Reveals when gaps opened, closed,
    and the impact of pit stops and safety cars.
    Use when user asks about: gap to leader, gap evolution, when did Verstappen
    build his lead, battle for position, closing gap.
    """
    try:
        from core.fastf1_adapter import load_session
        import pandas as pd
        import numpy as np

        wrapper = get_async_wrapper()
        session_obj = await wrapper.run_sync_tool(load_session, year, grand_prix, session)
        if session_obj is None:
            return f"Could not load session data for {grand_prix} {year}."

        laps = session_obj.laps
        if laps.empty:
            return "No lap data available."

        # Calculate cumulative race time per driver per lap
        laps_clean = laps[['Driver', 'LapNumber', 'LapTime']].dropna()
        laps_clean = laps_clean.copy()
        laps_clean['LapTime_s'] = laps_clean['LapTime'].dt.total_seconds()
        laps_clean['CumTime'] = laps_clean.groupby('Driver')['LapTime_s'].cumsum()

        # Leader cumulative time per lap
        leader_times = laps_clean.sort_values('CumTime').groupby('LapNumber').first()[['Driver', 'CumTime']]
        leader_times.columns = ['Leader', 'LeaderCumTime']

        merged = laps_clean.merge(leader_times, on='LapNumber')
        merged['GapToLeader'] = merged['CumTime'] - merged['LeaderCumTime']

        import fastf1.plotting
        fig, ax = plt.subplots(figsize=(16, 9))
        fig.patch.set_facecolor('#1E1E1E')
        ax.set_facecolor('#1E1E1E')

        for driver, d_data in merged.groupby('Driver'):
            d_data = d_data.sort_values('LapNumber')
            if d_data['GapToLeader'].max() > 120:
                continue  # Skip lapped drivers for readability
            try:
                color = fastf1.plotting.get_driver_color(driver, session=session_obj)
            except Exception:
                color = '#AAAAAA'
            ax.plot(d_data['LapNumber'], d_data['GapToLeader'],
                    color=color, linewidth=1.5, alpha=0.85)
            last = d_data.iloc[-1]
            ax.annotate(driver, (last['LapNumber'], last['GapToLeader']),
                        color=color, fontsize=7, va='center',
                        xytext=(3, 0), textcoords='offset points')

        ax.axhline(y=0, color='white', linestyle='--', alpha=0.4, linewidth=1)
        ax.set_xlabel('Lap', color='white')
        ax.set_ylabel('Gap to Leader (s)', color='white')
        ax.set_title(f'Gap to Leader — {grand_prix} {year} {session}', color='white', fontsize=14)
        ax.tick_params(colors='white')
        ax.grid(axis='both', alpha=0.2, color='gray')
        plt.tight_layout()

        filename = f"{PLOTS_DIR}/{year}_{grand_prix.replace(' ', '_')}_gap_evolution.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#1E1E1E')
        plt.close()

        return f"Gap evolution chart saved: {filename}"
    except Exception as e:
        logger.error(f"Gap evolution failed: {e}")
        return f"Gap evolution error: {e}"


def get_analysis_tools() -> list:
    """
    Get all analysis tools.

    Returns:
        List of analysis tool functions
    """
    return [
        f1_schedule,
        f1_session_results,
        f1_telemetry_plot,
        f1_tire_strategy,
        f1_championship_calculator,
        f1_race_weekend_summary,
        f1_lap_chart,
        f1_gap_evolution,
    ]

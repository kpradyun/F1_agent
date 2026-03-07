"""
Advanced F1 Tools - Complete API Utilization
Leveraging ALL OpenF1 endpoints for maximum functionality
"""
import logging
import asyncio
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.api_client import get_enhanced_client
from config.settings import DATA_DEFAULT_YEAR, PLOTS_DIR
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger("AdvancedTools")


# ============================================================================
# Real-Time Telemetry Tools
# ============================================================================

@tool
async def f1_live_car_telemetry(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Get car telemetry data (speed, RPM, gear, throttle, brake, DRS).
    Works for both LIVE and HISTORICAL sessions.
    
    Use when user asks about:
    - Speed, gear, or RPM in a session
    - Throttle/brake application
    - DRS activation zones
    - Car performance comparisons
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        telemetry = await client.get_car_data_async(session_key, driver_number)
        
        if not telemetry:
            return "No telemetry data available for this session."
        
        df = pd.DataFrame(telemetry)
        
        # Get latest data per driver
        latest = df.sort_values('date').groupby('driver_number').tail(1)
        
        output = "=== LIVE CAR TELEMETRY ===\n\n"
        
        for _, row in latest.iterrows():
            driver = int(row['driver_number'])
            output += f"Driver #{driver}:\n"
            output += f"  Speed: {row.get('speed', 'N/A')} km/h\n"
            output += f"  RPM: {row.get('rpm', 'N/A')}\n"
            output += f"  Gear: {row.get('n_gear', 'N/A')}\n"
            output += f"  Throttle: {row.get('throttle', 'N/A')}%\n"
            output += f"  Brake: {'ON' if row.get('brake', 0) else 'OFF'}\n"
            output += f"  DRS: {row.get('drs', 'N/A')}\n"
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Telemetry fetch failed: {e}")
        return f"Failed to get telemetry: {e}"


@tool
async def f1_driver_info(
    grand_prix: str = "latest",
    year: int = 2025,
    session_key: str = None
) -> str:
    """
    Get comprehensive driver information for a session.
    
    Use when user asks about:
    - Driver lineup for a specific race
    - Team rosters and nationalities
    - Driver abbreviations/numbers
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        drivers = await client.get_drivers_async(session_key)
        
        if not drivers:
            return "No driver data available."
        
        output = "=== F1 DRIVER LINEUP ===\n\n"
        
        # Group by team
        df = pd.DataFrame(drivers)
        
        for team in df['team_name'].unique():
            team_drivers = df[df['team_name'] == team]
            output += f"🏎️  {team}:\n"
            
            for _, driver in team_drivers.iterrows():
                output += f"   #{driver['driver_number']} {driver['full_name']} "
                output += f"({driver['name_acronym']}) - {driver.get('country_code', 'N/A')}\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Driver info failed: {e}")
        return f"Failed to get driver info: {e}"


@tool
async def f1_pit_stop_analysis(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Analyze pit stop performance and strategy for a session.
    
    Use when user asks about:
    - Pit stop times/durations
    - Fastest pit stops in a race
    - Pit stop ranking
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        pit_stops = await client.get_pit_stops_async(session_key, driver_number)
        
        if not pit_stops:
            return "No pit stop data available for this session."
        
        df = pd.DataFrame(pit_stops)
        
        output = "=== PIT STOP ANALYSIS ===\n\n"
        
        # Overall stats
        output += f"Total Pit Stops: {len(df)}\n"
        output += f"Average Duration: {df['pit_duration'].mean():.2f}s\n"
        output += f"Fastest Stop: {df['pit_duration'].min():.2f}s\n"
        output += f"Slowest Stop: {df['pit_duration'].max():.2f}s\n\n"
        
        # Top 5 fastest stops
        output += "⚡ TOP 5 FASTEST STOPS:\n"
        fastest = df.nsmallest(5, 'pit_duration')
        
        for idx, (_, stop) in enumerate(fastest.iterrows(), 1):
            output += f"{idx}. Driver #{int(stop['driver_number'])} - "
            output += f"{stop['pit_duration']:.2f}s (Lap {stop['lap_number']})\n"
        
        output += "\n"
        
        # Per-driver breakdown
        if driver_number is None:
            output += "PER-DRIVER PIT STOPS:\n"
            driver_stats = df.groupby('driver_number').agg({
                'pit_duration': ['count', 'mean', 'min']
            }).round(2)
            
            for driver_num in driver_stats.index:
                count, avg, best = driver_stats.loc[driver_num, 'pit_duration']
                output += f"  #{int(driver_num)}: {int(count)} stops | "
                output += f"Avg: {avg:.2f}s | Best: {best:.2f}s\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Pit stop analysis failed: {e}")
        return f"Failed to analyze pit stops: {e}"


@tool
async def f1_race_control_messages(
    grand_prix: str = "latest",
    year: int = 2025,
    session_key: str = None
) -> str:
    """
    Get race control messages (flags, penalties, safety car, DRS) for a session.
    
    Use when user asks about:
    - Race control events (SC, VSC, Flags)
    - DRS status in a race
    - Penalties issued during a session
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        messages = await client.get_race_control_async(session_key)
        
        if not messages:
            return "No race control messages available."
        
        df = pd.DataFrame(messages)
        df = df.sort_values('date')
        
        output = "=== RACE CONTROL MESSAGES ===\n\n"
        
        # Group by category
        for category in df['category'].unique():
            cat_messages = df[df['category'] == category]
            
            if category == 'Flag':
                emoji = "🚩"
            elif category == 'SafetyCar':
                emoji = "🚗"
            elif category == 'DRS':
                emoji = "🔓"
            elif category == 'CarEvent':
                emoji = "⚠️"
            else:
                emoji = "📢"
            
            output += f"{emoji} {category.upper()}:\n"
            
            for _, msg in cat_messages.head(10).iterrows():
                output += f"   [{msg.get('lap_number', '?')}] {msg['message']}\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Race control fetch failed: {e}")
        return f"Failed to get race control messages: {e}"


@tool
async def f1_position_changes(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Track position changes throughout a session.
    
    Use when user asks about:
    - Position battles and overtakes
    - Gained/lost positions in a race
    - Final standings for a session
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        positions = await client.get_position_async(session_key, driver_number)
        
        if not positions:
            return "No position data available."
        
        df = pd.DataFrame(positions)
        
        output = "=== POSITION CHANGES ===\n\n"
        
        # Current standings
        latest = df.sort_values(['date']).groupby('driver_number').tail(1)
        latest = latest.sort_values('position')
        
        output += "CURRENT ORDER:\n"
        for _, pos in latest.iterrows():
            output += f"P{int(pos['position'])}: Driver #{int(pos['driver_number'])}\n"
        
        output += "\n"
        
        # Calculate position changes (start vs current)
        start_positions = df.sort_values('date').groupby('driver_number').first()
        current_positions = df.sort_values('date').groupby('driver_number').last()
        
        changes = []
        for driver in start_positions.index:
            if driver in current_positions.index:
                start_pos = start_positions.loc[driver, 'position']
                current_pos = current_positions.loc[driver, 'position']
                change = start_pos - current_pos  # Positive = gained positions
                
                changes.append({
                    'driver': int(driver),
                    'start': int(start_pos),
                    'current': int(current_pos),
                    'change': int(change)
                })
        
        # Sort by biggest gains
        changes.sort(key=lambda x: x['change'], reverse=True)
        
        output += "📈 BIGGEST GAINERS:\n"
        for entry in changes[:5]:
            if entry['change'] > 0:
                output += f"  #{entry['driver']}: P{entry['start']} → P{entry['current']} "
                output += f"(L+{entry['change']} positions)\n"
        
        output += "\n📉 BIGGEST LOSERS:\n"
        for entry in reversed(changes[-5:]):
            if entry['change'] < 0:
                output += f"  #{entry['driver']}: P{entry['start']} → P{entry['current']} "
                output += f"({entry['change']} positions)\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Position tracking failed: {e}")
        return f"Failed to track positions: {e}"


@tool
async def f1_stint_analysis(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Analyze tire stints and compound strategies.
    
    Use when user asks about:
    - Tire choices and stint lengths
    - Tire age and degradation
    - Historical compound performance
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        stints = await client.get_stints_async(session_key, driver_number)
        
        if not stints:
            return "No stint data available."
        
        df = pd.DataFrame(stints)
        
        output = "=== TIRE STINT ANALYSIS ===\n\n"
        
        # Per-driver breakdown
        for driver in df['driver_number'].unique():
            driver_stints = df[df['driver_number'] == driver].sort_values('stint_number')
            
            output += f"Driver #{int(driver)}:\n"
            
            for _, stint in driver_stints.iterrows():
                compound = stint['compound']
                lap_start = stint.get('lap_start', '?')
                lap_end = stint.get('lap_end', '?')
                tire_age = stint.get('tyre_age_at_start', 0)
                
                # Compound emoji
                if compound == 'SOFT':
                    emoji = "🔴"
                elif compound == 'MEDIUM':
                    emoji = "🟡"
                elif compound == 'HARD':
                    emoji = "⚪"
                elif compound == 'INTERMEDIATE':
                    emoji = "🟢"
                elif compound == 'WET':
                    emoji = "🔵"
                else:
                    emoji = "⚫"
                
                output += f"  Stint {int(stint['stint_number'])}: {emoji} {compound} "
                output += f"(Laps {lap_start}-{lap_end}, "
                output += f"Age: {int(tire_age)} laps)\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Stint analysis failed: {e}")
        return f"Failed to analyze stints: {e}"


@tool
async def f1_team_radio_log(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Get team radio communications log for a session.
    
    Use when user asks about:
    - Team radio messages and comms
    - Historical strategy calls over radio
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        radio = await client.get_team_radio_async(session_key, driver_number)
        
        if not radio:
            return "No team radio data available."
        
        df = pd.DataFrame(radio)
        df = df.sort_values('date')
        
        output = "=== TEAM RADIO LOG ===\n\n"
        
        for _, msg in df.iterrows():
            driver = int(msg['driver_number'])
            recording_url = msg.get('recording_url', 'N/A')
            
            output += f"📻 Driver #{driver}: {recording_url}\n"
        
        output += f"\nTotal messages: {len(df)}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Team radio fetch failed: {e}")
        return f"Failed to get team radio: {e}"


@tool
async def f1_lap_analysis(
    grand_prix: str = "latest",
    year: int = 2025,
    driver_number: Optional[int] = None,
    session_key: str = None
) -> str:
    """
    Detailed lap time and sector analysis for a session.
    
    Use when user asks about:
    - Lap/sector times comparison
    - Fastest lap details
    - Personal bests and consistency
    
    Args:
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        driver_number: Specific driver number (optional)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        if not session_key:
            if grand_prix == "latest":
                session_key = await client.get_latest_session_key_async()
            else:
                resolver = get_resolver()
                session_key = resolver.resolve(year, grand_prix, "Race")
        
        laps = await client.get_laps_async(session_key, driver_number)
        
        if not laps:
            return "No lap data available."
        
        df = pd.DataFrame(laps)
        
        # Convert lap times to seconds
        df['lap_duration_seconds'] = df['lap_duration'].apply(
            lambda x: float(x) if x else None
        )
        
        output = "=== LAP TIME ANALYSIS ===\n\n"
        
        # Overall fastest lap
        fastest_lap = df.loc[df['lap_duration_seconds'].idxmin()]
        output += f"⚡ FASTEST LAP:\n"
        output += f"   Driver #{int(fastest_lap['driver_number'])} - "
        output += f"{fastest_lap['lap_duration_seconds']:.3f}s "
        output += f"(Lap {int(fastest_lap['lap_number'])})\n\n"
        
        # Per-driver stats
        driver_stats = df.groupby('driver_number').agg({
            'lap_duration_seconds': ['count', 'mean', 'min', 'std']
        }).round(3)
        
        output += "PER-DRIVER STATISTICS:\n"
        
        for driver in driver_stats.index:
            count, avg, best, std = driver_stats.loc[driver, 'lap_duration_seconds']
            output += f"  #{int(driver)}: Best {best:.3f}s | "
            output += f"Avg {avg:.3f}s | "
            output += f"Consistency ±{std:.3f}s | "
            output += f"({int(count)} laps)\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Lap analysis failed: {e}")
        return f"Failed to analyze laps: {e}"


# ============================================================================
# Tool Collection
# ============================================================================

def get_advanced_tools() -> List:
    """
    Get all advanced tools utilizing complete API coverage.
    
    Returns:
        List of advanced tool functions
    """
    return [
        f1_live_car_telemetry,
        f1_driver_info,
        f1_pit_stop_analysis,
        f1_race_control_messages,
        f1_position_changes,
        f1_stint_analysis,
        f1_team_radio_log,
        f1_lap_analysis
    ]

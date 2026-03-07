"""
Live Data Tools
Real-time F1 data tools for weather, positions, and intervals
"""
import logging
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fastf1.plotting
from langchain_core.tools import tool
from core.api_client import get_enhanced_client
from config.settings import PLOTS_DIR, TODAY

logger = logging.getLogger("LiveTools")

async def verify_live_session(client, session_key: str) -> str:
    """Verifies that the session is actually happening today. Returns session_key or raises Exception."""
    if session_key == "latest":
        sessions = await client.get_sessions_async(session_key="latest")
        if not sessions:
            raise Exception("No sessions available from API.")
        
        latest_session = sessions[0]
        date_start = latest_session.get('date_start', '')
        date_end = latest_session.get('date_end', '')
        
        if not date_start.startswith(TODAY) and not date_end.startswith(TODAY):
            raise Exception(f"There is no live F1 session occurring today ({TODAY}). The last recorded session was {latest_session.get('session_name')} on {date_start.split('T')[0]}.")
            
        return latest_session['session_key']
    return session_key


@tool
async def f1_live_weather(session_key: str = "latest") -> str:
    """
    Returns current weather conditions at the track.
    Use when user asks about: weather, temperature, rain, track conditions.
    Shows air temp, humidity, pressure, rainfall, track temp, and wind.
    """
    try:
        client = get_enhanced_client()
        session_key = await verify_live_session(client, session_key)
        
        weather_data = await client.get_weather_async(session_key)
        
        if not weather_data:
            return "No weather data available for this session."
        
        latest = weather_data[-1] if isinstance(weather_data, list) else weather_data
        
        output = "--- LIVE WEATHER CONDITIONS ---\n"
        output += f"Air Temperature: {latest.get('air_temperature', 'N/A')}°C\n"
        output += f"Track Temperature: {latest.get('track_temperature', 'N/A')}°C\n"
        output += f"Humidity: {latest.get('humidity', 'N/A')}%\n"
        output += f"Pressure: {latest.get('pressure', 'N/A')} mbar\n"
        output += f"Rainfall: {latest.get('rainfall', 0)} (0=Dry, 1=Wet)\n"
        output += f"Wind Direction: {latest.get('wind_direction', 'N/A')}°\n"
        output += f"Wind Speed: {latest.get('wind_speed', 'N/A')} m/s\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return f"Weather data unavailable: {e}"


@tool
async def f1_live_position_map(session_key: str = "latest") -> str:
    """
    Generates a satellite view map of current driver positions on track.
    Use when user asks about: where drivers are, track positions, visual map.
    Creates and saves a PNG file showing all car locations.
    """
    try:
        client = get_enhanced_client()
        session_key = await verify_live_session(client, session_key)

        location_data = await client.get_location_async(session_key)
        df = pd.DataFrame(location_data)
        
        if df.empty:
            return "No location data found for this session."

        current_positions = df.sort_values('date').groupby('driver_number').tail(1)

        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
        plt.figure(figsize=(12, 9))
        plt.style.use('dark_background')
        
        # Plot track outline using historical positions
        plt.scatter(
            df['x'].tail(5000),
            df['y'].tail(5000),
            s=1,
            c='gray',
            alpha=0.3,
            label='Track'
        )
        
        # Plot current car positions
        plt.scatter(
            current_positions['x'],
            current_positions['y'],
            s=100,
            c='red',
            edgecolors='yellow',
            linewidths=2,
            label='Cars'
        )
        
        # Annotate with driver numbers
        for _, row in current_positions.iterrows():
            plt.annotate(
                str(int(row['driver_number'])),
                (row['x'], row['y']),
                color='white',
                fontsize=10,
                ha='center'
            )
        
        plt.xlabel('X Position (m)')
        plt.ylabel('Y Position (m)')
        plt.title('Live Track Positions')
        plt.legend()
        plt.grid(alpha=0.2)
        
        filename = f"{PLOTS_DIR}/live_positions_{session_key}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filename
        
    except Exception as e:
        logger.error(f"Position map failed: {e}")
        return f"Position map error: {e}"


@tool
async def f1_live_intervals(session_key: str = "latest") -> str:
    """
    Live timing gaps between drivers during a session.
    Use when user asks about: current race positions, gaps, intervals, live timing.
    Shows P1-P20 with time gaps to leader.
    """
    try:
        client = get_enhanced_client()
        session_key = await verify_live_session(client, session_key)
        
        intervals = await client.get_intervals_async(session_key)
        df = pd.DataFrame(intervals)
        
        if df.empty:
            return "No interval data available for this session."
        
        # Get latest interval for each driver
        latest_intervals = df.sort_values('date').groupby('driver_number').tail(1)
        latest_intervals = latest_intervals.sort_values('interval')
        
        output = "--- LIVE TIMING INTERVALS ---\n"
        for idx, row in latest_intervals.iterrows():
            pos = row.get('position', '?')
            driver = row['driver_number']
            gap = row.get('gap_to_leader', '0.000')
            interval = row.get('interval', '0.000')
            
            output += f"P{pos}: #{driver} | Gap: +{gap}s | Interval: {interval}s\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Intervals fetch failed: {e}")
        return f"Interval data unavailable: {e}"


def get_live_tools() -> list:
    """
    Get all live data tools.
    
    Returns:
        List of live tool functions
    """
    return [
        f1_live_weather,
        f1_live_position_map,
        f1_live_intervals
    ]

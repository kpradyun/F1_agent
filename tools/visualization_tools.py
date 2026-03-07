"""
Visualization Tools
Interactive charts and graphs using Plotly.
Generates HTML files for deep data exploration.
"""
import logging
import os
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from langchain_core.tools import tool
import fastf1
import fastf1.plotting
from core.api_client import get_enhanced_client
from config.settings import PLOTS_DIR

logger = logging.getLogger("VizTools")

# Ensure plots directory exists
os.makedirs(PLOTS_DIR, exist_ok=True)

@tool
async def f1_plot_telemetry_interactive(
    driver1_number: int,
    driver2_number: int,
    session_key: str = "latest"
) -> str:
    """
    Generates an INTERACTIVE telemetry comparison (Speed, Throttle, Brake).
    Saves as HTML file allowing zoom/pan.
    Use for deep dive comparisons between two drivers.
    """
    try:
        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
        client = get_enhanced_client()
        if session_key == "latest":
            session_key = await client.get_latest_session_key_async()
            
        # 1. Fetch telemetry concurrently
        drivers = [driver1_number, driver2_number]
        results = await client.get_all_driver_data_async(session_key, drivers)
        
        data1 = results.get(driver1_number, [])
        data2 = results.get(driver2_number, [])
        
        if not data1 or not data2:
            return "Insufficient telemetry data for comparison."
            
        # 2. Process Data
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)
        
        # Merge on distance or time? Distance is standard for track position.
        # Ensure date/time is sorted
        df1['date'] = pd.to_datetime(df1['date'])
        df2['date'] = pd.to_datetime(df2['date'])
        
        # Calculate distance if missing (FastF1 usually provides it, OpenF1 might not)
        # OpenF1 'car_data' doesn't explicitly have distance.
        # We might need to map to 'laps' or just use Time index.
        # Using Index (samples) is rough. Using DateTime is better.
        # Best is to synchronize laps.
        # For simplicity in this tool, we'll align by 'date' relative to start of a "fast lap"?
        # Actually, extracting a specific lap is hard without 'laps' data overlay.
        # Basic approach: Plot entire session? Too distinct.
        # Better: Plot LAST 60 Seconds of available data (Live comparison).
        # Or if historical: Plot specific lap?
        # Let's plot the LAST 2 MINUTES of data for live analysis context.
        
        latest_time = max(df1['date'].max(), df2['date'].max())
        start_time = latest_time - pd.Timedelta(seconds=120)
        
        df1 = df1[df1['date'] > start_time]
        df2 = df2[df2['date'] > start_time]
        
        # 3. Create Plot
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=("Speed (km/h)", "Throttle (%)", "Brake"))
        
        # Get Driver Colors from FastF1
        try:
            # We need the year and event for FastF1. OpenF1 session gives meeting_key.
            session_info = await client.get_sessions_async(session_key=session_key)
            if session_info:
                s_year = session_info[0]['year']
                s_country = session_info[0]['country_name']
                f1_session = fastf1.get_session(s_year, s_country, 'R')
                # Load minimal data just for driver info
                f1_session.load(telemetry=False, weather=False, messages=False)
                
                # Plotly uses hex strings directly, fastf1 returns #RRGGBB
                d1_abbrev = str(driver1_number) # fallback
                d2_abbrev = str(driver2_number) # fallback
                
                # Find abbreviations
                for drv in f1_session.drivers:
                    try:
                        d = f1_session.get_driver(drv)
                        if d['DriverNumber'] == str(driver1_number):
                            d1_abbrev = d['Abbreviation']
                        if d['DriverNumber'] == str(driver2_number):
                            d2_abbrev = d['Abbreviation']
                    except:
                        pass
                
                color1 = fastf1.plotting.get_driver_color(d1_abbrev, session=f1_session)
                color2 = fastf1.plotting.get_driver_color(d2_abbrev, session=f1_session)
            else:
                color1, color2 = 'cyan', 'magenta'
        except Exception as e:
            logger.warning(f"Could not load FastF1 colors, using defaults: {e}")
            color1, color2 = 'cyan', 'magenta'

        # Speed
        fig.add_trace(go.Scatter(x=df1['date'], y=df1['speed'], name=f"#{driver1_number}", line=dict(color=color1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df2['date'], y=df2['speed'], name=f"#{driver2_number}", line=dict(color=color2)), row=1, col=1)
        
        # Throttle
        fig.add_trace(go.Scatter(x=df1['date'], y=df1['throttle'], name=f"#{driver1_number}", line=dict(color=color1), showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df2['date'], y=df2['throttle'], name=f"#{driver2_number}", line=dict(color=color2), showlegend=False), row=2, col=1)
        
        # Brake
        fig.add_trace(go.Scatter(x=df1['date'], y=df1['brake'], name=f"#{driver1_number}", line=dict(color=color1), showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df2['date'], y=df2['brake'], name=f"#{driver2_number}", line=dict(color=color2), showlegend=False), row=3, col=1)
        
        fig.update_layout(
            title=f"Telemetry Comparison: #{driver1_number} vs #{driver2_number}",
            template="plotly_dark",
            height=800
        )
        
        filename = f"telemetry_{session_key}_{driver1_number}_{driver2_number}.html"
        filepath = os.path.join(PLOTS_DIR, filename)
        fig.write_html(filepath)
        
        return f"Interactive telemetry chart saved: {filepath}"
        
    except Exception as e:
        logger.error(f"Telemetry plot failed: {e}")
        return f"Error generating chart: {e}"

@tool
async def f1_plot_strategy_gantt(session_key: str = "latest") -> str:
    """
    Generates an INTERACTIVE Gantt chart of tire strategies.
    Shows stints, compounds, and tire age for all drivers.
    Saves as HTML.
    """
    try:
        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
        client = get_enhanced_client()
        if session_key == "latest":
            session_key = await client.get_latest_session_key_async()
            
        stints = await client.get_stints_async(session_key)
        if not stints:
            return "No stint data available."
            
        df = pd.DataFrame(stints)
        
        # Map compounds to colors
        try:
            session_info = await client.get_sessions_async(session_key=session_key)
            if session_info:
                s_year = session_info[0]['year']
                s_country = session_info[0]['country_name']
                f1_session = fastf1.get_session(s_year, s_country, 'R')
                f1_session.load(telemetry=False, weather=False, messages=False)
                colors = fastf1.plotting.get_compound_mapping(session=f1_session)
            else:
                colors = {"SOFT": "red", "MEDIUM": "yellow", "HARD": "white", "INTERMEDIATE": "green", "WET": "blue"}
        except Exception:
            colors = {"SOFT": "red", "MEDIUM": "yellow", "HARD": "white", "INTERMEDIATE": "green", "WET": "blue"}
        
        # Process for Gantt
        gantt_data = []
        for _, row in df.iterrows():
            compound = str(row.get('compound', '')).upper()
            gantt_data.append(dict(
                Driver=f"#{row['driver_number']}",
                Start=row['lap_start'],
                Finish=row['lap_end'],
                Compound=compound,
                Color=colors.get(compound, '#808080')
            ))
            
        df_gantt = pd.DataFrame(gantt_data)
        
        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Finish", 
            y="Driver", 
            color="Compound",
            color_discrete_map=colors,
            title=f"Tire Strategy History - Session {session_key}"
        )
        
        fig.update_yaxes(autorange="reversed") # Leader on top
        fig.update_layout(
            xaxis_title="Lap Number",
            template="plotly_dark",
            height=800
        )
        
        filename = f"strategy_{session_key}.html"
        filepath = os.path.join(PLOTS_DIR, filename)
        fig.write_html(filepath)
        
        return f"Strategy chart saved: {filepath}"
        
    except Exception as e:
        logger.error(f"Strategy plot failed: {e}")
        return f"Error generating chart: {e}"

def get_visualization_tools() -> list:
    return [f1_plot_telemetry_interactive, f1_plot_strategy_gantt]

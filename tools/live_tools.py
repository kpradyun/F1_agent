"""
Live Data Tools
Real-time F1 data tools for weather, positions, and intervals
"""
import logging
import asyncio
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fastf1.plotting
from langchain_core.tools import tool
from core.api_client import get_enhanced_client
from config.settings import PLOTS_DIR, TODAY, DATA_DEFAULT_YEAR

logger = logging.getLogger("LiveTools")

async def verify_live_session(client, session_key: str) -> dict:
    """
    Returns a session dict for the current or most-recently-started session.
    Raises Exception if no session has started today (no race weekend).
    """
    import datetime as _dt

    if session_key:
        session_key = str(session_key).strip()
        if session_key.startswith("/sessions"):
            session_key = session_key.replace("/sessions", "").strip()

    if not session_key or session_key.lower() in ["latest", "nil", "unknown", "live_leaderboard"]:
        session_key = "latest"

    if session_key == "latest":
        now_utc = _dt.datetime.now(_dt.timezone.utc)
        now_str = now_utc.strftime('%Y-%m-%dT%H:%M:%S')
        today_str = now_utc.strftime('%Y-%m-%d')

        logger.info(f"Resolving 'latest': looking for sessions started today ({today_str})")

        # Fetch sessions that start today or earlier in the current window
        sessions = await client.get_sessions_async(date_start=f">={today_str}T00:00:00")

        # Filter to sessions that have ALREADY started (exclude future sessions)
        started = [s for s in sessions if s.get('date_start', '') <= now_str]

        if not started:
            raise Exception(
                f"No active F1 session right now (today: {TODAY}). "
                "Live tools only work during a race weekend. "
                "For historical data use f1_session_results instead."
            )

        # Return the most recently started session
        started.sort(key=lambda x: x.get('date_start', ''))
        return started[-1]
    
    # Ensure session_key is numeric
    if not str(session_key).isdigit():
        logger.warning(f"Invalid session_key format: {session_key}. Falling back to 'latest'.")
        return await verify_live_session(client, "latest")
    
    # If a valid numeric key was provided, fetch its details
    sessions = await client.get_sessions_async(session_key=session_key)
    if not sessions:
        raise Exception(f"Session {session_key} not found.")
    return sessions[0]


@tool
async def f1_live_weather(session_key: str = "latest") -> str:
    """
    Returns REAL-TIME current weather conditions at the track.
    Use ONLY for live sessions or when user asks about: "current" weather, "now", "live" temperature, "right now".
    Shows current air temp, humidity, pressure, rainfall, track temp, and wind.
    """
    try:
        client = get_enhanced_client()
        session = await verify_live_session(client, session_key)
        session_key = session['session_key']
        
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
    Generates a REAL-TIME satellite view map of current driver positions on track.
    Use ONLY for live sessions or when user asks about: "where are they now", "live" track positions, "current" visual map.
    Creates and saves a PNG file showing all car locations right now.
    """
    try:
        client = get_enhanced_client()
        session = await verify_live_session(client, session_key)
        session_key = session['session_key']
        
        # CRITICAL FIX for 422, Timeout & 429 Error: 
        # Fetching all at once is slow; parallel is fast but triggers 429s.
        # We'll fetch in parallel but with strict concurrency limits and delays.
        from datetime import datetime, timedelta
        import asyncio
        
        # Parse session end time
        date_end_str = session.get('date_end', '').replace('Z', '+00:00')
        if not date_end_str:
            return "Cannot determine session time for positions."
            
        session_end = datetime.fromisoformat(date_end_str)
        reference_time = min(datetime.now(session_end.tzinfo), session_end)
        # Use a very small window (1 second) to minimize data volume
        filter_start = (reference_time - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%S')
        
        # Get list of drivers in this session
        drivers_data = await client.get_drivers_async(session_key=session_key)
        driver_numbers = [d['driver_number'] for d in drivers_data]
        
        if not driver_numbers:
            return "No drivers found for this session."
            
        logger.info(f"Fetching parallel location data for {len(driver_numbers)} drivers with rate-limiting...")
        
        # Helper with rate-limiting
        sem = asyncio.Semaphore(3) # Only 3 concurrent requests
        
        async def fetch_driver(dn):
            async with sem:
                # Add a tiny jitter/delay to avoid hitting rate limits simultaneously
                await asyncio.sleep(0.1 * (dn % 5)) 
                try:
                    return await client.get_location_async(session_key, driver_number=dn, date=f">{filter_start}")
                except Exception as e:
                    logger.warning(f"Failed for driver {dn}: {e}")
                    return []
        
        tasks = [fetch_driver(dn) for dn in driver_numbers]
        results = await asyncio.gather(*tasks)
        
        # Flatten results and create DataFrame
        all_location_data = []
        for res in results:
            if res:
                all_location_data.extend(res)
                
        df = pd.DataFrame(all_location_data)
        
        if df.empty:
            return "No location data found for this session."

        current_positions = df.sort_values('date').groupby('driver_number').tail(1)

        # Get driver metadata for colors and acronyms
        drivers_info = {d['driver_number']: d for d in drivers_data}
        
        # --- TRACK OUTLINE FIX ---
        # Fetch a larger window for ONE driver to draw the track layout
        ref_driver = driver_numbers[0]
        track_start = (reference_time - timedelta(minutes=2)).strftime('%Y-%m-%dT%H:%M:%S')
        logger.info(f"Fetching track outline using driver {ref_driver} after {track_start}")
        track_data = await client.get_location_async(session_key, driver_number=ref_driver, date=f">{track_start}")
        track_df = pd.DataFrame(track_data)
        
        # --- PLOTTING ---
        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
        plt.figure(figsize=(14, 10))
        plt.style.use('dark_background')
        
        # Plot track outline (high-fidelity from ref driver)
        if not track_df.empty:
            plt.plot(
                track_df['x'],
                track_df['y'],
                color='white',
                alpha=0.2,
                linewidth=5,
                zorder=1
            )
            plt.plot(
                track_df['x'],
                track_df['y'],
                color='gray',
                alpha=0.5,
                linewidth=1,
                zorder=2,
                label='Track Layout'
            )
        
        # Plot current car positions with team colors
        for _, row in current_positions.iterrows():
            dn = row['driver_number']
            info = drivers_info.get(dn, {})
            team_color = f"#{info.get('team_colour', 'FF0000')}"
            acronym = info.get('name_acronym', str(dn))
            
            # Marker
            plt.scatter(
                row['x'], 
                row['y'], 
                s=250, 
                c=team_color, 
                edgecolors='white', 
                linewidths=1.5,
                zorder=5
            )
            
            # Label (Acronym)
            plt.annotate(
                acronym,
                (row['x'], row['y']),
                color='white',
                fontsize=9,
                fontweight='bold',
                ha='center',
                va='center',
                zorder=6,
                bbox=dict(boxstyle='round,pad=0.2', fc=team_color, ec='none', alpha=0.7)
            )
        
        plt.title(f'Live Track Positions - {session.get("session_name")} {session.get("year")}', fontsize=16)
        plt.axis('off') # Remove axes for cleaner "satellite" look
        plt.tight_layout()
        
        filename = f"{PLOTS_DIR}/live_positions_{session_key}.png"
        plt.savefig(filename, dpi=200, bbox_inches='tight', facecolor='black')
        plt.close()
        
        return filename
        
    except Exception as e:
        logger.error(f"Position map failed: {e}")
        return f"Position map error: {e}"


@tool
async def f1_live_intervals(session_key: str = "latest") -> str:
    """
    REAL-TIME timing gaps and leaderboard between drivers during a session.
    Use ONLY for live sessions or when user asks about: "live" leaderboard, "current" race positions, "live" gaps, gaps "now".
    Shows P1-P20 with time gaps to leader.
    """
    session = None
    try:
        client = get_enhanced_client()
        session = await verify_live_session(client, session_key)
        active_key = session['session_key']

        intervals = await client.get_intervals_async(active_key)
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
        # User-friendly explanation for common live-data issues
        err_msg = str(e)
        if "404" in err_msg and session is not None:
            from tools.analysis_tools import f1_session_results
            session_name = session.get('session_name', 'current session')

            # Check if session is actually finished (end time in past)
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            end_str = session.get('date_end')
            is_finished = False
            if end_str:
                try:
                    end_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    if now > end_dt:
                        is_finished = True
                except:
                    pass

            if is_finished:
                logger.info(f"Session {session_name} is finished. Falling back to f1_session_results.")
                results = await f1_session_results.ainvoke({
                    "grand_prix": session.get('location', 'latest'),
                    "year": session.get('year', DATA_DEFAULT_YEAR),
                    "session": session_name
                })
                return f"NOTE: The {session_name} has concluded, so live intervals are no longer active. Here are the final results instead:\n\n{results}"

            return (
                f"Live timing data is not yet available for the {session_name}. "
                f"This happens if the session hasn't started or the live feed is delayed.\n\n"
                f"TIP: Use f1_session_results(grand_prix='{session.get('location', 'latest')}', "
                f"year={session.get('year', DATA_DEFAULT_YEAR)}, session='{session_name}') for final results."
            )

        logger.error(f"Intervals fetch failed: {e}")
        return f"Interval data unavailable: {e}"


@tool
async def f1_live_leaderboard(session_key: str = "latest") -> str:
    """
    Returns THE MOST COMPLETE current race leaderboard (POS, NO, GAP, INT).
    Use for: "current standings", "live leaderboard", "who is winning", "current positions".
    """
    try:
        client = get_enhanced_client()
        session = await verify_live_session(client, session_key)
        s_key = session['session_key']
        
        # Parallel fetch for intervals and drivers
        intervals_task = client.get_intervals_async(s_key)
        drivers_task = client.get_drivers_async(session_key=s_key)
        
        intervals, drivers = await asyncio.gather(intervals_task, drivers_task)
        
        if not intervals:
            # Detect whether the session has ended and fall back to results
            import datetime as _dt
            now = _dt.datetime.now(_dt.timezone.utc)
            end_str = session.get('date_end', '')
            if end_str:
                try:
                    end_dt = _dt.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    if now > end_dt:
                        from tools.analysis_tools import f1_session_results
                        results = await f1_session_results.ainvoke({
                            "grand_prix": session.get('location', 'latest'),
                            "year": session.get('year', DATA_DEFAULT_YEAR),
                            "session": session.get('session_name', 'Race'),
                        })
                        return (
                            f"ℹ️ The {session.get('session_name')} has concluded — "
                            f"live intervals are no longer active. Final results:\n\n{results}"
                        )
                except Exception:
                    pass
            return (
                "No live timing data yet. The session may not have started, "
                "or the feed is under a red flag / safety car delay."
            )

        # Build driver map
        d_map = {d['driver_number']: d for d in drivers}

        # Get latest per driver; sort by position numerically
        df = pd.DataFrame(intervals)
        latest = df.sort_values('date').groupby('driver_number').tail(1).copy()
        latest['_pos_num'] = pd.to_numeric(latest['position'], errors='coerce').fillna(99)
        latest = latest.sort_values('_pos_num')

        res = f"### 🏁 Live Leaderboard: {session.get('session_name')}\n\n"
        res += "| Pos | # | Driver | Gap | Int | Team |\n"
        res += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"

        for _, row in latest.iterrows():
            dn = row['driver_number']
            info = d_map.get(dn, {})
            name = info.get('name_acronym', f"#{dn}")
            team = info.get('team_name', 'N/A')
            pos = row.get('position', '?')
            raw_gap = row.get('gap_to_leader')
            raw_int = row.get('interval')

            # P1 gets "LEADER" label; others get "+Xs"
            try:
                gap_str = "LEADER" if not raw_gap or float(raw_gap) == 0 else f"+{raw_gap}s"
                int_str = "—" if not raw_int or float(raw_int) == 0 else f"+{raw_int}s"
            except (ValueError, TypeError):
                gap_str = f"+{raw_gap}s" if raw_gap else "LEADER"
                int_str = f"+{raw_int}s" if raw_int else "—"

            res += f"| {pos} | {dn} | **{name}** | {gap_str} | {int_str} | {team} |\n"

        return res
    except Exception as e:
        err = str(e)
        if "404" in err:
            # Session exists but interval feed is dead → check if finished and fall back
            try:
                import datetime as _dt
                session_obj = await verify_live_session(get_enhanced_client(), "latest")
                end_str = session_obj.get("date_end", "")
                now = _dt.datetime.now(_dt.timezone.utc)
                end_dt = _dt.datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if now > end_dt:
                    from tools.analysis_tools import f1_session_results
                    results = await f1_session_results.ainvoke({
                        "grand_prix": session_obj.get("location", "latest"),
                        "year": session_obj.get("year", DATA_DEFAULT_YEAR),
                        "session": session_obj.get("session_name", "Race"),
                    })
                    return (
                        f"ℹ️ No live session active — showing last completed session results:\n\n{results}"
                    )
            except Exception:
                pass
            return (
                "No live timing data available right now. "
                "There is no active F1 session — use f1_session_results for historical data."
            )
        return f"Live leaderboard unavailable: {e}"


def get_live_tools() -> list:
    """
    Get all live data tools.
    
    Returns:
        List of live tool functions
    """
    return [
        f1_live_weather,
        f1_live_position_map,
        f1_live_intervals,
        f1_live_leaderboard
    ]

import fastf1
import fastf1.plotting
import pandas as pd
import numpy as np
import os
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime
from datetime import timedelta

logger = logging.getLogger("F1_Data_Miner")

# Resolve absolute path for cache to ensure consistency across execution contexts
CACHE_DIR = os.path.abspath('cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
if not os.path.exists('plots'):
    os.makedirs('plots')

fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl()

def validate_year(year: int) -> bool:
    """Validate year is within FastF1 data range dynamically."""
    if year < 2018:
        return False
    try:
        schedule = fastf1.get_event_schedule(year)
        return not schedule.empty
    except fastf1.api.CacheMissError:
        return False
    except Exception:
        return False

def resolve_driver_name(driver_input: str, session) -> str:
    """
    Resolves a driver name to the 3-letter abbreviation using fastf1 native fuzzy matcher.
    Supports full name, last name, abbreviation, or driver number.
    Returns None if no match is found.
    """
    try:
        return fastf1.plotting.get_driver_abbreviation(str(driver_input), session=session)
    except KeyError:
        return None

def validate_driver(driver: str, session) -> bool:
    return resolve_driver_name(driver, session) is not None

def get_schedule(year: int):
    """Returns the full race calendar for a specific year, including remaining races."""
    if not validate_year(year):
        return f"Year {year} is out of range. FastF1 data available for 2018-2026."
    
    try:
        schedule = fastf1.get_event_schedule(year)
        races = schedule[schedule['EventFormat'] != 'testing']
        
        output = f"--- {year} F1 Schedule ---\n"
        for _, row in races.iterrows():
            round_num = row['RoundNumber']
            date = row['EventDate'].strftime('%Y-%m-%d')
            output += f"Round {round_num}: {row['EventName']} ({row['Location']}) - {date}\n"
            
        import datetime
        if year == datetime.datetime.now().year:
            try:
                remaining = fastf1.get_events_remaining()
                if not remaining.empty:
                    output += f"\n--- Remaining Events ---\n"
                    for _, row in remaining.iterrows():
                         output += f"Next: {row['EventName']} starts {row['Session1Date'].strftime('%Y-%m-%d')}\n"
            except Exception as e:
                pass
                
        return output
    except Exception as e:
        logger.error(f"Schedule fetch error: {e}")
        return f"Error fetching schedule: {e}"

def load_session(year, grand_prix, session_type):
    """Load FastF1 session with robust error handling."""
    if not validate_year(year):
        logger.warning(f"Invalid year: {year}")
        return None
    
    st_map = {
        'race': 'R', 'r': 'R', 
        'qualifying': 'Q', 'q': 'Q', 
        'fp1': 'FP1', 'fp2': 'FP2', 'fp3': 'FP3', 
        'sprint': 'S', 's': 'S',
        'sprint qualifying': 'SQ', 'sq': 'SQ'
    }
    st = st_map.get(str(session_type).lower(), 'R')
    
    try:
        # Check connectivity before attempting load
        import socket
        # Cleaning logic for LLM hallucinations like "/sessions latest" or "GP: Melbourne"
        def clean_arg(arg: str) -> str:
            if not arg: return arg
            arg = str(arg).strip()
            # Remove common prefixes from small LLMs
            for prefix in ['/sessions', 'GP:', 'Session:', 'Event:']:
                if arg.startswith(prefix):
                    arg = arg[len(prefix):].strip()
            return arg

        grand_prix = clean_arg(grand_prix)
        session_type = clean_arg(session_type)
        
        gp_clean = grand_prix.lower()
        st = session_type
        
        # Comprehensive mapping for all session types
        def map_session(s: str) -> str:
            s = str(s).upper()
            if 'QUALIFYING' in s or s == 'Q': return 'Q'
            if 'RACE' in s or s == 'R': return 'R'
            if 'SPRINT' in s and 'QUALIFYING' in s: return 'SQ'
            if 'SPRINT' in s and 'SHOOTOUT' in s: return 'SQ'
            if 'SPRINT' in s: return 'S'
            if 'FP1' in s or ('FREE' in s and 'PRACTICE' in s and '1' in s): return 'FP1'
            if 'FP2' in s or ('FREE' in s and 'PRACTICE' in s and '2' in s): return 'FP2'
            if 'FP3' in s or ('FREE' in s and 'PRACTICE' in s and '3' in s): return 'FP3'
            if 'P1' in s: return 'FP1'
            if 'P2' in s: return 'FP2'
            if 'P3' in s: return 'FP3'
            return s # Fallback to original

        st = map_session(st)
        
        logger.info(f"load_session called for {year} '{grand_prix}' ({session_type})")
        
        # Test for internet
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
        except OSError:
            logger.error("OFFLINE MODE DETECTED: Cannot fetch new race data.")
            # Only proceed if we think we might have cache, otherwise warn user
            
        is_testing = "test" in gp_clean or "pre-season" in gp_clean
        if is_testing:
            # FastF1 uses get_testing_session since v3.0 for testing sessions
            test_day = 1
            if '2' in session_type or st in ['FP2', 'FP3', 'S']: test_day = 2
            if '3' in session_type or st in ['SQ']: test_day = 3
            
            session = fastf1.get_testing_session(year, 1, test_day)
        else:
            # Resolve "today" or "latest" to actual event name
            if gp_clean in ['today', 'latest', 'current']:
                try:
                    from config.settings import TODAY
                    from core.api_client import get_client
                    client = get_client()
                    
                    # Try OpenF1 first for "today" (most accurate for live events)
                    logger.info(f"Querying OpenF1 for today's sessions ({TODAY})...")
                    today_sessions = client.get_sessions_by_date(TODAY)
                    
                    if today_sessions:
                        # Pick the latest session of the day
                        latest_today = today_sessions[-1]
                        location = latest_today.get('location', '')
                        # Map common locations to full GP names if needed
                        if 'Melbourne' in location or 'Albert Park' in location:
                            grand_prix = "Australian Grand Prix"
                        else:
                            grand_prix = f"{location} Grand Prix"
                        
                        logger.info(f"OpenF1 resolved '{grand_prix}' from location '{location}'")
                    else:
                        # Fallback to schedule logic
                        now = datetime.datetime.fromisoformat(TODAY)
                        schedule = fastf1.get_event_schedule(year)
                        # Find the closest event (within 4 days)
                        diffs = (schedule['EventDate'] - now).abs()
                        closest_idx = diffs.idxmin()
                        grand_prix = schedule.loc[closest_idx, 'EventName']
                        logger.info(f"Schedule resolved '{grand_prix}' as closest to {TODAY}")
                except Exception as e:
                    logger.warning(f"Resolution failed: {e}. Using raw '{grand_prix}'")

            session = fastf1.get_session(year, grand_prix, st)
            
        try:
            # For results, we don't ALWAYS need telemetry.
            # But we keep it True by default here for other tools. 
            # We'll override in get_session_results.
            session.load(telemetry=True, weather=True, messages=True)
            logger.info(f"Loaded session: {year} {grand_prix} {st}")
        except Exception as e:
            logger.warning(f"Full load failed for {grand_prix}: {e}. Trying minimal load...")
            try:
                session.load(telemetry=False, weather=False, messages=False)
                logger.info(f"Minimal load successful for {grand_prix} {st}")
            except Exception as e2:
                logger.error(f"Minimal load also failed for {grand_prix} {st}: {e2}")
                # Don't return None yet, the tools might still access partial data or we handle it there
        return session

    except Exception as e:
        error_str = str(e)
        if "NameResolutionError" in error_str or "ConnectionError" in error_str:
            logger.error(f"NETWORK ERROR: Could not download data for {grand_prix} {year}. Check your internet connection.")
        else:
            logger.error(f"Session load error: {e}")
        return None

def get_session_results(year: int, grand_prix: str, session: str):
    """Full classification table for a session."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: 
        return "Session not found or failed to load."
    
    try:
        # Ensure numerical sorting for positions
        import pandas as pd
        
        # Safely access results/laps properties to avoid SessionNotLoadedError crash
        res = pd.DataFrame()
        laps = pd.DataFrame()
        
        try:
            res = session_obj.results.copy()
        except Exception as e:
            logger.info(f"Results table unavailable: {e}")
            
        try:
            laps = session_obj.laps.copy()
        except Exception as e:
            logger.info(f"Lap data unavailable: {e}")
        
        is_provisional = False
        # Fallback to laps if results table is empty or for Practice/Qualifying
        st_clean = str(session).upper()
        is_practice = 'P' in st_clean or 'FP' in st_clean or 'PRACTICE' in st_clean
        is_qualifying = 'Q' in st_clean or 'QUALIFYING' in st_clean or 'SQ' in st_clean
        
        if (res.empty or is_practice or is_qualifying) and not laps.empty:
            logger.info(f"Using lap data to calculate standings for {session}")
            is_provisional = True
            provisional = []
            
            # Sort drivers by their BEST lap time for Practice/Qualifying
            # For Race, we use the last lap position (already implemented)
            drivers_stats = []
            # Get all drivers registered for the session to ensure DNS/DNF are included
            session_drivers = []
            try:
                session_drivers = session_obj.drivers
            except:
                session_drivers = laps['Driver'].unique() if not laps.empty else []

            for driver in session_drivers:
                # Use DriverNumber for consistent comparison (both should be strings)
                d_laps = laps[laps['DriverNumber'] == str(driver)].copy() if not laps.empty else pd.DataFrame()
                
                if is_practice or is_qualifying:
                    # Best lap time
                    best_lap = d_laps['LapTime'].min() if not d_laps.empty else None
                    drivers_stats.append((driver, best_lap))
                else:
                    # Last position in race
                    last_pos = d_laps.iloc[-1].get('Position', 99) if not d_laps.empty else 999
                    drivers_stats.append((driver, last_pos))
            
            # Sort: for times, smaller is better (asc); for pos, smaller is better (asc)
            def sort_key(x):
                val = x[1]
                if pd.isna(val) or val is None:
                    return pd.Timedelta(hours=24) if is_practice or is_qualifying else 999
                return val
            
            drivers_stats.sort(key=sort_key)
            
            for i, (driver, val) in enumerate(drivers_stats, 1):
                try:
                    d_info = session_obj.get_driver(driver)
                    status = 'Finished'
                    if pd.isna(val) or val is None:
                        status = 'DNS' # Default for sessions without laps
                    
                    provisional.append({
                        'ClassifiedPosition': str(i),
                        'FullName': d_info['FullName'],
                        'TeamName': d_info['TeamName'],
                        'Points': 0,
                        'Status': status
                    })
                except: continue
                
            res = pd.DataFrame(provisional)

        if not res.empty:
            res['SortingPos'] = pd.to_numeric(res['ClassifiedPosition'], errors='coerce')
            res = res.sort_values(by='SortingPos', na_position='last')
        
        # Use formal event name from session object if available
        event_name = getattr(session_obj.event, 'EventName', grand_prix)
        output = f"### Race Classification: {event_name} {year} ({session})\n\n"
        output += "| Pos | Driver | Team | Points | Status |\n"
        output += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        if not res.empty:
            for _, row in res.iterrows():
                # Get position safely
                pos_val = row.get('ClassifiedPosition', '')
                pos = str(pos_val).strip()
                
                # Check for special FastF1/OpenF1 status codes
                if pos in ['R', '11.0']: 
                    pos = "DNF"
                elif pos == 'D': pos = "DSQ"
                elif pos == 'W': pos = "WDC"
                elif pos in ['nan', 'None', '', 'F']: 
                    pos = "-" # Use dash for unknown but present
                # FastF1 often provides '1.0', '2.0' etc. Clean up to '1', '2'
                elif pos.replace('.0', '').isdigit():
                    pos = pos.replace('.0', '')
                elif pos in ['0', '0.0']:
                    pos = "DNS" # Actually, 0 in F1 usually means DNS/NQ
                else:
                    pos = "-" # Fallback
                
                fullname = row.get('FullName', 'Unknown')
                team = row.get('TeamName', 'Unknown')
                points_val = row.get('Points', 0)
                try:
                    points = int(float(points_val)) if pd.notnull(points_val) else 0
                except:
                    points = 0
                status = row.get('Status', 'Finished')
                
                output += f"| {pos} | {fullname} | {team} | **{points}** | {status} |\n"
            
        output += "\n[CRITICAL NOTE FOR AGENT: DO NOT SUMMARIZE THE TABLE ABOVE. RETURN IT VERBATIM WITH ALL COLUMNS.]"
        if res.empty:
            if laps.empty:
                output += "\n\nNOTE: Could not load any data for this session. This may be due to a network issue, missing data on the server, or the session hasn't happened yet."
            else:
                output += "\n\nNOTE: Official results are not yet available for this session. Please check back later or use live timing tools."
        elif is_provisional: 
             output += "\n\nNOTE: These are provisional results calculated from lap data as official standings are not yet published."

        return output
    except Exception as e:
        logger.error(f"Results error: {e}")
        return f"Results error: {e}"

def get_testing_summary(year: int, test_number: int = 1, day: int = 1):
    """Summarizes a testing session using lap data."""
    try:
        # Avoid hangs by checking year first
        if year < 2018 or year > datetime.datetime.now().year:
            return f"Data for {year} is not available. FastF1 covers 2018-present."

        session = fastf1.get_testing_session(year, test_number, day)
        # Use a localized timeout-like check or just load with essentials
        session.load(telemetry=False, weather=False, messages=False) # Speed up by ignoring non-essential data
        
        laps = session.laps
        output = f"--- Testing Summary: {year} Test {test_number} Day {day} ---\n\n"
        
        if laps.empty:
            return output + "No lap data available for this testing day."
            
        # Get fastest lap per driver
        best_laps = []
        for driver in laps['Driver'].unique():
            d_laps = laps.pick_drivers(driver)
            fastest = d_laps.pick_fastest()
            
            # Fallback if no "accurate" laps found (common in testing)
            if fastest.empty and not d_laps.empty:
                fastest = d_laps.sort_values(by='LapTime').iloc[0]
                
            if not fastest.empty:
                best_laps.append({
                    'Driver': driver,
                    'Team': fastest['Team'],
                    'BestLap': fastest['LapTime'],
                    'Laps': len(d_laps)
                })
        
        if not best_laps:
            return output + "No valid laps found."
            
        df = pd.DataFrame(best_laps).sort_values(by='BestLap')
        for i, row in enumerate(df.head(15).itertuples(), 1):
            lap_time = str(row.BestLap).split('days')[-1].strip()
            output += f"{i}. {row.Driver} ({row.Team}) | Best: {lap_time} | Laps: {row.Laps}\n"
            
        return output
    except Exception as e:
        logger.error(f"Testing summary error: {e}")
        return f"Error: {e}"

def get_tyre_summary(year: int, grand_prix: str, session: str):
    """Detailed tyre life and compound breakdown."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session not found."
    
    try:
        laps = session_obj.laps
        output = f"--- Tyre Analysis: {grand_prix} {year} ({session}) ---\n\n"
        
        for driver in laps['Driver'].unique():
            d_laps = laps.pick_drivers(driver)
            current_tyre = d_laps.iloc[-1]
            output += f"{driver}: {current_tyre['Compound']} (Age: {int(current_tyre['TyreLife'])} laps)\n"
            
            # Stint history
            stints = d_laps[['Stint', 'Compound', 'TyreLife']].groupby('Stint').max()
            for s_num, row in stints.iterrows():
                output += f"  - Stint {int(s_num)}: {row['Compound']} ({int(row['TyreLife'])} laps)\n"
            output += "\n"
            
        return output
    except Exception as e:
        return f"Tyre analysis error: {e}"

def get_sector_analysis(year: int, grand_prix: str, session: str, driver1: str, driver2: str = None):
    """Sector-by-sector performance comparison."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session not found."
    
    try:
        d1_abbr = resolve_driver_name(driver1, session_obj)
        l1 = session_obj.laps.pick_drivers(d1_abbr).pick_fastest()
        
        output = f"--- Sector Analysis: {grand_prix} {year} ({session}) ---\n\n"
        
        def fmt_sector(t):
            if pd.isnull(t): return "N/A"
            # Format as SS.mmm
            total_seconds = t.total_seconds()
            return f"{total_seconds:.3f}s"
        
        def fmt_lap(t):
            if pd.isnull(t): return "N/A"
            # Format as M:SS.mmm
            total_seconds = t.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:06.3f}"
        
        output += f"{d1_abbr} Best Lap: {fmt_lap(l1['LapTime'])}\n"
        output += f"S1: {fmt_sector(l1['Sector1Time'])} | S2: {fmt_sector(l1['Sector2Time'])} | S3: {fmt_sector(l1['Sector3Time'])}\n\n"
        
        if driver2:
            d2_abbr = resolve_driver_name(driver2, session_obj)
            l2 = session_obj.laps.pick_drivers(d2_abbr).pick_fastest()
            output += f"{d2_abbr} Best Lap: {fmt_lap(l2['LapTime'])}\n"
            output += f"S1: {fmt_sector(l2['Sector1Time'])} | S2: {fmt_sector(l2['Sector2Time'])} | S3: {fmt_sector(l2['Sector3Time'])}\n"
            
            # Deltas
            s1_d = l1['Sector1Time'] - l2['Sector1Time']
            s2_d = l1['Sector2Time'] - l2['Sector2Time']
            s3_d = l1['Sector3Time'] - l2['Sector3Time']
            
            output += f"\nDelta ({d1_abbr} vs {d2_abbr}):\n"
            output += f"S1: {s1_d.total_seconds():+.3f}s | S2: {s2_d.total_seconds():+.3f}s | S3: {s3_d.total_seconds():+.3f}s\n"
            
        return output
    except Exception as e:
        return f"Sector analysis error: {e}"

def get_weather_analysis(year: int, grand_prix: str, session: str):
    """Provides session-long weather trends."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session not found."
    
    try:
        weather = session_obj.weather_data
        if weather.empty: return "No weather data available for this session."
        
        output = f"--- Weather Analysis: {grand_prix} {year} ({session}) ---\n"
        output += f"Air Temp: Min {weather['AirTemp'].min():.1f}°C, Max {weather['AirTemp'].max():.1f}°C\n"
        output += f"Track Temp: Min {weather['TrackTemp'].min():.1f}°C, Max {weather['TrackTemp'].max():.1f}°C\n"
        output += f"Humidity: {weather['Humidity'].mean():.1f}%\n"
        output += f"Rainfall: {'Yes' if weather['Rainfall'].any() else 'No'}\n"
        
        # Trend
        if len(weather) > 1:
            temp_change = weather['TrackTemp'].iloc[-1] - weather['TrackTemp'].iloc[0]
            trend = "Increasing" if temp_change > 1 else "Decreasing" if temp_change < -1 else "Stable"
            output += f"Track Temp Trend: {trend} ({temp_change:+.1f}°C)\n"
            
        return output
    except Exception as e:
        return f"Weather analysis error: {e}"

def get_race_control_messages(year: int, grand_prix: str, session: str):
    """Lists all race control messages (flags, SC, etc.)."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session not found."
    
    try:
        messages = session_obj.race_control_messages
        if messages.empty: return "No race control messages recorded."
        
        output = f"--- Race Control: {grand_prix} {year} ({session}) ---\n\n"
        # Filter for interesting ones
        important_keywords = ['SAFETY CAR', 'VIRTUAL', 'YELLOW', 'RED FLAG', 'INVESTIGATION', 'PENALTY', 'DRS']
        
        for _, msg in messages.iterrows():
            text = msg['Message']
            category = msg['Category']
            # Highlight important messages
            prefix = "🚨 " if any(kw in text.upper() for kw in important_keywords) else "ℹ️ "
            output += f"{prefix} [{category}] {text}\n"
            
        return output
    except Exception as e:
        return f"Race control error: {e}"

def get_circuit_data(year: int, grand_prix: str, session: str):
    """Corner analysis and circuit information."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: 
        return "Session not found or failed to load."
    
    try:
        info = session_obj.get_circuit_info()
        if not info: 
            return "Circuit info unavailable for this session."
        
        output = f"--- Circuit Data: {grand_prix} ---\n"
        output += f"Marshall Sectors: {len(info.marshal_lights)}\n"
        output += "Corners (Angle/Distance):\n"
        corners = info.corners
        selected = pd.concat([corners.head(5), corners.tail(5)])
        
        for _, row in selected.iterrows():
            output += f"T{row['Number']}: {row['Angle']:.1f}° at {row['Distance']:.0f}m\n"
        return output
    except Exception as e:
        logger.error(f"Circuit error: {e}")
        return f"Circuit error: {e}"

def plot_driver_comparison(driver1: str, driver2: str, year: int, grand_prix: str, session: str):
    """Generates Speed + Time Delta comparison plot."""
    if not validate_year(year):
        return f"Year {year} is out of range."
    
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: 
        return "Session not found or failed to load."
    
    try:
        d1_abbr = resolve_driver_name(driver1, session_obj)
        d2_abbr = resolve_driver_name(driver2, session_obj)
        
        if not d1_abbr or not d2_abbr:
            return "Driver(s) not found."
        
        l1 = session_obj.laps.pick_drivers(d1_abbr).pick_fastest()
        l2 = session_obj.laps.pick_drivers(d2_abbr).pick_fastest()
        
        if l1.empty or l2.empty:
            return "Could not find valid laps for comparison."
        
        d1_name = session_obj.get_driver(d1_abbr)['FullName']
        d2_name = session_obj.get_driver(d2_abbr)['FullName']

        car1 = l1.get_car_data().add_distance()
        car2 = l2.get_car_data().add_distance()

        common_dist = np.linspace(0, min(car1['Distance'].max(), car2['Distance'].max()), 1000)
        
        speed1_interp = np.interp(common_dist, car1['Distance'], car1['Speed'])
        speed2_interp = np.interp(common_dist, car2['Distance'], car2['Speed'])
        
        dist_step = common_dist[1] - common_dist[0]
        speed_diff = speed1_interp - speed2_interp
        time_delta = np.cumsum(speed_diff * dist_step / ((speed1_interp + speed2_interp) / 2 + 1e-6)) / 3.6
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        color1 = fastf1.plotting.get_team_color(l1['Team'], session_obj)
        color2 = fastf1.plotting.get_team_color(l2['Team'], session_obj)

        ax1.plot(car1['Distance'], car1['Speed'], color=color1, label=d1_name, linewidth=2)
        ax1.plot(car2['Distance'], car2['Speed'], color=color2, label=d2_name, linewidth=2)
        ax1.set_ylabel('Speed (km/h)')
        ax1.set_title(f"{d1_name} vs {d2_name} - {grand_prix} {year}")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(common_dist, time_delta, color='purple', linewidth=2)
        ax2.axhline(y=0, color='white', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Distance (m)')
        ax2.set_ylabel('Delta Time (s)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filename = f"plots/{year}_{grand_prix}_{driver1}_vs_{driver2}_delta.png".replace(" ", "_")
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Delta plot saved: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Plotting failed: {e}")
        return f"Plotting failed: {e}"

def analyze_telemetry(driver: str, year: int, grand_prix: str, session: str):
    """Detailed telemetry breakdown."""
    if not validate_year(year): return f"Year {year} is out of range."
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session load failed."
    
    try:
        d_abbr = resolve_driver_name(driver, session_obj)
        if not d_abbr: return f"Driver {driver} not found."
        
        laps = session_obj.laps.pick_drivers(d_abbr)
        fastest = laps.pick_fastest()
        car = fastest.get_car_data()
        
        gear_counts = car['nGear'].value_counts(normalize=True).sort_index()
        top_gear = gear_counts.idxmax()
        
        return (
            f"--- Analysis: {driver} ---\n"
            f"Fastest Lap: {str(fastest['LapTime']).split('days')[-1]}\n"
            f"Max Speed: {car['Speed'].max():.1f} km/h\n"
            f"Most Used Gear: {top_gear} ({gear_counts[top_gear]*100:.1f}%)\n"
            f"Brake Usage: {car['Brake'].astype(int).mean()*100:.1f}%"
        )
    except Exception as e:
        return f"Analysis error: {e}"

def get_tire_strategy_gantt(year: int, grand_prix: str, session: str = "Race"):
    """Visual Gantt Chart for Tire Strategy."""
    if not validate_year(year):
        return f"Year {year} is out of range."
    
    session_obj = load_session(year, grand_prix, session)
    if not session_obj:
        return "Session not found or failed to load."
    
    try:
        laps = session_obj.laps
        
        fig, ax = plt.subplots(figsize=(14, 10))
        fig.patch.set_facecolor('#1E1E1E')
        ax.set_facecolor('#1E1E1E')
        
        drivers = sorted(laps['Driver'].unique())
        y_pos = 0
        
        for driver in drivers:
            driver_laps = laps.pick_drivers(driver)
            driver_name = driver_laps['DriverNumber'].iloc[0]
            
            for stint_num, stint_laps in driver_laps.groupby('Stint'):
                if not stint_laps.empty:
                    compound = stint_laps['Compound'].iloc[0]
                    lap_start = stint_laps['LapNumber'].min()
                    lap_end = stint_laps['LapNumber'].max()
                    stint_length = lap_end - lap_start + 1
                    
                    try:
                        color = fastf1.plotting.get_compound_color(compound, session=session_obj)
                    except:
                        color = '#808080'
                    
                    ax.barh(y_pos, stint_length, left=lap_start-1, height=0.8, 
                           color=color, edgecolor='black', linewidth=1.5)
                    
                    if stint_length >= 3:
                        ax.text(lap_start + stint_length/2 - 0.5, y_pos, 
                               f"{compound[:3]}", ha='center', va='center', 
                               fontsize=8, fontweight='bold', color='black')
            
            ax.text(-2, y_pos, f"{driver} (#{driver_name})", 
                   ha='right', va='center', fontsize=10, color='white', fontweight='bold')
            y_pos += 1
        
        ax.set_xlabel('Lap Number', fontsize=12, color='white')
        ax.set_title(f'Tire Strategy - {grand_prix} {year}', fontsize=14, fontweight='bold', color='white')
        ax.grid(axis='x', alpha=0.3, color='gray')
        ax.tick_params(colors='white')
        ax.invert_yaxis()
        ax.set_yticks([])
        
        # Generate legend manually or using native dictionary
        try:
            compound_colors = fastf1.plotting.get_compound_mapping(session=session_obj)
            legend_elements = [plt.Rectangle((0,0),1,1, fc=color, ec='black', label=comp.title()) 
                              for comp, color in compound_colors.items()]
            ax.legend(handles=legend_elements, loc='upper right', facecolor='#2E2E2E', edgecolor='white', labelcolor='white')
        except:
            pass
        
        plt.tight_layout()
        filename = f"plots/{year}_{grand_prix}_tire_strategy_gantt.png".replace(" ", "_")
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#1E1E1E')
        plt.close()
        
        return filename
    except Exception as e:
        logger.error(f"Strategy Gantt error: {e}")
        return f"Strategy Gantt error: {e}"

def get_tire_strategy_analysis(year: int, grand_prix: str, session: str = "Race"):
    """Analyzes tire strategies (text format)."""
    if not validate_year(year): return f"Year {year} is out of range."
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: return "Session not found."
    
    try:
        laps = session_obj.laps
        output = f"--- Tire Strategy: {grand_prix} {year} ---\n\n"
        
        for driver in laps['Driver'].unique():
            driver_laps = laps.pick_drivers(driver)
            driver_name = driver_laps['DriverNumber'].iloc[0]
            output += f"{driver} (#{driver_name}):\n"
            
            for stint_num, stint_laps in driver_laps.groupby('Stint'):
                if not stint_laps.empty:
                    compound = stint_laps['Compound'].iloc[0]
                    lap_start = stint_laps['LapNumber'].min()
                    lap_end = stint_laps['LapNumber'].max()
                    output += f"  Stint {int(stint_num)}: {compound} (Laps {lap_start}-{lap_end})\n"
            output += "\n"
        return output
    except Exception as e:
        return f"Strategy analysis error: {e}"

def calculate_championship_standings(year: int, grand_prix: str):
    """Projects updated standings after a race."""
    if not validate_year(year): return f"Year {year} is out of range."
    
    try:
        schedule = fastf1.get_event_schedule(year)
        race_event = schedule[schedule['EventName'].str.contains(grand_prix, case=False, na=False)]
        
        if race_event.empty: return f"Could not find event {grand_prix}."
        race_round = race_event['RoundNumber'].iloc[0]
        
        driver_standings = {}
        constructor_standings = {}
        
        for round_num in range(1, race_round + 1):
            try:
                event = schedule[schedule['RoundNumber'] == round_num].iloc[0]
                race_session = fastf1.get_session(year, event['EventName'], 'R')
                race_session.load(telemetry=False, weather=False, messages=False)
                
                for _, row in race_session.results.iterrows():
                    driver = row['Abbreviation']
                    team = row['TeamName']
                    points = row.get('Points', 0)
                    
                    if driver not in driver_standings:
                        driver_standings[driver] = {'points': 0, 'team': team}
                    driver_standings[driver]['points'] += points
                    
                    if team not in constructor_standings:
                        constructor_standings[team] = 0
                    constructor_standings[team] += points
            except:
                continue
        
        output = f"--- Standings after {grand_prix} {year} ---\n\nDRIVERS:\n"
        sorted_drivers = sorted(driver_standings.items(), key=lambda x: x[1]['points'], reverse=True)
        for pos, (driver, data) in enumerate(sorted_drivers[:10], 1):
            output += f"{pos}. {driver} ({data['team']}) - {data['points']} pts\n"
            
        output += "\nCONSTRUCTORS:\n"
        sorted_constructors = sorted(constructor_standings.items(), key=lambda x: x[1], reverse=True)
        for pos, (team, points) in enumerate(sorted_constructors[:10], 1):
            output += f"{pos}. {team} - {points} pts\n"
            
        return output
    except Exception as e:
        return f"Championship calculation error: {e}"

def prepare_replay_data(year: int, grand_prix: str, session_type: str = "Race"):
    """
    Prepares data for replay UI.
    """
    session = load_session(year, grand_prix, session_type)
    if not session: return None

    try:
        drivers = session.drivers
        driver_info = {}
        
        car_data_cache = {}
        pos_data_cache = {}
        
        logger.info("Pre-loading telemetry for all drivers...")
        
        for d in drivers:
            try:
                drv = session.get_driver(d)
                team_color = fastf1.plotting.get_team_color(drv['TeamName'], session)
                
                if isinstance(team_color, str):
                    team_color = team_color.lstrip('#')
                    rgb = tuple(int(team_color[i:i+2], 16) for i in (0, 2, 4))
                else:
                    rgb = tuple(int(c * 255) for c in team_color[:3])
                
                driver_info[d] = {
                    "color": rgb,
                    "team": drv['TeamName'],
                    "name": drv['Abbreviation'],
                    "number": drv['DriverNumber'],
                    "status": "OK"
                }

                d_laps = session.laps.pick_drivers(d)
                if not d_laps.empty:
                    car_data_cache[d] = d_laps.get_car_data().add_distance()
                    pos_data_cache[d] = d_laps.get_pos_data()
                
            except Exception as e:
                logger.warning(f"Failed to load driver {d}: {e}")
                continue

        laps = session.laps
        fastest_lap = laps.pick_fastest()
        ref_tel = fastest_lap.get_telemetry().add_distance()
        
        track_layout = {
            "x": ref_tel['X'].to_list(),
            "y": ref_tel['Y'].to_list(),
            "min_x": ref_tel['X'].min(),
            "max_x": ref_tel['X'].max(),
            "min_y": ref_tel['Y'].min(),
            "max_y": ref_tel['Y'].max()
        }

        try:
            sec1_time = fastest_lap['Sector1Time']
            sec2_time = fastest_lap['Sector2Time']
            
            def get_pos_at_time(tel, time_delta):
                row = tel.iloc[(tel['Time'] - time_delta).abs().argsort()[:1]]
                return float(row['X'].values[0]), float(row['Y'].values[0])

            s1_x, s1_y = get_pos_at_time(ref_tel, sec1_time)
            s2_x, s2_y = get_pos_at_time(ref_tel, sec1_time + sec2_time)
            
            track_layout["sectors"] = [
                {"name": "S1", "x": s1_x, "y": s1_y},
                {"name": "S2", "x": s2_x, "y": s2_y}
            ]
        except:
            track_layout["sectors"] = []

        return {
            "session": session,
            "driver_info": driver_info,
            "track_layout": track_layout,
            "total_laps": session.total_laps,
            "car_data": car_data_cache,
            "pos_data": pos_data_cache
        }

    except Exception as e:
        logger.error(f"Data prep error: {e}")
        return None
import fastf1
import fastf1.plotting
import pandas as pd
import numpy as np
import os
import logging
import matplotlib.pyplot as plt
from datetime import timedelta
from typing import Optional
from collections import OrderedDict
from threading import RLock


_SESSION_CACHE = OrderedDict()
_SESSION_CACHE_LIMIT = 8
_SESSION_CACHE_LOCK = RLock()

logger = logging.getLogger("F1_Data_Miner")

if not os.path.exists('cache'):
    os.makedirs('cache')
if not os.path.exists('plots'):
    os.makedirs('plots')

fastf1.Cache.enable_cache('cache')
fastf1.plotting.setup_mpl()

def validate_year(year: int) -> bool:
    """Validate year is within FastF1 data range."""
    return 2018 <= year <= 2026

def resolve_driver_name(driver_input: str, session) -> str:
    """
    Resolves a driver name to the 3-letter abbreviation.
    Supports full name, last name, abbreviation, or driver number.
    """
    unique_drivers = session.laps['Driver'].unique()
    if driver_input in unique_drivers:
        return driver_input
        
    if str(driver_input) in session.drivers:
        try:
            d = session.get_driver(str(driver_input))
            return d['Abbreviation']
        except:
            pass

    driver_input_lower = str(driver_input).lower()
    
    for driver_id in session.drivers:
        try:
            d = session.get_driver(driver_id)
            full_name = d['FullName'].lower()
            last_name = d['LastName'].lower()
            abbrev = d['Abbreviation'].lower()
            
            if (driver_input_lower == full_name or 
                driver_input_lower == last_name or
                driver_input_lower == abbrev):
                return d['Abbreviation']
                
            if driver_input_lower in full_name:
                 return d['Abbreviation']
        except:
            continue
            
    return None

def validate_driver(driver: str, session) -> bool:
    return resolve_driver_name(driver, session) is not None

def get_schedule(year: int):
    """Returns the full race calendar for a specific year."""
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
        return output
    except Exception as e:
        logger.error(f"Schedule fetch error: {e}")
        return f"Error fetching schedule: {e}"

def load_session(year, grand_prix, session_type):
    """Load FastF1 session with robust error handling."""
    return _load_session_internal(year, grand_prix, session_type, telemetry=True, weather=True, messages=True)


def _normalize_session_type(session_type: str) -> str:
    """Normalize human-readable session names to FastF1 identifiers."""
    st_map = {
        'race': 'R', 'r': 'R',
        'qualifying': 'Q', 'q': 'Q',
        'fp1': 'FP1', 'fp2': 'FP2', 'fp3': 'FP3',
        'practice 1': 'FP1', 'practice 2': 'FP2', 'practice 3': 'FP3',
        'sprint': 'S', 's': 'S',
        'sprint qualifying': 'SQ', 'sq': 'SQ',
        'sprint shootout': 'SS', 'ss': 'SS'
    }
    return st_map.get(str(session_type).lower(), 'R')


def _cache_key(year: int, grand_prix: str, session_type: str, telemetry: bool, weather: bool, messages: bool):
    return (year, str(grand_prix).lower(), session_type, telemetry, weather, messages)


def _load_session_internal(year, grand_prix, session_type, telemetry=True, weather=True, messages=True):
    """Load and cache FastF1 session objects by payload profile."""
    if not validate_year(year):
        logger.warning(f"Invalid year: {year}")
        return None

    st = _normalize_session_type(session_type)
    cache_key = _cache_key(year, grand_prix, st, telemetry, weather, messages)
    with _SESSION_CACHE_LOCK:
        if cache_key in _SESSION_CACHE:
            _SESSION_CACHE.move_to_end(cache_key)
            return _SESSION_CACHE[cache_key]
    
    try:
        # Check connectivity before attempting load
        import socket
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
        except OSError:
            logger.error("OFFLINE MODE DETECTED: Cannot fetch new race data.")
            # Only proceed if we think we might have cache, otherwise warn user
            
        session = fastf1.get_session(year, grand_prix, st)
        session.load(telemetry=telemetry, weather=weather, messages=messages)
        logger.info(f"Loaded session: {year} {grand_prix} {st}")

        with _SESSION_CACHE_LOCK:
            if len(_SESSION_CACHE) >= _SESSION_CACHE_LIMIT:
                _SESSION_CACHE.popitem(last=False)
            _SESSION_CACHE[cache_key] = session
        return session

    except Exception as e:
        error_str = str(e)
        if "NameResolutionError" in error_str or "ConnectionError" in error_str:
            logger.error(f"NETWORK ERROR: Could not download data for {grand_prix} {year}. Check your internet connection.")
        else:
            logger.error(f"Session load error: {e}")
        return None


def get_event_details(year: int, grand_prix: Optional[str] = None, round_number: Optional[int] = None) -> str:
    """FastF1 event metadata lookup using get_event/get_event_schedule APIs."""
    if not validate_year(year):
        return f"Year {year} is out of range."

    try:
        if grand_prix:
            event = fastf1.get_event(year, grand_prix)
        elif round_number:
            event = fastf1.get_event(year, round_number)
        else:
            return "Provide either grand_prix or round_number."

        output = f"--- Event Details: {event['EventName']} ({year}) ---\n"
        output += f"Round: {event['RoundNumber']}\n"
        output += f"Country: {event['Country']} | Location: {event['Location']}\n"
        output += f"Format: {event['EventFormat']}\n"

        for label, key in [
            ("FP1", "Session1"), ("FP2", "Session2"), ("FP3", "Session3"),
            ("Qualifying", "Session4"), ("Race/Sprint", "Session5")
        ]:
            session_name = event.get(key)
            session_date = event.get(f"{key}Date")
            if session_name and pd.notna(session_date):
                output += f"{label}: {session_name} @ {session_date}\n"
        return output
    except Exception as e:
        logger.error(f"Event lookup error: {e}")
        return f"Event lookup error: {e}"


def get_testing_schedule(year: int) -> str:
    """Get pre-season testing events via FastF1 get_testing_event_schedule."""
    if not validate_year(year):
        return f"Year {year} is out of range."

    try:
        schedule = fastf1.get_testing_event_schedule(year)
        if schedule.empty:
            return f"No testing events found for {year}."

        output = f"--- {year} Testing Schedule ---\n"
        for _, row in schedule.iterrows():
            output += f"{row['EventName']} ({row['Location']}) - {row['EventDate'].strftime('%Y-%m-%d')}\n"
        return output
    except Exception as e:
        logger.error(f"Testing schedule error: {e}")
        return f"Testing schedule error: {e}"


def get_next_event(year: int = None) -> str:
    """Get next remaining event in a season via FastF1 get_events_remaining."""
    year = year or pd.Timestamp.utcnow().year
    if not validate_year(year):
        return f"Year {year} is out of range."

    try:
        remaining = fastf1.get_events_remaining(year)
        if remaining.empty:
            return f"No remaining events found for {year}."

        next_event = remaining.iloc[0]
        return (
            f"Next event: {next_event['EventName']} (Round {next_event['RoundNumber']})\n"
            f"Location: {next_event['Location']}, {next_event['Country']}\n"
            f"Date: {next_event['EventDate'].strftime('%Y-%m-%d')}"
        )
    except Exception as e:
        logger.error(f"Next event lookup error: {e}")
        return f"Next event lookup error: {e}"


def get_session_status_summary(year: int, grand_prix: str, session: str = "Race") -> str:
    """Summarize session_status, track_status, race control and weather data from FastF1 session APIs."""
    session_obj = _load_session_internal(year, grand_prix, session, telemetry=False, weather=True, messages=True)
    if not session_obj:
        return "Session not found or failed to load."

    try:
        out = [f"--- Session Control Summary: {grand_prix} {year} ({session}) ---"]

        track_status = getattr(session_obj, 'track_status', pd.DataFrame())
        if isinstance(track_status, pd.DataFrame) and not track_status.empty:
            out.append(f"Track status samples: {len(track_status)}")
            out.append("Latest track statuses:")
            for _, row in track_status.tail(5).iterrows():
                out.append(f"- {row.get('Time', 'n/a')}: {row.get('Message', row.get('Status', 'n/a'))}")

        session_status = getattr(session_obj, 'session_status', pd.DataFrame())
        if isinstance(session_status, pd.DataFrame) and not session_status.empty:
            out.append("Latest session statuses:")
            for _, row in session_status.tail(3).iterrows():
                out.append(f"- {row.get('Time', 'n/a')}: {row.get('Status', 'n/a')}")

        race_control = getattr(session_obj, 'race_control_messages', pd.DataFrame())
        if isinstance(race_control, pd.DataFrame) and not race_control.empty:
            out.append("Recent race control messages:")
            for _, row in race_control.tail(5).iterrows():
                msg = row.get('Message', 'n/a')
                category = row.get('Category', 'INFO')
                out.append(f"- [{category}] {msg}")

        weather = getattr(session_obj, 'weather_data', pd.DataFrame())
        if isinstance(weather, pd.DataFrame) and not weather.empty:
            latest = weather.iloc[-1]
            out.append(
                "Latest weather: "
                f"air={latest.get('AirTemp', 'n/a')}°C, track={latest.get('TrackTemp', 'n/a')}°C, "
                f"humidity={latest.get('Humidity', 'n/a')}%, rain={latest.get('Rainfall', 'n/a')}"
            )

        return "\n".join(out)
    except Exception as e:
        logger.error(f"Session status summary error: {e}")
        return f"Session status summary error: {e}"

def get_session_results(year: int, grand_prix: str, session: str):
    """Full classification table for a session."""
    session_obj = load_session(year, grand_prix, session)
    if not session_obj: 
        return "Session not found or failed to load."
    
    try:
        res = session_obj.results.sort_values(by='ClassifiedPosition')
        output = f"--- Results: {grand_prix} {year} ({session}) ---\n"
        for _, row in res.iterrows():
            pos = str(row['ClassifiedPosition'])
            if pos == 'R': pos = "DNF"
            elif pos == 'nan': pos = "DNS"
            points = row.get('Points', 0)
            status = row.get('Status', 'Unknown')
            output += f"{pos}. {row['FullName']} ({row['TeamName']}) | Pts: {points} | Status: {status}\n"
        return output
    except Exception as e:
        logger.error(f"Results error: {e}")
        return f"Results error: {e}"

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
        compound_colors = {
            'SOFT': '#FF0000', 'MEDIUM': '#FFD700', 'HARD': '#FFFFFF',
            'INTERMEDIATE': '#00FF00', 'WET': '#0000FF'
        }
        
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
                    
                    color = compound_colors.get(compound.upper(), '#808080')
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
        
        legend_elements = [plt.Rectangle((0,0),1,1, fc=color, ec='black', label=comp.title()) 
                          for comp, color in compound_colors.items()]
        ax.legend(handles=legend_elements, loc='upper right', facecolor='#2E2E2E', edgecolor='white', labelcolor='white')
        
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

"""
Predictive Tools
AI-powered tools for race strategy and performance prediction.
"""
import logging
import asyncio
import pandas as pd
from langchain_core.tools import tool
from core.api_client import get_enhanced_client
from core.analytics import RaceAnalytics

logger = logging.getLogger("PredictiveTools")

@tool
async def f1_predict_tire_life(
    driver_number: int,
    session_key: str = "latest"
) -> str:
    """
    Predicts tire degradation and remaining life for a driver.
    Use when user asks: "How are Verstappen's tires?", "Tire deg for Hamilton", "Is his pace dropping?"
    """
    try:
        client = get_enhanced_client()
        if session_key == "latest":
            session_key = await client.get_latest_session_key_async()
            
        # Fetch laps
        laps_data = await client.get_laps_async(session_key, driver_number)
        if not laps_data:
            return f"No lap data available for driver #{driver_number}"
            
        df = pd.DataFrame(laps_data)
        if df.empty:
            return "Insufficient data for prediction."
            
        # Identify current stint
        # Assuming last lap's stint is the current one.
        # FastF1/OpenF1 usually has 'stint' column, but if not we assume continuous from last pit.
        # OpenF1 'laps' endpoint has 'stint'.
        
        if 'stint' in df.columns:
            current_stint = df['stint'].max()
            stint_laps = df[df['stint'] == current_stint]
        else:
            # Fallback: take last 15 laps
            stint_laps = df.tail(15)
            
        if len(stint_laps) < 5:
            return "Not enough laps in current stint to model degradation (need > 5)."
            
        # Prepare data
        lap_numbers = stint_laps['lap_number'].tolist()
        lap_times = stint_laps['lap_duration'].tolist()
        
        # Analyze
        analysis = RaceAnalytics.calculate_tire_degradation(lap_numbers, lap_times)
        
        if not analysis['is_valid']:
            return f"Could not model tire deg: {analysis.get('reason')}"
            
        deg = analysis['degradation_rate']
        r2 = analysis['r_squared']
        
        # Interpret
        if deg > 0.1:
            status = "HIGH DEGRADATION 🔴"
            desc = "Pace is dropping significantly."
        elif deg > 0.05:
            status = "MODERATE DEGRADATION 🟡"
            desc = "Normal wear levels."
        elif deg > 0:
            status = "LOW DEGRADATION 🟢"
            desc = "Tires are holding up well."
        else:
            status = "IMPROVING / STEADY 🟣"
            desc = "Driver is getting faster (fuel burn effect > tire wear)."
            
        return f"""
=== TIRE ANALYSIS: Driver #{driver_number} ===
Status: {status}
Degradation Rate: {deg:.3f}s per lap
Model Confidence: {r2*100:.1f}%
Context: {desc}
Based on last {analysis['laps_analyzed']} laps.
"""
    except Exception as e:
        logger.error(f"Tire prediction failed: {e}")
        return f"Error predicting tire life: {e}"

@tool
async def f1_predict_overtake(
    chaser_driver_number: int,
    target_driver_number: int,
    session_key: str = "latest"
) -> str:
    """
    Predicts if/when a chasing driver will catch the target.
    Use when user asks: "Will Lewis catch Max?", "When will the overtake happen?", "Gap analysis"
    """
    try:
        client = get_enhanced_client()
        if session_key == "latest":
            session_key = await client.get_latest_session_key_async()
            
        # 1. Get current interval/gap
        intervals = await client.get_intervals_async(session_key)
        df_int = pd.DataFrame(intervals)
        
        # Filter for latest data
        latest_int = df_int.sort_values('date').groupby('driver_number').tail(1)
        
        try:
            chaser_row = latest_int[latest_int['driver_number'] == chaser_driver_number].iloc[0]
            target_row = latest_int[latest_int['driver_number'] == target_driver_number].iloc[0]
            
            # Calculate gap (OpenF1 interval is gap to leader, or interval to car ahead?)
            # 'gap_to_leader' is safer if available.
            gap_diff = float(chaser_row['gap_to_leader']) - float(target_row['gap_to_leader'])
            gap = abs(gap_diff)
            
            # Check who is ahead. if gap_diff > 0, chaser is behind (larger gap to leader).
            if gap_diff < 0:
                return f"Driver #{chaser_driver_number} is already AHEAD of #{target_driver_number}."
                
        except IndexError:
            return "One or both drivers not found in current session intervals."
            
        # 2. Get recent pace (last 5 laps)
        laps_chaser = await client.get_laps_async(session_key, chaser_driver_number)
        laps_target = await client.get_laps_async(session_key, target_driver_number)
        
        if not laps_chaser or not laps_target:
            return "Lap data unavailable for pace analysis."
            
        df_c = pd.DataFrame(laps_chaser).tail(5)
        df_t = pd.DataFrame(laps_target).tail(5)
        
        pace_c = df_c['lap_duration'].mean()
        pace_t = df_t['lap_duration'].mean()
        
        # 3. Predict
        prediction = RaceAnalytics.predict_catch_lap(gap, pace_c, pace_t)
        
        output = f"""
=== OVERTAKE PREDICTION ===
Chaser: #{chaser_driver_number} ({pace_c:.3f}s avg)
Target: #{target_driver_number} ({pace_t:.3f}s avg)
Current Gap: {gap:.3f}s
Pace Delta: {prediction.get('pace_delta', 0):.3f}s per lap

Prediction: """

        if prediction['will_catch']:
            laps = prediction['laps_to_catch']
            output += f"CATCH EXPECTED in ~{laps} laps 🎯"
        else:
            output += f"NO CATCH PREDICTED ❌ (Chaser is slower/equal)"
            
        return output
        
    except Exception as e:
        logger.error(f"Overtake prediction failed: {e}")
        return f"Error predicting overtake: {e}"

def get_predictive_tools() -> list:
    return [f1_predict_tire_life, f1_predict_overtake]

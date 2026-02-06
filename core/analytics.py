"""
Predictive Analytics Engine for F1 Agent
Handles mathematical modeling for race strategy, tire degradation, and performance projection.
"""
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("RaceAnalytics")

class RaceAnalytics:
    """
    Core math engine for F1 predictive analytics.
    Uses statistical models to project race outcomes.
    """

    @staticmethod
    def calculate_tire_degradation(
        lap_numbers: List[int],
        lap_times: List[float],
        exclude_outliers: bool = True
    ) -> Dict:
        """
        Calculates tire degradation rate (seconds lost per lap) using linear regression.
        
        Args:
            lap_numbers: List of lap numbers (x-axis)
            lap_times: List of lap times in seconds (y-axis)
            exclude_outliers: Whether to filter out slow laps (Yellow flags/Traffic)
            
        Returns:
            Dict containing:
            - degradation_rate: Seconds lost per lap
            - base_pace: Theoretical pace at lap 0 of stint
            - correlation: R-squared value of the fit
            - is_valid: Boolean indicating if calculation is reliable
        """
        if len(lap_times) < 3:
            return {"is_valid": False, "reason": "Insufficient data"}
            
        x = np.array(lap_numbers)
        y = np.array(lap_times)
        
        if exclude_outliers:
            # Filter laps > 107% of median (simple outlier detection)
            median_time = np.median(y)
            threshold = median_time * 1.07
            mask = y < threshold
            x = x[mask]
            y = y[mask]
            
            if len(y) < 3:
                return {"is_valid": False, "reason": "Too much noise/outliers"}

        try:
            # Linear regression: y = mx + c
            # m = degradation rate (slope)
            slope, intercept = np.polyfit(x, y, 1)
            
            # Calculate R-squared
            y_pred = slope * x + intercept
            residuals = y - y_pred
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            return {
                "is_valid": True,
                "degradation_rate": float(slope),  # Positive = Getting slower
                "base_pace": float(intercept),
                "r_squared": float(r_squared),
                "laps_analyzed": len(y)
            }
            
        except Exception as e:
            logger.error(f"Degradation calc failed: {e}")
            return {"is_valid": False, "reason": str(e)}

    @staticmethod
    def calculate_undercut_window(
        gap_to_target: float,
        my_in_lap_pace: float,
        target_in_lap_pace: float,
        pit_loss_time: float,
        fresh_tire_advantage: float
    ) -> Dict:
        """
        Analyzes feasibility of an undercut.
        
        The undercut works if:
        (Gap + Time_in_Pits) < (Target_Sector_Times + Target_Pit_Loss) 
        ...simplified to: can I gain enough time on fresh tires to offset the gap?
        
        Rough formula:
        Time Gained = (Target Pace - My New Pace)
        If Time Gained > Gap, Undercut is ON.
        
        Args:
            gap_to_target: Seconds behind the car ahead
            my_in_lap_pace: Estimated in-lap time
            target_in_lap_pace: Estimated target's in-lap time (usually slower due to old tires)
            pit_loss_time: Time lost in pit lane (avg for track)
            fresh_tire_advantage: Seconds gained per lap on new tires vs old
            
        Returns:
             Dict with 'feasible', 'margin', and 'recommendation'
        """
        # Estimated time gain on out-lap vs target's old-tire in-lap or normal lap
        # Simple heuristic: Undercut gain ~ 2-3 seconds on typical tracks
        # Margin = (Fresh Tire Advantage) - Gap
        
        margin = fresh_tire_advantage - gap_to_target
        
        feasible = margin > 0.5  # Safety margin
        
        likelihood = "High" if margin > 1.5 else "Medium" if margin > 0.5 else "Low"
        if margin < -0.5: likelihood = "Impossible"
            
        return {
            "feasible": feasible,
            "estimated_gain": float(margin),
            "likelihood": likelihood,
            "gap": gap_to_target,
            "required_pace_delta": float(gap_to_target + 0.5)
        }

    @staticmethod
    def predict_catch_lap(
        gap: float,
        chaser_pace: float,
        leader_pace: float
    ) -> Dict:
        """
        Predicts when a chasing car will catch the leader.
        
        Args:
            gap: Current gap in seconds
            chaser_pace: Chaser avg lap time
            leader_pace: Leader avg lap time
            
        Returns:
            Dict estimate of laps_to_catch
        """
        pace_delta = leader_pace - chaser_pace
        
        if pace_delta <= 0:
            return {
                "will_catch": False,
                "reason": "Chaser is slower or matching pace",
                "laps_to_catch": None
            }
            
        laps_to_catch = gap / pace_delta
        
        return {
            "will_catch": True,
            "laps_to_catch": int(np.ceil(laps_to_catch)),
            "pace_delta": float(pace_delta)
        }

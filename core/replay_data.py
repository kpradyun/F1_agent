"""
Replay Data Management
Handles grid position extraction and race data processing
"""
import pandas as pd

def extract_grid_positions(session, driver_info, laps, car_data_cache):
    """
    Extract starting grid positions for all drivers.
    
    Uses multiple fallback methods:
    1. From session.results DataFrame (most reliable)
    2. From lap data GridPosition/Position
    3. From initial telemetry distances
    4. Sequential fallback
    
    Args:
        session: FastF1 session object
        driver_info: Dictionary of driver information
        laps: DataFrame of lap data
        car_data_cache: Dictionary of cached car telemetry
        
    Returns:
        dict: {driver_abbr: grid_position}
    """
    grid_positions = {}
    
    try:
        # Method 1: From session.results DataFrame (most reliable)
        if hasattr(session, 'results') and session.results is not None:
            results_df = session.results
            print(f"\n=== Extracting Grid Positions ===")
            print(f"Found session results with {len(results_df)} drivers")
            
            for idx, row in results_df.iterrows():
                # Get driver abbreviation
                drv_abbr = row.get('Abbreviation')
                if pd.isna(drv_abbr):
                    drv_abbr = row.get('Driver')
                
                # Get grid position
                grid_pos = None
                if 'GridPosition' in row and pd.notna(row['GridPosition']):
                    try:
                        grid_pos = int(row['GridPosition'])
                    except (ValueError, TypeError):
                        pass
                
                if not grid_pos and 'Position' in row and pd.notna(row['Position']):
                    try:
                        grid_pos = int(row['Position'])
                    except (ValueError, TypeError):
                        pass
                
                # Find the correct key in driver_info
                if drv_abbr and grid_pos:
                    driver_key = None
                    if drv_abbr in driver_info:
                        driver_key = drv_abbr
                    else:
                        # driver_info might use driver numbers as keys
                        driver_num = str(row.get('DriverNumber', ''))
                        if driver_num in driver_info:
                            driver_key = driver_num
                    
                    if driver_key:
                        grid_positions[driver_key] = grid_pos
                        print(f"  Grid P{grid_pos}: {driver_key} ({drv_abbr})")
        
        # Method 2: If no results, try from laps
        if not grid_positions:
            print("No grid positions from results, trying lap data...")
            for drv in driver_info:
                drv_laps = laps[laps['Driver'] == drv]
                if not drv_laps.empty:
                    # Sort by lap number and get first lap
                    first_lap = drv_laps.sort_values('LapNumber').iloc[0]
                    grid_pos = None
                    if 'GridPosition' in first_lap and pd.notna(first_lap['GridPosition']):
                        grid_pos = int(first_lap['GridPosition'])
                    elif 'Position' in first_lap and pd.notna(first_lap['Position']):
                        grid_pos = int(first_lap['Position'])
                    
                    if grid_pos:
                        grid_positions[drv] = grid_pos
                        print(f"  From laps - P{grid_pos}: {drv}")
        
        # Method 3: Use starting distance if nothing else works
        if not grid_positions:
            print("Using initial telemetry distances")
            initial_data = {}
            for drv in driver_info:
                if drv in car_data_cache:
                    df = car_data_cache[drv]
                    if not df.empty and 'Distance' in df.columns:
                        # Get one of the earliest distances
                        initial_data[drv] = df['Distance'].iloc[min(5, len(df)-1)]
            
            # Lowest distance = front of grid
            sorted_by_dist = sorted(initial_data.items(), key=lambda x: x[1])
            for pos, (drv, _) in enumerate(sorted_by_dist, 1):
                grid_positions[drv] = pos
                print(f"  Estimated P{pos}: {drv}")
        
        # Fallback
        if not grid_positions:
            print("WARNING: Using fallback sequential positions")
            for idx, drv in enumerate(driver_info.keys(), 1):
                grid_positions[drv] = idx
        
        print(f"\nFinal grid positions: {sorted(grid_positions.items(), key=lambda x: x[1])}")
                
    except Exception as e:
        print(f"Error extracting grid positions: {e}")
        import traceback
        traceback.print_exc()
        # Emergency fallback
        for idx, drv in enumerate(driver_info.keys(), 1):
            grid_positions[drv] = idx
    
    return grid_positions

def get_current_lap_number(current_time, laps):
    """
    Get the current lap number based on race time.
    
    Args:
        current_time: Current race timedelta
        laps: DataFrame of lap data
        
    Returns:
        int: Current lap number
    """
    if laps.empty:
        return 1
    
    # Find lap based on LapStartTime
    for idx, row in laps.iterrows():
        if pd.notna(row.get('LapStartTime')):
            if row['LapStartTime'] > current_time:
                return max(1, int(row.get('LapNumber', 1)) - 1)
    
    # Fallback to last lap
    return int(laps['LapNumber'].max()) if 'LapNumber' in laps.columns else 1

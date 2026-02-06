"""
Validation utilities for F1 Agent
"""
from config.settings import FASTF1_MIN_YEAR, FASTF1_MAX_YEAR


def validate_year(year: int) -> None:
    """
    Validate year is within FastF1 data range.
    
    Args:
        year: Year to validate
        
    Raises:
        ValueError: If year is out of range
    """
    if not (FASTF1_MIN_YEAR <= year <= FASTF1_MAX_YEAR):
        raise ValueError(
            f"Year must be between {FASTF1_MIN_YEAR} and {FASTF1_MAX_YEAR}. Got: {year}"
        )


def validate_driver(driver: str, session) -> str:
    """
    Validate driver exists in session and return the correct abbreviation.
    
    Args:
        driver: Driver name or abbreviation
        session: FastF1 session object
        
    Returns:
        Valid driver abbreviation
        
    Raises:
        ValueError: If driver not found in session
    """
    driver_upper = driver.upper()
    
    # Check if it's already a valid abbreviation
    if driver_upper in session.drivers:
        return driver_upper
    
    # Try to find by last name
    for drv in session.drivers:
        driver_info = session.get_driver(drv)
        if driver.lower() in driver_info['LastName'].lower():
            return drv
    
    raise ValueError(
        f"Driver '{driver}' not found in session. "
        f"Available drivers: {', '.join(session.drivers)}"
    )


def validate_session_type(session_type: str) -> str:
    """
    Validate and normalize session type.
    
    Args:
        session_type: Session type (Race, Qualifying, Sprint, etc.)
        
    Returns:
        Normalized session type
        
    Raises:
        ValueError: If session type is invalid
    """
    valid_sessions = {
        'race': 'Race',
        'qualifying': 'Qualifying',
        'q': 'Qualifying',
        'sprint': 'Sprint',
        'sprint qualifying': 'Sprint Qualifying',
        'sq': 'Sprint Qualifying',
        'fp1': 'FP1',
        'fp2': 'FP2',
        'fp3': 'FP3',
        'practice 1': 'FP1',
        'practice 2': 'FP2',
        'practice 3': 'FP3'
    }
    
    normalized = valid_sessions.get(session_type.lower())
    if not normalized:
        raise ValueError(
            f"Invalid session type: {session_type}. "
            f"Valid options: {', '.join(set(valid_sessions.values()))}"
        )
    
    return normalized

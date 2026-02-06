"""
UI Helper Functions
Utility functions for the replay UI
"""
import arcade.types
from datetime import timedelta

def create_rect(cx, cy, width, height):
    """
    Creates an arcade.types.LBWH rectangle from center coordinates.
    
    Args:
        cx: Center X coordinate
        cy: Center Y coordinate
        width: Rectangle width
        height: Rectangle height
        
    Returns:
        arcade.types.LBWH rectangle
    """
    return arcade.types.LBWH(
        left=cx - (width / 2), 
        bottom=cy - (height / 2), 
        width=width, 
        height=height
    )

def format_time(td: timedelta) -> str:
    """
    Formats timedelta as HH:MM:SS (removes '0 days').
    
    Args:
        td: Timedelta object
        
    Returns:
        Formatted time string
    """
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def format_gap(gap_seconds):
    """
    Format gap to leader/car ahead.
    
    Args:
        gap_seconds: Gap in seconds
        
    Returns:
        Formatted gap string
    """
    if gap_seconds is None or gap_seconds == 0:
        return "—"
    elif gap_seconds < 0.1:
        return "—"
    elif gap_seconds < 1:
        return f"{gap_seconds:.3f}"
    else:
        return f"{gap_seconds:.2f}"

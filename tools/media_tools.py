"""
Media Tools
Tools for downloading and managing F1 media assets (Radio messages, etc.)
"""
import logging
import os
import requests
from config.settings import PLOTS_DIR
from core.api_client import get_enhanced_client
from langchain_core.tools import tool

logger = logging.getLogger("MediaTools")

@tool
async def f1_download_radio(
    driver_number: int, 
    grand_prix: str = "latest", 
    year: int = 2025,
    session_key: str = None
) -> str:
    """
    Downloads the most recent team radio recording for a specific driver.
    Saves the .mp3 to the /plots directory.
    
    Args:
        driver_number: The car number (e.g. 44, 1, 4)
        grand_prix: Grand Prix name or 'latest'
        year: The F1 season (default: 2025)
        session_key: Direct session key (optional, overrides GP/Year)
    """
    try:
        from core.session_resolver import get_resolver
        client = get_enhanced_client()
        
        # Filter out pseudo-nulls from Agent
        if str(session_key).lower() in ['nil', 'none', 'null', 'unknown']:
            session_key = None

        # Resolve session key if not provided
        if not session_key:
            resolver = get_resolver()
            session_key = resolver.resolve(year, grand_prix, "Race")
            
        if not session_key or str(session_key).lower() in ['null', 'none', 'unknown', 'nil', '']:
            return f"Could not resolve a valid session key for '{grand_prix}' in {year}. Please specify the year clearly (e.g., '2024') or provide a direct session key."
            
        # Get radio messages
        session_key_str = str(session_key)
        try:
            radio_data = client.get_team_radio(session_key=session_key_str, driver_number=driver_number)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "ACCESS RESTRICTED: The OpenF1 API restricts global access to historical data while a LIVE F1 session is in progress. Please try again after the current session ends, or provide a premium API key if you have one."
            raise e
        
        if not radio_data:
            return f"No radio messages were found for driver #{driver_number} in the resolved session {session_key_str} ({year} {grand_prix}). This might mean the data is not yet available in the OpenF1 API for this specific race."
        
        # Take the most recent recording
        latest = radio_data[-1]
        url = latest.get('recording_url')
        
        if not url:
            return "Found radio entry but no recording URL available."

        # Get metadata for a better filename
        driver_name = str(driver_number)
        try:
            drivers = client.get_drivers(session_key=session_key)
            for d in drivers:
                if d.get('driver_number') == driver_number:
                    # Use last name or full name
                    driver_name = d.get('last_name') or d.get('full_name', str(driver_number))
                    driver_name = driver_name.replace(" ", "_")
                    break
        except Exception as e:
            logger.warning(f"Could not resolve driver name: {e}")

        session_meta = f"Session_{session_key}"
        try:
            sessions = client.get_sessions(session_key=session_key)
            if sessions:
                s = sessions[0]
                year_val = s.get('year', year)
                location = s.get('location', 'Unknown').replace(" ", "_")
                session_meta = f"{year_val}_{location}"
        except Exception as e:
            logger.warning(f"Could not resolve session metadata: {e}")

        # Download the file
        timestamp = latest['date'].split('T')[1].split('.')[0].replace(':', '-')
        filename = f"radio_{driver_name}_{session_meta}_{timestamp}.mp3"
        filepath = os.path.abspath(os.path.join(PLOTS_DIR, filename))
        
        logger.info(f"Downloading radio from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
            
        return f"Successfully downloaded radio message for {driver_name} ({session_meta}) to:\n{filepath}"
        
    except Exception as e:
        logger.error(f"Radio download failed: {e}")
        return f"Error downloading radio: {e}"

def get_media_tools() -> list:
    """Return list of media tools."""
    return [f1_download_radio]

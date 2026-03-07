"""
Session Key Resolution Logic
Handles intelligent session key resolution with year auto-detection
"""
import re
import logging
from typing import Optional, Set
from core.api_client import get_client

logger = logging.getLogger("SessionResolver")


class SessionResolver:
    """Resolves session keys from natural language inputs"""
    
    def __init__(self):
        self.client = get_client()
        # Words to ignore when matching Grand Prix names
        self.ignored_tokens = {'grand', 'prix', 'race', 'gp'}
        
        # Mapping for common GP names that don't match location/circuit strings
        self.gp_mapping = {
            'british': ['silverstone', 'united kingdom'],
            'dutch': ['zandvoort', 'netherlands'],
            'spanish': ['barcelona', 'catalunya', 'spain'],
            'belgian': ['spa', 'francorchamps', 'belgium'],
            'italian': ['monza', 'imola', 'italy'],
            'japanese': ['suzuka', 'japan'],
            'brazilian': ['sao paulo', 'interlagos', 'brazil'],
            'mexican': ['mexico city', 'mexico'],
            'austrian': ['spielberg', 'red bull ring', 'austria'],
            'canadian': ['montreal', 'gilles villeneuve', 'canada'],
            'chinese': ['shanghai', 'china'],
            'azerbaijan': ['baku'],
            'hungarian': ['budapest', 'hungaroring', 'hungary'],
            'emilia romagna': ['imola'],
            'saudi arabian': ['jeddah', 'saudi arabia'],
            'abu dhabi': ['yas marina', 'abu dhabi'],
            'united states': ['austin', 'cotas', 'usa'],
            'miami': ['miami', 'usa'],
            'las vegas': ['las vegas', 'usa'],
            'monaco': ['monte carlo', 'cote d\'azur', 'monaco'],
            'emirati': ['abu dhabi', 'yas marina'],
            'bahrain': ['sakhir', 'manama'],
            'qatar': ['lusail', 'doha'],
            'singapore': ['marina bay', 'singapore'],
            'australian': ['melbourne', 'albert park', 'australia']
        }
    
    def _extract_year(self, grand_prix: str, default_year: int) -> tuple[int, str]:
        """
        Extract year from GP string if present.
        
        Args:
            grand_prix: GP name (might include year like "Abu Dhabi 2023")
            default_year: Default year to use if not found
            
        Returns:
            Tuple of (year, cleaned_gp_name)
        """
        year_match = re.search(r'\b(20\d{2})\b', str(grand_prix))
        
        if year_match:
            extracted_year = int(year_match.group(1))
            cleaned_gp = grand_prix.replace(str(extracted_year), "").strip()
            logger.info(f"Detected year {extracted_year} in GP name")
            return extracted_year, cleaned_gp
        
        return default_year, grand_prix
    
    def _get_meaningful_tokens(self, query: str) -> Set[str]:
        """
        Extract meaningful search tokens from query.
        
        Args:
            query: GP search query
            
        Returns:
            Set of meaningful tokens (excluding common words)
        """
        tokens = set(query.lower().split())
        return {t for t in tokens if t not in self.ignored_tokens}
    
    def _match_session(
        self,
        sessions: list,
        gp_tokens: Set[str],
        full_query: str
    ) -> Optional[dict]:
        """
        Match a session from the list based on GP tokens.
        
        Args:
            sessions: List of session objects
            gp_tokens: Meaningful tokens from GP query
            full_query: Full original query
            
        Returns:
            Matched session dict or None
        """
        matches = []
        
        for session in sessions:
            location = session.get('location', '')
            circuit = session.get('circuit_short_name', '')
            country = session.get('country_name', '')
            
            name_str = f"{location} {circuit} {country}".lower()
            
            # Check if any GP token is a key in our mapping
            expanded_tokens = set(gp_tokens)
            for token in gp_tokens:
                if token in self.gp_mapping:
                    expanded_tokens.update(self.gp_mapping[token])
            
            # If no meaningful tokens (after expansion), do exact substring match
            if not expanded_tokens:
                if full_query.lower() in name_str:
                    matches.append(session)
            # Otherwise, check if any expanded token matches
            elif any(token in name_str for token in expanded_tokens):
                matches.append(session)
        
        if matches:
            # Return the most recent match by date
            matches.sort(key=lambda x: x.get('date_start', ''))
            return matches[-1]
        
        return ""
    
    def resolve(
        self,
        year: int,
        grand_prix: str,
        session_type: str = "Race"
    ) -> str:
        """
        Resolve a session key from year, GP name, and session type.
        
        Args:
            year: Race year
            grand_prix: Grand Prix name or "latest"
            session_type: Session type (Race, Qualifying, etc.)
            
        Returns:
            Session key string
        """
        logger.info(f"Resolving session: Year={year}, GP='{grand_prix}', Type='{session_type}'")
        # Handle "latest" special case
        if grand_prix == "latest":
            return self.client.get_latest_session_key()
        
        # Auto-detect year from GP string
        year, grand_prix = self._extract_year(grand_prix, year)
        
        try:
            # Fetch all sessions for the year
            logger.info(f"Fetching sessions for year {year}...")
            sessions = self.client.get_sessions(year=year)
            
            if not sessions:
                logger.warning(f"No sessions found for {year}. Using latest.")
                fallback = self.client.get_latest_session_key()
                return str(fallback) if fallback else ""
            
            # Filter by session type
            filtered = [
                s for s in sessions
                if session_type.lower() in s['session_name'].lower()
            ]
            
            # Use all sessions if type filter yields nothing
            if not filtered:
                filtered = sessions
            
            # Get meaningful tokens and match
            gp_tokens = self._get_meaningful_tokens(grand_prix)
            matched = self._match_session(filtered, gp_tokens, grand_prix)
            
            if matched:
                session_key = matched['session_key']
                if session_key and str(session_key).lower() not in ['none', 'null', 'unknown', 'nil', '', 'undefined']:
                    logger.info(
                        f"Resolved '{grand_prix}' ({year}, {session_type}) "
                        f"to session key: {session_key}"
                    )
                    return str(session_key)
            
            # If no match but a year was provided, default to first/last race of that year 
            # instead of global 'latest' (which could be the wrong year)
            if filtered:
                default_session = filtered[-1] # Last race usually better than first
                session_key = default_session.get('session_key')
                logger.warning(
                    f"No match for '{grand_prix}' {year}. Defaulting to {default_session.get('location')} ({session_key})"
                )
                return str(session_key) if session_key else ""

            logger.warning(
                f"No match found for '{grand_prix}' {year}. Using latest."
            )
            return self.client.get_latest_session_key()
            
        except Exception as e:
            logger.error(f"Error resolving session: {e}")
            fallback = self.client.get_latest_session_key()
            logger.info(f"Fallback resolution to: {fallback}")
            return str(fallback) if fallback else ""


# Singleton instance
_resolver_instance = None


def get_resolver() -> SessionResolver:
    """
    Get the singleton SessionResolver instance.
    
    Returns:
        SessionResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = SessionResolver()
    return _resolver_instance

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
            
            # If no meaningful tokens, do exact substring match
            if not gp_tokens:
                if full_query.lower() in name_str:
                    matches.append(session)
            # Otherwise, check if any token matches
            elif any(token in name_str for token in gp_tokens):
                matches.append(session)
        
        if matches:
            # Return the most recent match
            matches.sort(key=lambda x: x['date_start'])
            return matches[-1]
        
        return None
    
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
        # Handle "latest" special case
        if grand_prix == "latest":
            return self.client.get_latest_session_key()
        
        # Auto-detect year from GP string
        year, grand_prix = self._extract_year(grand_prix, year)
        
        try:
            # Fetch all sessions for the year
            sessions = self.client.get_sessions(year=year)
            
            if not sessions:
                logger.warning(f"No sessions found for {year}. Using latest.")
                return self.client.get_latest_session_key()
            
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
                logger.info(
                    f"Resolved '{grand_prix}' ({year}, {session_type}) "
                    f"to session key: {session_key}"
                )
                return session_key
            
            logger.warning(
                f"No match found for '{grand_prix}' {year}. Using latest."
            )
            return self.client.get_latest_session_key()
            
        except Exception as e:
            logger.error(f"Error resolving session: {e}")
            return self.client.get_latest_session_key()


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

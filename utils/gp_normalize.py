"""
GP Name Normalization

Maps colloquial and abbreviated GP names to the official FastF1 event names.
Called by load_session() so all tools benefit automatically.
"""

# Maps lowercase colloquial → FastF1 EventName substring (case-insensitive match)
_GP_ALIASES: dict[str, str] = {
    # Circuit nicknames → full name
    "spa": "Belgian Grand Prix",
    "monza": "Italian Grand Prix",
    "silverstone": "British Grand Prix",
    "monaco": "Monaco Grand Prix",
    "monte carlo": "Monaco Grand Prix",
    "zandvoort": "Dutch Grand Prix",
    "suzuka": "Japanese Grand Prix",
    "interlagos": "São Paulo Grand Prix",
    "sao paulo": "São Paulo Grand Prix",
    "são paulo": "São Paulo Grand Prix",
    "brazil": "São Paulo Grand Prix",
    "barcelona": "Spanish Grand Prix",
    "catalunya": "Spanish Grand Prix",
    "imola": "Emilia Romagna Grand Prix",
    "emilia romagna": "Emilia Romagna Grand Prix",
    "baku": "Azerbaijan Grand Prix",
    "montreal": "Canadian Grand Prix",
    "gilles villeneuve": "Canadian Grand Prix",
    "albert park": "Australian Grand Prix",
    "melbourne": "Australian Grand Prix",
    "shanghai": "Chinese Grand Prix",
    "jeddah": "Saudi Arabian Grand Prix",
    "bahrain": "Bahrain Grand Prix",
    "sakhir": "Bahrain Grand Prix",
    "lusail": "Qatar Grand Prix",
    "doha": "Qatar Grand Prix",
    "yas marina": "Abu Dhabi Grand Prix",
    "hungaroring": "Hungarian Grand Prix",
    "budapest": "Hungarian Grand Prix",
    "red bull ring": "Austrian Grand Prix",
    "spielberg": "Austrian Grand Prix",
    "nurburgring": "Eifel Grand Prix",
    "istanbul": "Turkish Grand Prix",
    "austin": "United States Grand Prix",
    "cota": "United States Grand Prix",
    "cotas": "United States Grand Prix",
    "marina bay": "Singapore Grand Prix",
    "singapore": "Singapore Grand Prix",
    "mexico city": "Mexico City Grand Prix",
    "mexico": "Mexico City Grand Prix",
    "las vegas": "Las Vegas Grand Prix",
    "miami": "Miami Grand Prix",
    "portimao": "Portuguese Grand Prix",
    "mugello": "Tuscan Grand Prix",
    "losail": "Qatar Grand Prix",
    "qatar": "Qatar Grand Prix",
    "paul ricard": "French Grand Prix",
    "ricard": "French Grand Prix",
    "french gp": "French Grand Prix",
    "zeltweg": "Austrian Grand Prix",
    "hockenheim": "German Grand Prix",
    "hockenheimring": "German Grand Prix",
    "german gp": "German Grand Prix",
    "suzuka circuit": "Japanese Grand Prix",
    "yas": "Abu Dhabi Grand Prix",
    "abu dhabi": "Abu Dhabi Grand Prix",
    "sochi": "Russian Grand Prix",
    "russian gp": "Russian Grand Prix",

    # Short-form GP names
    "australian gp": "Australian Grand Prix",
    "bahrain gp": "Bahrain Grand Prix",
    "chinese gp": "Chinese Grand Prix",
    "japanese gp": "Japanese Grand Prix",
    "miami gp": "Miami Grand Prix",
    "emilia romagna gp": "Emilia Romagna Grand Prix",
    "monaco gp": "Monaco Grand Prix",
    "canadian gp": "Canadian Grand Prix",
    "spanish gp": "Spanish Grand Prix",
    "austrian gp": "Austrian Grand Prix",
    "british gp": "British Grand Prix",
    "hungarian gp": "Hungarian Grand Prix",
    "belgian gp": "Belgian Grand Prix",
    "dutch gp": "Dutch Grand Prix",
    "italian gp": "Italian Grand Prix",
    "azerbaijan gp": "Azerbaijan Grand Prix",
    "singapore gp": "Singapore Grand Prix",
    "us gp": "United States Grand Prix",
    "usgp": "United States Grand Prix",
    "mexican gp": "Mexico City Grand Prix",
    "las vegas gp": "Las Vegas Grand Prix",
    "qatar gp": "Qatar Grand Prix",
    "abu dhabi gp": "Abu Dhabi Grand Prix",
    "brazilian gp": "São Paulo Grand Prix",
    "saudi arabian gp": "Saudi Arabian Grand Prix",
    "saudi gp": "Saudi Arabian Grand Prix",
}


def normalize_gp_name(name: str) -> str:
    """
    Normalize a GP name to the official FastF1 EventName.

    Returns the normalized name if a mapping exists, otherwise returns
    the original name unchanged so existing matching logic still applies.
    """
    if not name:
        return name
    key = name.strip().lower()
    return _GP_ALIASES.get(key, name)

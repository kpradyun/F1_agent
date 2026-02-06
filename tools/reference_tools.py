"""
Reference Tools
F1 historical data, lists, and reference information from Wikipedia
"""
import logging
import re
from functools import lru_cache
import wikipedia
from langchain_core.tools import tool

logger = logging.getLogger("ReferenceTools")


@lru_cache(maxsize=100)
def _cached_wikipedia_search(query: str, results: int = 5) -> tuple:
    """Cached Wikipedia search to avoid redundant API calls"""
    return tuple(wikipedia.search(query, results=results))


@lru_cache(maxsize=50)
def _cached_wikipedia_page(title: str):
    """Cached Wikipedia page fetch to avoid redundant API calls"""
    return wikipedia.page(title, auto_suggest=False)


def extract_list_content(page, query: str) -> str:
    """
    Extract relevant list content from a Wikipedia page.
    For list queries, tries to find specific sections.
    """
    query_lower = query.lower()
    content = page.content
    
    # For champion queries, look for specific year ranges or tables
    if 'champion' in query_lower or 'winner' in query_lower:
        # Try to find sections with years
        sections = content.split('\n\n')
        relevant_sections = []
        
        # Extract year mentioned in query (e.g., "since 2000")
        year_match = re.search(r'since\s+(\d{4})', query_lower)
        if year_match:
            start_year = int(year_match.group(1))
            # Look for content with years >= start_year
            for section in sections:
                # Find years in section
                years_in_section = re.findall(r'\b(19\d{2}|20\d{2})\b', section)
                if any(int(year) >= start_year for year in years_in_section):
                    relevant_sections.append(section)
        
        if relevant_sections:
            return '\n\n'.join(relevant_sections[:10])  # Limit to first 10 relevant sections
    
    return content


@tool
async def f1_wikipedia_lookup(query: str) -> str:
    """
    Use for HISTORICAL FACTS, LISTS, and GENERAL F1 INFORMATION.
    Searches Wikipedia for F1-related topics like:
    - Lists of champions, records, achievements
    - Driver/team histories and biographies
    - Historical race results
    - General F1 knowledge and trivia
    
    Examples of when to use:
    - "List of F1 world champions since 2000"
    - "Who has won the most F1 races?"
    - "History of Ferrari in F1"
    - "Lewis Hamilton career stats"
    - "What is DRS in F1?"
    
    DO NOT use for:
    - Current season data (use f1_schedule or f1_session_results)
    - Live race data (use live tools)
    - Official regulations (use f1_rules_lookup)
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()
        
        # Add "Formula One" or "F1" to query if not already present
        search_query = query
        if "formula" not in query.lower() and "f1" not in query.lower():
            search_query = f"Formula One {query}"
        
        logger.info(f"Wikipedia search: {search_query}")
        
        # Use cached search (run in thread pool)
        search_results = await wrapper.run_sync_tool(
            lambda: list(_cached_wikipedia_search(search_query, results=5))
        )
        
        if not search_results:
            return f"No Wikipedia articles found for query: {query}"
        
        # Prioritize 'List' pages for list-type queries
        query_lower = query.lower()
        is_list_query = any(word in query_lower for word in ['list', 'champions', 'winners', 'who has', 'since'])
        
        if is_list_query:
            list_results = [r for r in search_results if 'list' in r.lower()]
            if list_results:
                search_results = list_results + [r for r in search_results if r not in list_results]
        
        # Try to get the most relevant page
        # This logic involves multiple calls, better to wrap the whole discovery logic
        def fetch_best_page():
            found_page = None
            for result in search_results:
                try:
                    found_page = _cached_wikipedia_page(result)
                    break
                except wikipedia.DisambiguationError as e:
                    # If disambiguation, try to pick most relevant option
                    logger.info(f"Disambiguation found, options: {e.options[:5]}")
                    # Try to find F1-related option
                    f1_options = [opt for opt in e.options if any(
                        term in opt.lower() 
                        for term in ['formula one', 'f1', 'grand prix', 'racing', 'driver']
                    )]
                    if f1_options:
                        try:
                            found_page = _cached_wikipedia_page(f1_options[0])
                            break
                        except:
                            continue
                except wikipedia.PageError:
                    continue
            return found_page

        page = await wrapper.run_sync_tool(fetch_best_page)
        
        if not page:
            return f"Could not find relevant Wikipedia page for: {query}"
        
        # Extract content based on query type
        if is_list_query:
            content = await wrapper.run_sync_tool(extract_list_content, page, query)
        else:
            content = page.summary
        
        # Increase limit to 5000 characters for more complete results
        if len(content) > 5000:
            content = content[:5000] + "..."
        
        result = f"=== {page.title} ===\n\n"
        result += f"{content}\n\n"
        result += f"Source: {page.url}"
        
        return result
        
    except Exception as e:
        logger.error(f"Wikipedia search failed: {e}")
        return f"Error searching Wikipedia: {e}"


@tool
async def f1_champions_quick_lookup(year_filter: str = "") -> str:
    """
    FAST lookup for F1 World Champions. Use this for champion queries instead of Wikipedia.
    Returns F1 Drivers' World Champions from 2000 onwards.
    
    Args:
        year_filter: Optional filter like "since 2000" or "2010-2020" (default: all from 2000)
    
    Examples:
    - "List of F1 champions since 2000"
    - "Who were the champions from 2010 to 2020?"
    - "F1 world champions"
    """
    # Hardcoded data for instant response (updated to 2025)
    champions = {
        2000: "Michael Schumacher (Ferrari)",
        2001: "Michael Schumacher (Ferrari)",
        2002: "Michael Schumacher (Ferrari)",
        2003: "Michael Schumacher (Ferrari)",
        2004: "Michael Schumacher (Ferrari)",
        2005: "Fernando Alonso (Renault)",
        2006: "Fernando Alonso (Renault)",
        2007: "Kimi Räikkönen (Ferrari)",
        2008: "Lewis Hamilton (McLaren)",
        2009: "Jenson Button (Brawn)",
        2010: "Sebastian Vettel (Red Bull)",
        2011: "Sebastian Vettel (Red Bull)",
        2012: "Sebastian Vettel (Red Bull)",
        2013: "Sebastian Vettel (Red Bull)",
        2014: "Lewis Hamilton (Mercedes)",
        2015: "Lewis Hamilton (Mercedes)",
        2016: "Nico Rosberg (Mercedes)",
        2017: "Lewis Hamilton (Mercedes)",
        2018: "Lewis Hamilton (Mercedes)",
        2019: "Lewis Hamilton (Mercedes)",
        2020: "Lewis Hamilton (Mercedes)",
        2021: "Max Verstappen (Red Bull)",
        2022: "Max Verstappen (Red Bull)",
        2023: "Max Verstappen (Red Bull)",
        2024: "Max Verstappen (Red Bull)",
        2025: "TBD - Season in progress"
    }
    
    # Parse year filter if provided
    start_year = 2000
    end_year = 2025
    
    if year_filter:
        # Extract years from filter
        year_match = re.search(r'since\s+(\d{4})', year_filter.lower())
        if year_match:
            start_year = int(year_match.group(1))
        
        range_match = re.search(r'(\d{4})\s*-\s*(\d{4})', year_filter)
        if range_match:
            start_year = int(range_match.group(1))
            end_year = int(range_match.group(2))
    
    # Filter champions
    filtered = {year: champ for year, champ in champions.items() 
                if start_year <= year <= end_year}
    
    result = f"=== F1 Drivers' World Champions ({start_year}-{end_year}) ===\n\n"
    
    for year, champion in sorted(filtered.items()):
        result += f"{year}: {champion}\n"
    
    # Add summary statistics
    driver_counts = {}
    for champion_info in filtered.values():
        if "TBD" not in champion_info:
            driver = champion_info.split("(")[0].strip()
            driver_counts[driver] = driver_counts.get(driver, 0) + 1
    
    if driver_counts:
        result += f"\n=== Championship Counts ===\n"
        for driver, count in sorted(driver_counts.items(), key=lambda x: -x[1]):
            result += f"{driver}: {count} title{'s' if count > 1 else ''}\n"
    
    result += f"\nSource: Fast lookup - F1 historical records"
    
    return result


@tool
async def f1_season_race_winners(year: int = 2023) -> str:
    """
    Returns a list of ALL race winners for a specific F1 season.
    Use when user asks about: race winners, who won races, season winners, list of winners.
    
    Args:
        year: The F1 season year (default: 2023)
    
    Examples:
    - "List of all race winners in 2023"
    - "Who won the races in the 2023 season?"
    - "2023 F1 race winners"
    """
    try:
        import fastf1
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()
        
        def fetch_season_winners():
            # Get the schedule for the year
            schedule = fastf1.get_event_schedule(year)
            races = schedule[schedule['EventFormat'] != 'testing']
            
            winners = []
            for _, race in races.iterrows():
                try:
                    # Load the race session
                    session = fastf1.get_session(year, race['EventName'], 'R')
                    session.load(telemetry=False, weather=False, messages=False)
                    
                    # Get the winner (position 1)
                    results = session.results.sort_values(by='ClassifiedPosition')
                    winner_row = results.iloc[0]
                    
                    winners.append({
                        'round': race['RoundNumber'],
                        'race': race['EventName'],
                        'location': race['Location'],
                        'date': race['EventDate'].strftime('%Y-%m-%d'),
                        'winner': winner_row['FullName'],
                        'team': winner_row['TeamName']
                    })
                    logger.info(f"Fetched winner for {race['EventName']}: {winner_row['FullName']}")
                except Exception as e:
                    logger.warning(f"Could not fetch winner for {race['EventName']}: {e}")
                    continue
            
            return winners
        
        # Run the fetch operation in a thread pool to avoid blocking
        winners = await wrapper.run_sync_tool(fetch_season_winners)
        
        if not winners:
            return f"Could not fetch race winners for {year} season."
        
        # Format the output
        result = f"=== {year} F1 Season - Race Winners ===\n\n"
        for w in winners:
            result += f"Round {w['round']}: {w['race']} ({w['location']}) - {w['date']}\n"
            result += f"  Winner: {w['winner']} ({w['team']})\n\n"
        
        # Add summary statistics
        driver_wins = {}
        team_wins = {}
        for w in winners:
            driver_wins[w['winner']] = driver_wins.get(w['winner'], 0) + 1
            team_wins[w['team']] = team_wins.get(w['team'], 0) + 1
        
        result += "=== Season Summary ===\n"
        result += "Most Wins by Driver:\n"
        for driver, wins in sorted(driver_wins.items(), key=lambda x: -x[1])[:5]:
            result += f"  {driver}: {wins} win{'s' if wins > 1 else ''}\n"
        
        result += "\nMost Wins by Team:\n"
        for team, wins in sorted(team_wins.items(), key=lambda x: -x[1])[:5]:
            result += f"  {team}: {wins} win{'s' if wins > 1 else ''}\n"
        
        result += f"\nTotal races fetched: {len(winners)}"
        
        return result
        
    except Exception as e:
        logger.error(f"Season race winners fetch failed: {e}")
        return f"Error fetching season race winners: {e}"


@tool
async def f1_fastest_lap_records() -> str:
    """
    FAST lookup for F1 fastest lap records and statistics.
    Returns notable fastest lap achievements and current record holders.
    
    Examples:
    - "Who has the most fastest laps?"
    - "Fastest lap records in F1"
    - "Most fastest laps by a driver"
    """
    records = {
        "Most Fastest Laps (All-Time)": [
            ("Michael Schumacher", 77),
            ("Lewis Hamilton", 66),
            ("Kimi Räikkönen", 46),
            ("Alain Prost", 41),
            ("Sebastian Vettel", 38),
            ("Nigel Mansell", 30),
            ("Jim Clark", 28),
            ("Niki Lauda", 25),
            ("Max Verstappen", 26),
            ("Fernando Alonso", 24)
        ],
        "Active Drivers (2025)": [
            ("Lewis Hamilton", 66),
            ("Max Verstappen", 26),
            ("Fernando Alonso", 24),
            ("Sergio Perez", 11),
            ("Valtteri Bottas", 19),
            ("Daniel Ricciardo", 16)
        ],
        "Circuit Record": "Circuit-specific fastest laps change frequently with car development"
    }
    
    result = "=== F1 Fastest Lap Records ===\n\n"
    result += "MOST FASTEST LAPS (All-Time):\n"
    for driver, count in records["Most Fastest Laps (All-Time)"][:10]:
        result += f"  {driver}: {count} fastest laps\n"
    
    result += "\nACTIVE DRIVERS:\n"
    for driver, count in records["Active Drivers (2025)"][:6]:
        result += f"  {driver}: {count} fastest laps\n"
    
    result += f"\n{records['Circuit Record']}\n"
    result += "\nNote: Statistics updated through 2024 season"
    
    return result


@tool
async def f1_pole_position_records() -> str:
    """
    FAST lookup for F1 pole position records.
    Returns pole position statistics and record holders.
    
    Examples:
    - "Who has the most pole positions?"
    - "Pole position records"
    - "Hamilton pole positions"
    """
    records = {
        "Most Pole Positions (All-Time)": [
            ("Lewis Hamilton", 104),
            ("Michael Schumacher", 68),
            ("Ayrton Senna", 65),
            ("Sebastian Vettel", 57),
            ("Jim Clark", 33),
            ("Alain Prost", 33),
            ("Nigel Mansell", 32),
            ("Juan Manuel Fangio", 29),
            ("Mika Häkkinen", 26),
            ("Max Verstappen", 32)
        ],
        "Most Consecutive Poles": [
            ("Ayrton Senna", "8 (1988-1989)"),
            ("Sebastian Vettel", "7 (2011)"),
            ("Alain Prost", "6 (1993)"),
            ("Lewis Hamilton", "Multiple streaks of 5-6")
        ]
    }
    
    result = "=== F1 Pole Position Records ===\n\n"
    result += "MOST POLE POSITIONS (All-Time):\n"
    for driver, count in records["Most Pole Positions (All-Time)"][:10]:
        result += f"  {driver}: {count} poles\n"
    
    result += "\nMOST CONSECUTIVE POLES:\n"
    for driver, detail in records["Most Consecutive Poles"]:
        result += f"  {driver}: {detail}\n"
    
    result += "\nNote: Statistics updated through 2024 season"
    
    return result


@tool
async def f1_constructor_champions(year_filter: str = "") -> str:
    """
    FAST lookup for F1 Constructor Championships.
    Returns constructor/team world champions from 2000 onwards.
    
    Args:
        year_filter: Optional filter like "since 2010" or "2010-2020"
    
    Examples:
    - "List of constructor champions"
    - "Team world champions since 2010"
    - "Constructor championships by team"
    """
    champions = {
        2000: "Ferrari",
        2001: "Ferrari",
        2002: "Ferrari",
        2003: "Ferrari",
        2004: "Ferrari",
        2005: "Renault",
        2006: "Renault",
        2007: "Ferrari",
        2008: "Ferrari",
        2009: "Brawn",
        2010: "Red Bull Racing",
        2011: "Red Bull Racing",
        2012: "Red Bull Racing",
        2013: "Red Bull Racing",
        2014: "Mercedes",
        2015: "Mercedes",
        2016: "Mercedes",
        2017: "Mercedes",
        2018: "Mercedes",
        2019: "Mercedes",
        2020: "Mercedes",
        2021: "Mercedes",
        2022: "Red Bull Racing",
        2023: "Red Bull Racing",
        2024: "Red Bull Racing",
        2025: "TBD - Season in progress"
    }
    
    # Parse year filter
    start_year = 2000
    end_year = 2025
    
    if year_filter:
        year_match = re.search(r'since\s+(\d{4})', year_filter.lower())
        if year_match:
            start_year = int(year_match.group(1))
        
        range_match = re.search(r'(\d{4})\s*-\s*(\d{4})', year_filter)
        if range_match:
            start_year = int(range_match.group(1))
            end_year = int(range_match.group(2))
    
    # Filter champions
    filtered = {year: champ for year, champ in champions.items() 
                if start_year <= year <= end_year}
    
    result = f"=== F1 Constructor Champions ({start_year}-{end_year}) ===\n\n"
    
    for year, champion in sorted(filtered.items()):
        result += f"{year}: {champion}\n"
    
    # Add summary statistics
    team_counts = {}
    for champion_name in filtered.values():
        if "TBD" not in champion_name:
            team_counts[champion_name] = team_counts.get(champion_name, 0) + 1
    
    if team_counts:
        result += f"\n=== Championship Counts ({start_year}-{end_year}) ===\n"
        for team, count in sorted(team_counts.items(), key=lambda x: -x[1]):
            result += f"{team}: {count} title{'s' if count > 1 else ''}\n"
    
    result += "\nSource: F1 historical records"
    
    return result


def get_reference_tools() -> list:
    """
    Get all reference tools.
    
    Returns:
        List of reference tool functions
    """
    return [
        f1_champions_quick_lookup,  # Fast lookup first
        f1_season_race_winners,  # Season race winners
        f1_fastest_lap_records,  # Fastest lap records
        f1_pole_position_records,  # Pole position records
        f1_constructor_champions,  # Constructor champions
        f1_wikipedia_lookup  # Wikipedia fallback for other queries
    ]

"""
Reference Tools
F1 historical data, lists, and reference information from Wikipedia
"""
import logging
import re
import os
import json
import time
import requests
import io
import pandas as pd
from functools import lru_cache
from datetime import datetime
import wikipedia
from fastf1.ergast import Ergast
from langchain_core.tools import tool

logger = logging.getLogger("ReferenceTools")
ergast = Ergast()


@lru_cache(maxsize=100)
def _cached_wikipedia_search(query: str, results: int = 5) -> tuple:
    """Cached Wikipedia search to avoid redundant API calls"""
    return tuple(wikipedia.search(query, results=results))


@lru_cache(maxsize=50)
def _cached_wikipedia_page(title: str):
    """Cached Wikipedia page fetch to avoid redundant API calls"""
    return wikipedia.page(title, auto_suggest=False)


@lru_cache(maxsize=50)
def _get_cached_driver_standings(year: int):
    """Cached Ergast driver standings"""
    return ergast.get_driver_standings(season=year)


@lru_cache(maxsize=50)
def _get_cached_constructor_standings(year: int):
    """Cached Ergast constructor standings"""
    return ergast.get_constructor_standings(season=year)


@lru_cache(maxsize=50)
def _get_cached_race_results(year: int):
    """Cached Ergast race results"""
    return ergast.get_race_results(season=year)


@lru_cache(maxsize=20)
def _get_cached_qualifying_results(year: int):
    """Cached Ergast qualifying results"""
    return ergast.get_qualifying_results(season=year)


@lru_cache(maxsize=100)
def _get_cached_driver_info(driver_id: str):
    """Cached Ergast driver info"""
    return ergast.get_driver_info(driver=driver_id)


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
    - Statistical records like "who has the most wins/poles" (use f1_all_time_records)
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
    FAST lookup for F1 World Champions using real-time API data.
    Provides accurate historical data from 1950 to the present.
    
    Args:
        year_filter: Optional filter like "since 2000" or "2010-2020"
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        # Parse year filter
        current_year = datetime.now().year
        start_year, end_year = 1950, current_year
        
        if year_filter:
            years = re.findall(r'\b(19\d{2}|20\d{2})\b', str(year_filter))
            if len(years) >= 2:
                sorted_years = sorted([int(y) for y in years])
                start_year, end_year = sorted_years[0], sorted_years[-1]
            elif len(years) == 1:
                year = int(years[0])
                filter_lower = str(year_filter).lower()
                if any(kw in filter_lower for kw in ["since", "after", "from"]):
                    start_year = year
                elif any(kw in filter_lower for kw in ["until", "before", "to"]):
                    end_year = year
                else:
                    start_year = end_year = year

        def fetch_champions_wiki():
            url = "https://en.wikipedia.org/wiki/List_of_Formula_One_World_Drivers%27_Champions"
            headers = {'User-Agent': 'F1Agent/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            tables = pd.read_html(io.StringIO(response.text))
            
            main_table = None
            for t in tables:
                cols_str = str(t.columns).lower()
                if 'season' in cols_str and 'driver' in cols_str:
                    main_table = t
                    break
            
            if main_table is None:
                raise ValueError("Could not find champions table on Wikipedia")

            df = main_table.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(dict.fromkeys(col)).strip() for col in df.columns.values]
            
            # Fuzzy column identification
            cols = list(df.columns)
            def find_col(keywords, exclude=None):
                for c in cols:
                    if any(k in c.lower() for k in keywords):
                        if exclude and any(e in c.lower() for e in exclude): continue
                        return c
                return None

            col_map = {
                'Season': find_col(['season']),
                'Driver': find_col(['driver']),
                'Constructor': find_col(['chassis', 'constructor', 'team']),
                'Points': find_col(['points']),
                'Margin': find_col(['margin'])
            }
            
            if not col_map['Season']: raise ValueError("Missing Season column")
            
            df = df[df[col_map['Season']].astype(str).str.contains(r'\d{4}')].copy()
            df['Year'] = df[col_map['Season']].astype(str).str.extract(r'(\d{4})').astype(int)
            
            filtered = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)].copy()
            
            res_list = []
            for _, row in filtered.iterrows():
                res_list.append({
                    "Year": int(row['Year']),
                    "Champion": str(row[col_map['Driver']]).replace(r'\[.*\]', '').strip() if col_map['Driver'] else "N/A",
                    "Team": str(row[col_map['Constructor']]).replace(r'\[.*\]', '').strip() if col_map['Constructor'] else "N/A",
                    "Points": row.get(col_map['Points'], 'N/A') if col_map['Points'] else "N/A",
                    "Margin": row.get(col_map['Margin'], 'N/A') if col_map['Margin'] else "N/A"
                })
            return res_list

        champions_list = await wrapper.run_sync_tool(fetch_champions_wiki)
        
        if not champions_list:
            return f"No champion data found for the period {start_year}-{end_year}."

        df = pd.DataFrame(champions_list)
        return f"### 🏆 F1 World Drivers' Champions ({start_year}-{end_year})\n\n" + df.to_markdown(index=False)
    except Exception as e:
        logger.error(f"Champions lookup failed: {e}")
        return f"Error fetching champions: {e}"


@tool
async def f1_season_race_winners(year: int = 2024) -> str:
    """
    Returns a list of ALL race winners for a specific F1 season using API data.
    Faster and more lightweight than full session loads.
    
    Args:
        year: The F1 season year (default: 2024)
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def fetch_winners_wiki():
            url = f"https://en.wikipedia.org/wiki/{year}_Formula_One_World_Championship"
            headers = {'User-Agent': 'F1Agent/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            tables = pd.read_html(io.StringIO(response.text))
            
            results_table = None
            for t in tables:
                cols_str = str(t.columns).lower()
                if 'grand prix' in cols_str and any(kw in cols_str for kw in ['winning driver', 'winner']):
                    results_table = t
                    break
            
            if results_table is None:
                return []

            df = results_table.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(dict.fromkeys(col)).strip() for col in df.columns.values]
            
            # Fuzzy column identification
            cols = list(df.columns)
            def find_col(keywords, exclude=None):
                for c in cols:
                    if any(k in c.lower() for k in keywords):
                        if exclude and any(e in c.lower() for e in exclude): continue
                        return c
                return None

            col_map = {
                'Rd': find_col(['round', 'no.']),
                'Grand Prix': find_col(['grand prix']),
                'Winner': find_col(['winner', 'winning driver']),
                'Team': find_col(['constructor', 'team']),
                'Pole': find_col(['pole position', 'pole'])
            }
            
            summary = []
            # Filter rows that look like race data (usually first col has a number)
            # Some tables have a nested round structure, we just need the rows
            valid_rows = df[df.iloc[:, 0].astype(str).str.contains(r'\d+')].copy()
            
            for _, row in valid_rows.iterrows():
                try:
                    rd = row[col_map['Rd']] if col_map['Rd'] else "N/A"
                    gp = row[col_map['Grand Prix']] if col_map['Grand Prix'] else "N/A"
                    winner = row[col_map['Winner']] if col_map['Winner'] else "N/A"
                    team = row[col_map['Team']] if col_map['Team'] else "N/A"
                    pole = row[col_map['Pole']] if col_map['Pole'] else "N/A"
                    
                    winner = str(winner).replace(r'\[.*\]', '').strip()
                    gp = str(gp).replace(r'\[.*\]', '').strip()
                    team = str(team).replace(r'\[.*\]', '').strip()
                    pole = str(pole).replace(r'\[.*\]', '').strip()
                    
                    if winner.lower() in ['nan', 'none', '']: continue
                    
                    summary.append({
                        "Rd": rd,
                        "🏁 Grand Prix": gp,
                        "🏆 Winner": winner,
                        "🏎️ Team": team,
                        "🅿️ Pole": pole
                    })
                except: continue
            return summary

        winners = await wrapper.run_sync_tool(fetch_winners_wiki)
        
        if not winners:
            # Final fallback to Ergast only if Wikipedia fails
            def fetch_ergast_fallback():
                try:
                    results = _get_cached_race_results(year)
                    summary = []
                    for i, race_desc in results.description.iterrows():
                        try:
                            race_results = results.content[i]
                            if not race_results.empty:
                                winner = race_results.iloc[0]
                                summary.append({
                                    "Rd": race_desc['round'],
                                    "🏁 Grand Prix": race_desc['raceName'],
                                    "🏆 Winner": f"{winner['givenName']} {winner['familyName']}",
                                    "🏎️ Team": winner['constructorName'],
                                    "🅿️ Pole": "N/A"
                                })
                        except: continue
                    return summary
                except: return []
            winners = await wrapper.run_sync_tool(fetch_ergast_fallback)

        if not winners:
            return f"No race results found for the {year} season."
            
        return f"## 🏎️ {year} F1 Season Overview\n\n" + pd.DataFrame(winners).to_markdown(index=False)
    except Exception as e:
        logger.error(f"Season winners fetch failed: {e}")
        return f"Error: {e}"


@tool
async def f1_driver_career_summary(driver_query: str) -> str:
    """
    Fetches detailed career statistics for any F1 driver (past or present).
    Includes total wins, poles, podiums, and championships.
    
    Args:
        driver_query: Driver name (e.g., 'Senna', 'Hamilton', 'Schumacher')
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def fetch_career():
            # First, find the driver ID
            driver_info = ergast.get_driver_info(driver=driver_query)
            logger.info(f"Driver info for '{driver_query}': empty={driver_info.empty}")
            if driver_info.empty:
                return None
            
            driver = driver_info.iloc[0]
            d_id = driver['driverId']
            logger.info(f"Using driver ID: {d_id}")
            
            # Fetch full history with Multi-page support (Ergast limit is usually 30-100)
            def fetch_all(method, **kwargs):
                all_content = []
                offset = 0
                limit = 100
                while True:
                    res = method(limit=limit, offset=offset, **kwargs)
                    if not hasattr(res, 'content') or not res.content:
                        break
                    all_content.extend(res.content)
                    if len(all_content) >= res.total_results:
                        break
                    offset += limit
                return all_content

            results_content = fetch_all(ergast.get_race_results, driver=d_id)
            qualy_content = fetch_all(ergast.get_qualifying_results, driver=d_id)
            
            # Aggregate stats
            wins, podiums = 0, 0
            for r in results_content:
                if not r.empty:
                    race_pos = pd.to_numeric(r['position'], errors='coerce')
                    wins += (race_pos == 1).sum()
                    podiums += (race_pos <= 3).sum()
            
            poles = 0
            for q in qualy_content:
                if not q.empty:
                    q_pos = pd.to_numeric(q['position'], errors='coerce')
                    poles += (q_pos == 1).sum()
            
            # Championships - more efficient lookup using unique seasons from results
            titles = 0
            seasons = set()
            for r in results_content:
                if 'season' in r.columns:
                    seasons.update(r['season'].unique())
            
            for s in sorted(seasons, reverse=True):
                try:
                    s_standings = _get_cached_driver_standings(int(s))
                    if hasattr(s_standings, 'content') and s_standings.content:
                        top = s_standings.content[0].iloc[0]
                        if top['driverId'] == d_id:
                            titles += 1
                except: continue
            
            return {
                "name": f"{driver['givenName']} {driver['familyName']}",
                "nationality": driver['driverNationality'],
                "dob": driver['dateOfBirth'],
                "titles": titles,
                "wins": int(wins),
                "poles": int(poles),
                "podiums": int(podiums),
                "entries": sum(len(r) for r in results_content),
                "url": driver['driverUrl']
            }
            logger.info(f"Career summary result: {res_data['name']}, {res_data['titles']} titles")
            return res_data

        stats = await wrapper.run_sync_tool(fetch_career)
        
        if not stats:
            return f"Could not find career data for driver: {driver_query}"
            
        res = f"## 🏁 Driver Career Profile: {stats['name']}\n\n"
        res += f"- **Nationality**: {stats['nationality']}\n"
        res += f"- **Born**: {stats['dob']}\n\n"
        
        res += "| Category | Total |\n"
        res += "| :--- | :--- |\n"
        res += f"| 🏆 Championships | **{stats['titles']}** |\n"
        res += f"| 🥇 Race Wins | **{stats['wins']}** |\n"
        res += f"| 🅿️ Pole Positions | **{stats['poles']}** |\n"
        res += f"| 🥉 Podiums | **{stats['podiums']}** |\n"
        res += f"| 🚩 Race Starts | **{stats['entries']}** |\n\n"
        
        res += f"[Full Biography]({stats['url']})"
        return res
    except Exception as e:
        logger.error(f"Career summary failed: {e}")
        return f"Error: {e}"


@tool
async def f1_all_time_records(category: str = "wins") -> str:
    """
    Returns THE most accurate all-time F1 records (Top 10) for various categories.
    ALWAYS use this tool instead of Wikipedia for queries like:
    - "Who has the most wins/poles/podiums in F1 history?"
    - "Top 10 winners list"
    - "Who is the most successful F1 driver?"
    
    Args:
        category: One of "wins", "poles", "titles", "podiums"
    """
    cat = category.lower().strip()
    mapping = {
        "wins": {"search": ["wins", "starts"], "primary": "wins", "ham_val": 100},
        "poles": {"search": ["pole", "entries"], "primary": "pole", "ham_val": 100},
        "podiums": {"search": ["podiums", "starts"], "primary": "podium", "ham_val": 150},
        "titles": {"search": ["titles", "seasons"], "primary": "titles", "schu_val": 7}
    }
    
    if cat not in mapping:
        return f"Error: Category '{category}' not supported. Use 'wins', 'poles', 'titles', or 'podiums'."

    cache_dir = "cache"
    cache_file = os.path.join(cache_dir, "f1_records_v6.json")
    os.makedirs(cache_dir, exist_ok=True)
    
    if os.path.exists(cache_file):
        try:
            import json, time
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            if time.time() - cached_data.get("timestamp", 0) < 86400:
                if cat in cached_data:
                    return cached_data[cat]
        except:
            pass

    url = "https://en.wikipedia.org/wiki/List_of_Formula_One_driver_records"
    headers = {"User-Agent": "F1Agent/1.0 (Mozilla/5.0)"}
    
    try:
        import requests, io, re, json, time
        import pandas as pd
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()
        
        def scrape_logic():
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return pd.read_html(io.StringIO(response.text))

        tables = await wrapper.run_sync_tool(scrape_logic)
        
        results = {}
        for c_key, c_meta in mapping.items():
            primary_key = c_meta["primary"]
            found_table = None
            
            for table in tables:
                if len(table.columns) < 2: continue
                cols_str = " ".join([str(c).lower() for c in table.columns])
                
                if "driver" in cols_str and any(s in cols_str for s in c_meta["search"]):
                    txt = table.to_string()
                    
                    if c_key == "titles":
                        if "Schumacher" in txt and str(c_meta["schu_val"]) in txt:
                            found_table = table
                            break
                    else:
                        if "percentage" in cols_str and "Hamilton" in txt:
                            try:
                                p_cols = [c for c in table.columns if primary_key in str(c).lower() and "percentage" not in str(c).lower()]
                                if not p_cols: continue
                                v_col = p_cols[0]
                                
                                d_col_idx = 1 if "driver" in str(table.columns[1]).lower() else 0
                                ham_row = table[table.iloc[:, d_col_idx].astype(str).str.contains("Hamilton", na=False)]
                                if not ham_row.empty:
                                    v_str = re.sub(r"\[.*\]", "", str(ham_row.iloc[0][v_col]))
                                    val = int(re.sub(r"\D", "", v_str))
                                    if val >= c_meta.get("ham_val", 0):
                                        found_table = table
                                        break
                            except: continue
            
            if found_table is not None:
                d_col = [c for c in found_table.columns if "driver" in str(c).lower()][0]
                p_cols = [c for c in found_table.columns if primary_key in str(c).lower() and "percentage" not in str(c).lower() and "seasons" not in str(c).lower()]
                v_col = p_cols[0] if p_cols else [c for c in found_table.columns if any(s in str(c).lower() for s in c_meta["search"]) and "percentage" not in str(c).lower()][0]
                
                top_10 = found_table[[d_col, v_col]].head(10).copy()
                top_10[v_col] = top_10[v_col].astype(str).str.replace(r"\[.*\]", "", regex=True)
                top_10[d_col] = top_10[d_col].astype(str).str.replace(r"\[.*\]", "", regex=True)
                top_10[d_col] = top_10[d_col].str.strip()
                
                md = f"### 🏆 All-Time F1 Records: {c_key.upper()}\n\n"

                md += top_10.to_markdown(index=False)
                results[c_key] = md
        
        results["timestamp"] = time.time()
        with open(cache_file, "w") as f:
            json.dump(results, f)
            
        return results.get(cat, f"Error: Could not parse {cat} table from Wikipedia. Layout might have changed.")
        
    except Exception as e:
        import traceback
        return f"Error fetching dynamic records: {e}."
@tool
async def f1_reliability_analysis(year: int, driver_query: str = "") -> str:
    """
    Analyzes car reliability and race finishing statuses (DNFs, Mechanicals).
    
    Args:
        year: Season year
        driver_query: Optional driver name to focus on
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def analyze():
            params = {"season": year}
            if driver_query:
                # Find driver ID first
                d_info = ergast.get_driver_info(driver=driver_query)
                if d_info.content:
                    params["driver"] = d_info.content[0].iloc[0]['driverId']
            
            results = ergast.get_race_results(**params)
            if results.content is None or len(results.content) == 0:
                return None
            
            # Flatten all results
            all_results = pd.concat(results.content)
            
            # Analyze status codes
            status_counts = all_results['status'].value_counts()
            
            # Filter for non-Finished statuses
            dnfs = status_counts[status_counts.index != 'Finished']
            # Also exclude '+1 Lap', '+2 Laps' etc
            dnfs = dnfs[~dnfs.index.str.contains(r'\+\d+\s+Lap')]
            
            return {
                "total_starts": len(all_results),
                "finished": status_counts.get('Finished', 0),
                "dnf_data": dnfs.to_dict()
            }

        data = await wrapper.run_sync_tool(analyze)
        
        if not data:
            return f"No reliability data found for {year}."
            
        res = f"## 🛠️ Reliability Analysis: {year} Season\n\n"
        res += f"- **Total Race Starts**: {data['total_starts']}\n"
        res += f"- **Classified Finishes**: {data['finished']}\n"
        res += f"- **Reliability Rate**: {(data['finished']/data['total_starts'])*100:.1f}%\n\n"
        
        if data['dnf_data']:
            res += "### ⛔ DNF Reasons (Mechanical & Incidents)\n\n"
            dnf_df = pd.DataFrame(list(data['dnf_data'].items()), columns=["Status", "Count"])
            res += dnf_df.to_markdown(index=False)
        else:
            res += "Perfect reliability! No DNFs recorded."
            
        return res
    except Exception as e:
        logger.error(f"Reliability analysis failed: {e}")
        return f"Error: {e}"


@tool
async def f1_head_to_head(driver1: str, driver2: str, year: int = 2024) -> str:
    """
    Head-to-head comparison between ANY two F1 drivers in a season (Rivals or Teammates).
    Compares race results, finish counts, and head-to-head wins.
    
    Args:
        driver1: Name of first driver (e.g. 'Norris', 'Verstappen')
        driver2: Name of second driver
        year: Season year (default: 2024)
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def compare():
            # Resolve driver names to IDs if needed
            all_drivers = ergast.get_driver_info(season=year)
            
            def get_id(query):
                if not all_drivers.empty:
                    q = query.lower()
                    for _, d in all_drivers.iterrows():
                        did = d['driverId'].lower()
                        dfam = d['familyName'].lower()
                        dcode = str(d.get('driverCode', '')).lower()
                        # Match if exact or if our known identifiers are in the query (e.g. 'Hamilton' in 'Lewis Hamilton')
                        if (q == did or q == dfam or q == dcode or 
                            dfam in q or did in q):
                            return d['driverId']
                
                # Final fallback
                try:
                    info = ergast.get_driver_info(driver=query)
                    return info.iloc[0]['driverId'] if not info.empty else query
                except:
                    return query

            id1 = get_id(driver1)
            id2 = get_id(driver2)
            
            # Get data for both
            d1_results = ergast.get_race_results(season=year, driver=id1)
            d2_results = ergast.get_race_results(season=year, driver=id2)
            
            if not d1_results.content or not d2_results.content:
                return f"Could not find sufficient data for both {driver1} and {driver2} in {year}."
            
            # Map round -> position
            d1_data = {row['round']: d1_results.content[i].iloc[0]['position'] 
                       for i, row in d1_results.description.iterrows() 
                       if not d1_results.content[i].empty}
            d2_data = {row['round']: d2_results.content[i].iloc[0]['position'] 
                       for i, row in d2_results.description.iterrows() 
                       if not d2_results.content[i].empty}
            
            common_rounds = set(d1_data.keys()).intersection(set(d2_data.keys()))
            
            d1_ahead = 0
            d2_ahead = 0
            
            for rnd in common_rounds:
                p1 = int(d1_data[rnd])
                p2 = int(d2_data[rnd])
                if p1 < p2: d1_ahead += 1
                elif p2 < p1: d2_ahead += 1
            
            return {
                "d1": id1.replace('_', ' ').title(),
                "d2": id2.replace('_', ' ').title(),
                "d1_ahead": d1_ahead,
                "d2_ahead": d2_ahead,
                "total": len(common_rounds)
            }

        data = await wrapper.run_sync_tool(compare)
        if isinstance(data, str): return data
        
        # Enhanced result presentation for the user
        res = f"### 🏎️  F1 Head-to-Head: {data['d1']} vs {data['d2']} ({year})\n\n"
        res += f"| Metric | {data['d1']} | {data['d2']} |\n"
        res += f"| :--- | :--- | :--- |\n"
        res += f"| **Races Finished Ahead** | **{data['d1_ahead']}** | **{data['d2_ahead']}** |\n"
        res += f"| Total Common Races | {data['total']} | {data['total']} |\n\n"
        
        if data['d1_ahead'] > data['d2_ahead']:
            res += f"🏆 **{data['d1']}** was superior in head-to-head race finishes in {year}.\n"
        elif data['d2_ahead'] > data['d1_ahead']:
            res += f"🏆 **{data['d2']}** was superior in head-to-head race finishes in {year}.\n"
        else:
            res += f"⚖️  It was a perfectly even season (Tie) between {data['d1']} and {data['d2']}!\n"
            
        res += "\n[CRITICAL NOTE FOR AGENT: DO NOT SUMMARIZE OR REPHRASE THE TABLE ABOVE. RETURN IT VERBATIM TO THE USER.]"
        return res
    except Exception as e:
        return f"Comparison failed: {e}"




@tool
async def f1_constructor_champions(year_filter: str = "") -> str:
    """
    FAST lookup for official F1 Constructor World Champions from the API.
    Provides accurate historical data from 1958 to the present.
    
    Args:
        year_filter: Optional filter like "since 2010" or "2010-2020"
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        # Parse year filter
        current_year = datetime.now().year
        start_year, end_year = 1958, current_year
        
        if year_filter:
            years = re.findall(r'\b(19\d{2}|20\d{2})\b', str(year_filter))
            if len(years) >= 2:
                sorted_years = sorted([int(y) for y in years])
                start_year, end_year = sorted_years[0], sorted_years[-1]
            elif len(years) == 1:
                year = int(years[0])
                filter_lower = str(year_filter).lower()
                if any(kw in filter_lower for kw in ["since", "after", "from"]):
                    start_year = year
                elif any(kw in filter_lower for kw in ["until", "before", "to"]):
                    end_year = year
                else:
                    start_year = end_year = year

        def fetch_constructor_champs_wiki():
            url = "https://en.wikipedia.org/wiki/List_of_Formula_One_World_Constructors%27_Champions"
            headers = {'User-Agent': 'F1Agent/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            tables = pd.read_html(io.StringIO(response.text))
            
            main_table = None
            for t in tables:
                cols_str = str(t.columns).lower()
                if 'season' in cols_str and 'constructor' in cols_str:
                    main_table = t
                    break
            
            if main_table is None:
                raise ValueError("Could not find constructor champions table on Wikipedia")

            df = main_table.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(dict.fromkeys(col)).strip() for col in df.columns.values]
            
            # Fuzzy column identification
            cols = list(df.columns)
            def find_col(keywords, exclude=None):
                for c in cols:
                    if any(k in c.lower() for k in keywords):
                        if exclude and any(e in c.lower() for e in exclude): continue
                        return c
                return None

            col_map = {
                'Season': find_col(['season']),
                'Constructor': find_col(['chassis', 'constructor', 'team']),
                'Engine': find_col(['engine']),
                'Points': find_col(['points']),
                'Wins': find_col(['wins'])
            }
            
            if not col_map['Season']: raise ValueError("Missing Season column")
            
            df = df[df[col_map['Season']].astype(str).str.contains(r'\d{4}')].copy()
            df['Year'] = df[col_map['Season']].astype(str).str.extract(r'(\d{4})').astype(int)
            
            filtered = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)].copy()
            
            res_list = []
            for _, row in filtered.iterrows():
                res_list.append({
                    "Year": int(row['Year']),
                    "Constructor": str(row[col_map['Constructor']]).replace(r'\[.*\]', '').strip() if col_map['Constructor'] else "N/A",
                    "Engine": str(row.get(col_map['Engine'], 'N/A')).replace(r'\[.*\]', '').strip() if col_map['Engine'] else "N/A",
                    "Points": row.get(col_map['Points'], 'N/A') if col_map['Points'] else "N/A",
                    "Wins": row.get(col_map['Wins'], 'N/A') if col_map['Wins'] else "N/A"
                })
            return res_list

        champions_list = await wrapper.run_sync_tool(fetch_constructor_champs_wiki)
        
        if not champions_list:
            return f"No constructor champion data found for the period {start_year}-{end_year}."

        df = pd.DataFrame(champions_list)
        return f"### 🏆 F1 World Constructors' Champions ({start_year}-{end_year})\n\n" + df.to_markdown(index=False)
    except Exception as e:
        logger.error(f"Constructor champions lookup failed: {e}")
        return f"Error: {e}"


@tool
async def f1_circuit_guide(circuit_query: str = "") -> str:
    """
    Provides technical and historical details about F1 circuits/tracks.
    Includes location, track length, and historical significance.
    
    Args:
        circuit_query: Circuit name or ID (e.g., 'Monaco', 'Silverstone', 'spa')
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def fetch_circuit():
            # If no query, list all circuits for current year
            if not circuit_query:
                # get_circuits returns a SimpleResponse (DataFrame)
                circuits = ergast.get_circuits(season=datetime.now().year)
                return circuits if not circuits.empty else None
            
            # Try to find specific circuit by getting all and filtering
            # Ergast.get_circuits does NOT support circuit= keyword in this version
            all_circs = ergast.get_circuits(limit=1000)
            
            # Filter by ID or Name
            q = circuit_query.lower()
            mask = (
                all_circs['circuitId'].str.lower().str.contains(q) | 
                all_circs['circuitName'].str.lower().str.contains(q)
            )
            circ = all_circs[mask]
            
            if circ.empty:
                # Try season search if query looks like a year
                if circuit_query.isdigit():
                    return ergast.get_circuits(season=int(circuit_query))
                return None
                
            return circ

        data = await wrapper.run_sync_tool(fetch_circuit)
        
        if data is None or data.empty:
            return f"No circuit data found for: {circuit_query}"
            
        if len(data) > 1 and not circuit_query:
            # Table of circuits
            df = data[['circuitId', 'circuitName', 'locality', 'country']]
            return "## 🏁 F1 Circuits\n\n" + df.to_markdown(index=False)
            
        circ = data.iloc[0]
        res = f"## 🗺️ Circuit Profile: {circ['circuitName']}\n\n"
        res += f"- **Location**: {circ.get('locality', 'N/A')}, {circ.get('country', 'N/A')}\n"
        res += f"- **Track ID**: `{circ['circuitId']}`\n"
        res += f"- **Coordinates**: Lat {circ.get('lat', 'N/A')}, Long {circ.get('long', 'N/A')}\n\n"
        res += f"[More Information]({circ.get('url', '#')})"
        return res
    except Exception as e:
        logger.error(f"Circuit guide failed: {e}")
        return f"Error: {e}"


@tool
async def f1_constructor_career_summary(constructor_query: str) -> str:
    """
    Comprehensive career summary for an F1 Constructor (Team).
    Includes championships, wins, and historical results.
    
    Args:
        constructor_query: Team name or ID (e.g., 'Ferrari', 'McLaren', 'red_bull')
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()

        def fetch_constructor():
            # Find constructor ID
            # get_constructor_info returns a SimpleResponse (DataFrame)
            c_info = ergast.get_constructor_info(constructor=constructor_query)
            logger.info(f"Constructor info for '{constructor_query}': empty={c_info.empty}")
            if c_info.empty:
                return None
            
            team = c_info.iloc[0]
            c_id = team['constructorId']
            logger.info(f"Using constructor ID: {c_id}")
            
            # Multi-page fetch
            def fetch_all(method, **kwargs):
                all_content = []
                offset, limit = 0, 100
                while True:
                    res = method(limit=limit, offset=offset, **kwargs)
                    if not hasattr(res, 'content') or not res.content: break
                    all_content.extend(res.content)
                    if len(all_content) >= res.total_results: break
                    offset += limit
                return all_content

            results_content = fetch_all(ergast.get_race_results, constructor=c_id)
            
            # Titles
            titles = 0
            seasons = set()
            for r in results_content:
                if 'season' in r.columns:
                    seasons.update(r['season'].unique())
            
            for s in sorted(seasons, reverse=True):
                try:
                    s_standings = _get_cached_constructor_standings(int(s))
                    if hasattr(s_standings, 'content') and s_standings.content:
                        top = s_standings.content[0].iloc[0]
                        if top['constructorId'] == c_id:
                            titles += 1
                except: continue
            
            wins, podiums = 0, 0
            for r in results_content:
                if not r.empty:
                    race_pos = pd.to_numeric(r['position'], errors='coerce')
                    wins += (race_pos == 1).sum()
                    podiums += (race_pos <= 3).sum()
            
            return {
                "name": team['constructorName'],
                "nationality": team['constructorNationality'],
                "titles": titles,
                "wins": wins,
                "podiums": podiums,
                "url": team['url']
            }

        stats = await wrapper.run_sync_tool(fetch_constructor)
        
        if not stats:
            return f"Could not find career data for constructor: {constructor_query}"
            
        res = f"## 🏎️ Constructor Profile: {stats['name']}\n\n"
        res += f"- **Nationality**: {stats['nationality']}\n\n"
        
        res += "| Achievement | Total |\n"
        res += "| :--- | :--- |\n"
        res += f"| 🏆 Championships | **{stats['titles']}** |\n"
        res += f"| 🥇 Race Wins | **{stats['wins']}** |\n"
        res += f"| 🥉 Podiums | **{stats['podiums']}** |\n\n"
        
        res += f"[History & Wiki]({stats['url']})"
        return res
    except Exception as e:
        logger.error(f"Constructor summary failed: {e}")
        return f"Error: {e}"


@tool
async def f1_standings(year: int = 2026) -> str:
    """
    Returns the CURRENT F1 World Championship standings for drivers and constructors.
    Use when user asks for: "current standings", "championship points", "who is leading",
    "driver standings", "team standings", "points table".
    
    Args:
        year: The F1 season year (default: 2026)
    """
    try:
        from utils.async_tools import get_async_wrapper
        wrapper = get_async_wrapper()
        
        def fetch_standings():
            # Get driver standings
            d_standings = _get_cached_driver_standings(year)
            # Get constructor standings
            c_standings = _get_cached_constructor_standings(year)
            
            output = f"## 🏆 {year} F1 Championship Standings\n\n"
            
            if hasattr(d_standings, 'content') and d_standings.content:
                df_d = d_standings.content[0]
                output += "### 👤 Driver Standings\n\n"
                # Select key columns
                cols = ['position', 'points', 'wins', 'givenName', 'familyName', 'constructorName']
                df_d_display = df_d.copy()
                df_d_display['Driver'] = df_d_display['givenName'] + " " + df_d_display['familyName']
                df_d_display = df_d_display[['position', 'points', 'wins', 'Driver', 'constructorName']]
                df_d_display.columns = ['Pos', 'Pts', 'Wins', 'Driver', 'Team']
                output += df_d_display.head(20).to_markdown(index=False) + "\n\n"
            
            if hasattr(c_standings, 'content') and c_standings.content:
                df_c = c_standings.content[0]
                output += "### 🏎️ Constructor Standings\n\n"
                df_c_display = df_c[['position', 'points', 'wins', 'name']]
                df_c_display.columns = ['Pos', 'Pts', 'Wins', 'Team']
                output += df_c_display.to_markdown(index=False) + "\n"
                
            return output

        return await wrapper.run_sync_tool(fetch_standings)
    except Exception as e:
        logger.error(f"Standings fetch failed: {e}")
        return f"Error fetching standings: {e}"


def get_reference_tools() -> list:
    """
    Returns a list of all historical reference and lookup tools.
    Includes the enhanced Ergast-based dynamic tools.
    """
    return [
        f1_standings,
        f1_champions_quick_lookup,
        f1_season_race_winners,
        f1_driver_career_summary,
        f1_constructor_career_summary,
        f1_all_time_records,
        f1_constructor_champions,
        f1_circuit_guide,
        f1_reliability_analysis,
        f1_head_to_head,
        f1_wikipedia_lookup,
        f1_diagnostics
    ]
@tool
async def f1_diagnostics() -> str:
    """
    Returns system diagnostic information, including FastF1 cache location, 
    versions, and environment variables. Use this when the agent seems to fail 
    to load data that should be available.
    """
    try:
        import fastf1
        import os
        import platform
        import sys
        from config.settings import TODAY, DATA_DEFAULT_YEAR
        
        cache_dir = "Not configured"
        try:
            # Check where FastF1 thinks the cache is
            # In older versions it's fastf1.Cache.cache_dir
            # In newer ones it might be different, but let's check common spots
            cache_dir = getattr(fastf1.Cache, 'cache_dir', 'Unknown (Old/New FastF1 version)')
        except:
            pass
            
        real_cache_path = os.path.abspath('cache')
        cache_exists = os.path.exists(real_cache_path)
        
        diag = "### 🛠️ F1 Agent Diagnostics\n\n"
        diag += f"- **Platform**: {platform.platform()}\n"
        diag += f"- **Python**: {sys.version.split()[0]}\n"
        diag += f"- **FastF1 Version**: {fastf1.__version__}\n"
        diag += f"- **Current Directory**: {os.getcwd()}\n"
        diag += f"- **Configured TODAY**: {TODAY}\n"
        diag += f"- **Configured Cache Path (Resolved)**: {real_cache_path}\n"
        diag += f"- **Cache Directory Exists**: {cache_exists}\n"
        
        if cache_exists:
            years = [d for d in os.listdir(real_cache_path) if os.path.isdir(os.path.join(real_cache_path, d)) and d.isdigit()]
            diag += f"- **Years in Cache**: {sorted(years)}\n"
        
        return diag
    except Exception as e:
        return f"Diagnostics failed: {e}"

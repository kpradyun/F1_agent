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
from langchain_core.tools import tool

from config.settings import PLOTS_DIR

# Wikipedia blocks the default library UA; set a descriptive one
wikipedia.set_user_agent("F1Agent/1.0 (educational F1 data tool; python-requests)")

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
async def f1_season_race_winners(year: int = 0) -> str:
    """
    Returns a list of ALL race winners for a specific F1 season.
    Data comes from the Jolpica REST API — real-time, no scraping.

    Args:
        year: The F1 season year (0 = current year)
    """
    from utils.async_tools import get_async_wrapper
    from datetime import datetime as _dt
    from core.api_client import get_jolpica_client

    year = year or _dt.now().year
    wrapper = get_async_wrapper()

    try:
        races = await wrapper.run_sync_tool(
            lambda: get_jolpica_client().get_race_winners(year)
        )
    except Exception as e:
        logger.error(f"Jolpica race winners fetch failed: {e}")
        return f"Could not fetch {year} race winners: {e}"

    if not races:
        return f"No race results found for the {year} season yet."

    rows = [
        {
            "Rd": r["round"],
            "Grand Prix": r["race_name"],
            "Date": r["date"],
            "Winner": r["winner"],
            "Team": r["team"],
        }
        for r in races
    ]
    return f"## 🏎️ {year} F1 Season Race Winners\n*(Source: api.jolpi.ca — live data)*\n\n" + pd.DataFrame(rows).to_markdown(index=False)


@tool
async def f1_driver_career_summary(driver_query: str) -> str:
    """
    Fetches career statistics for any F1 driver (past or present) from Jolpica.
    Includes total wins, poles, podiums, race starts and championships.

    Args:
        driver_query: Driver name or partial name (e.g., 'Senna', 'Hamilton', 'nor')
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client

    wrapper = get_async_wrapper()

    def fetch():
        jolpica = get_jolpica_client()
        # Resolve driver name → Jolpica driverId (search current + all-time)
        driver_id = jolpica.search_driver_id(driver_query)
        if not driver_id:
            # Try year-scoped search (handles rookies not in all-time list)
            from datetime import datetime as _dt
            driver_id = jolpica.search_driver_id(driver_query, year=_dt.now().year)
        if not driver_id:
            return None
        return jolpica.get_driver_career(driver_id)

    try:
        stats = await wrapper.run_sync_tool(fetch)
    except Exception as e:
        logger.error(f"Career summary failed: {e}")
        return f"Error fetching career data: {e}"

    if not stats or not stats.get("name"):
        return f"Could not find career data for driver: '{driver_query}'. Try the driver's last name or Jolpica ID (e.g. 'hamilton', 'max_verstappen')."

    entries = stats.get("entries", 0) or 0
    wins = stats.get("wins", 0) or 0
    dob_year = int(stats.get("dob", "1990")[:4]) if stats.get("dob") else 1990
    is_historical = dob_year < 1970  # pre-1990 era drivers; qualifying data sparse
    poles_note = " \\*" if is_historical else ""
    win_rate = f"{wins / entries * 100:.1f}%" if entries > 0 else "N/A"

    res = f"## 🏁 Driver Career Profile: {stats['name']}\n\n"
    if stats.get("nationality"):
        res += f"- **Nationality**: {stats['nationality']}\n"
    if stats.get("dob"):
        res += f"- **Born**: {stats['dob']}\n"
    res += "\n"
    res += "| Category | Total |\n"
    res += "| :--- | :--- |\n"
    res += f"| 🏆 Championships | **{stats['championships']}** |\n"
    res += f"| 🥇 Race Wins | **{wins}** |\n"
    res += f"| 🥈 Podiums | **{stats.get('podiums', 'N/A')}** |\n"
    res += f"| 🅿️ Pole Positions | **{stats['poles']}{poles_note}** |\n"
    res += f"| 🚩 Race Starts | **{entries}** |\n"
    res += f"| 📈 Win Rate | **{win_rate}** |\n\n"
    if is_historical:
        res += "_\\* Historical qualifying data may be incomplete in the Jolpica database._\n\n"
    if stats.get("url"):
        res += f"[Full Biography]({stats['url']})"
    return res


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
    # Normalise aliases
    if cat in ("fastest_lap", "fastestlap", "fastest laps", "fastest_laps"):
        cat = "fastest_laps"
    mapping = {
        "wins":         {"search": ["wins", "starts"],    "primary": "wins",    "ham_val": 100},
        "poles":        {"search": ["pole", "entries"],   "primary": "pole",    "ham_val": 100},
        "podiums":      {"search": ["podiums", "starts"], "primary": "podium",  "ham_val": 150},
        "titles":       {"search": ["titles", "seasons"], "primary": "titles",  "schu_val": 7},
        "fastest_laps": {"search": ["fastest", "laps"],   "primary": "fastest", "ham_val": 30},
    }

    if cat not in mapping:
        return (
            f"Error: Category '{category}' not supported. "
            "Use 'wins', 'poles', 'titles', 'podiums', or 'fastest_laps'."
        )

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
    Data comes from Jolpica — real-time, no scraping.

    Args:
        year: Season year
        driver_query: Optional driver name to focus on (e.g., 'Norris', 'Hamilton')
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client
    import collections

    wrapper = get_async_wrapper()

    def analyze():
        jolpica = get_jolpica_client()
        if driver_query:
            driver_id = jolpica.search_driver_id(driver_query) or jolpica.search_driver_id(driver_query, year=year)
            if not driver_id:
                return None, f"Driver '{driver_query}' not found."
            results = jolpica.get_driver_results(driver_id, year)
        else:
            results = jolpica.get_season_all_results(year)
        return results, None

    try:
        results, error = await wrapper.run_sync_tool(analyze)
    except Exception as e:
        logger.error(f"Reliability analysis failed: {e}")
        return f"Error: {e}"

    if error:
        return error
    if not results:
        return f"No reliability data found for {year}."

    import collections

    def _is_finish(status: str) -> bool:
        return status == "Finished" or bool(re.match(r'\+\d+ Lap', status))

    status_counts = collections.Counter(r["status"] for r in results)
    total = len(results)
    finished = sum(v for k, v in status_counts.items() if _is_finish(k))
    dnfs = {k: v for k, v in status_counts.items() if not _is_finish(k) and k}

    scope = f" — {driver_query.title()}" if driver_query else ""
    res = f"## 🛠️ Reliability Analysis: {year} Season{scope}\n\n"
    res += f"- **Total Race Starts**: {total}\n"
    res += f"- **Classified Finishes**: {finished}\n"
    if total:
        res += f"- **Reliability Rate**: {finished/total*100:.1f}%\n"
    res += "\n"

    if dnfs:
        res += "### ⛔ DNF Reasons\n\n"
        dnf_df = pd.DataFrame(
            sorted(dnfs.items(), key=lambda x: -x[1]),
            columns=["Status", "Count"]
        )
        res += dnf_df.to_markdown(index=False)
    else:
        res += "Perfect reliability — no DNFs recorded."

    # Season-wide view: add per-team breakdown
    if not driver_query:
        team_stats: dict = collections.defaultdict(lambda: {"total": 0, "finished": 0, "dnfs": 0})
        for r in results:
            team = r.get("team", r.get("driver", "Unknown"))
            team_stats[team]["total"] += 1
            if _is_finish(r.get("status", "")):
                team_stats[team]["finished"] += 1
            else:
                team_stats[team]["dnfs"] += 1

        rows = []
        for team, s in sorted(team_stats.items(), key=lambda x: x[0]):
            t = s["total"]
            f_ = s["finished"]
            rows.append({
                "Team": team,
                "Starts": t,
                "Finished": f_,
                "DNFs": s["dnfs"],
                "Rate": f"{f_/t*100:.0f}%" if t else "N/A",
            })
        if rows:
            res += "\n\n### 🏎️ Per-Team Breakdown\n\n"
            res += pd.DataFrame(rows).to_markdown(index=False)

    return res


@tool
async def f1_head_to_head(driver1: str, driver2: str, year: int = 0) -> str:
    """
    Head-to-head comparison between ANY two F1 drivers in a season.
    Compares race finish positions, race-by-race results, and head-to-head wins.
    Data comes from Jolpica — real-time, no scraping.

    Args:
        driver1: Name of first driver (e.g. 'Norris', 'Verstappen')
        driver2: Name of second driver
        year: Season year (0 = current year)
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client
    from datetime import datetime as _dt

    year = year or _dt.now().year
    wrapper = get_async_wrapper()

    def compare():
        jolpica = get_jolpica_client()
        id1 = jolpica.search_driver_id(driver1) or jolpica.search_driver_id(driver1, year=year)
        id2 = jolpica.search_driver_id(driver2) or jolpica.search_driver_id(driver2, year=year)
        if not id1:
            return None, f"Could not find driver: '{driver1}'. Try the last name or Jolpica ID."
        if not id2:
            return None, f"Could not find driver: '{driver2}'. Try the last name or Jolpica ID."

        r1 = jolpica.get_driver_results(id1, year)
        r2 = jolpica.get_driver_results(id2, year)
        if not r1:
            return None, f"No {year} race data for '{driver1}'."
        if not r2:
            return None, f"No {year} race data for '{driver2}'."

        d1_map = {r["round"]: r for r in r1}
        d2_map = {r["round"]: r for r in r2}
        common = sorted(set(d1_map) & set(d2_map))

        d1_name = id1.replace("_", " ").title()
        d2_name = id2.replace("_", " ").title()
        d1_ahead = d2_ahead = 0
        rows = []
        for rnd in common:
            p1 = d1_map[rnd]["position"]
            p2 = d2_map[rnd]["position"]
            try:
                if int(p1) < int(p2):
                    d1_ahead += 1
                elif int(p2) < int(p1):
                    d2_ahead += 1
            except (ValueError, TypeError):
                pass
            rows.append({
                "Round": rnd,
                "Race": d1_map[rnd]["race_name"],
                d1_name: p1,
                d2_name: p2,
            })

        return {
            "id1": d1_name, "id2": d2_name,
            "d1_ahead": d1_ahead, "d2_ahead": d2_ahead,
            "total": len(common), "rows": rows,
        }, None

    try:
        data, error = await wrapper.run_sync_tool(compare)
    except Exception as e:
        return f"Comparison failed: {e}"

    if error:
        return error

    res = f"### 🏎️ F1 Head-to-Head: {data['id1']} vs {data['id2']} ({year})\n\n"
    res += f"| Metric | {data['id1']} | {data['id2']} |\n"
    res += "| :--- | :--- | :--- |\n"
    res += f"| **Races Finished Ahead** | **{data['d1_ahead']}** | **{data['d2_ahead']}** |\n"
    res += f"| Total Common Races | {data['total']} | {data['total']} |\n\n"

    if data["d1_ahead"] > data["d2_ahead"]:
        res += f"🏆 **{data['id1']}** was superior in head-to-head finishes in {year}.\n"
    elif data["d2_ahead"] > data["d1_ahead"]:
        res += f"🏆 **{data['id2']}** was superior in head-to-head finishes in {year}.\n"
    else:
        res += f"⚖️ It was a perfectly even season between {data['id1']} and {data['id2']}!\n"

    if data["rows"]:
        res += "\n### Race-by-Race Results\n\n"
        res += pd.DataFrame(data["rows"]).to_markdown(index=False)
    return res




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
    Provides details about F1 circuits/tracks from Jolpica.
    Includes location, coordinates, and Wikipedia link.

    Args:
        circuit_query: Circuit name or ID (e.g., 'Monaco', 'Silverstone', 'spa').
                       Leave empty to list all circuits in the current season.
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client

    wrapper = get_async_wrapper()

    def fetch():
        jolpica = get_jolpica_client()
        if not circuit_query:
            return jolpica.get_circuits(year=datetime.now().year)
        all_circuits = jolpica.get_circuits()
        q = circuit_query.lower()
        matches = [
            c for c in all_circuits
            if q in c["circuit_name"].lower()
            or q in c["circuit_id"].lower()
            or q in c.get("locality", "").lower()
            or q in c.get("country", "").lower()
        ]
        return matches

    try:
        data = await wrapper.run_sync_tool(fetch)
    except Exception as e:
        logger.error(f"Circuit guide failed: {e}")
        return f"Error: {e}"

    if not data:
        return f"No circuit found for: '{circuit_query}'"

    if len(data) > 1:
        df = pd.DataFrame([{
            "ID": c["circuit_id"],
            "Circuit": c["circuit_name"],
            "Location": c["locality"],
            "Country": c["country"],
        } for c in data])
        return "## 🏁 F1 Circuits\n\n" + df.to_markdown(index=False)

    c = data[0]
    res = f"## 🗺️ Circuit Profile: {c['circuit_name']}\n\n"
    res += f"- **Location**: {c['locality']}, {c['country']}\n"
    res += f"- **Circuit ID**: `{c['circuit_id']}`\n"
    res += f"- **Coordinates**: Lat {c['lat']}, Long {c['long']}\n"
    if c.get("url"):
        res += f"- **Wikipedia**: [{c['circuit_name']}]({c['url']})\n"

    # Fetch recent race winners at this circuit
    def fetch_winners():
        from core.api_client import get_jolpica_client
        return get_jolpica_client().get_circuit_winners(c["circuit_id"], limit=5)

    try:
        winners = await wrapper.run_sync_tool(fetch_winners)
        if winners:
            res += "\n### 🏆 Recent Race Winners\n\n"
            res += "| Year | Winner | Team |\n| :--- | :--- | :--- |\n"
            for w in winners:
                res += f"| {w['year']} | {w['winner']} | {w['team']} |\n"
    except Exception:
        pass

    return res


@tool
async def f1_constructor_career_summary(constructor_query: str) -> str:
    """
    Comprehensive career summary for an F1 Constructor (Team) from Jolpica.
    Includes championships, wins, and total race entries.

    Args:
        constructor_query: Team name or ID (e.g., 'Ferrari', 'McLaren', 'red bull')
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client

    wrapper = get_async_wrapper()

    def fetch():
        jolpica = get_jolpica_client()
        constructor_id = jolpica.search_constructor_id(constructor_query)
        if not constructor_id:
            return None
        return jolpica.get_constructor_career(constructor_id)

    try:
        stats = await wrapper.run_sync_tool(fetch)
    except Exception as e:
        logger.error(f"Constructor summary failed: {e}")
        return f"Error: {e}"

    if not stats:
        return (
            f"Could not find constructor: '{constructor_query}'. "
            "Try the team name (e.g. 'ferrari', 'mclaren', 'red bull', 'mercedes')."
        )

    entries = stats.get("entries", 0) or 0
    wins = stats.get("wins", 0) or 0
    win_rate = f"{wins / entries * 100:.1f}%" if entries > 0 else "N/A"

    res = f"## 🏎️ Constructor Profile: {stats['name']}\n\n"
    if stats.get("nationality"):
        res += f"- **Nationality**: {stats['nationality']}\n\n"
    res += "| Achievement | Total |\n"
    res += "| :--- | :--- |\n"
    res += f"| 🏆 Championships | **{stats['championships']}** |\n"
    res += f"| 🥇 Race Wins | **{wins}** |\n"
    res += f"| 🅿️ Pole Positions | **{stats.get('poles', 'N/A')}** |\n"
    res += f"| 🚩 Race Entries | **{entries}** |\n"
    res += f"| 📈 Win Rate | **{win_rate}** |\n\n"
    if stats.get("url"):
        res += f"[History & Wiki]({stats['url']})"
    return res


def _fetch_standings_wikipedia(year: int) -> str:
    """
    Scrape current championship standings from Wikipedia.
    Used as fallback when Ergast doesn't have data for recent/current seasons.
    """
    url = f"https://en.wikipedia.org/wiki/{year}_Formula_One_World_Championship"
    headers = {'User-Agent': 'F1Agent/1.0'}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))

    output = f"## 🏆 {year} F1 Championship Standings (via Wikipedia)\n\n"
    found_any = False

    for t in tables:
        cols_str = str(t.columns).lower()
        text = t.to_string().lower()
        # Driver standings table: has 'driver' and 'points' columns
        if 'driver' in cols_str and 'points' in cols_str and len(t) >= 5:
            # Check it's not the race-results table (too wide)
            if len(t.columns) <= 30:
                df = t.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [' '.join(dict.fromkeys(str(c) for c in col)).strip()
                                  for col in df.columns.values]
                # Try to find position and points columns
                pos_col = next((c for c in df.columns if 'pos' in str(c).lower()), None)
                drv_col = next((c for c in df.columns if 'driver' in str(c).lower()), None)
                pts_col = next((c for c in df.columns if 'point' in str(c).lower()), None)
                if drv_col and pts_col:
                    display_cols = [c for c in [pos_col, drv_col, pts_col] if c]
                    snippet = df[display_cols].dropna(subset=[pts_col]).head(25)
                    if not snippet.empty:
                        output += "### 👤 Driver Standings\n\n"
                        output += snippet.to_markdown(index=False) + "\n\n"
                        found_any = True
                        break

    for t in tables:
        cols_str = str(t.columns).lower()
        if 'constructor' in cols_str and 'points' in cols_str and len(t) >= 5:
            if len(t.columns) <= 30:
                df = t.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [' '.join(dict.fromkeys(str(c) for c in col)).strip()
                                  for col in df.columns.values]
                pos_col = next((c for c in df.columns if 'pos' in str(c).lower()), None)
                con_col = next((c for c in df.columns if 'constructor' in str(c).lower()), None)
                pts_col = next((c for c in df.columns if 'point' in str(c).lower()), None)
                if con_col and pts_col:
                    display_cols = [c for c in [pos_col, con_col, pts_col] if c]
                    snippet = df[display_cols].dropna(subset=[pts_col]).head(15)
                    if not snippet.empty:
                        output += "### 🏎️ Constructor Standings\n\n"
                        output += snippet.to_markdown(index=False) + "\n"
                        found_any = True
                        break

    if not found_any:
        raise ValueError(f"Could not parse standings tables from Wikipedia for {year}")
    return output


@tool
async def f1_standings(year: int = 0) -> str:
    """
    Returns the LIVE F1 World Championship standings for drivers and constructors.
    Data comes directly from the Jolpica REST API (api.jolpi.ca) — real-time JSON,
    updated within minutes of each session ending.
    Use when user asks for: "current standings", "championship points", "who is leading",
    "driver standings", "team standings", "points table", or any year's standings.

    Args:
        year: The F1 season year (0 = current year)
    """
    from utils.async_tools import get_async_wrapper
    from datetime import datetime as _dt
    from core.api_client import get_jolpica_client

    year = year or _dt.now().year
    wrapper = get_async_wrapper()

    def fetch():
        client = get_jolpica_client()
        drivers = client.get_driver_standings(year)
        constructors = client.get_constructor_standings(year)
        return drivers, constructors

    try:
        drivers, constructors = await wrapper.run_sync_tool(fetch)
    except Exception as e:
        logger.error(f"Jolpica standings fetch failed: {e}")
        return f"Could not fetch {year} standings: {e}"

    if not drivers and not constructors:
        return (
            f"No standings data found for {year} via the Jolpica API. "
            "The season may not have started, or the API may be temporarily unavailable."
        )

    output = f"## 🏆 {year} F1 Championship Standings\n*(Source: api.jolpi.ca — live data)*\n\n"

    if drivers:
        df_d = pd.DataFrame(drivers)
        df_d = df_d[['position', 'points', 'wins', 'driver_name', 'team_name']]
        df_d.columns = ['Pos', 'Pts', 'Wins', 'Driver', 'Team']
        output += "### 👤 Driver Standings\n\n"
        output += df_d.to_markdown(index=False) + "\n\n"

    if constructors:
        df_c = pd.DataFrame(constructors)
        df_c = df_c[['position', 'points', 'wins', 'team_name']]
        df_c.columns = ['Pos', 'Pts', 'Wins', 'Team']
        output += "### 🏎️ Constructor Standings\n\n"
        output += df_c.to_markdown(index=False) + "\n"

    return output


@tool
async def f1_next_race_preview() -> str:
    """
    Shows information about the NEXT upcoming F1 race: date, circuit, location,
    and the last 5 winners at that circuit — fetched from Jolpica (no FastF1 session loads).
    Use when user asks: 'next race', 'when is the next GP', 'what's coming up',
    'upcoming race', 'next round'.
    """
    try:
        import fastf1
        from utils.async_tools import get_async_wrapper
        from core.api_client import get_jolpica_client

        wrapper = get_async_wrapper()

        def fetch():
            # FastF1 schedule is lightweight — only reads the calendar, no telemetry
            remaining = fastf1.get_events_remaining()
            if remaining.empty:
                return None

            next_event = remaining.iloc[0]
            circuit_id = str(next_event.get('OfficialEventName', '')).lower()
            # FastF1 doesn't expose circuitId directly; get it from Jolpica schedule
            jolpica = get_jolpica_client()
            current_year = next_event['EventDate'].year
            schedule = jolpica.get_season_schedule(current_year)

            # Match by race name fragment
            event_name = next_event['EventName']
            circuit_id = None
            circuit_name = next_event.get('Location', '')
            for race in schedule:
                if event_name.lower() in race['race_name'].lower() or race['race_name'].lower() in event_name.lower():
                    circuit_id = race['circuit_id']
                    circuit_name = race['circuit']
                    break

            history = []
            if circuit_id:
                try:
                    winners = jolpica.get_circuit_winners(circuit_id, limit=5)
                    history = [f"{w['year']}: {w['winner']} ({w['team']})" for w in winners]
                except Exception as e:
                    logger.warning(f"Could not fetch circuit winners for {circuit_id}: {e}")

            return {
                "name": event_name,
                "circuit": circuit_name,
                "location": next_event.get('Location', ''),
                "country": next_event.get('Country', ''),
                "date": next_event['EventDate'].strftime('%Y-%m-%d'),
                "round": int(next_event.get('RoundNumber', 0)),
                "history": history,
            }

        data = await wrapper.run_sync_tool(fetch)
        if not data:
            return "No upcoming races found. The season may be over."

        out = f"## 🏁 Next Race: {data['name']}\n\n"
        out += f"- **Round**: {data['round']}\n"
        out += f"- **Date**: {data['date']}\n"
        out += f"- **Circuit**: {data['circuit']}\n"
        out += f"- **Location**: {data['location']}, {data['country']}\n\n"
        if data['history']:
            out += "### 🏆 Recent Winners at This Circuit\n\n"
            for h in data['history']:
                out += f"- {h}\n"
        else:
            out += "*Historical winners not yet available for this circuit.*\n"
        return out
    except Exception as e:
        logger.error(f"Next race preview failed: {e}")
        return f"Error fetching next race: {e}"


@tool
async def f1_driver_form(driver: str, n_races: int = 5) -> str:
    """
    Shows a driver's results in their last N races to assess current form.
    Data comes from Jolpica — real-time, no scraping.
    Use when user asks: 'recent form', 'how has X been performing lately',
    'last 5 races for Norris', 'is Hamilton in form', 'driver momentum'.

    Args:
        driver: Driver name (e.g. 'Norris', 'Hamilton', 'Verstappen')
        n_races: Number of recent races to look at (default: 5)
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client
    from datetime import datetime as _dt

    wrapper = get_async_wrapper()

    def fetch():
        jolpica = get_jolpica_client()
        current_year = _dt.now().year
        for year in [current_year, current_year - 1]:
            driver_id = jolpica.search_driver_id(driver, year=year)
            if not driver_id:
                continue
            results = jolpica.get_driver_results(driver_id, year)
            if results:
                return results, year, driver_id
        return None, None, None

    try:
        results, year, driver_id = await wrapper.run_sync_tool(fetch)
    except Exception as e:
        logger.error(f"Driver form fetch failed: {e}")
        return f"Error fetching driver form: {e}"

    if not results:
        return f"Could not find recent race data for '{driver}'."

    recent = list(reversed(results[-n_races:] if len(results) >= n_races else results))
    total_pts = sum(r.get("points", 0) or 0 for r in recent)
    positions = [int(r["position"]) for r in recent if str(r.get("position", "")).isdigit()]
    avg_pos = sum(positions) / len(positions) if positions else None

    display = [{
        "Round": r["round"],
        "Race": r["race_name"],
        "Grid": r["grid"],
        "Pos": r["position"],
        "Pts": int(r["points"]) if r.get("points") and r["points"] == int(r["points"]) else r.get("points", 0),
        "Status": r["status"],
    } for r in recent]

    driver_label = driver_id.replace("_", " ").title() if driver_id else driver.title()
    out = f"## 📊 {driver_label} — Last {len(recent)} Races ({year})\n\n"
    out += pd.DataFrame(display).to_markdown(index=False) + "\n\n"
    out += f"**Points in this period**: {total_pts:.0f}\n"
    if avg_pos:
        out += f"**Average finishing position**: P{avg_pos:.1f}\n"
    return out


@tool
async def f1_points_progression(year: int = 0, top_n: int = 8) -> str:
    """
    Generates a line chart showing cumulative championship points per driver
    across all rounds of a season. Saves as PNG and auto-opens.

    Use when user asks: 'points progression', 'championship battle chart',
    'points over the season', 'who has been gaining points fastest'.

    Args:
        year: F1 season year (0 = current year)
        top_n: Number of top drivers to show (default 8)
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client
    from datetime import datetime as _dt
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import collections

    year = year or _dt.now().year
    wrapper = get_async_wrapper()

    try:
        results = await wrapper.run_sync_tool(
            lambda: get_jolpica_client().get_season_all_results(year)
        )
    except Exception as e:
        return f"Error fetching {year} season data: {e}"

    if not results:
        return f"No race results found for {year} yet."

    # Build cumulative points per driver per round
    rounds = sorted(set(r["round"] for r in results))
    driver_round_pts: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for r in results:
        driver_round_pts[r["driver_name"]][r["round"]] = r.get("points", 0.0)

    cumulative: dict[str, list[float]] = {}
    for driver, rnd_pts in driver_round_pts.items():
        total = 0.0
        series = []
        for rnd in rounds:
            total += rnd_pts.get(rnd, 0.0)
            series.append(total)
        cumulative[driver] = series

    # Select top N by final total
    final = {d: pts[-1] for d, pts in cumulative.items()}
    top_drivers = sorted(final, key=lambda d: -final[d])[:top_n]

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 7))
    colors = ["#E8002D", "#FF8000", "#00D2BE", "#0067FF", "#006F62",
              "#B6BABD", "#FF1744", "#00E5FF", "#FF6D00", "#64DD17"]

    for i, driver in enumerate(top_drivers):
        series = cumulative[driver]
        label = driver.split()[-1]  # surname only
        ax.plot(rounds[:len(series)], series,
                marker="o", markersize=3, linewidth=2,
                color=colors[i % len(colors)], label=label)
        # Annotate final value
        ax.annotate(f"{label} ({series[-1]:.0f})",
                    xy=(rounds[len(series)-1], series[-1]),
                    xytext=(5, 0), textcoords="offset points",
                    fontsize=8, color=colors[i % len(colors)])

    ax.set_xlabel("Round", fontsize=12, color="white")
    ax.set_ylabel("Cumulative Points", fontsize=12, color="white")
    ax.set_title(f"{year} F1 Championship Points Progression", fontsize=15, color="white", pad=15)
    ax.legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.3)
    ax.grid(True, alpha=0.25, color="gray")
    ax.set_xticks(rounds)
    ax.tick_params(colors="white")
    plt.tight_layout()

    filename = f"{PLOTS_DIR}/points_progression_{year}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight", facecolor="black")
    plt.close()

    top3 = ", ".join(f"{d.split()[-1]}: {final[d]:.0f}pts" for d in top_drivers[:3])
    return f"Chart saved: {filename}\nTop 3 after {len(rounds)} rounds: {top3}"


@tool
async def f1_sprint_results(year: int = 0, round_number: int = 0) -> str:
    """
    Returns sprint race results from Jolpica (real-time data).
    Use when user asks about sprint races, sprint results, sprint shootout outcomes.

    Args:
        year: F1 season year (0 = current year)
        round_number: Specific round (0 = all sprint races in the season)
    """
    from utils.async_tools import get_async_wrapper
    from core.api_client import get_jolpica_client
    from datetime import datetime as _dt

    year = year or _dt.now().year
    wrapper = get_async_wrapper()
    rnd = round_number or None

    try:
        results = await wrapper.run_sync_tool(
            lambda: get_jolpica_client().get_sprint_results(year, rnd)
        )
    except Exception as e:
        return f"Error fetching sprint data: {e}"

    if not results:
        return (
            f"No sprint results found for {year}"
            + (f" round {round_number}" if round_number else "")
            + ". Sprint races only occur at selected rounds."
        )

    if round_number:
        race_name = results[0]["race_name"] if results else ""
        header = f"## 🏎️ Sprint Results — {race_name} ({year} Round {round_number})\n\n"
        rows = [{"Pos": r["position"], "Driver": r["driver_name"],
                 "Team": r["constructor"], "Pts": r["points"], "Status": r["status"]}
                for r in results]
        return header + pd.DataFrame(rows).to_markdown(index=False)

    # All sprints in season
    output = f"## 🏎️ {year} F1 Sprint Race Results\n*(Source: api.jolpi.ca — live data)*\n\n"
    from itertools import groupby
    for rnd_num, group in groupby(sorted(results, key=lambda x: x["round"]), key=lambda x: x["round"]):
        rnd_list = list(group)
        race_name = rnd_list[0]["race_name"]
        output += f"### Round {rnd_num}: {race_name}\n\n"
        rows = [{"Pos": r["position"], "Driver": r["driver_name"],
                 "Team": r["constructor"], "Pts": r["points"]}
                for r in rnd_list[:10]]  # top 10
        output += pd.DataFrame(rows).to_markdown(index=False) + "\n\n"
    return output


def get_reference_tools() -> list:
    """Returns all historical reference and lookup tools (Jolpica-backed, real-time)."""
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
        f1_diagnostics,
        f1_next_race_preview,
        f1_driver_form,
        f1_points_progression,
        f1_sprint_results,
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

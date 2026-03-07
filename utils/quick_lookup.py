"""
Quick Lookup Bypass Module

Provides instant responses for simple queries by calling tools directly,
bypassing the LLM agent overhead.
"""
import asyncio
import re
from tools.reference_tools import (
    f1_all_time_records,
    f1_constructor_champions,
    f1_champions_quick_lookup
)
from tools.live_tools import (
    f1_live_weather,
    f1_live_position_map
)

class QuickLookupBypass:
    """Direct tool access for instant responses on simple queries."""
    
    def __init__(self):
        self.patterns = {
            r"(pole\s+position|poles|most\s+poles|pole\s+record|how\s+many\s+pole)": {
                "tool": f1_all_time_records,
                "name": "Pole Position Records",
                "category": "poles"
            },
            r"(fastest\s+lap|fast\s+lap|fastest\s+laps|most\s+fastest)": {
                "tool": f1_all_time_records,
                "name": "Fastest Lap Records",
                "category": "wins"
            },
            r"(constructor\s+champion|team\s+champion|constructor.*since|team.*champion|constructor.*title)": {
                "tool": f1_constructor_champions,
                "name": "Constructor Champions",
                "extract_year": True
            },
            r"(driver\s+champion|world\s+champion|f1\s+champion|champions?\s+list|how\s+many\s+title|how\s+many\s+championship|hamilton.*title|verstappen.*title|.*titles.*hamilton|.*championships.*driver)": {
                "tool": f1_champions_quick_lookup,
                "name": "Driver Champions",
                "extract_year": True
            },
            r"(live\s+weather|current\s+weather|weather\s+now|weather$|^weather|rain\s+now|rain$|^rain)": {
                "tool": f1_live_weather,
                "name": "Live Weather"
            },
            r"(positions|current\s+race\s+positions|standings.*live|where\s+is\s+.*now)": {
                "tool": f1_live_position_map,
                "name": "Live Positions"
            }
        }
    
    def match(self, query: str) -> dict | None:
        """Check if query matches a quick lookup pattern."""
        query_lower = query.lower()
        
        for pattern, config in self.patterns.items():
            if re.search(pattern, query_lower):
                # Skip live tools if historical context (year) is present without 'live/current'
                if config["name"] in ["Live Weather", "Live Positions"]:
                    has_year = re.search(r"\b(19\d{2}|20\d{2})\b", query_lower)
                    is_explicitly_live = re.search(r"\b(live|current|now|today)\b", query_lower)
                    if has_year and not is_explicitly_live:
                        continue

                result = {"tool": config["tool"], "name": config["name"]}
                
                if config.get("category"):
                    result["category"] = config["category"]
                    
                # Extract year filter if applicable
                if config.get("extract_year"):
                    years = re.findall(r"\b(19\d{2}|20\d{2})\b", query_lower)
                    if len(years) >= 2:
                        sorted_years = sorted([int(y) for y in years])
                        result["year_filter"] = f"from {sorted_years[0]} to {sorted_years[-1]}"
                        result["year"] = sorted_years[-1] # Primary year
                    elif len(years) == 1:
                        year = years[0]
                        ctx_match = re.search(r"(since|after|from|until|before|to|in)\s+" + year, query_lower)
                        result["year"] = int(year)
                        if ctx_match:
                            result["year_filter"] = f"{ctx_match.group(1)} {year}"
                        else:
                            result["year_filter"] = year

                # Extract drivers if applicable
                if config.get("extract_drivers"):
                    # Common F1 driver names/IDs
                    # This is a simplified regex, but good for common cases
                    drivers = re.findall(r"\b(hamilton|russell|verstappen|norris|leclerc|piastri|sainz|alonso|perez|stroll|gasly|ocon|albon|magnussen|hulkenberg|bottas|zhou|tsunoda|ricciardo|lawson|sargeant|colapinto|bearman|antonelli|hadjar|lindblad|bortoleto)\b", query_lower)
                    if len(drivers) >= 2:
                        result["driver1"] = drivers[0]
                        result["driver2"] = drivers[1]
                    elif len(drivers) == 1:
                        result["driver1"] = drivers[0]
                
                # Extract test day if applicable
                if config.get("extract_test_day"):
                    day_match = re.search(r"day\s+([1-3])", query_lower)
                    if day_match:
                        result["day"] = int(day_match.group(1))
                    else:
                        result["day"] = 1 # Default to day 1
                
                return result
        
        return None
    
    async def execute(self, match_result: dict) -> str:
        """Execute the matched tool and return result."""
        tool_func = match_result["tool"]
        tool_name = match_result["name"]
        
        # Handle different tool signature requirements
        if "year_filter" in match_result:
            result = await tool_func.ainvoke({"year_filter": match_result["year_filter"]})
        elif "category" in match_result:
            result = await tool_func.ainvoke({"category": match_result["category"]})
        elif tool_name in ["Live Weather", "Live Positions"]:
            result = await tool_func.ainvoke({"session_key": "latest"})
        else:
            result = await tool_func.ainvoke({})
        
        return result

"""
Quick Lookup Bypass Module

Provides instant responses for simple queries by calling tools directly,
bypassing the LLM agent overhead.
"""
import asyncio
import re
from tools.reference_tools import (
    f1_pole_position_records,
    f1_fastest_lap_records,
    f1_constructor_champions,
    f1_champions_quick_lookup
)

class QuickLookupBypass:
    """Direct tool access for instant responses on simple queries."""
    
    def __init__(self):
        self.patterns = {
            r"(pole\s+position|poles|most\s+poles|pole\s+record|how\s+many\s+pole)": {
                "tool": f1_pole_position_records,
                "name": "Pole Position Records"
            },
            r"(fastest\s+lap|fast\s+lap|fastest\s+laps|most\s+fastest)": {
                "tool": f1_fastest_lap_records,
                "name": "Fastest Lap Records"
            },
            r"(constructor\s+champion|team\s+champion|constructor.*since|team.*champion|constructor.*title)": {
                "tool": f1_constructor_champions,
                "name": "Constructor Champions",
                "extract_year": True
            },
            r"(driver\s+champion|world\s+champion|f1\s+champion|champions?\s+list|how\s+many\s+title|how\s+many\s+championship|hamilton.*title|verstappen.*title|.*titles.*hamilton|.*championships.*driver)": {
                "tool": f1_champions_quick_lookup,
                "name": "Driver Champions"
            },
        }
    
    def match(self, query: str) -> dict | None:
        """Check if query matches a quick lookup pattern."""
        query_lower = query.lower()
        
        for pattern, config in self.patterns.items():
            if re.search(pattern, query_lower):
                result = {"tool": config["tool"], "name": config["name"]}
                
                # Extract year filter if applicable
                if config.get("extract_year"):
                    year_match = re.search(r"since\s+(\d{4})", query_lower)
                    if year_match:
                        result["year_filter"] = f"since {year_match.group(1)}"
                
                return result
        
        return None
    
    async def execute(self, match_result: dict) -> str:
        """Execute the matched tool and return result."""
        tool_func = match_result["tool"]
        
        # Call tool with year filter if present
        if "year_filter" in match_result:
            result = await tool_func(match_result["year_filter"])
        else:
            result = await tool_func()
        
        return result

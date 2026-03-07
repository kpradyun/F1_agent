"""
Agent Creation and Configuration
Handles F1 agent setup with all tools
"""
import logging
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from config.settings import TODAY, LLM_MODEL
from tools.live_tools import get_live_tools
from tools.analysis_tools import get_analysis_tools
from tools.replay_tools import get_replay_tools
from tools.reference_tools import get_reference_tools
from tools.advanced_tools import get_advanced_tools
from tools.predictive_tools import get_predictive_tools
from tools.visualization_tools import get_visualization_tools
from tools.media_tools import get_media_tools
from tools.session_tools import get_session_tools
from rag_engine import get_rag_tool

logger = logging.getLogger("F1_Agent")

def get_system_prompt():
    """Generate the system prompt for the agent"""
    return SystemMessage(content=(
        f"You are an F1 Race Engineer. Date: {TODAY}.\n"
        "Rules: Use tools for ANY F1 stats/data (2018-2026). Internal knowledge is outdated.\n"
        "- For driver comparisons (v rivals or teammates), use `f1_head_to_head`.\n"
        "- For testing/pre-season results, use `f1_testing_summary`.\n"
        "- For results/standings/schedules, use the corresponding tools.\n"
        "- CRITICAL: For statistics, head-to-head counts, standings, and RACE CLASSIFICATIONS, you MUST return the tool output exactly as provided. Do NOT summarize or remove details like 'Points' or 'Status'. If the tool provides a list of finishers with points, you MUST show the points for every driver listed. Provide the data VERBATIM first, then offer analysis ONLY if asked.\n"
        "- NEVER pass the string 'nil' or 'unknown' as a `session_key`. If you don't know the key, leave the argument empty so the tool can resolve it automatically.\n"
        "- If a tool returns a 401 error marked as 'ACCESS RESTRICTED' or 'Live Session', explain to the user that OpenF1 data is temporarily limited due to a live race weekend in progress."
    ))

def get_all_tools() -> list:
    """Assemble all agent tools from different modules."""
    tools = []
    tools.extend(get_live_tools())           # 3 tools: weather, positions, intervals
    tools.extend(get_analysis_tools())       # 6 tools: schedule, results, telemetry, etc.
    tools.extend(get_reference_tools())      # 10 tools: champions, winners, head-to-head, etc.
    tools.extend(get_media_tools())          # 1 tool: radio download
    tools.extend(get_session_tools())        # 4 tools: testing, weather, race control, telem breakdown
    tools.append(get_rag_tool())             # 1 tool: regulations
    
    # We prune predictive, visualization, and advanced tools to keep the model fast and accurate
    # (34 tools was overwhelming Llama 3.2, now down to ~25)
    
    logger.info(f"Loaded {len(tools)} tools total")
    return tools

def create_f1_agent(llm):
    """
    Create the F1 ReAct agent with all tools
    
    Args:
        llm: The language model instance
        
    Returns:
        The configured agent
    """
    logger.info(f"Creating ReAct agent with {LLM_MODEL}...")
    agent = create_react_agent(llm, get_all_tools())
    return agent

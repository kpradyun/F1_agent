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
from rag_engine import get_rag_tool

logger = logging.getLogger("F1_Agent")

def get_system_prompt():
    """Generate the system prompt for the agent"""
    return SystemMessage(content=(
        f"F1 engineer. Today: {TODAY}. "
        "Tools: f1_constructor_champions, f1_pole_position_records, f1_fastest_lap_records, "
        "f1_champions_quick_lookup, f1_schedule, f1_next_event, f1_event_details, f1_session_results, f1_tavily_search. "
        "USE ONE TOOL. RETURN ITS OUTPUT VERBATIM. NO COMMENTARY."
    ))

def get_all_tools() -> list:
    """Assemble all agent tools from different modules."""
    tools = []
    tools.extend(get_live_tools())           # 3 tools: weather, positions, intervals
    tools.extend(get_analysis_tools())       # analysis suite: schedule, event, results, telemetry, strategy
    tools.extend(get_replay_tools())         # 1 tool: race replay
    tools.extend(get_reference_tools())      # 6 tools: season winners, champions, records, poles, constructors, wikipedia
    tools.extend(get_advanced_tools())       # 8 tools: complete API coverage
    tools.extend(get_predictive_tools())     # 2 tools: tire life, overtake
    tools.extend(get_visualization_tools())  # 2 tools: interactive charts
    tools.append(get_rag_tool())             # 1 tool: regulations
    
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

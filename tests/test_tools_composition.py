"""Tests for tool list counts and structure — no network required."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_analysis_tools_count():
    from tools.analysis_tools import get_analysis_tools
    tools = get_analysis_tools()
    assert len(tools) == 8, f"Expected 8 analysis tools, got {len(tools)}"


def test_session_tools_count():
    from tools.session_tools import get_session_tools
    tools = get_session_tools()
    assert len(tools) == 6, f"Expected 6 session tools, got {len(tools)}"


def test_reference_tools_count():
    from tools.reference_tools import get_reference_tools
    tools = get_reference_tools()
    assert len(tools) == 16, f"Expected 16 reference tools, got {len(tools)}"


def test_live_tools_count():
    from tools.live_tools import get_live_tools
    tools = get_live_tools()
    assert len(tools) == 4, f"Expected 4 live tools, got {len(tools)}"


def test_media_tools_count():
    from tools.media_tools import get_media_tools
    tools = get_media_tools()
    assert len(tools) == 1, f"Expected 1 media tool, got {len(tools)}"


def test_replay_tools_count():
    from tools.replay_tools import get_replay_tools
    tools = get_replay_tools()
    assert len(tools) == 1, f"Expected 1 replay tool, got {len(tools)}"


def test_tools_are_callable():
    from tools.analysis_tools import get_analysis_tools
    for tool in get_analysis_tools():
        assert callable(tool) or hasattr(tool, "ainvoke"), f"Tool {tool} is not callable"


def test_all_tools_have_names():
    from tools.analysis_tools import get_analysis_tools
    from tools.session_tools import get_session_tools
    from tools.live_tools import get_live_tools
    from tools.media_tools import get_media_tools

    all_tools = (
        get_analysis_tools() + get_session_tools() +
        get_live_tools() + get_media_tools()
    )
    for tool in all_tools:
        assert hasattr(tool, "name") and tool.name, f"Tool missing name: {tool}"


def test_replay_tool_importable_without_arcade():
    # replay_tools must be importable even if arcade is not installed
    # (arcade import is now deferred inside the tool function)
    import importlib
    mod = importlib.import_module("tools.replay_tools")
    assert hasattr(mod, "get_replay_tools")
    assert hasattr(mod, "f1_race_replay")

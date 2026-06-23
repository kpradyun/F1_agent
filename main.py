"""
F1 Race Engineer Agent - Main Entry Point

A clean CLI interface for the F1 analysis agent.
"""
import sys
import os
import time
import asyncio
import logging
import warnings
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.markdown import Markdown
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="fastf1")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")

from config.settings import (
    TODAY, LOG_LEVEL, LOG_FORMAT, LOG_FILE, LLM_MODEL, DATA_DEFAULT_YEAR,
    LLM_PROVIDER, GEMINI_MODEL,
)
from core.initialization import initialize_systems, get_llm
from core.agent import create_f1_agent, get_system_prompt
from utils.metrics import PerformanceMetrics
from utils.cache_manager import get_cache
from utils.async_tools import get_async_wrapper
from core.monitor import LiveRaceMonitor

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

for name in logging.root.manager.loggerDict:
    if 'langchain' not in name.lower() and 'f1_data_miner' not in name.lower() and 'fastf1' not in name.lower():
        logging.getLogger(name).setLevel(logging.WARNING)
    else:
        logging.getLogger(name).setLevel(getattr(logging, LOG_LEVEL))

logger = logging.getLogger("F1_Agent")
console = Console()
metrics = PerformanceMetrics()

# Track the most recently generated file for /open command
_last_generated_file: str | None = None


def open_file(path: str):
    """Open a file with the system default viewer."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", path], check=False)
        else:
            import subprocess
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        console.print(f"[yellow]Could not auto-open file: {e}[/yellow]")


def extract_file_path(text: str) -> str | None:
    """Extract a file path from tool output if one was saved."""
    import re
    patterns = [
        r'saved[:\s]+([^\s]+\.(?:png|html|mp3))',
        r'chart[:\s]+([^\s]+\.(?:png|html))',
        r'([^\s]+plots[/\\][^\s]+\.(?:png|html))',
        r'([A-Za-z]:[\\/][^\s]+\.(?:png|html|mp3))',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def display_status(tool_name: str, status: str, duration: float = 0.0,
                   mode: str = "Agent"):
    """Display completion status with timing and mode indicator."""
    color_map = {"DONE": "green", "ERROR": "red"}
    mode_color = "cyan" if mode == "Quick Lookup" else "yellow"
    console.print(
        f"[dim][{color_map.get(status, 'white')}]{status}[/{color_map.get(status, 'white')}] "
        f"[{mode_color}]({mode})[/{mode_color}] "
        f"[dim]{duration:.2f}s[/dim][/dim]"
    )


async def stream_agent_response(agent, messages):
    """
    Stream agent execution with progressive display.
    Shows tool execution in real-time and streams text as it's generated.
    """
    global _last_generated_file

    config = RunnableConfig(
        recursion_limit=15,
        configurable={"thread_id": "main"}
    )

    response_text = ""
    response_started = False
    last_tool_output = None

    try:
        async for event in agent.astream({"messages": messages}, config=config, stream_mode="values"):
            if "messages" not in event:
                continue

            msg = event["messages"][-1]

            if msg.type == "tool":
                tool_name = getattr(msg, 'name', 'Unknown')
                tool_output = getattr(msg, 'content', '')

                icon = "🔍" if "lookup" in tool_name.lower() or "search" in tool_name.lower() else "🏎️"
                if "all_time" in tool_name.lower() or "champion" in tool_name.lower():
                    icon = "🏆"
                if "plot" in tool_name.lower() or "chart" in tool_name.lower():
                    icon = "📊"
                if "predict" in tool_name.lower():
                    icon = "🔮"

                console.print(f"[yellow]{icon} Executing: {tool_name}...[/yellow]")
                metrics.record_tool(tool_name)

                last_tool_output = tool_output

                # Auto-detect and open generated files
                file_path = extract_file_path(str(tool_output))
                if file_path and os.path.exists(file_path):
                    _last_generated_file = file_path
                    open_file(file_path)
                    console.print(f"[dim green]Opened: {file_path}[/dim green]")

                if any(keyword in tool_name.lower() for keyword in
                       ['strategy', 'plot', 'chart', 'visual', 'replay', 'head_to_head',
                        'summary', 'stats', 'champions', 'radio', 'media', 'results',
                        'session', 'classification', 'standings', 'predict', 'form']):
                    console.print(f"\n[dim]{tool_output}[/dim]")

            elif msg.type == "ai" and not msg.tool_calls:
                response_text = msg.content
                response_started = True

    except Exception as e:
        error_msg = str(e)
        if "memory" in error_msg.lower():
            console.print("\n[bold red]✕ Error: System out of memory for this model. Try a smaller one in config/settings.py.[/bold red]")
        elif "not found" in error_msg.lower():
            console.print(f"\n[bold red]✕ Error: Model '{LLM_MODEL}' not found. Run 'ollama pull {LLM_MODEL}' or check config.[/bold red]")
        else:
            console.print(f"\n[bold red]✕ Error during generation: {e}[/bold red]")
        return None

    if not response_text.strip() and last_tool_output:
        response_text = str(last_tool_output)

    if response_text.strip():
        console.print("\n[bold cyan]Engineer:[/bold cyan]")
        console.print(Markdown(response_text))

    console.print()
    return response_text


async def get_dynamic_welcome() -> str:
    """Build a dynamic welcome line showing next race and current champion."""
    try:
        import fastf1
        remaining = fastf1.get_events_remaining()
        if not remaining.empty:
            next_event = remaining.iloc[0]
            name = next_event.get('EventName', '')
            date = next_event['EventDate'].strftime('%d %b %Y')
            return f"Next race: [bold]{name}[/bold] on [cyan]{date}[/cyan]"
    except Exception:
        pass
    return f"Season: [bold]{DATA_DEFAULT_YEAR}[/bold]"


def print_help():
    """Print all available commands."""
    commands = {
        "/weather": "Check live track weather",
        "/positions": "Live track position map",
        "/standings": "Current championship standings",
        "/next": "Next race preview",
        "/last": "Last race results",
        "/monitor": "Launch live race monitor dashboard",
        "/stats": "Performance stats and cache info",
        "/history [N]": "Show last N messages (default 10)",
        "/save [file]": "Save conversation to Markdown file",
        "/open": "Re-open the last generated plot/file",
        "/year [YYYY]": "Switch default season year",
        "/clear": "Clear conversation history (keep system prompt)",
        "/help": "Show this help",
        "quit / exit / q": "Exit the agent",
    }
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    for cmd, desc in commands.items():
        console.print(f"  [yellow]{cmd:<22}[/yellow] {desc}")
    console.print()


async def main_async():
    """Main interactive loop for the F1 agent"""
    global _last_generated_file

    # Initialize systems
    llm, QuickLookupBypass = initialize_systems()

    # Wire up LangGraph persistent checkpointing
    checkpointer = None
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3
        db_path = os.path.join("cache", "agent_memory.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        logger.info(f"Persistent memory enabled: {db_path}")
    except Exception as e:
        logger.warning(f"Could not enable persistent memory: {e}. Running without checkpointer.")

    # Create agent
    agent = create_f1_agent(llm, checkpointer=checkpointer)

    # Initialize quick lookup bypass
    bypass = QuickLookupBypass()

    # Build dynamic welcome
    dynamic_line = await get_dynamic_welcome()

    active_model = GEMINI_MODEL if LLM_PROVIDER == "gemini" else LLM_MODEL
    provider_label = "Gemini" if LLM_PROVIDER == "gemini" else "Ollama"
    console.print(Panel(
        f"[bold green]F1 Race Engineer Online[/bold green]\n"
        f"Date: [cyan]{TODAY}[/cyan] | "
        f"Model: [yellow]{active_model}[/yellow] via [yellow]{provider_label}[/yellow]\n"
        f"{dynamic_line}\n"
        f"Type [yellow]/help[/yellow] for commands or [yellow]quit[/yellow] to exit.",
        title="🏎️  F1 RACE ENGINEER",
        border_style="green"
    ))

    chat_history = [get_system_prompt()]
    current_year = DATA_DEFAULT_YEAR

    while True:
        try:
            user_input = console.input("\n[bold yellow]You:[/bold yellow] ")
            user_input_stripped = user_input.strip()

            if not user_input_stripped:
                continue

            # ── Exit ──────────────────────────────────────────────────────────
            if user_input_stripped.lower() in ["quit", "exit", "q"]:
                console.print(f"\n[green]Session complete. {metrics.get_summary()}[/green]")
                console.print("[green]Goodbye! 🏁[/green]")
                break

            # ── /help ─────────────────────────────────────────────────────────
            if user_input_stripped.lower() in ["/help", "help"]:
                print_help()
                continue

            # ── /stats ────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/stats":
                console.print(metrics.get_summary())
                cache = get_cache()
                stats = cache.get_stats()
                console.print(f"\n[cyan]Cache:[/cyan] {stats['total_entries']} entries, "
                              f"{stats['total_size_mb']:.2f}MB")
                continue

            # ── /clear ────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/clear":
                chat_history = [get_system_prompt()]
                console.print("[green]Conversation history cleared.[/green]")
                continue

            # ── /history [N] ──────────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/history"):
                parts = user_input_stripped.split()
                n = 10
                if len(parts) > 1 and parts[1].isdigit():
                    n = int(parts[1])
                history_msgs = chat_history[-n:]
                for msg in history_msgs:
                    role = "You" if isinstance(msg, HumanMessage) else "Engineer"
                    color = "yellow" if isinstance(msg, HumanMessage) else "cyan"
                    preview = str(msg.content)[:200] + ("..." if len(str(msg.content)) > 200 else "")
                    console.print(f"[{color}]{role}:[/{color}] {preview}")
                continue

            # ── /save [filename] ──────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/save"):
                parts = user_input_stripped.split(maxsplit=1)
                fname = parts[1] if len(parts) > 1 else f"f1_conversation_{TODAY}.md"
                if not fname.endswith(".md"):
                    fname += ".md"
                lines = [f"# F1 Agent Conversation — {TODAY}\n"]
                for msg in chat_history[1:]:  # skip system prompt
                    role = "**You**" if isinstance(msg, HumanMessage) else "**Engineer**"
                    lines.append(f"\n{role}: {msg.content}\n")
                with open(fname, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                console.print(f"[green]Conversation saved to {fname}[/green]")
                continue

            # ── /open ─────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/open":
                if _last_generated_file and os.path.exists(_last_generated_file):
                    open_file(_last_generated_file)
                    console.print(f"[green]Opening: {_last_generated_file}[/green]")
                else:
                    console.print("[yellow]No file has been generated in this session yet.[/yellow]")
                continue

            # ── /year [YYYY] ──────────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/year"):
                parts = user_input_stripped.split()
                if len(parts) > 1 and parts[1].isdigit():
                    current_year = int(parts[1])
                    console.print(f"[green]Default year set to {current_year}[/green]")
                else:
                    console.print(f"[yellow]Current default year: {current_year}[/yellow]")
                continue

            # ── /monitor ──────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/monitor":
                console.print("[cyan]Initializing Live Monitor...[/cyan]")
                monitor = LiveRaceMonitor()
                await monitor.start_monitoring()
                continue

            # ── /clear cache ──────────────────────────────────────────────────
            if user_input_stripped.lower() in ["/clearcache", "/clear cache"]:
                cache = get_cache()
                cache.clear()
                console.print("[green]Cache cleared.[/green]")
                continue

            # ── Shorthand aliases ─────────────────────────────────────────────
            aliases = {
                "/weather": "What's the current weather at the track?",
                "/positions": "Show me the current race positions on track",
                "/standings": "What are the current championship standings?",
                "/next": "When and where is the next race?",
                "/last": "What were the results of the last race?",
            }
            if user_input_stripped.lower() in aliases:
                user_input_stripped = aliases[user_input_stripped.lower()]
                console.print(f"[dim]→ {user_input_stripped}[/dim]")

            # ── Quick lookup bypass ───────────────────────────────────────────
            bypass_match = bypass.match(user_input_stripped)
            if bypass_match:
                console.print(f"[cyan]⚡ Quick lookup: {bypass_match['name']}[/cyan]")
                start_time = time.time()
                try:
                    result = await bypass.execute(bypass_match)
                    elapsed = time.time() - start_time

                    # Auto-open any file in the result
                    file_path = extract_file_path(str(result))
                    if file_path and os.path.exists(file_path):
                        _last_generated_file = file_path
                        open_file(file_path)

                    console.print("\n[bold cyan]Engineer:[/bold cyan]")
                    console.print(Markdown(str(result)))
                    metrics.record_query(elapsed)
                    display_status(bypass_match["name"], "DONE", elapsed, mode="Quick Lookup")
                    chat_history.append(HumanMessage(content=user_input_stripped))
                    chat_history.append(AIMessage(content=result))
                    continue
                except Exception as e:
                    console.print(f"[yellow]⚠ Bypass failed, using full agent: {e}[/yellow]")

            # ── Full agent path ───────────────────────────────────────────────
            chat_history.append(HumanMessage(content=user_input_stripped))
            start_time = time.time()

            response_text = await stream_agent_response(agent, chat_history)

            elapsed = time.time() - start_time
            metrics.record_query(elapsed)

            display_status("Response Complete", "DONE", elapsed, mode="Agent")

            if response_text:
                chat_history.append(AIMessage(content=response_text))
                # Keep last 20 turns + system prompt
                if len(chat_history) > 21:
                    chat_history = [chat_history[0]] + chat_history[-20:]

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")

        except Exception as e:
            error_msg = str(e)
            if "memory" in error_msg.lower():
                console.print("\n[bold red]✕ ERROR: Out of memory. Try a smaller model.[/bold red]")
            elif "not found" in error_msg.lower():
                console.print(f"\n[bold red]✕ ERROR: Model not found. Run 'ollama pull {LLM_MODEL}'[/bold red]")
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                console.print("\n[bold red]✕ ERROR: Cannot connect to Ollama. Run 'ollama serve'[/bold red]")
            else:
                console.print(f"\n[bold red]✕ Unexpected Error: {e}[/bold red]")
            logger.error(f"Main loop error: {e}")
            display_status("Error Handler", "ERROR", 0.0)


def main():
    """Synchronous wrapper for async main loop"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        wrapper = get_async_wrapper()
        wrapper.shutdown()
        console.print("[dim]Async tools shut down.[/dim]")


if __name__ == "__main__":
    main()

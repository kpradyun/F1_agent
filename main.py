"""
F1 Race Engineer Agent - Main Entry Point

A clean CLI interface for the F1 analysis agent.
"""
import sys
import os
import time
import asyncio
import logging
import logging.handlers
import subprocess
import warnings
from dataclasses import dataclass, field
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
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
        logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)
logging.getLogger().handlers[-1].setLevel(logging.WARNING)

for name in logging.root.manager.loggerDict:
    if 'langchain' not in name.lower() and 'f1_data_miner' not in name.lower() and 'fastf1' not in name.lower():
        logging.getLogger(name).setLevel(logging.WARNING)
    else:
        logging.getLogger(name).setLevel(getattr(logging, LOG_LEVEL))

logger = logging.getLogger("F1_Agent")
console = Console()
metrics = PerformanceMetrics()

MAX_HISTORY_TURNS = 20  # Keep last N turns + system prompt


@dataclass
class SessionState:
    last_generated_file: str | None = None
    current_year: int = DATA_DEFAULT_YEAR
    chat_history: list = field(default_factory=list)


def open_file(path: str) -> None:
    """Open a file with the system default viewer."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
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


def display_status(status: str, duration: float = 0.0, mode: str = "Agent") -> None:
    """Display completion status with timing and mode indicator."""
    color_map = {"DONE": "green", "ERROR": "red"}
    mode_color = "cyan" if mode == "Quick Lookup" else "yellow"
    console.print(
        f"[dim][{color_map.get(status, 'white')}]{status}[/{color_map.get(status, 'white')}] "
        f"[{mode_color}]({mode})[/{mode_color}] "
        f"[dim]{duration:.2f}s[/dim][/dim]"
    )


def print_error(message: str, hint: str = "") -> None:
    """Display a structured error panel."""
    body = f"[bold]{message}[/bold]"
    if hint:
        body += f"\n[dim]{hint}[/dim]"
    console.print(Panel(body, title="[bold red]Error[/bold red]", border_style="red", padding=(0, 2)))


_TOOL_ICONS: dict[str, str] = {
    "lookup":    "🔍",
    "search":    "🔍",
    "standings": "🏆",
    "champion":  "🏆",
    "plot":      "📊",
    "chart":     "📊",
    "visual":    "📊",
    "predict":   "🔮",
    "weather":   "🌦️",
    "live":      "📡",
    "radio":     "📻",
    "replay":    "▶️ ",
    "strategy":  "♟️ ",
}


def _tool_icon(name: str) -> str:
    lname = name.lower()
    for keyword, icon in _TOOL_ICONS.items():
        if keyword in lname:
            return icon
    return "⚙️ "


async def stream_agent_response(agent, messages) -> tuple[str, float] | None:
    """
    Stream agent execution with progressive display.
    Shows tool execution in real-time and streams text as it's generated.
    Returns (response_text, elapsed) or None on unrecoverable error.
    """
    config = RunnableConfig(
        recursion_limit=15,
        configurable={"thread_id": "main"}
    )

    response_text = ""
    last_tool_output = None
    tool_count = 0
    start_time = time.time()

    # state.last_generated_file is updated via the caller after we return
    _file_found: list[str] = []

    try:
        async for event in agent.astream({"messages": messages}, config=config, stream_mode="values"):
            if "messages" not in event:
                continue

            msg = event["messages"][-1]

            if msg.type == "tool":
                tool_name = getattr(msg, 'name', 'Unknown')
                tool_output = getattr(msg, 'content', '')
                tool_count += 1

                icon = _tool_icon(tool_name)
                console.print(f"  [dim]{icon}  {tool_name.replace('_', ' ').title()}…[/dim]")
                metrics.record_tool(tool_name)

                last_tool_output = tool_output

                # Auto-detect and open generated files
                file_path = extract_file_path(str(tool_output))
                if file_path and os.path.exists(file_path):
                    _file_found.append(file_path)
                    open_file(file_path)
                    console.print(f"[dim green]Opened: {file_path}[/dim green]")

                if any(keyword in tool_name.lower() for keyword in
                       ['strategy', 'plot', 'chart', 'visual', 'replay', 'head_to_head',
                        'summary', 'stats', 'champions', 'radio', 'media', 'results',
                        'session', 'classification', 'standings', 'predict', 'form']):
                    console.print(f"\n[dim]{tool_output}[/dim]")

            elif msg.type == "ai" and not msg.tool_calls:
                response_text = msg.content

    except Exception as e:
        error_msg = str(e)
        if "memory" in error_msg.lower():
            print_error(
                "System out of memory for this model.",
                "Try a smaller one in config/settings.py."
            )
        elif "not found" in error_msg.lower():
            print_error(
                f"Model '{LLM_MODEL}' not found.",
                f"Run 'ollama pull {LLM_MODEL}' or check config."
            )
        else:
            print_error(f"Error during generation: {e}")
        return None

    if not response_text.strip() and last_tool_output:
        response_text = str(last_tool_output)

    elapsed = time.time() - start_time

    if response_text.strip():
        console.print(Panel(
            Markdown(response_text),
            title="[bold cyan]F1 Race Engineer[/bold cyan]",
            subtitle=f"[dim]{elapsed:.2f}s · {tool_count} tool{'s' if tool_count != 1 else ''} used[/dim]",
            border_style="cyan",
            padding=(1, 2),
        ))

    # Surface any discovered file path to caller via a side-channel attribute
    stream_agent_response._last_file = _file_found[0] if _file_found else None

    return response_text, elapsed


async def get_dynamic_welcome() -> str | None:
    """Return a formatted next-race string, or None if season is complete."""
    try:
        import fastf1
        remaining = fastf1.get_events_remaining()
        if not remaining.empty:
            evt = remaining.iloc[0]
            name = evt.get("EventName", "")
            date = evt["EventDate"].strftime("%d %b %Y")
            location = evt.get("Location", "")
            loc_part = f" · [cyan]{location}[/cyan]" if location else ""
            return f"[bold]{name}[/bold]{loc_part} · [yellow]{date}[/yellow]"
    except Exception:
        pass
    return None


stream_agent_response._last_file = None


def print_help() -> None:
    """Render help as a structured table inside a panel."""
    tbl = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
        show_lines=False,
        expand=False,
    )
    tbl.add_column("Command",     style="bold yellow", no_wrap=True, min_width=20)
    tbl.add_column("Description", style="white")

    rows = [
        # Live Race
        ("/weather",      "Current track weather conditions"),
        ("/positions",    "Live track position map"),
        ("/monitor",      "Launch live race monitoring dashboard"),
        ("", ""),
        # Season Data
        ("/standings",    "Current championship standings"),
        ("/next",         "Next race preview and circuit info"),
        ("/last",         "Last race results and podium"),
        ("", ""),
        # Session
        ("/stats",        "Performance metrics and cache info"),
        ("/history [N]",  "Show last N messages  (default 10)"),
        ("/save [file]",  "Save conversation to a Markdown file"),
        ("/open",         "Re-open the last generated plot / file"),
        ("/year [YYYY]",  "Switch default season year"),
        ("/clear",        "Clear conversation history"),
        ("/version",      "Show agent version"),
        ("/help",         "Show this help"),
        ("quit / exit",   "Exit the agent"),
    ]

    for cmd, desc in rows:
        tbl.add_row(cmd, desc)

    console.print(Panel(
        tbl,
        title="[bold cyan]F1 Race Engineer — Help[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))

    examples = Table(box=None, show_header=False, padding=(0, 2))
    examples.add_column(style="dim cyan")
    for q in [
        '"Who won the last race?"',
        '"Show me Hamilton vs Verstappen lap times at Silverstone 2024"',
        '"What are the current championship standings?"',
        '"Predict the tyre strategy for the next race"',
        '"Plot the gap evolution from Monaco 2024"',
    ]:
        examples.add_row(q)

    console.print(Panel(
        examples,
        title="[yellow]Example Queries[/yellow]",
        border_style="dim yellow",
        padding=(0, 1),
    ))
    console.print()


async def main_async() -> None:
    """Main interactive loop for the F1 agent"""

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
    dynamic_next_race = await get_dynamic_welcome()

    active_model = GEMINI_MODEL if LLM_PROVIDER == "gemini" else LLM_MODEL
    provider_label = "Gemini" if LLM_PROVIDER == "gemini" else "Ollama"

    # Build a clean two-column info table
    info_tbl = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    info_tbl.add_column(style="dim", no_wrap=True)
    info_tbl.add_column(style="bold white")
    info_tbl.add_row("Model", f"{active_model}  [dim]via[/dim]  {provider_label}")
    info_tbl.add_row("Date", TODAY)
    info_tbl.add_row("Season", str(DATA_DEFAULT_YEAR))
    if dynamic_next_race:
        info_tbl.add_row("Next race", dynamic_next_race)
    info_tbl.add_row("", "")
    info_tbl.add_row("", "[dim]Type [bold cyan]/help[/bold cyan] for commands · [bold cyan]quit[/bold cyan] to exit[/dim]")

    console.print(Panel(
        info_tbl,
        title="[bold white]🏎️  F1 RACE ENGINEER[/bold white]",
        border_style="green",
        padding=(1, 3),
    ))

    state = SessionState(chat_history=[get_system_prompt()])

    while True:
        try:
            console.print(Rule(style="dim"))
            user_input = console.input("\n[bold yellow]›[/bold yellow] ")
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

            # ── /version ──────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/version":
                try:
                    from importlib.metadata import version as _ver
                    v = _ver("f1-race-engineer-agent")
                except Exception:
                    v = "dev"
                console.print(f"[cyan]F1 Race Engineer Agent[/cyan] v{v}")
                continue

            # ── /stats ────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/stats":
                s = metrics.get_stats()
                cache_s = get_cache().get_stats()
                tbl = Table(box=None, show_header=False, padding=(0, 2))
                tbl.add_column(style="dim", no_wrap=True)
                tbl.add_column(style="bold white")
                tbl.add_row("Queries", str(s["queries"]))
                tbl.add_row("Avg response", f"{s['avg_time']:.2f}s")
                tbl.add_row("Top tools", ", ".join(s["top_tools"]) if s["top_tools"] else "none")
                tbl.add_row("Cache entries", str(cache_s["total_entries"]))
                tbl.add_row("Cache size", f"{cache_s['total_size_mb']:.2f} MB")
                tbl.add_row("Cache hit rate", f"{cache_s.get('hit_rate', 0):.1f}%")
                console.print(Panel(tbl, title="[bold cyan]Session Statistics[/bold cyan]", border_style="cyan"))
                continue

            # ── /clear ────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/clear":
                state.chat_history = [get_system_prompt()]
                console.print("[green]Conversation history cleared.[/green]")
                continue

            # ── /history [N] ──────────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/history"):
                parts = user_input_stripped.split()
                n = 10
                if len(parts) > 1 and parts[1].isdigit():
                    n = int(parts[1])
                history_msgs = state.chat_history[-n:]
                for i, msg in enumerate(history_msgs):
                    role = "You" if isinstance(msg, HumanMessage) else "Engineer"
                    color = "yellow" if isinstance(msg, HumanMessage) else "cyan"
                    preview = str(msg.content)[:280] + ("…" if len(str(msg.content)) > 280 else "")
                    console.print(f"[dim]({i+1:>2})[/dim]  [{color}]{role}:[/{color}] {preview}")
                    console.print()
                continue

            # ── /save [filename] ──────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/save"):
                from datetime import datetime as _dt
                parts = user_input_stripped.split(maxsplit=1)
                ts = _dt.now().strftime("%H%M")
                fname = parts[1] if len(parts) > 1 else f"f1_session_{TODAY}_{ts}.md"
                if not fname.endswith(".md"):
                    fname += ".md"
                turns = [m for m in state.chat_history[1:] if isinstance(m, (HumanMessage, AIMessage))]
                front = (
                    f"---\ntitle: F1 Agent Conversation\ndate: {TODAY}\n"
                    f"model: {active_model}\nturns: {len(turns)}\n---\n\n"
                )
                lines = [front]
                for msg in turns:
                    role = "**You**" if isinstance(msg, HumanMessage) else "**Engineer**"
                    lines.append(f"{role}: {msg.content}\n\n---\n\n")
                with open(fname, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                console.print(Panel(f"Saved to [bold]{fname}[/bold]", border_style="green", padding=(0, 2)))
                continue

            # ── /open ─────────────────────────────────────────────────────────
            if user_input_stripped.lower() == "/open":
                if state.last_generated_file and os.path.exists(state.last_generated_file):
                    open_file(state.last_generated_file)
                    console.print(f"[green]Opening: {state.last_generated_file}[/green]")
                else:
                    console.print("[yellow]No file has been generated in this session yet.[/yellow]")
                continue

            # ── /year [YYYY] ──────────────────────────────────────────────────
            if user_input_stripped.lower().startswith("/year"):
                parts = user_input_stripped.split()
                if len(parts) > 1 and parts[1].isdigit():
                    state.current_year = int(parts[1])
                    console.print(f"[green]Default year set to {state.current_year}[/green]")
                else:
                    console.print(f"[yellow]Current default year: {state.current_year}[/yellow]")
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
                        state.last_generated_file = file_path
                        open_file(file_path)

                    console.print(Panel(
                        Markdown(str(result)),
                        title="[bold cyan]F1 Race Engineer[/bold cyan]",
                        subtitle=f"[dim]⚡ Quick Lookup · {elapsed:.2f}s[/dim]",
                        border_style="cyan",
                        padding=(1, 2),
                    ))
                    metrics.record_query(elapsed)
                    state.chat_history.append(HumanMessage(content=user_input_stripped))
                    state.chat_history.append(AIMessage(content=result))
                    continue
                except Exception as e:
                    console.print(f"[yellow]⚠ Bypass failed, using full agent: {e}[/yellow]")

            # ── Full agent path ───────────────────────────────────────────────
            state.chat_history.append(HumanMessage(content=user_input_stripped))

            result = await stream_agent_response(agent, state.chat_history)

            if result is not None:
                response_text, elapsed = result
                metrics.record_query(elapsed)

                # Pick up any file discovered during streaming
                discovered_file = stream_agent_response._last_file
                if discovered_file:
                    state.last_generated_file = discovered_file

                if response_text:
                    state.chat_history.append(AIMessage(content=response_text))
                    # Keep last N turns + system prompt
                    if len(state.chat_history) > MAX_HISTORY_TURNS + 1:
                        state.chat_history = [state.chat_history[0]] + state.chat_history[-MAX_HISTORY_TURNS:]

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")

        except Exception as e:
            error_msg = str(e)
            if "memory" in error_msg.lower():
                print_error("Out of memory.", "Try a smaller model.")
            elif "not found" in error_msg.lower():
                print_error("Model not found.", f"Run 'ollama pull {LLM_MODEL}'")
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                print_error("Cannot connect to Ollama.", "Run 'ollama serve'")
            else:
                print_error(f"Unexpected Error: {e}")
            logger.error(f"Main loop error: {e}")
            display_status("ERROR", 0.0)


def main() -> None:
    """Synchronous wrapper for async main loop"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        get_cache().close()
        wrapper = get_async_wrapper()
        wrapper.shutdown()
        console.print("[dim]Async tools shut down.[/dim]")


if __name__ == "__main__":
    main()

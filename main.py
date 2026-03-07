"""
F1 Race Engineer Agent - Main Entry Point

A clean CLI interface for the F1 analysis agent.
Heavy logic extracted to core/ and utils/ modules.
"""
import sys
import time
import asyncio
import logging
import warnings
from rich.console import Console
from rich.panel import Panel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

warnings.filterwarnings("ignore")

from config.settings import TODAY, LOG_LEVEL, LOG_FORMAT, LOG_FILE
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

def display_status(tool_name: str, status: str, duration: float = 0.0):
    """Display agent status in a formatted panel."""
    color_map = {
        "EXECUTING": "yellow",
        "DONE": "green",
        "ERROR": "red"
    }
    
    panel = Panel(
        f"[bold]{status}[/bold] | Tool: [cyan]{tool_name}[/cyan] | {duration:.2f}s",
        title="🏎️ F1 Agent Status",
        expand=False,
        border_style=color_map.get(status, "white")
    )
    console.print(panel)

async def stream_agent_response(agent, messages):
    """
    Stream agent execution with progressive display.
    Shows tool execution in real-time and streams text as it's generated.
    """
    config = RunnableConfig(
        recursion_limit=10,
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
            
            # Tool execution
            if msg.type == "tool":
                tool_name = getattr(msg, 'name', 'Unknown')
                tool_output = getattr(msg, 'content', '')
                
                # Show tool execution in a nice way
                icon = "🔍" if "lookup" in tool_name.lower() or "search" in tool_name.lower() else "🏎️"
                if "all_time" in tool_name.lower(): icon = "🏆"
                
                console.print(f"[yellow]{icon} Executing: {tool_name}...[/yellow]")
                metrics.record_tool(tool_name)
                
                last_tool_output = tool_output
                
                # Print tool output for certain tools
                if any(keyword in tool_name.lower() for keyword in 
                       ['strategy', 'plot', 'chart', 'visual', 'replay', 'head_to_head', 'summary', 'stats', 'champions', 'radio', 'media', 'results', 'session', 'classification']):
                    console.print(f"\n[dim]{tool_output}[/dim]")
            
            # AI response streaming
            elif msg.type == "ai" and not msg.tool_calls:
                if not response_started:
                    console.print("\n[bold cyan]Engineer:[/bold cyan] ", end="")
                    response_started = True
                
                new_text = msg.content[len(response_text):]
                if new_text:
                    console.print(new_text, end="")
                    response_text = msg.content
    except Exception as e:
        # Handle LLM errors gracefully during streaming
        error_msg = str(e)
        if "memory" in error_msg.lower():
            console.print("\n[bold red]✕ Error: System out of memory for this model. Try a smaller one in config/settings.py.[/bold red]")
        elif "not found" in error_msg.lower():
            console.print(f"\n[bold red]✕ Error: Model '{LLM_MODEL}' not found. Please run 'ollama pull {LLM_MODEL}' or check config.[/bold red]")
        else:
            console.print(f"\n[bold red]✕ Error during generation: {e}[/bold red]")
        return None
    
    if not response_text.strip() and last_tool_output:
        console.print(f"\n[bold cyan]Engineer:[/bold cyan] {last_tool_output}")
        response_text = last_tool_output
    
    console.print()
    return response_text

async def main_async():
    """Main interactive loop for the F1 agent"""
    
    # Initialize systems
    llm, QuickLookupBypass = initialize_systems()
    
    # Create agent
    agent = create_f1_agent(llm)
    
    # Initialize quick lookup bypass
    bypass = QuickLookupBypass()
    console.print("[dim]Quick lookup bypass enabled for instant responses[/dim]")
    
    # Welcome banner
    console.print(Panel(
        f"[bold green]F1 Hybrid Agent Online[/bold green]\n"
        f"Date: {TODAY}\n"
        f"Type 'quit', 'exit', or '/stats' to check performance",
        title="F1 RACE ENGINEER",
        border_style="green"
    ))

    chat_history = [get_system_prompt()]

    while True:
        try:
            user_input = console.input("\n[bold yellow]You:[/bold yellow] ")
            
            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("[green]Goodbye! 🏁[/green]")
                console.print(metrics.get_summary())
                break
            
            if user_input.lower() == "/stats":
                console.print(metrics.get_summary())
                cache = get_cache()
                cache_stats = cache.get_stats()
                console.print(f"\n[cyan]Cache Statistics:[/cyan]")
                console.print(f"- Total Entries: {cache_stats['total_entries']}")
                console.print(f"- Size: {cache_stats['total_size_mb']:.2f}MB")
                console.print(f"- Categories: {cache_stats['categories']}")
                continue

            if not user_input.strip():
                continue
            
            quick_commands = {
                "/weather": "What's the current weather at the track?",
                "/positions": "Show me the current race positions",
                "/standings": "What are the current championship standings?",
                "/next": "When is the next race?",
                "/last": "What were the results of the last race?",
                "/clear": "clear_cache",
                "/monitor": "monitor",
                "/help": "Available commands: /weather, /positions, /standings, /next, /last, /stats, /monitor, /clear, /help"
            }
            
            if user_input.lower() in quick_commands:
                if user_input.lower() == "/help":
                    console.print(f"[yellow]{quick_commands['/help']}[/yellow]")
                    continue
                elif user_input.lower() == "/monitor":
                    console.print("[cyan]Initializing Live Monitor...[/cyan]")
                    monitor = LiveRaceMonitor()
                    await monitor.start_monitoring()
                    continue
                elif user_input.lower() == "/clear":
                    cache = get_cache()
                    cache.clear()
                    console.print("[green]Cache cleared[/green]")
                    continue
                else:
                    user_input = quick_commands[user_input.lower()]
                    console.print(f"[dim]→ {user_input}[/dim]")

            # Check for quick lookup bypass
            bypass_match = bypass.match(user_input)
            if bypass_match:
                console.print(f"[cyan]Quick lookup: {bypass_match['name']}[/cyan]")
                start_time = time.time()
                
                try:
                    result = await bypass.execute(bypass_match)
                    elapsed = time.time() - start_time
                    
                    console.print(f"\n[bold cyan]Engineer:[/bold cyan] {result}")
                    metrics.record_query(elapsed)
                    
                    display_status(
                        tool_name=f"Quick Lookup: {bypass_match['name']}",
                        status="DONE",
                        duration=elapsed
                    )
                    
                    chat_history.append(HumanMessage(content=user_input))
                    chat_history.append(AIMessage(content=result))
                    
                    continue
                except Exception as e:
                    console.print(f"[yellow]⚠ Bypass failed, using full agent: {e}[/yellow]")

            chat_history.append(HumanMessage(content=user_input))
            start_time = time.time()

            response_text = await stream_agent_response(agent, chat_history)
            
            elapsed = time.time() - start_time
            metrics.record_query(elapsed)
            
            display_status(
                tool_name="Response Complete",
                status="DONE",
                duration=elapsed
            )

            if response_text:
                chat_history.append(AIMessage(content=response_text))
                
                if len(chat_history) > 21:
                    chat_history = [chat_history[0]] + chat_history[-20:]

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            break
            
        except Exception as e:
            error_msg = str(e)
            if "memory" in error_msg.lower():
                console.print("\n[bold red]✕ ERROR: System out of memory. Try switching to a smaller model (e.g., llama3.2).[/bold red]")
            elif "not found" in error_msg.lower():
                console.print(f"\n[bold red]✕ ERROR: Model not found. Run 'ollama pull {LLM_MODEL}' or check config/settings.py.[/bold red]")
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                console.print("\n[bold red]✕ ERROR: Cannot connect to Ollama. Is it running? (Try 'ollama serve')[/bold red]")
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
        console.print("[dim]Async tools shut down[/dim]")

if __name__ == "__main__":
    main()
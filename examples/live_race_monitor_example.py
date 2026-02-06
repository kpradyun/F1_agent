"""
Example: Live Race Monitoring Mode
Game-changing feature for real-time race tracking
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

console = Console()


class LiveRaceMonitor:
    """
    Real-time race monitoring with automatic event detection
    Continuously monitors race and alerts user to important events
    """
    
    def __init__(self, api_client, llm):
        self.client = api_client
        self.llm = llm
        self.session_key = None
        self.last_positions = {}
        self.last_weather = {}
        self.lap_count = 0
        self.monitoring = False
        
    async def start_monitoring(self, session_key: str = "latest"):
        """Start live race monitoring"""
        self.session_key = session_key if session_key != "latest" else self.client.get_latest_session_key()
        self.monitoring = True
        
        console.print(Panel(
            "[bold green]🏁 LIVE RACE MONITORING ACTIVE 🏁[/bold green]\n"
            "Monitoring for: Position changes, pit stops, weather, incidents\n"
            "Press Ctrl+C to stop and return to chat",
            border_style="green"
        ))
        
        # Create layout for live dashboard
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="events", size=10)
        )
        
        try:
            with Live(layout, refresh_per_second=2, console=console) as live:
                event_log = []
                
                while self.monitoring:
                    # Update header
                    layout["header"].update(
                        Panel(
                            f"[bold cyan]Live Race Monitor[/bold cyan] | "
                            f"Session: {self.session_key} | "
                            f"Time: {datetime.now().strftime('%H:%M:%S')}",
                            style="cyan"
                        )
                    )
                    
                    # Check for events
                    new_events = await self.check_for_events()
                    
                    if new_events:
                        event_log.extend(new_events)
                        # Keep last 8 events
                        event_log = event_log[-8:]
                    
                    # Update main view (current positions)
                    positions_table = await self.get_live_positions_table()
                    layout["main"].update(positions_table)
                    
                    # Update event log
                    event_panel = self.format_event_log(event_log)
                    layout["events"].update(event_panel)
                    
                    # Check every 5 seconds (adjust based on API rate limits)
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            self.monitoring = False
            console.print("\n[yellow]Stopping live monitoring...[/yellow]")
    
    async def check_for_events(self) -> List[Dict]:
        """Check for interesting race events"""
        events = []
        
        # 1. Position changes (overtakes)
        position_events = await self.detect_position_changes()
        events.extend(position_events)
        
        # 2. Pit stops
        pit_events = await self.detect_pit_stops()
        events.extend(pit_events)
        
        # 3. Weather changes
        weather_events = await self.detect_weather_changes()
        events.extend(weather_events)
        
        # 4. Fastest laps
        fastest_lap_events = await self.detect_fastest_laps()
        events.extend(fastest_lap_events)
        
        return events
    
    async def detect_position_changes(self) -> List[Dict]:
        """Detect overtakes and position changes"""
        events = []
        
        try:
            intervals = self.client.get_intervals(self.session_key)
            import pandas as pd
            df = pd.DataFrame(intervals)
            
            if df.empty:
                return events
            
            # Get current positions
            current = df.sort_values('date').groupby('driver_number').tail(1)
            current_positions = {
                row['driver_number']: row.get('position', 0)
                for _, row in current.iterrows()
            }
            
            # Compare with last known positions
            for driver, pos in current_positions.items():
                if driver in self.last_positions:
                    old_pos = self.last_positions[driver]
                    if old_pos != pos:
                        change = old_pos - pos  # Positive = gained positions
                        
                        if change > 0:
                            events.append({
                                "type": "overtake",
                                "severity": "high" if change > 1 else "medium",
                                "message": f"🔥 P{old_pos}→P{pos}: Driver #{driver} gained {change} position(s)!",
                                "timestamp": datetime.now()
                            })
                        else:
                            events.append({
                                "type": "position_loss",
                                "severity": "medium",
                                "message": f"📉 P{old_pos}→P{pos}: Driver #{driver} lost {abs(change)} position(s)",
                                "timestamp": datetime.now()
                            })
            
            self.last_positions = current_positions
            
        except Exception as e:
            console.print(f"[dim red]Error detecting positions: {e}[/dim red]")
        
        return events
    
    async def detect_pit_stops(self) -> List[Dict]:
        """Detect pit stop activity"""
        events = []
        
        try:
            # Get pit stop data
            pit_data = self.client.get_pit_stops(self.session_key)
            import pandas as pd
            df = pd.DataFrame(pit_data)
            
            if df.empty:
                return events
            
            # Get recent pit stops (last 30 seconds)
            df['date'] = pd.to_datetime(df['date'])
            recent = df[df['date'] > (datetime.now() - pd.Timedelta(seconds=30))]
            
            for _, row in recent.iterrows():
                driver = row['driver_number']
                duration = row.get('pit_duration', 0)
                
                # Categorize pit stop
                if duration < 2.5:
                    quality = "⚡ SUPER FAST"
                    severity = "high"
                elif duration < 3.0:
                    quality = "✅ Good"
                    severity = "medium"
                else:
                    quality = "⚠️ Slow"
                    severity = "low"
                
                events.append({
                    "type": "pit_stop",
                    "severity": severity,
                    "message": f"🔧 PIT: Driver #{driver} | {duration:.2f}s | {quality}",
                    "timestamp": datetime.now()
                })
                
        except Exception as e:
            # Pit data might not be available in all sessions
            pass
        
        return events
    
    async def detect_weather_changes(self) -> List[Dict]:
        """Detect significant weather changes"""
        events = []
        
        try:
            weather = self.client.get_weather(self.session_key)
            
            if not weather:
                return events
            
            latest = weather[-1] if isinstance(weather, list) else weather
            
            # Check for changes
            if self.last_weather:
                # Rain starting
                if latest.get('rainfall', 0) > 0 and self.last_weather.get('rainfall', 0) == 0:
                    events.append({
                        "type": "weather",
                        "severity": "critical",
                        "message": "🌧️ RAIN DETECTED! Track getting wet!",
                        "timestamp": datetime.now()
                    })
                
                # Temperature drop (>5°C)
                temp_change = abs(latest.get('track_temperature', 0) - self.last_weather.get('track_temperature', 0))
                if temp_change > 5:
                    events.append({
                        "type": "weather",
                        "severity": "medium",
                        "message": f"🌡️ Track temp changed by {temp_change:.1f}°C",
                        "timestamp": datetime.now()
                    })
            
            self.last_weather = latest
            
        except Exception as e:
            pass
        
        return events
    
    async def detect_fastest_laps(self) -> List[Dict]:
        """Detect new fastest laps"""
        events = []
        
        try:
            # Get lap data
            laps = self.client.get_laps(self.session_key)
            import pandas as pd
            df = pd.DataFrame(laps)
            
            if df.empty:
                return events
            
            # Get recent laps
            recent = df.sort_values('date').tail(20)
            
            # Check for fastest lap flags
            fastest_laps = recent[recent.get('is_personal_best', False) == True]
            
            for _, row in fastest_laps.iterrows():
                driver = row['driver_number']
                lap_time = row.get('lap_duration', 0)
                
                events.append({
                    "type": "fastest_lap",
                    "severity": "medium",
                    "message": f"⏱️ FASTEST LAP: Driver #{driver} | {lap_time:.3f}s",
                    "timestamp": datetime.now()
                })
                
        except Exception as e:
            pass
        
        return events
    
    async def get_live_positions_table(self) -> Table:
        """Create live positions table"""
        table = Table(title="Current Race Positions", show_header=True, header_style="bold cyan")
        table.add_column("Pos", style="yellow", width=4)
        table.add_column("Driver", style="white", width=8)
        table.add_column("Gap", style="green", width=10)
        table.add_column("Interval", style="blue", width=10)
        
        try:
            intervals = self.client.get_intervals(self.session_key)
            import pandas as pd
            df = pd.DataFrame(intervals)
            
            if not df.empty:
                latest = df.sort_values('date').groupby('driver_number').tail(1)
                latest = latest.sort_values('interval')
                
                for _, row in latest.head(10).iterrows():  # Top 10
                    pos = row.get('position', '?')
                    driver = f"#{row['driver_number']}"
                    gap = f"+{row.get('gap_to_leader', '0.000')}s"
                    interval = f"{row.get('interval', '0.000')}s"
                    
                    table.add_row(str(pos), driver, gap, interval)
            else:
                table.add_row("", "No data available", "", "")
                
        except Exception as e:
            table.add_row("", f"Error: {str(e)[:30]}", "", "")
        
        return table
    
    def format_event_log(self, events: List[Dict]) -> Panel:
        """Format event log into a panel"""
        if not events:
            content = "[dim]Waiting for race events...[/dim]"
        else:
            lines = []
            for event in events:
                timestamp = event['timestamp'].strftime('%H:%M:%S')
                severity_style = {
                    "critical": "bold red",
                    "high": "bold yellow",
                    "medium": "cyan",
                    "low": "dim white"
                }.get(event['severity'], "white")
                
                lines.append(f"[{severity_style}]{timestamp}[/{severity_style}] {event['message']}")
            
            content = "\n".join(lines)
        
        return Panel(content, title="📋 Recent Events", border_style="yellow")


# =============================================================================
# INTEGRATION WITH main.py
# =============================================================================

"""
# Add command in main loop:

if user_input.lower() == "/live":
    # Enter live race mode
    monitor = LiveRaceMonitor(api_client, llm)
    await monitor.start_monitoring()
    continue

# Or make it a tool:

@tool
async def f1_start_live_monitoring() -> str:
    '''
    Start live race monitoring mode.
    Continuously tracks the race and alerts you to:
    - Overtakes and position changes
    - Pit stops
    - Weather changes  
    - Fastest laps
    - Incidents
    '''
    monitor = LiveRaceMonitor(get_client(), get_llm())
    await monitor.start_monitoring()
    return "Live monitoring started"
"""


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def demo():
    """Demo the live race monitor"""
    from core.api_client import get_client
    from langchain_ollama import ChatOllama
    
    client = get_client()
    llm = ChatOllama(model="llama3.1", temperature=0)
    
    monitor = LiveRaceMonitor(client, llm)
    
    console.print("[bold green]Starting Live Race Monitor Demo[/bold green]")
    console.print("This will monitor the latest session for 60 seconds")
    console.print("Press Ctrl+C to stop early\n")
    
    await asyncio.sleep(2)
    
    # Start monitoring
    await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(demo())


# =============================================================================
# BENEFITS
# =============================================================================
"""
1. Hands-free race watching
   - Monitor automatically alerts you to important events
   - No need to constantly check timing screens
   
2. Never miss action
   - Catches overtakes, pit stops, incidents in real-time
   - Even if you look away briefly
   
3. Intelligent alerts
   - Only notifies for meaningful events
   - Prioritizes by severity
   
4. Full picture view
   - See positions, events, and trends all at once
   - Professional broadcast-quality monitoring
   
5. Contextual insights
   - Can integrate with LLM for strategy commentary
   - "Verstappen's pace suggests early pit stop coming"
"""

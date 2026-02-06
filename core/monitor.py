"""
Live Race Monitor Core Logic
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
import pandas as pd

from core.api_client import get_enhanced_client

console = Console()

class LiveRaceMonitor:
    """
    Real-time race monitoring with automatic event detection
    Continuously monitors race and alerts user to important events
    """
    
    def __init__(self):
        self.client = get_enhanced_client()
        self.session_key = None
        self.last_positions = {}
        self.last_weather = {}
        self.lap_count = 0
        self.monitoring = False
        
    async def start_monitoring(self, session_key: str = "latest"):
        """Start live race monitoring"""
        if session_key == "latest":
            self.session_key = await self.client.get_latest_session_key_async()
        else:
            self.session_key = session_key
            
        self.monitoring = True
        
        console.clear()
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
                    
                    # Check for events (Parallel Execution)
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
                    
                    # Check every 5 seconds
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            self.monitoring = False
            console.print("\n[yellow]Stopping live monitoring...[/yellow]")
        except Exception as e:
            console.print(f"[red]Monitor crashed: {e}[/red]")
            self.monitoring = False
    
    async def check_for_events(self) -> List[Dict]:
        """Check for interesting race events in parallel"""
        # Run detection tasks concurrently for maximum speed
        tasks = [
            self.detect_position_changes(),
            self.detect_pit_stops(),
            self.detect_weather_changes(),
            self.detect_fastest_laps()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        events = []
        for res in results:
            if isinstance(res, list):
                events.extend(res)
        
        return events
    
    async def detect_position_changes(self) -> List[Dict]:
        """Detect overtakes and position changes"""
        events = []
        try:
            intervals = await self.client.get_intervals_async(self.session_key)
            if not intervals: return []
            
            df = pd.DataFrame(intervals)
            if df.empty: return []
            
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
            
        except Exception:
            pass
        return events
    
    async def detect_pit_stops(self) -> List[Dict]:
        """Detect pit stop activity"""
        events = []
        try:
            pit_data = await self.client.get_pit_stops_async(self.session_key)
            if not pit_data: return []
            
            df = pd.DataFrame(pit_data)
            if df.empty: return []
            
            # Get recent pit stops (last 30 seconds)
            df['date'] = pd.to_datetime(df['date'])
            # Ensure timezone-aware comparison if needed, but FastF1 usually returns naive UTC or similar
            # If naive, datetime.now() should be fine, or datetime.utcnow()
            
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
        except Exception:
            pass
        return events
    
    async def detect_weather_changes(self) -> List[Dict]:
        """Detect significant weather changes"""
        events = []
        try:
            weather = await self.client.get_weather_async(self.session_key)
            if not weather: return []
            
            latest = weather[-1] if isinstance(weather, list) else weather
            
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
        except Exception:
            pass
        return events
    
    async def detect_fastest_laps(self) -> List[Dict]:
        """Detect new fastest laps"""
        events = []
        try:
            laps = await self.client.get_laps_async(self.session_key)
            if not laps: return []
            
            df = pd.DataFrame(laps)
            if df.empty: return []
            
            # Get recent laps
            recent = df.sort_values('date').tail(20)
            
            # Check for fastest lap flags (assuming 'is_personal_best' or similar logic available)
            # Simplification: just check if any recent lap is faster than all previous?
            # Or rely on a known flag. FastF1 doesn't always have 'is_personal_best'.
            # We'll skip complex logic for now and just look for purple laps if available
            # or just log very fast laps
            pass 
                
        except Exception:
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
            intervals = await self.client.get_intervals_async(self.session_key)
            if intervals:
                df = pd.DataFrame(intervals)
                if not df.empty:
                    latest = df.sort_values('date').groupby('driver_number').tail(1)
                    latest = latest.sort_values('interval')
                    
                    for _, row in latest.head(20).iterrows():
                        pos = row.get('position', '?')
                        driver = f"#{row['driver_number']}"
                        gap = f"+{row.get('gap_to_leader', 0):.3f}s"
                        
                        try:
                            interval_val = float(row.get('interval', 0))
                            interval = f"{interval_val:.3f}s"
                        except:
                            interval = str(row.get('interval', 'N/A'))
                        
                        table.add_row(str(pos), driver, gap, interval)
            else:
                table.add_row("", "No data", "", "")
                
        except Exception as e:
            table.add_row("", "Error", "", "")
        
        return table
    
    def format_event_log(self, events: List[Dict]) -> Panel:
        """Format event log into a panel"""
        if not events:
            content = "[dim]Waiting for race events...[/dim]"
        else:
            lines = []
            for event in reversed(events): # Show newest top
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

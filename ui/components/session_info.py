"""
Session Info Component
Displays race/event information, lap counter, and timer
"""
import arcade
from ui.helpers import format_time
from config.ui_settings import UI_TEXT_PRIMARY, UI_ACCENT_COLOR

class SessionInfoComponent:
    """Component showing session name, lap, and time"""
    
    def __init__(self, x, y, event_name, total_laps):
        self.x, self.y = x, y
        self.event_name = event_name
        self.total_laps = total_laps
        
        self.lbl_event = arcade.Text(
            event_name, x, y + 45, UI_TEXT_PRIMARY, 18, 
            bold=True, anchor_x="left", anchor_y="baseline"
        )
        self.lbl_lap = arcade.Text(
            f"Lap 1/{total_laps}", x, y + 20, UI_ACCENT_COLOR, 14, 
            bold=True, anchor_x="left", anchor_y="baseline"
        )
        self.lbl_timer = arcade.Text(
            "00:00:00", x, y - 5, UI_TEXT_PRIMARY, 15, 
            font_name=("Consolas", "Monospace"), bold=True, 
            anchor_x="left", anchor_y="baseline"
        )
    
    def draw(self, current_lap, current_time):
        """Draw session info"""
        self.lbl_lap.text = f"LAP {current_lap}/{self.total_laps}"
        self.lbl_timer.text = format_time(current_time)
        
        self.lbl_event.draw()
        self.lbl_lap.draw()
        self.lbl_timer.draw()

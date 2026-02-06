"""
Progress Bar Component
Visual progress indicator for race replay
"""
import arcade
from ui.helpers import create_rect
from config.ui_settings import UI_BORDER_COLOR, UI_ACCENT_COLOR

class ProgressBarComponent:
    """Progress bar showing race completion"""
    
    def __init__(self, x, y, width, height, total_time):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.total_time = total_time
    
    def draw(self, current_time):
        """Draw the progress bar"""
        # Background with depth
        bg_rect = create_rect(self.x + self.width/2, self.y + self.height/2, self.width, self.height)
        arcade.draw_rect_filled(bg_rect, (20, 20, 25))
        arcade.draw_rect_outline(bg_rect, UI_BORDER_COLOR, 2)
        
        # Fill with red F1 gradient
        if self.total_time.total_seconds() > 0:
            pct = min(1.0, current_time.total_seconds() / self.total_time.total_seconds())
            prog_w = self.width * pct
            if prog_w > 0:
                prog_rect = create_rect(self.x + prog_w/2, self.y + self.height/2, prog_w, self.height)
                arcade.draw_rect_filled(prog_rect, UI_ACCENT_COLOR)

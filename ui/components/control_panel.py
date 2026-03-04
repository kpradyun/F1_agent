"""
Control Panel Component
Playback control buttons (play/pause, speed, restart)
"""
import arcade
from ui.helpers import create_rect
from config.ui_settings import UI_TEXT_PRIMARY, UI_ACCENT_COLOR, PLAYBACK_SPEEDS

class ControlPanel:
    """Control panel with playback buttons"""
    
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.button_width = 70
        self.button_height = 40
        self.buttons = [
            {'key': 'rewind', 'label': '<<', 'x': 0},
            {'key': 'play_pause', 'label': 'PLAY', 'x': 80},
            {'key': 'forward', 'label': '>>', 'x': 160},
            {'key': 'slower', 'label': '0.5x', 'x': 250},
            {'key': 'faster', 'label': '2x', 'x': 330},
            {'key': 'restart', 'label': 'RESTART', 'x': 410},
        ]
        
    def draw(self, paused, speed):
        """Draw control buttons"""
        for btn in self.buttons:
            bx = self.x + btn['x']
            by = self.y
            
            # Determine button appearance
            label = btn['label']
            if btn['key'] == 'play_pause':
                label = 'PLAY' if paused else 'PAUSE'
                color = (40, 180, 40) if paused else (180, 40, 40)
                border = (60, 255, 60) if paused else (255, 60, 60)
            elif btn['key'] == 'restart':
                color = (100, 30, 30)
                border = UI_ACCENT_COLOR
            elif btn['key'] == 'slower' and speed <= min(PLAYBACK_SPEEDS):
                color = (45, 60, 90)
                border = (120, 170, 255)
            elif btn['key'] == 'faster' and speed >= max(PLAYBACK_SPEEDS):
                color = (45, 60, 90)
                border = (120, 170, 255)
            else:
                color = (30, 30, 40)
                border = (100, 100, 120)
            
            # Draw button
            rect = create_rect(bx + self.button_width/2, by + self.button_height/2, 
                             self.button_width, self.button_height)
            arcade.draw_rect_filled(rect, color)
            arcade.draw_rect_outline(rect, border, 3)
            
            # Draw text
            arcade.draw_text(
                label, bx + self.button_width/2, by + self.button_height/2, 
                UI_TEXT_PRIMARY, 11, 
                anchor_x="center", anchor_y="center", bold=True
            )
        
        # Speed indicator
        arcade.draw_text(
            f"Speed: {speed:.2f}x", self.x + 520, self.y + self.button_height/2, 
            UI_TEXT_PRIMARY, 12, 
            anchor_x="left", anchor_y="center", bold=True
        )
        arcade.draw_text(
            "Hotkeys: SPACE play/pause | ←/→ seek | +/- speed",
            self.x + 520, self.y + self.button_height/2 - 16,
            (170, 170, 185), 10,
            anchor_x="left", anchor_y="center"
        )
    
    def get_clicked_button(self, x, y):
        """Detect which button was clicked"""
        for btn in self.buttons:
            bx = self.x + btn['x']
            by = self.y
            if (bx <= x <= bx + self.button_width and 
                by <= y <= by + self.button_height):
                return btn['key']
        return None

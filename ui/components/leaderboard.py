"""
Leaderboard Component
Displays live race positions with gaps and position changes
"""
import arcade
from ui.helpers import create_rect, format_gap
from config.ui_settings import (
    UI_BG_COLOR, UI_BORDER_COLOR, UI_ACCENT_COLOR,
    UI_TEXT_PRIMARY, UI_TEXT_SECONDARY,
    LEADERBOARD_ROW_HEIGHT, LEADERBOARD_HEADER_OFFSET
)

class LeaderboardComponent:
    """Leaderboard displaying live race positions with gaps and position tracking"""
    
    def __init__(self, x, y, width, grid_positions=None):
        self.x, self.y = x, y
        self.width = width
        self.row_height = LEADERBOARD_ROW_HEIGHT
        self.grid_positions = grid_positions or {}
        
        self.header = arcade.Text(
            "P   DRIVER            GAP", 
            x + 10, y - 20, UI_TEXT_SECONDARY, 10, 
            font_name="Consolas", bold=True,
            anchor_x="left", anchor_y="baseline"
        )
        
        self.rows = []
        self.prev_positions = {}
        
        for i in range(20):
            row_y = y - LEADERBOARD_HEADER_OFFSET - (i * self.row_height)
            self.rows.append({
                'y': row_y,
                'index': i,
                'pos': arcade.Text(
                    f"{i+1}", x + 15, row_y, UI_TEXT_PRIMARY, 11, 
                    anchor_x="center", anchor_y="center", bold=True
                ),
                'name': arcade.Text(
                    "", x + 42, row_y, UI_TEXT_PRIMARY, 11, 
                    bold=True, anchor_x="left", anchor_y="center"
                ),
                'gap': arcade.Text(
                    "", x + width - 15, row_y, UI_TEXT_SECONDARY, 10, 
                    anchor_x="right", anchor_y="center", bold=True
                ),
                'bg_rect': create_rect(x + width/2, row_y, width - 10, 22)
            })

    def draw(self, sorted_drivers, selected_driver, leader_dist=None):
        """Draw the leaderboard"""
        # Background panel
        h = 50 + (len(self.rows) * self.row_height)
        bg = create_rect(self.x + self.width/2, self.y - h/2 + 15, self.width, h)
        arcade.draw_rect_filled(bg, UI_BG_COLOR)
        arcade.draw_rect_outline(bg, UI_BORDER_COLOR, 2)
        
        self.header.draw()
        
        # Calculate gaps
        for i, (drv_key, data) in enumerate(sorted_drivers):
            if i >= len(self.rows): 
                break
            
            row = self.rows[i]
            
            # Position change detection
            prev_pos = self.prev_positions.get(drv_key, i)
            position_changed = (prev_pos != i)
            
            # Selection highlight
            if drv_key == selected_driver:
                glow_rect = create_rect(
                    row['bg_rect'].left + row['bg_rect'].width/2, 
                    row['bg_rect'].bottom + row['bg_rect'].height/2, 
                    row['bg_rect'].width + 4, row['bg_rect'].height + 4
                )
                arcade.draw_rect_filled(glow_rect, (255, 255, 255, 40))
                arcade.draw_rect_filled(row['bg_rect'], (40, 40, 60))
                arcade.draw_rect_outline(row['bg_rect'], UI_ACCENT_COLOR, 2)
            elif position_changed:
                arcade.draw_rect_filled(row['bg_rect'], (30, 30, 40))
            
            # Team color strip
            arcade.draw_rect_filled(
                create_rect(self.x + 5, row['y'], 4, 18), 
                data['color']
            )
            
            # Position number
            row['pos'].text = str(i + 1)
            
            # Driver name
            driver_abbr = str(data['name']).upper()
            row['name'].text = driver_abbr
            
            # Gap calculation
            if data['status'] == 'OUT':
                row['gap'].text = "OUT"
                row['gap'].color = UI_ACCENT_COLOR
                row['name'].color = (120, 120, 120)
            else:
                if i == 0:
                    row['gap'].text = "LEADER"
                    row['gap'].color = (100, 255, 100)
                else:
                    if leader_dist is not None and leader_dist > 0:
                        gap_dist = leader_dist - data['dist']
                        gap_seconds = gap_dist / (250 / 3.6)
                        row['gap'].text = format_gap(gap_seconds)
                    else:
                        row['gap'].text = "—"
                    row['gap'].color = UI_TEXT_SECONDARY
                row['name'].color = UI_TEXT_PRIMARY
            
            row['pos'].draw()
            row['name'].draw()
            row['gap'].draw()
        
        # Update position tracking
        self.prev_positions = {drv_key: i for i, (drv_key, _) in enumerate(sorted_drivers)}
    
    def get_click_index(self, x, y):
        """Accurate click detection for leaderboard rows"""
        if x < self.x or x > self.x + self.width:
            return None
        
        header_bottom = self.y - LEADERBOARD_HEADER_OFFSET
        relative_y = header_bottom - y
        
        if relative_y < 0:
            return None
        
        idx = int(relative_y // self.row_height)
        
        if 0 <= idx < len(self.rows):
            return idx
        return None

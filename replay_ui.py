"""
F1 Race Replay UI - Main Window

Clean entry point - UI components and data logic extracted to modules
"""
import arcade
import pandas as pd
from datetime import timedelta
import threading
import time

from ui import (
    create_rect,
    LeaderboardComponent,
    TelemetryPanel,
    SessionInfoComponent,
    ProgressBarComponent,
    ControlPanel
)

from config.ui_settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    COUNTDOWN_DURATION, PLAYBACK_SPEEDS,
    LEFT_UI_MARGIN, RIGHT_UI_MARGIN,
    TRACK_LINE_WIDTH, CAR_DOT_SIZE, SELECTED_CAR_SIZE
)

from core.replay_data import extract_grid_positions

class F1ReplayWindow(arcade.Window):
    """Main replay window - orchestrates UI components"""
    
    def __init__(self, ui_data):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "F1 Race Replay", resizable=True)
        self.center_window()
        self.background_color = (8, 8, 10)
        
        self.session = ui_data['session']
        self.driver_info = ui_data['driver_info']
        self.track_layout = ui_data['track_layout']
        self.total_laps = ui_data.get('total_laps', 57)
        self.laps = self.session.laps
        self.max_time = self.laps['Time'].max()
        
        self.car_data_cache = ui_data.get('car_data', {})
        self.pos_data_cache = ui_data.get('pos_data', {})
        
        self.grid_positions = extract_grid_positions(
            self.session, 
            self.driver_info, 
            self.laps, 
            self.car_data_cache
        )
        
        start_times = []
        self.driver_max_times = {}
        for drv, df in self.pos_data_cache.items():
            if not df.empty:
                times = df['Time'] if 'Time' in df.columns else df.index
                self.driver_max_times[drv] = times.max()
                if isinstance(times, pd.TimedeltaIndex):
                    start_times.append(times.min())
        
        self.min_time = min(start_times) if start_times else timedelta(0)
        self.current_time = self.min_time + timedelta(seconds=1.0)
        self.total_time = self.max_time
        
        self.playback_start_time = self.current_time
        self.race_start_threshold = timedelta(seconds=30)
        
        self.playback_speed = 1.0
        self.speed_index = PLAYBACK_SPEEDS.index(1.0)
        self.paused = True
        self.selected_driver = None
        
        self._calc_track_scale()
        self._init_ui_components()
        
        self.current_frame_data = {}
        for drv in self.driver_info:
            self.current_frame_data[drv] = {
                "x": 0, "y": 0, "dist": 0,
                "color": self.driver_info[drv]['color'],
                "status": "OK",
                "name": self.driver_info[drv]['name'],
                "grid_pos": self.grid_positions.get(drv, 99),
                "compound": "",
                "telemetry": {"Speed": 0, "RPM": 0, "nGear": 0, "Throttle": 0, "Brake": 0}
            }
        
        self.update_frame_data()

    def _init_ui_components(self):
        """Initialize all UI components"""
        self.session_info = SessionInfoComponent(
            30, self.height - 70, 
            self.session.event['EventName'], 
            self.total_laps
        )
        self.telemetry = TelemetryPanel(30, 230, 280, 220)  # Increased height for readability
        self.leaderboard = LeaderboardComponent(
            self.width - RIGHT_UI_MARGIN + 20, 
            self.height - 50, 
            240,
            self.grid_positions
        )
        self.controls = ControlPanel(LEFT_UI_MARGIN + 20, 15)
        self.progress = ProgressBarComponent(
            LEFT_UI_MARGIN + 20, 
            self.height - 30, 
            self.width - LEFT_UI_MARGIN - RIGHT_UI_MARGIN - 40, 
            12, 
            self.total_time
        )

    def _calc_track_scale(self):
        """Calculate track scaling and offset for display"""
        t = self.track_layout
        w = t['max_x'] - t['min_x']
        h = t['max_y'] - t['min_y']
        
        pad_x, pad_y = w * 0.1, h * 0.1
        view_w = self.width - LEFT_UI_MARGIN - RIGHT_UI_MARGIN - 50
        view_h = self.height - 100
        
        scale = min(view_w / (w + pad_x*2), view_h / (h + pad_y*2))
        
        cx = (t['min_x'] + t['max_x']) / 2
        cy = (t['min_y'] + t['max_y']) / 2
        
        screen_cx = LEFT_UI_MARGIN + view_w / 2
        screen_cy = self.height / 2
        
        self.track_scale = scale
        self.offset_x = screen_cx - (cx * scale)
        self.offset_y = screen_cy - (cy * scale)

    def to_screen(self, x, y):
        """Convert track coordinates to screen coordinates"""
        return (x * self.track_scale + self.offset_x, 
                y * self.track_scale + self.offset_y)
    
    def get_sorted_drivers(self):
        """
        Get drivers sorted appropriately for current time.
        At race start: sorted by grid position
        During race: sorted by distance traveled
        """
        # Calculate elapsed playback time
        elapsed_time = self.current_time - self.playback_start_time
        
        if elapsed_time < self.race_start_threshold:
            # First 30 seconds of playback - use grid order
            return sorted(
                self.current_frame_data.items(), 
                key=lambda x: x[1].get('grid_pos', 99)
            )
        else:
            # After 30 seconds - use live positions by distance
            return sorted(
                self.current_frame_data.items(), 
                key=lambda x: -x[1]['dist'] if x[1]['status'] != 'OUT' else -999999
            )

    def on_draw(self):
        """Main draw method"""
        self.clear()
        
        pts = list(zip(self.track_layout['x'], self.track_layout['y']))
        screen_pts = [self.to_screen(x, y) for x, y in pts]
        if len(screen_pts) > 1:
            arcade.draw_line_strip(screen_pts, (80, 80, 90), TRACK_LINE_WIDTH + 2)
            arcade.draw_line_strip(screen_pts, (120, 120, 130), TRACK_LINE_WIDTH)
        
        for sec in self.track_layout.get('sectors', []):
            sx, sy = self.to_screen(sec['x'], sec['y'])
            arcade.draw_line(sx - 12, sy, sx + 12, sy, (255, 220, 0), 3)
            arcade.draw_text(
                sec['name'], sx + 18, sy, (255, 220, 0), 11, 
                bold=True, anchor_x="left", anchor_y="center"
            )

        for drv, data in self.current_frame_data.items():
            if data['status'] == 'OUT': 
                continue
            
            sx, sy = self.to_screen(data['x'], data['y'])
            
            if drv == self.selected_driver:
                arcade.draw_circle_filled(sx, sy, SELECTED_CAR_SIZE + 3, (255, 255, 255, 30))
                arcade.draw_circle_outline(sx, sy, SELECTED_CAR_SIZE, (255, 20, 20), 3)
                arcade.draw_text(
                    data['name'], sx + 20, sy + 8, (0, 0, 0), 13, 
                    bold=True, anchor_x="left", anchor_y="center"
                )
                arcade.draw_text(
                    data['name'], sx + 19, sy + 9, (255, 255, 255), 13, 
                    bold=True, anchor_x="left", anchor_y="center"
                )
            
            arcade.draw_circle_filled(sx, sy, CAR_DOT_SIZE, data['color'])
            arcade.draw_circle_outline(sx, sy, CAR_DOT_SIZE, (255, 255, 255), 2)

        sorted_drivers = self.get_sorted_drivers()
        
        leader_dist = sorted_drivers[0][1]['dist'] if sorted_drivers else 0
        
        self.telemetry.draw(
            self.selected_driver, 
            self.current_frame_data.get(self.selected_driver, {}).get('telemetry')
        )
        self.leaderboard.draw(sorted_drivers, self.selected_driver, leader_dist)
        self.session_info.draw(self.get_current_lap(), self.current_time)
        self.progress.draw(self.current_time)
        self.controls.draw(self.paused, self.playback_speed)

    def get_current_lap(self):
        """Get current lap number based on race leader's progress"""
        if self.laps.empty:
            return 1
        
        current_lap = 1
        
        # Check if laps has a Time column we can use
        if 'Time' in self.laps.columns:
            # Use Time column (lap finish time)
            for idx, row in self.laps.iterrows():
                lap_time = row.get('Time')
                lap_num = row.get('LapNumber', 1)
                
                if pd.notna(lap_time) and lap_time <= self.current_time:
                    current_lap = max(current_lap, int(lap_num))
        elif 'LapStartTime' in self.laps.columns:
            # Use LapStartTime if available
            for idx, row in self.laps.iterrows():
                lap_start = row.get('LapStartTime')
                lap_num = row.get('LapNumber', 1)
                
                if pd.notna(lap_start) and lap_start <= self.current_time:
                    current_lap = max(current_lap, int(lap_num))
        
        return min(current_lap, self.total_laps)

    def update_frame_data(self):
        """Update current frame data from cached telemetry"""
        for drv in self.driver_info:
            if drv in self.pos_data_cache:
                df_pos = self.pos_data_cache[drv]
                if not df_pos.empty:
                    mask = df_pos['Time'] <= self.current_time
                    closest = df_pos[mask].tail(1)
                    
                    if not closest.empty:
                        row = closest.iloc[0]
                        self.current_frame_data[drv]['x'] = row.get('X', 0)
                        self.current_frame_data[drv]['y'] = row.get('Y', 0)
            
            if drv in self.car_data_cache:
                df_tel = self.car_data_cache[drv]
                if not df_tel.empty:
                    mask = df_tel['Time'] <= self.current_time
                    closest = df_tel[mask].tail(1)
                    
                    if not closest.empty:
                        row = closest.iloc[0]
                        
                        if 'Distance' in row:
                            self.current_frame_data[drv]['dist'] = float(row.get('Distance', 0))
                            
                        self.current_frame_data[drv]['telemetry'] = {
                            'Speed': row.get('Speed', 0),
                            'RPM': row.get('RPM', 0),
                            'nGear': row.get('nGear', 0),
                            'Throttle': row.get('Throttle', 0),
                            'Brake': row.get('Brake', 0)
                        }
            
            if self.current_time > self.driver_max_times.get(drv, timedelta(0)):
                self.current_frame_data[drv]['status'] = 'OUT'

    def on_update(self, delta_time):
        """Update loop"""
        if not self.paused:
            advance = timedelta(seconds=delta_time * self.playback_speed)
            self.current_time += advance
            
            if self.current_time > self.total_time:
                self.current_time = self.total_time
                self.paused = True
            
            self.update_frame_data()

    def on_key_press(self, key, modifiers):
        """Handle keyboard input"""
        if key == arcade.key.SPACE:
            self.paused = not self.paused
        elif key == arcade.key.R:
            self.current_time = self.min_time
            self.paused = True
            self.update_frame_data()
        elif key == arcade.key.RIGHT:
            self.current_time += timedelta(seconds=10)
            self.update_frame_data()
        elif key == arcade.key.LEFT:
            self.current_time = max(self.min_time, self.current_time - timedelta(seconds=10))
            self.update_frame_data()

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse clicks"""
        btn_key = self.controls.get_clicked_button(x, y)
        if btn_key:
            if btn_key == 'play_pause':
                self.paused = not self.paused
            elif btn_key == 'restart':
                self.current_time = self.min_time
                self.paused = True
                self.update_frame_data()
            elif btn_key == 'forward':
                self.current_time += timedelta(seconds=30)
                self.update_frame_data()
            elif btn_key == 'rewind':
                self.current_time = max(self.min_time, self.current_time - timedelta(seconds=30))
                self.update_frame_data()
            elif btn_key == 'faster':
                self.speed_index = min(len(PLAYBACK_SPEEDS) - 1, self.speed_index + 1)
                self.playback_speed = PLAYBACK_SPEEDS[self.speed_index]
            elif btn_key == 'slower':
                self.speed_index = max(0, self.speed_index - 1)
                self.playback_speed = PLAYBACK_SPEEDS[self.speed_index]
            return
        
        idx = self.leaderboard.get_click_index(x, y)
        if idx is not None:
            sorted_drivers = self.get_sorted_drivers()
            if idx < len(sorted_drivers):
                drv_key = sorted_drivers[idx][0]
                self.selected_driver = drv_key

    def on_resize(self, width, height):
        """Handle window resize"""
        super().on_resize(width, height)
        self._calc_track_scale()
        self._init_ui_components()

def run_replay_threaded(data):
    """Run the replay in a separate thread"""
    def run():
        time.sleep(COUNTDOWN_DURATION)
        window = F1ReplayWindow(data)
        window.set_update_rate(1/FPS)
        arcade.run()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
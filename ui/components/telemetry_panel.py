"""
Telemetry Panel Component
Displays selected driver's telemetry data (speed, gear, RPM, throttle, brake)
"""
import arcade
from ui.helpers import create_rect
from config.ui_settings import (
    UI_BG_COLOR, UI_BORDER_COLOR, UI_ACCENT_COLOR, 
    UI_TEXT_PRIMARY, UI_TEXT_SECONDARY
)

class TelemetryPanel:
    """Telemetry panel displaying driver's live data"""
    
    def __init__(self, x, y, width, height):
        self.x, self.y = x, y
        self.width = width
        self.height = height
        
        self.lbl_driver_header = arcade.Text(
            "SELECTED DRIVER", x + 15, y + height - 15, UI_TEXT_SECONDARY, 9, 
            bold=True, anchor_x="left", anchor_y="top"
        )
        self.val_driver = arcade.Text(
            "Click driver", x + 15, y + height - 30, UI_TEXT_PRIMARY, 16, 
            bold=True, anchor_x="left", anchor_y="top"
        )
        
        self.lbl_speed = arcade.Text(
            "SPEED", x + 15, y + 150, UI_TEXT_SECONDARY, 9, 
            bold=True, anchor_x="left", anchor_y="baseline"
        )
        self.val_speed = arcade.Text(
            "0", x + 15, y + 110, UI_ACCENT_COLOR, 32, 
            bold=True, anchor_x="left", anchor_y="baseline"
        )
        self.unit_speed = arcade.Text(
            "km/h", x + 90, y + 117, UI_TEXT_SECONDARY, 10,
            anchor_x="left", anchor_y="baseline"
        )
        
        self.lbl_gear = arcade.Text(
            "GEAR", x + 180, y + 150, UI_TEXT_SECONDARY, 9, 
            bold=True, anchor_x="left", anchor_y="baseline"
        )
        self.val_gear = arcade.Text(
            "1", x + 195, y + 110, (255, 215, 0), 32, 
            bold=True, anchor_x="center", anchor_y="baseline"
        )

    def draw(self, driver_name, data):
        """Draw telemetry panel"""
        # Premium panel background
        center_x = self.x + self.width/2
        center_y = self.y + self.height/2
        bg = create_rect(center_x, center_y, self.width, self.height)
        arcade.draw_rect_filled(bg, UI_BG_COLOR)
        arcade.draw_rect_outline(bg, UI_BORDER_COLOR, 2)
        
        self.lbl_driver_header.draw()
        
        if not data:
            self.val_driver.text = "Click driver"
            self.val_driver.draw()
            return

        # Update values
        self.val_driver.text = str(driver_name)
        self.val_speed.text = str(int(data.get('Speed', 0)))
        gear_val = int(data.get('nGear', 0))
        self.val_gear.text = "N" if gear_val == 0 else str(gear_val)
        
        self.val_driver.draw()
        self.lbl_speed.draw()
        self.val_speed.draw()
        self.unit_speed.draw()
        self.lbl_gear.draw()
        self.val_gear.draw()
        
        rpm_val = data.get('RPM', 0)
        rpm_y = self.y + 70
        
        arcade.draw_text(
            "RPM", self.x + 15, rpm_y + 15, UI_TEXT_SECONDARY, 9, 
            anchor_x="left", anchor_y="baseline", bold=True
        )
        
        # RPM Bar
        bar_x = self.x + 15
        bar_w = self.width - 30
        rpm_pct = min(1.0, rpm_val / 13000)
        
        arcade.draw_rect_filled(create_rect(bar_x + bar_w/2, rpm_y, bar_w, 8), (30,30,35))
        if rpm_pct > 0:
            fill_w = bar_w * rpm_pct
            color = (255, 40, 40) if rpm_pct > 0.9 else (40, 255, 40)
            arcade.draw_rect_filled(create_rect(bar_x + fill_w/2, rpm_y, fill_w, 8), color)
        
        arcade.draw_text(
            f"{int(rpm_val)}", self.x + 15, rpm_y - 18,
            UI_TEXT_SECONDARY, 9, anchor_x="left", anchor_y="baseline", bold=True
        )
        
        controls_y = self.y + 20
        throttle_w = 110
        brake_w = 110
        brake_x = bar_x + throttle_w + 10
        
        arcade.draw_text(
            "THR", self.x + 15, controls_y + 15, UI_TEXT_SECONDARY, 8, 
            anchor_x="left", anchor_y="baseline", bold=True
        )
        thr_pct = min(1.0, data.get('Throttle', 0) / 100)
        arcade.draw_rect_filled(create_rect(bar_x + throttle_w/2, controls_y, throttle_w, 6), (30,30,35))
        if thr_pct > 0:
            fill_w = throttle_w * thr_pct
            arcade.draw_rect_filled(create_rect(bar_x + fill_w/2, controls_y, fill_w, 6), (40, 255, 40))
        
        arcade.draw_text(
            "BRK", brake_x, controls_y + 15, UI_TEXT_SECONDARY, 8, 
            anchor_x="left", anchor_y="baseline", bold=True
        )
        brk = 1.0 if data.get('Brake', 0) else 0.0
        arcade.draw_rect_filled(create_rect(brake_x + brake_w/2, controls_y, brake_w, 6), (30,30,35))
        if brk > 0:
            arcade.draw_rect_filled(create_rect(brake_x + brake_w/2, controls_y, brake_w, 6), (255, 40, 40))

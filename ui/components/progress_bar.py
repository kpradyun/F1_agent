"""
Progress Bar Component
Visual progress indicator for race replay
"""
import arcade
from datetime import timedelta
from ui.helpers import create_rect, format_time
from config.ui_settings import UI_BORDER_COLOR, UI_ACCENT_COLOR


class ProgressBarComponent:
    """Progress bar showing race completion"""

    def __init__(self, x, y, width, height, total_time):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.total_time = total_time

    def contains(self, x, y) -> bool:
        """Return True if a click is inside the progress bar area."""
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def time_from_x(self, x):
        """Map X coordinate to replay time on the progress timeline."""
        total_seconds = self.total_time.total_seconds()
        if total_seconds <= 0:
            return timedelta(seconds=0)
        clamped_x = min(max(x, self.x), self.x + self.width)
        pct = (clamped_x - self.x) / self.width
        return timedelta(seconds=total_seconds * pct)

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

            # 25/50/75 tick marks
            for tick in (0.25, 0.5, 0.75):
                tx = self.x + self.width * tick
                arcade.draw_line(tx, self.y - 1, tx, self.y + self.height + 1, (90, 90, 110), 1)

            arcade.draw_text(
                f"{pct*100:5.1f}%",
                self.x + self.width - 4, self.y + self.height + 4,
                (190, 190, 205), 10,
                anchor_x="right", anchor_y="bottom", bold=True
            )
            arcade.draw_text(
                f"{format_time(current_time)} / {format_time(self.total_time)}",
                self.x + 2, self.y + self.height + 4,
                (170, 170, 185), 10,
                anchor_x="left", anchor_y="bottom"
            )

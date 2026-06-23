"""
Tests for core/analytics.py — RaceAnalytics math engine.
These are pure-math unit tests with no network or FastF1 calls.
"""
import pytest
from core.analytics import RaceAnalytics


class TestTireDegradation:
    def test_basic_slope(self):
        laps = list(range(1, 11))
        # Each lap 0.1s slower: 90.0, 90.1, ..., 90.9
        times = [90.0 + i * 0.1 for i in range(10)]
        result = RaceAnalytics.calculate_tire_degradation(laps, times)
        assert result["is_valid"]
        assert pytest.approx(result["degradation_rate"], abs=0.01) == 0.1

    def test_insufficient_data_returns_invalid(self):
        result = RaceAnalytics.calculate_tire_degradation([1, 2], [90.0, 90.1])
        assert not result["is_valid"]

    def test_flat_laps_near_zero_degradation(self):
        laps = list(range(1, 11))
        times = [90.0] * 10
        result = RaceAnalytics.calculate_tire_degradation(laps, times)
        # ss_tot == 0, so r_squared should be 0
        assert result["is_valid"]
        assert abs(result["degradation_rate"]) < 1e-9

    def test_outlier_exclusion(self):
        laps = list(range(1, 11))
        times = [90.0 + i * 0.1 for i in range(10)]
        # Inject a massive outlier (SC lap)
        times[5] = 120.0
        result = RaceAnalytics.calculate_tire_degradation(laps, times, exclude_outliers=True)
        assert result["is_valid"]
        # Slope should still be ~0.1 after outlier is removed
        assert pytest.approx(result["degradation_rate"], abs=0.05) == 0.1

    def test_r_squared_good_fit(self):
        laps = list(range(1, 21))
        times = [90.0 + i * 0.05 for i in range(20)]
        result = RaceAnalytics.calculate_tire_degradation(laps, times)
        assert result["r_squared"] > 0.99


class TestUndercutWindow:
    def test_feasible_undercut(self):
        result = RaceAnalytics.calculate_undercut_window(
            gap_to_target=1.0,
            my_in_lap_pace=92.0,
            target_in_lap_pace=91.0,
            pit_loss_time=22.0,
            fresh_tire_advantage=3.0,
        )
        assert result["feasible"]
        assert result["likelihood"] in ("High", "Medium")

    def test_impossible_undercut(self):
        result = RaceAnalytics.calculate_undercut_window(
            gap_to_target=5.0,
            my_in_lap_pace=92.0,
            target_in_lap_pace=92.5,
            pit_loss_time=22.0,
            fresh_tire_advantage=1.0,
        )
        assert not result["feasible"]
        assert result["likelihood"] == "Impossible"

    def test_margin_calculation(self):
        result = RaceAnalytics.calculate_undercut_window(
            gap_to_target=2.0,
            my_in_lap_pace=92.0,
            target_in_lap_pace=92.5,
            pit_loss_time=22.0,
            fresh_tire_advantage=4.0,
        )
        # margin = 4.0 - 2.0 = 2.0
        assert pytest.approx(result["estimated_gain"], abs=0.01) == 2.0


class TestCatchPrediction:
    def test_chaser_will_catch(self):
        result = RaceAnalytics.predict_catch_lap(
            gap=3.0,
            chaser_pace=90.0,
            leader_pace=90.5,
        )
        assert result["will_catch"]
        assert result["laps_to_catch"] == 6  # 3.0 / 0.5 = 6

    def test_chaser_slower_will_not_catch(self):
        result = RaceAnalytics.predict_catch_lap(
            gap=3.0,
            chaser_pace=91.0,
            leader_pace=90.0,
        )
        assert not result["will_catch"]

    def test_equal_pace_will_not_catch(self):
        result = RaceAnalytics.predict_catch_lap(
            gap=5.0,
            chaser_pace=90.0,
            leader_pace=90.0,
        )
        assert not result["will_catch"]

    def test_laps_ceiling(self):
        result = RaceAnalytics.predict_catch_lap(
            gap=5.0,
            chaser_pace=90.0,
            leader_pace=90.3,
        )
        # 5.0 / 0.3 ≈ 16.67 → ceil → 17
        assert result["laps_to_catch"] == 17

"""Tests for QuickLookupBypass — pure regex, no network required."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.quick_lookup import QuickLookupBypass


def test_pole_records_match():
    bypass = QuickLookupBypass()
    result = bypass.match("who has the most pole positions in F1?")
    assert result is not None
    assert result["name"] == "Pole Position Records"
    assert result["category"] == "poles"


def test_driver_champion_match():
    bypass = QuickLookupBypass()
    result = bypass.match("who are the F1 world champions since 2010?")
    assert result is not None
    assert result["name"] == "Driver Champions"


def test_constructor_champion_match():
    bypass = QuickLookupBypass()
    result = bypass.match("list of F1 constructor champions")
    assert result is not None
    assert result["name"] == "Constructor Champions"


def test_fastest_lap_category():
    bypass = QuickLookupBypass()
    result = bypass.match("who has the most fastest laps?")
    assert result is not None
    assert result["name"] == "Fastest Lap Records"


def test_no_match_returns_none():
    bypass = QuickLookupBypass()
    result = bypass.match("what is DRS and how does it work?")
    assert result is None


def test_year_range_extraction():
    bypass = QuickLookupBypass()
    result = bypass.match("F1 world champions from 2010 to 2020")
    assert result is not None
    assert result.get("year_filter") == "from 2010 to 2020"


def test_single_year_extraction():
    bypass = QuickLookupBypass()
    result = bypass.match("who was the F1 champion in 2021?")
    assert result is not None
    assert result.get("year") == 2021


def test_since_year_extraction():
    bypass = QuickLookupBypass()
    result = bypass.match("F1 driver champions since 2015")
    assert result is not None
    assert "2015" in str(result.get("year_filter", ""))


def test_live_weather_skipped_with_historical_year():
    # A query with a past year and no "live/current" should NOT trigger live weather
    bypass = QuickLookupBypass()
    result = bypass.match("what was the weather in Monaco 2023?")
    # Should not match Live Weather (has year, no "live/current/now")
    if result is not None:
        assert result["name"] != "Live Weather"


def test_live_weather_with_current_keyword():
    bypass = QuickLookupBypass()
    result = bypass.match("what is the current weather at the track?")
    assert result is not None
    assert result["name"] == "Live Weather"


def test_hamilton_titles_match():
    bypass = QuickLookupBypass()
    result = bypass.match("how many titles does Hamilton have?")
    assert result is not None
    assert result["name"] == "Driver Champions"

"""Tests for validate_year in core/fastf1_adapter.py — no network required."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from core.fastf1_adapter import validate_year


def test_year_before_fastf1_era_is_invalid():
    assert not validate_year(2017)
    assert not validate_year(2000)
    assert not validate_year(1950)


def test_first_valid_year():
    assert validate_year(2018)


def test_current_year_is_valid():
    assert validate_year(datetime.now().year)


def test_future_year_is_invalid():
    assert not validate_year(datetime.now().year + 1)
    assert not validate_year(2099)


def test_boundary_year_2019():
    assert validate_year(2019)


def test_boundary_year_2023():
    assert validate_year(2023)


def test_negative_year():
    assert not validate_year(-1)


def test_zero():
    assert not validate_year(0)

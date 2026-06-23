"""
Tests for utils/gp_normalize.py — GP name normalization.
All pure string tests, no network calls.
"""
import pytest
from utils.gp_normalize import normalize_gp_name


class TestNormalizeGpName:
    # ── Colloquial → official ─────────────────────────────────────────────
    def test_spa_to_belgian(self):
        assert normalize_gp_name("Spa") == "Belgian Grand Prix"

    def test_monza_to_italian(self):
        assert normalize_gp_name("monza") == "Italian Grand Prix"

    def test_silverstone_to_british(self):
        assert normalize_gp_name("Silverstone") == "British Grand Prix"

    def test_monaco_to_monaco(self):
        assert normalize_gp_name("Monaco") == "Monaco Grand Prix"

    def test_suzuka_to_japanese(self):
        assert normalize_gp_name("suzuka") == "Japanese Grand Prix"

    def test_interlagos_to_sao_paulo(self):
        assert normalize_gp_name("Interlagos") == "São Paulo Grand Prix"

    def test_zandvoort_to_dutch(self):
        assert normalize_gp_name("Zandvoort") == "Dutch Grand Prix"

    def test_jeddah_to_saudi(self):
        assert normalize_gp_name("jeddah") == "Saudi Arabian Grand Prix"

    def test_baku_to_azerbaijan(self):
        assert normalize_gp_name("Baku") == "Azerbaijan Grand Prix"

    def test_singapore_to_singapore(self):
        assert normalize_gp_name("singapore") == "Singapore Grand Prix"

    # ── Case insensitivity ────────────────────────────────────────────────
    def test_uppercase_passes_through(self):
        result = normalize_gp_name("SPA")
        assert result == "Belgian Grand Prix"

    def test_mixed_case(self):
        result = normalize_gp_name("SpA")
        assert result == "Belgian Grand Prix"

    # ── Pass-through for already-official names ───────────────────────────
    def test_official_name_unchanged(self):
        official = "Belgian Grand Prix"
        assert normalize_gp_name(official) == official

    def test_unknown_name_returned_as_is(self):
        unknown = "Fictional Circuit"
        assert normalize_gp_name(unknown) == unknown

    # ── Edge cases ────────────────────────────────────────────────────────
    def test_empty_string_returned_as_is(self):
        assert normalize_gp_name("") == ""

    def test_none_returned_as_none(self):
        assert normalize_gp_name(None) is None

    def test_leading_trailing_whitespace_stripped(self):
        assert normalize_gp_name("  spa  ") == "Belgian Grand Prix"

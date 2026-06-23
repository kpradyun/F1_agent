"""
Tests for core/session_resolver.py — year extraction, token filtering, and GP matching.
These tests stub out the API client to avoid network calls.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.session_resolver import SessionResolver


@pytest.fixture
def resolver():
    """Return a SessionResolver with a stubbed API client (no network)."""
    with patch("core.session_resolver.get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_latest_session_key.return_value = "9999"
        mock_get.return_value = mock_client
        r = SessionResolver()
        r.client = mock_client
        return r


class TestExtractYear:
    def test_year_in_gp_string(self, resolver):
        year, cleaned = resolver._extract_year("Abu Dhabi 2023", 2024)
        assert year == 2023
        assert "2023" not in cleaned

    def test_no_year_uses_default(self, resolver):
        year, cleaned = resolver._extract_year("Belgian Grand Prix", 2024)
        assert year == 2024
        assert cleaned == "Belgian Grand Prix"

    def test_year_only_string(self, resolver):
        year, cleaned = resolver._extract_year("2022", 2024)
        assert year == 2022


class TestGetMeaningfulTokens:
    def test_filters_ignored_words(self, resolver):
        tokens = resolver._get_meaningful_tokens("Belgian Grand Prix")
        assert "grand" not in tokens
        assert "prix" not in tokens
        assert "belgian" in tokens

    def test_single_location(self, resolver):
        tokens = resolver._get_meaningful_tokens("Silverstone")
        assert "silverstone" in tokens

    def test_gp_keyword_filtered(self, resolver):
        tokens = resolver._get_meaningful_tokens("Monaco GP")
        assert "gp" not in tokens
        assert "monaco" in tokens


class TestMatchSession:
    def _make_sessions(self):
        return [
            {
                "session_key": "100",
                "session_name": "Race",
                "location": "Spa-Francorchamps",
                "circuit_short_name": "SPA",
                "country_name": "Belgium",
                "date_start": "2023-07-30",
            },
            {
                "session_key": "200",
                "session_name": "Race",
                "location": "Monza",
                "circuit_short_name": "MON",
                "country_name": "Italy",
                "date_start": "2023-09-03",
            },
        ]

    def test_spa_matches_belgium(self, resolver):
        sessions = self._make_sessions()
        tokens = resolver._get_meaningful_tokens("belgian")
        matched = resolver._match_session(sessions, tokens, "belgian")
        assert matched is not None
        assert matched["session_key"] == "100"

    def test_monza_matches_italy(self, resolver):
        sessions = self._make_sessions()
        tokens = resolver._get_meaningful_tokens("italian")
        matched = resolver._match_session(sessions, tokens, "italian")
        assert matched is not None
        assert matched["session_key"] == "200"

    def test_no_match_returns_none(self, resolver):
        sessions = self._make_sessions()
        tokens = resolver._get_meaningful_tokens("Azerbaijan")
        matched = resolver._match_session(sessions, tokens, "Azerbaijan")
        assert matched is None

    def test_most_recent_returned_on_multiple_matches(self, resolver):
        # Two sessions with same location, different dates
        sessions = [
            {
                "session_key": "A",
                "session_name": "Race",
                "location": "Spa",
                "circuit_short_name": "SPA",
                "country_name": "Belgium",
                "date_start": "2022-08-28",
            },
            {
                "session_key": "B",
                "session_name": "Race",
                "location": "Spa",
                "circuit_short_name": "SPA",
                "country_name": "Belgium",
                "date_start": "2023-07-30",
            },
        ]
        tokens = {"spa"}
        matched = resolver._match_session(sessions, tokens, "spa")
        # Most recent should win
        assert matched["session_key"] == "B"


class TestResolveLatest:
    def test_latest_gp_calls_client(self, resolver):
        key = resolver.resolve(2024, "latest", "Race")
        resolver.client.get_latest_session_key.assert_called_once()
        assert key == "9999"

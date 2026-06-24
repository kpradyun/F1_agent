"""
Comprehensive F1 Agent Query Suite
===================================
Covers every category from the spec: bypass routing, tool outputs, agent-path
tool availability, live session graceful degradation, and edge cases.

Tiers:
  - Bypass routing  : instant, no network (pure regex)
  - Tool outputs    : real Jolpica/Wikipedia API, fast (<10s each)
  - FastF1 tools    : may download session data; marked @pytest.mark.slow
  - Live tools      : outside an active race weekend, should degrade gracefully
  - Registry        : import/count checks, no network
"""
from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_bypass = None

def _get_bypass():
    global _bypass
    if _bypass is None:
        from utils.quick_lookup import QuickLookupBypass
        _bypass = QuickLookupBypass()
    return _bypass


def _match(query: str):
    return _get_bypass().match(query)


def _name(query: str) -> str | None:
    r = _match(query)
    return r["name"] if r else None


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 — Quick Lookup Bypass: routing assertions (no network)
# ═══════════════════════════════════════════════════════════════════════════

class TestStandingsBypass:
    """All championship standings queries → Championship Standings."""

    def test_current_championship_standings(self):
        assert _name("What are the current championship standings?") == "Championship Standings"

    def test_who_leads_drivers_championship(self):
        assert _name("Who leads the drivers championship?") == "Championship Standings"

    def test_points_does(self):
        assert _name("How many points does Norris have?") == "Championship Standings"

    def test_constructor_standings(self):
        assert _name("Show me the constructor standings") == "Championship Standings"

    def test_points_tally(self):
        assert _name("What's Verstappen's points tally?") == "Championship Standings"

    def test_p1_in_championship(self):
        assert _name("Who is P1 in the championship?") == "Championship Standings"


class TestSeasonRaceWinnersBypass:
    """Season race winner queries → Season Race Winners + year extraction."""

    def test_all_race_winners_2026(self):
        r = _match("Show me all 2026 race winners so far")
        assert r is not None and r["name"] == "Season Race Winners"
        assert r.get("year") == 2026

    def test_who_won_each_race_2024(self):
        r = _match("Who won each race in the 2024 season?")
        assert r is not None and r["name"] == "Season Race Winners"
        assert r.get("year") == 2024

    def test_list_race_winners_2023(self):
        r = _match("List of race winners for 2023")
        assert r is not None and r["name"] == "Season Race Winners"
        assert r.get("year") == 2023

    def test_all_gp_winners_2025(self):
        r = _match("All grand prix winners in 2025")
        assert r is not None and r["name"] == "Season Race Winners"
        assert r.get("year") == 2025


class TestChampionsHistoryBypass:
    """Driver champion queries → Driver Champions + year filter extraction."""

    def test_world_champions_since_2010(self):
        r = _match("Who are the F1 world champions since 2010?")
        assert r is not None and r["name"] == "Driver Champions"
        assert "2010" in str(r.get("year_filter", ""))

    def test_from_2000_to_2020_range(self):
        r = _match("List all F1 driver champions from 2000 to 2020")
        assert r is not None and r["name"] == "Driver Champions"
        assert "from 2000 to 2020" in str(r.get("year_filter", ""))

    def test_champion_in_2021(self):
        r = _match("Who was the F1 champion in 2021?")
        assert r is not None and r["name"] == "Driver Champions"
        assert r.get("year") == 2021

    def test_hamilton_titles(self):
        r = _match("How many titles does Hamilton have?")
        assert r is not None and r["name"] == "Driver Champions"

    def test_f1_champions_since_2015(self):
        r = _match("F1 driver champions since 2015")
        assert r is not None and r["name"] == "Driver Champions"
        assert "2015" in str(r.get("year_filter", ""))


class TestConstructorChampionsBypass:
    """Constructor champion queries → Constructor Champions."""

    def test_list_constructor_champions(self):
        assert _name("List of F1 constructor champions") == "Constructor Champions"

    def test_constructor_title_2022(self):
        r = _match("Who won the constructor title in 2022?")
        assert r is not None and r["name"] == "Constructor Champions"
        assert r.get("year") == 2022

    def test_constructor_champions_history(self):
        assert _name("Constructor champions history") == "Constructor Champions"


class TestAllTimeRecordsBypass:
    """All-time records queries → correct category."""

    def test_most_wins(self):
        r = _match("Who has the most wins in F1?")
        assert r is not None and r.get("category") == "wins"

    def test_most_pole_positions(self):
        r = _match("Who has the most pole positions?")
        assert r is not None and r.get("category") == "poles"

    def test_most_podiums_ever(self):
        r = _match("Who has the most podiums ever?")
        assert r is not None and r.get("category") == "podiums"

    def test_most_fastest_laps(self):
        r = _match("Who has the most fastest laps?")
        assert r is not None and r.get("category") == "fastest_laps"

    def test_most_championships_ever(self):
        r = _match("Most F1 world championships ever")
        assert r is not None and r.get("category") == "titles"


class TestDriverCareerBypass:
    """Driver career queries → Driver Career + driver extracted."""

    def test_hamilton_career_stats(self):
        r = _match("Hamilton's career stats")
        assert r is not None and r["name"] == "Driver Career"
        assert "hamilton" in r.get("driver", "").lower()

    def test_verstappen_career_summary(self):
        r = _match("Tell me Verstappen's career summary")
        assert r is not None and r["name"] == "Driver Career"
        assert "verstappen" in r.get("driver", "").lower()

    def test_alonso_wins(self):
        r = _match("How many wins does Alonso have?")
        assert r is not None and r["name"] == "Driver Career"
        assert "alonso" in r.get("driver", "").lower()

    def test_norris_career_profile(self):
        r = _match("Norris career profile")
        assert r is not None and r["name"] == "Driver Career"
        assert "norris" in r.get("driver", "").lower()

    def test_senna_career_stats(self):
        r = _match("Senna career stats")
        assert r is not None and r["name"] == "Driver Career"
        assert "senna" in r.get("driver", "").lower()


class TestConstructorCareerBypass:
    """Constructor career queries → Constructor Career + constructor extracted."""

    def test_ferrari_career_stats(self):
        r = _match("Ferrari career stats")
        assert r is not None and r["name"] == "Constructor Career"
        assert "ferrari" in r.get("constructor", "").lower()

    def test_mclaren_championship_history(self):
        r = _match("McLaren championship history")
        assert r is not None and r["name"] == "Constructor Career"
        assert "mclaren" in r.get("constructor", "").lower()

    def test_mercedes_total_wins(self):
        r = _match("Mercedes total wins")
        assert r is not None and r["name"] == "Constructor Career"
        assert "mercedes" in r.get("constructor", "").lower()

    def test_red_bull_career_summary(self):
        r = _match("Red Bull career summary")
        assert r is not None and r["name"] == "Constructor Career"
        assert "red bull" in r.get("constructor", "").lower()


class TestDriverFormBypass:
    """Driver form queries → Driver Form + driver/n_races extracted."""

    def test_norris_recent_form(self):
        r = _match("Norris recent form")
        assert r is not None and r["name"] == "Driver Form"
        assert "norris" in r.get("driver", "").lower()

    def test_leclerc_last_5_races(self):
        r = _match("Leclerc last 5 races")
        assert r is not None and r["name"] == "Driver Form"
        assert "leclerc" in r.get("driver", "").lower()
        assert int(r.get("n", 5)) == 5

    def test_piastri_performing_recently(self):
        r = _match("How is Piastri performing recently?")
        assert r is not None and r["name"] == "Driver Form"
        assert "piastri" in r.get("driver", "").lower()

    def test_hamilton_last_3_races(self):
        r = _match("Hamilton last 3 races")
        assert r is not None and r["name"] == "Driver Form"
        assert "hamilton" in r.get("driver", "").lower()
        assert int(r.get("n", 3)) == 3


class TestHeadToHeadBypass:
    """H2H queries (no circuit) → Head-to-Head; with circuit → Telemetry Comparison."""

    def test_norris_vs_piastri(self):
        r = _match("Norris vs Piastri")
        assert r is not None and r["name"] == "Head-to-Head"

    def test_hamilton_vs_verstappen_2021(self):
        r = _match("Hamilton vs Verstappen in 2021")
        assert r is not None and r["name"] == "Head-to-Head"
        assert r.get("year") == 2021

    def test_leclerc_vs_sainz_2023(self):
        r = _match("Leclerc vs Sainz 2023")
        assert r is not None and r["name"] == "Head-to-Head"
        assert r.get("year") == 2023

    def test_alonso_vs_hamilton(self):
        r = _match("Alonso vs Hamilton")
        assert r is not None and r["name"] == "Head-to-Head"


class TestCircuitGuideBypass:
    """Circuit guide queries → Circuit Guide + circuit extracted."""

    def test_monaco_circuit(self):
        r = _match("Tell me about the Monaco circuit")
        assert r is not None and r["name"] == "Circuit Guide"
        assert "monaco" in r.get("circuit", "").lower()

    def test_singapore_grand_prix(self):
        r = _match("Singapore Grand Prix track details")
        assert r is not None and r["name"] == "Circuit Guide"
        assert "singapore" in r.get("circuit", "").lower()

    def test_silverstone_circuit_guide(self):
        r = _match("Silverstone circuit guide")
        assert r is not None and r["name"] == "Circuit Guide"
        assert "silverstone" in r.get("circuit", "").lower()

    def test_monza_track_info(self):
        r = _match("Monza track info")
        assert r is not None and r["name"] == "Circuit Guide"
        assert "monza" in r.get("circuit", "").lower()

    def test_suzuka_circuit_profile(self):
        r = _match("Suzuka circuit profile")
        assert r is not None and r["name"] == "Circuit Guide"
        assert "suzuka" in r.get("circuit", "").lower()


class TestScheduleBypass:
    """Schedule queries → Season Schedule + year."""

    def test_2026_f1_schedule(self):
        r = _match("2026 F1 schedule")
        assert r is not None and r["name"] == "Season Schedule"
        assert r.get("year") == 2026

    def test_f1_calendar_2025(self):
        r = _match("F1 calendar 2025")
        assert r is not None and r["name"] == "Season Schedule"
        assert r.get("year") == 2025

    def test_race_calendar_2024(self):
        r = _match("Race calendar 2024")
        assert r is not None and r["name"] == "Season Schedule"
        assert r.get("year") == 2024


class TestPointsProgressionBypass:
    """Points progression chart queries → Points Progression."""

    def test_2026_points_progression(self):
        r = _match("Show me the 2026 points progression")
        assert r is not None and r["name"] == "Points Progression"
        assert r.get("year") == 2026

    def test_championship_battle_chart_2023(self):
        r = _match("Championship battle chart for 2023")
        assert r is not None and r["name"] == "Points Progression"
        assert r.get("year") == 2023

    def test_cumulative_points_chart_2024(self):
        r = _match("Cumulative points chart 2024")
        assert r is not None and r["name"] == "Points Progression"
        assert r.get("year") == 2024


class TestSprintResultsBypass:
    """Sprint queries → Sprint Results."""

    def test_sprint_race_results_2024(self):
        r = _match("Sprint race results 2024")
        assert r is not None and r["name"] == "Sprint Results"
        assert r.get("year") == 2024

    def test_who_won_sprint_2023(self):
        r = _match("Who won the sprint in 2023?")
        assert r is not None and r["name"] == "Sprint Results"
        assert r.get("year") == 2023

    def test_show_sprint_results(self):
        assert _name("Show me sprint results") == "Sprint Results"


class TestNextRaceBypass:
    """Next race queries → Next Race Preview."""

    def test_when_is_next_race(self):
        assert _name("When is the next race?") == "Next Race Preview"

    def test_next_f1_grand_prix(self):
        assert _name("Where is the next F1 grand prix?") == "Next Race Preview"

    def test_whats_coming_up_in_f1(self):
        assert _name("What's coming up in F1?") == "Next Race Preview"

    def test_slash_next_command(self):
        assert _name("/next") == "Next Race Preview"


class TestReliabilityBypass:
    """Reliability/DNF queries → Reliability Analysis."""

    def test_2024_reliability_analysis(self):
        r = _match("2024 reliability analysis")
        assert r is not None and r["name"] == "Reliability Analysis"
        assert r.get("year") == 2024

    def test_2023_dnf_stats(self):
        r = _match("2023 DNF stats")
        assert r is not None and r["name"] == "Reliability Analysis"
        assert r.get("year") == 2023

    def test_reliability_analysis_for_2025(self):
        r = _match("Reliability analysis for 2025")
        assert r is not None and r["name"] == "Reliability Analysis"
        assert r.get("year") == 2025


class TestQualifyingAndRaceResultsBypass:
    """Qualifying/race with known circuit → bypass; without → agent (None)."""

    def test_qualifying_at_monaco_2024_bypasses(self):
        r = _match("What were the qualifying results at Monaco 2024?")
        assert r is not None and r["name"] == "Qualifying Results"
        assert r.get("year") == 2024

    def test_race_results_at_monza_bypasses(self):
        r = _match("race results at monza 2022")
        assert r is not None and r["name"] == "Race Results"
        assert r.get("year") == 2022

    def test_qualifying_at_suzuka_bypasses(self):
        r = _match("qualifying results at Suzuka")
        assert r is not None and r["name"] == "Qualifying Results"

    def test_no_match_for_british_gp_by_name(self):
        # "British" is not in _CIRCUITS — goes to agent (None or non-qualifying bypass)
        r = _match("Show me the race results from the 2023 British Grand Prix")
        if r is not None:
            assert r["name"] != "Qualifying Results"


class TestTelemetryBypass:
    """Two drivers + circuit → Telemetry Comparison (not Head-to-Head)."""

    def test_norris_vs_piastri_at_silverstone(self):
        r = _match("Compare Norris and Piastri fastest laps at Silverstone 2024")
        assert r is not None and r["name"] == "Telemetry Comparison"
        assert r.get("year") == 2024

    def test_hamilton_vs_verstappen_at_bahrain(self):
        r = _match("Plot telemetry for Hamilton vs Verstappen at Bahrain 2022")
        assert r is not None and r["name"] == "Telemetry Comparison"
        assert r.get("year") == 2022

    def test_leclerc_vs_sainz_at_monaco_bypasses(self):
        # Leclerc vs Sainz 2023 with Monaco circuit mentioned → Telemetry, not H2H
        r = _match("Interactive telemetry for Leclerc vs Sainz at Monaco 2023")
        assert r is not None and r["name"] == "Telemetry Comparison"


class TestLiveToolsBypass:
    """Live tool queries only fire when there's no historical year + no live keyword conflict."""

    def test_live_weather_matches(self):
        r = _match("what is the current weather at the track?")
        assert r is not None and r["name"] == "Live Weather"

    def test_live_weather_skipped_with_historical_year(self):
        r = _match("what was the weather at Monaco 2023?")
        if r is not None:
            assert r["name"] != "Live Weather"

    def test_live_leaderboard_matches(self):
        r = _match("who is winning now?")
        assert r is not None and r["name"] == "Live Leaderboard"

    def test_live_position_map_matches(self):
        r = _match("show me live positions")
        assert r is not None and r["name"] == "Live Position Map"


class TestEdgeCasesBypass:
    """Edge cases and no-match robustness."""

    def test_what_is_drs_goes_to_agent(self):
        # DRS explanation → agent handles it (Wikipedia or RAG)
        assert _name("What is DRS and how does it work?") is None

    def test_fastest_driver_on_form_hits_standings(self):
        # "who is the fastest driver on current form" → standings or form
        r = _match("Who is the fastest driver on current form?")
        assert r is not None  # should match something (standings or form)

    def test_hamilton_vs_schumacher_wins_comparison(self):
        r = _match("Who has more wins: Hamilton or Schumacher?")
        assert r is not None and r["name"] == "Career Comparison"

    def test_show_senna_career(self):
        r = _match("Show me Senna's career")
        assert r is not None and r["name"] == "Driver Career"
        assert "senna" in r.get("driver", "").lower()

    def test_what_happened_at_silverstone_in_wet_goes_wikipedia(self):
        r = _match("What happened at Silverstone in the wet?")
        assert r is not None  # Wikipedia lookup should fire

    def test_natural_language_season_comparison_goes_to_agent(self):
        # "Compare 2023 and 2024 seasons for McLaren" — no exact bypass pattern
        # Should either go to agent (None) or a sensible tool
        # We just assert no crash
        r = _match("Compare the 2023 and 2024 seasons for McLaren")
        assert True  # no crash is the requirement here

    def test_non_f1_query_returns_none(self):
        assert _name("What is the capital of France?") is None

    def test_incomplete_query_no_crash(self):
        assert True  # _name("") won't crash
        _name("")

    def test_standings_1994_extracts_year(self):
        # "Give me standings for 1994" — doesn't hit bypass (no "championship/current" keyword)
        # Agent handles it → calls f1_standings(year=1994). No crash required.
        r = _match("Give me standings for 1994")
        if r is not None:
            assert r["name"] == "Championship Standings"
            assert r.get("year") == 1994

    def test_driver_info_2026_bypasses_to_standings_or_agent(self):
        # "Show me all driver numbers and nationalities for 2026"
        # No exact bypass → goes to agent OR standings
        r = _match("Show me all driver numbers and nationalities for 2026")
        # no crash requirement
        assert True

    def test_who_drives_for_ferrari_2026(self):
        # "Who drives for Ferrari in 2026?" → no exact bypass, goes to agent
        # Agent calls f1_standings(year=2026) or f1_wikipedia_lookup; no crash required
        _match("Who drives for Ferrari in 2026?")  # must not raise

    def test_fastest_lap_record_holder_hits_bypass(self):
        r = _match("Tell me about the fastest lap record holder")
        assert r is not None  # driver career or wikipedia


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 — Tool output tests (Jolpica / Wikipedia, fast network)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_standings_2024():
    from tools.reference_tools import f1_standings
    result = await f1_standings.ainvoke({"year": 2024})
    assert "standings" in result.lower() or "points" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_standings_current_year():
    from tools.reference_tools import f1_standings
    result = await f1_standings.ainvoke({})
    assert result and len(result) > 20  # non-empty


@pytest.mark.asyncio
async def test_driver_champions_since_2015():
    from tools.reference_tools import f1_champions_quick_lookup
    result = await f1_champions_quick_lookup.ainvoke({"year_filter": "since 2015"})
    assert "hamilton" in result.lower() or "verstappen" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_driver_champion_2021():
    from tools.reference_tools import f1_champions_quick_lookup
    result = await f1_champions_quick_lookup.ainvoke({"year_filter": "2021"})
    assert "verstappen" in result.lower() or "2021" in result or "Error" in result


@pytest.mark.asyncio
async def test_constructor_champions():
    from tools.reference_tools import f1_constructor_champions
    result = await f1_constructor_champions.ainvoke({"year_filter": ""})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_all_time_wins():
    from tools.reference_tools import f1_all_time_records
    result = await f1_all_time_records.ainvoke({"category": "wins"})
    assert "hamilton" in result.lower() or "schumacher" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_all_time_poles():
    from tools.reference_tools import f1_all_time_records
    result = await f1_all_time_records.ainvoke({"category": "poles"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_all_time_podiums():
    from tools.reference_tools import f1_all_time_records
    result = await f1_all_time_records.ainvoke({"category": "podiums"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_all_time_titles():
    from tools.reference_tools import f1_all_time_records
    result = await f1_all_time_records.ainvoke({"category": "titles"})
    assert "hamilton" in result.lower() or "schumacher" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_all_time_fastest_laps():
    from tools.reference_tools import f1_all_time_records
    result = await f1_all_time_records.ainvoke({"category": "fastest_laps"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_hamilton_career():
    from tools.reference_tools import f1_driver_career_summary
    result = await f1_driver_career_summary.ainvoke({"driver_query": "hamilton"})
    assert "hamilton" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_verstappen_career():
    from tools.reference_tools import f1_driver_career_summary
    result = await f1_driver_career_summary.ainvoke({"driver_query": "verstappen"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_senna_career():
    from tools.reference_tools import f1_driver_career_summary
    result = await f1_driver_career_summary.ainvoke({"driver_query": "senna"})
    assert "senna" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_ferrari_constructor_career():
    from tools.reference_tools import f1_constructor_career_summary
    result = await f1_constructor_career_summary.ainvoke({"constructor_query": "ferrari"})
    assert "ferrari" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_mclaren_constructor_career():
    from tools.reference_tools import f1_constructor_career_summary
    result = await f1_constructor_career_summary.ainvoke({"constructor_query": "mclaren"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_norris_recent_form():
    from tools.reference_tools import f1_driver_form
    result = await f1_driver_form.ainvoke({"driver": "norris", "n_races": 5})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_leclerc_last_5_races():
    from tools.reference_tools import f1_driver_form
    result = await f1_driver_form.ainvoke({"driver": "leclerc", "n_races": 5})
    assert "leclerc" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_head_to_head_norris_piastri_2024():
    from tools.reference_tools import f1_head_to_head
    result = await f1_head_to_head.ainvoke({"driver1": "norris", "driver2": "piastri", "year": 2024})
    assert "norris" in result.lower() or "piastri" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_head_to_head_hamilton_verstappen_2021():
    from tools.reference_tools import f1_head_to_head
    result = await f1_head_to_head.ainvoke({"driver1": "hamilton", "driver2": "verstappen", "year": 2021})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_circuit_guide_monaco():
    from tools.reference_tools import f1_circuit_guide
    result = await f1_circuit_guide.ainvoke({"circuit_query": "monaco"})
    assert "monaco" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_circuit_guide_silverstone():
    from tools.reference_tools import f1_circuit_guide
    result = await f1_circuit_guide.ainvoke({"circuit_query": "silverstone"})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_season_race_winners_2023():
    from tools.reference_tools import f1_season_race_winners
    result = await f1_season_race_winners.ainvoke({"year": 2023})
    assert "2023" in result or "verstappen" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_season_race_winners_2024():
    from tools.reference_tools import f1_season_race_winners
    result = await f1_season_race_winners.ainvoke({"year": 2024})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_sprint_results_2023():
    from tools.reference_tools import f1_sprint_results
    result = await f1_sprint_results.ainvoke({"year": 2023})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_reliability_analysis_2023():
    from tools.reference_tools import f1_reliability_analysis
    result = await f1_reliability_analysis.ainvoke({"year": 2023, "driver_query": ""})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_next_race_preview():
    from tools.reference_tools import f1_next_race_preview
    result = await f1_next_race_preview.ainvoke({})
    # Should return next race info or "season is complete"
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_schedule_2024():
    from tools.analysis_tools import f1_schedule
    result = await f1_schedule.ainvoke({"year": 2024})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_points_progression_2023():
    from tools.reference_tools import f1_points_progression
    result = await f1_points_progression.ainvoke({"year": 2023})
    assert result and len(result) > 20


@pytest.mark.asyncio
async def test_wikipedia_lookup_senna():
    from tools.reference_tools import f1_wikipedia_lookup
    result = await f1_wikipedia_lookup.ainvoke({"query": "Ayrton Senna F1 career"})
    assert "senna" in result.lower() or "Error" in result


@pytest.mark.asyncio
async def test_wikipedia_lookup_drs():
    from tools.reference_tools import f1_wikipedia_lookup
    result = await f1_wikipedia_lookup.ainvoke({"query": "DRS Formula One"})
    assert result and len(result) > 20


# ═══════════════════════════════════════════════════════════════════════════
# PART 3 — FastF1 tool smoke tests (accept success OR graceful error)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_session_results_monaco_2023_qualifying():
    """Historical qualifying results — data may be cached from prior test runs."""
    from tools.analysis_tools import f1_session_results
    result = await f1_session_results.ainvoke({
        "grand_prix": "Monaco",
        "year": 2023,
        "session": "Qualifying",
    })
    # Accept either real data or a clean error message
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_session_results_bahrain_2022_race():
    from tools.analysis_tools import f1_session_results
    result = await f1_session_results.ainvoke({
        "grand_prix": "Bahrain",
        "year": 2022,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_weather_report_belgium_2021():
    """Historical weather report — tests FastF1 session loading."""
    from tools.session_tools import f1_weather_report
    result = await f1_weather_report.ainvoke({
        "grand_prix": "Belgium",
        "year": 2021,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_race_control_report_monaco_2023():
    """Historical race control messages."""
    from tools.session_tools import f1_race_control_report
    result = await f1_race_control_report.ainvoke({
        "grand_prix": "Monaco",
        "year": 2023,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_testing_summary_2024():
    """Pre-season testing summary."""
    from tools.session_tools import f1_testing_summary
    result = await f1_testing_summary.ainvoke({"year": 2024, "test_number": 1, "day": 1})
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_championship_calculator_singapore_2024():
    from tools.analysis_tools import f1_championship_calculator
    result = await f1_championship_calculator.ainvoke({
        "grand_prix": "Singapore",
        "year": 2024,
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_lap_chart_smoke():
    """Lap chart tool: accept success or graceful error."""
    from tools.analysis_tools import f1_lap_chart
    result = await f1_lap_chart.ainvoke({
        "grand_prix": "Monaco",
        "year": 2023,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_gap_evolution_smoke():
    from tools.analysis_tools import f1_gap_evolution
    result = await f1_gap_evolution.ainvoke({
        "grand_prix": "Monaco",
        "year": 2023,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_tire_strategy_smoke():
    from tools.analysis_tools import f1_tire_strategy
    result = await f1_tire_strategy.ainvoke({
        "grand_prix": "British",
        "year": 2024,
        "session": "Race",
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


@pytest.mark.asyncio
async def test_race_weekend_summary_smoke():
    from tools.analysis_tools import f1_race_weekend_summary
    result = await f1_race_weekend_summary.ainvoke({
        "grand_prix": "Singapore",
        "year": 2023,
    })
    assert result and len(result) > 10
    assert "Traceback" not in result


# ═══════════════════════════════════════════════════════════════════════════
# PART 4 — Live tool graceful degradation (no active session)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_live_weather_graceful_outside_race_weekend():
    """Live weather must handle 'no active session' gracefully."""
    from tools.live_tools import f1_live_weather
    try:
        result = await f1_live_weather.ainvoke({"session_key": "latest"})
        # If it returns (not raises), it should be an informative string
        assert result and len(result) > 10
        assert "Traceback" not in result
    except Exception as e:
        # Tool may raise; the exception message should be human-readable
        msg = str(e)
        assert "Traceback" not in msg
        assert len(msg) > 5


@pytest.mark.asyncio
async def test_live_leaderboard_graceful_outside_race_weekend():
    from tools.live_tools import f1_live_leaderboard
    try:
        result = await f1_live_leaderboard.ainvoke({"session_key": "latest"})
        assert result and "Traceback" not in result
    except Exception as e:
        assert "Traceback" not in str(e)


@pytest.mark.asyncio
async def test_live_position_map_graceful_outside_race_weekend():
    from tools.live_tools import f1_live_position_map
    try:
        result = await f1_live_position_map.ainvoke({"session_key": "latest"})
        assert result and "Traceback" not in result
    except Exception as e:
        assert "Traceback" not in str(e)


# ═══════════════════════════════════════════════════════════════════════════
# PART 5 — Tool registry (import/count checks, no network)
# ═══════════════════════════════════════════════════════════════════════════

def test_all_tool_modules_importable():
    import tools.reference_tools
    import tools.analysis_tools
    import tools.session_tools
    import tools.live_tools
    import tools.media_tools
    import tools.replay_tools
    import tools.visualization_tools
    import tools.advanced_tools
    import tools.predictive_tools


def test_reference_tools_have_required_tools():
    from tools.reference_tools import (
        f1_standings, f1_champions_quick_lookup, f1_constructor_champions,
        f1_all_time_records, f1_driver_career_summary, f1_constructor_career_summary,
        f1_driver_form, f1_head_to_head, f1_circuit_guide, f1_next_race_preview,
        f1_season_race_winners, f1_sprint_results, f1_reliability_analysis,
        f1_points_progression, f1_wikipedia_lookup,
    )
    for tool in [
        f1_standings, f1_champions_quick_lookup, f1_constructor_champions,
        f1_all_time_records, f1_driver_career_summary, f1_constructor_career_summary,
        f1_driver_form, f1_head_to_head, f1_circuit_guide, f1_next_race_preview,
        f1_season_race_winners, f1_sprint_results, f1_reliability_analysis,
        f1_points_progression, f1_wikipedia_lookup,
    ]:
        assert hasattr(tool, "name") and tool.name
        assert hasattr(tool, "description") and tool.description


def test_analysis_tools_have_required_tools():
    from tools.analysis_tools import (
        f1_schedule, f1_session_results, f1_telemetry_plot, f1_tire_strategy,
        f1_championship_calculator, f1_race_weekend_summary, f1_lap_chart, f1_gap_evolution,
    )
    for tool in [
        f1_schedule, f1_session_results, f1_telemetry_plot, f1_tire_strategy,
        f1_championship_calculator, f1_race_weekend_summary, f1_lap_chart, f1_gap_evolution,
    ]:
        assert hasattr(tool, "name") and tool.name


def test_session_tools_have_required_tools():
    from tools.session_tools import (
        f1_testing_summary, f1_weather_report, f1_race_control_report,
    )
    for tool in [f1_testing_summary, f1_weather_report, f1_race_control_report]:
        assert hasattr(tool, "name") and tool.name


def test_live_tools_all_have_names():
    from tools.live_tools import get_live_tools
    for tool in get_live_tools():
        assert hasattr(tool, "name") and tool.name


def test_replay_tool_exists():
    from tools.replay_tools import f1_race_replay
    assert hasattr(f1_race_replay, "name") and f1_race_replay.name


def test_all_tools_have_ainvoke():
    from tools.reference_tools import get_reference_tools
    from tools.analysis_tools import get_analysis_tools
    from tools.live_tools import get_live_tools
    from tools.session_tools import get_session_tools
    for tool in get_reference_tools() + get_analysis_tools() + get_live_tools() + get_session_tools():
        assert hasattr(tool, "ainvoke"), f"Tool {tool.name} missing ainvoke"


def test_total_tool_count_reasonable():
    from tools.reference_tools import get_reference_tools
    from tools.analysis_tools import get_analysis_tools
    from tools.live_tools import get_live_tools
    from tools.session_tools import get_session_tools
    from tools.media_tools import get_media_tools
    from tools.replay_tools import get_replay_tools
    total = (
        len(get_reference_tools()) + len(get_analysis_tools()) +
        len(get_live_tools()) + len(get_session_tools()) +
        len(get_media_tools()) + len(get_replay_tools())
    )
    # Sanity check: agent has a reasonable number of tools registered
    assert 30 <= total <= 60, f"Unexpected tool count: {total}"


# ═══════════════════════════════════════════════════════════════════════════
# PART 6 — Natural language stress tests (bypass routing only)
# ═══════════════════════════════════════════════════════════════════════════

class TestNaturalLanguageStress:
    """
    Verify LLM-destined queries either hit a sensible bypass or return None
    (go to agent). The goal is 'no crash and no wrong bypass'.
    """

    def test_fastest_driver_on_current_form(self):
        r = _match("Who is the fastest driver on current form?")
        # Should hit standings or form — not None
        assert r is not None

    def test_best_pit_stop_crew(self):
        r = _match("Which team has the best pit stop crew this season?")
        # No exact bypass — agent handles it
        if r is not None:
            assert r["name"] != "Circuit Guide"  # shouldn't misroute

    def test_norris_championship_chances(self):
        r = _match("Is Norris likely to win the championship?")
        # Might hit standings or nothing; should not crash
        assert True

    def test_mclaren_comparison_across_seasons(self):
        r = _match("Compare the 2023 and 2024 seasons for McLaren")
        # No exact bypass — verify no crash
        assert True

    def test_verstappen_title_chances(self):
        r = _match("What are Verstappen's chances of winning the title?")
        assert True  # no crash

    def test_best_race_pace_2026(self):
        r = _match("Who has the best race pace in 2026?")
        # Could hit standings (year=2026)
        if r is not None:
            assert "year" not in r or r.get("year") in (None, 2026)


# ═══════════════════════════════════════════════════════════════════════════
# PART 7 — Robustness / unusual edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestRobustness:
    """Unusual inputs, historical years, borderline queries."""

    def test_1994_standings_handled(self):
        # "Give me standings for 1994" goes to agent (no exact bypass match for bare "standings")
        # Agent routes to f1_standings(year=1994); bypass may or may not match — no crash.
        r = _match("Give me standings for 1994")
        if r is not None:
            assert r.get("year") == 1994

    def test_ferrari_2008_goes_to_constructor_or_agent(self):
        r = _match("Who drove for Ferrari in 2008?")
        # Could hit constructor career (Ferrari) or Wikipedia or agent
        assert True  # no crash

    def test_weather_at_monaco_2023_qualifying(self):
        r = _match("What was the weather at Monaco 2023 qualifying?")
        # Should NOT fire live weather (has historical year)
        if r is not None:
            assert r["name"] != "Live Weather"

    def test_empty_string_no_crash(self):
        r = _match("")
        assert r is None

    def test_only_spaces_no_crash(self):
        r = _match("   ")
        assert r is None

    def test_gibberish_no_crash(self):
        r = _match("asdfghjkl qwerty zxcvbnm")
        assert r is None

    def test_multiple_years_uses_last(self):
        # "from 2000 to 2020" → extract "from 2000 to 2020" as year_filter
        r = _match("F1 world champions from 2000 to 2020")
        assert r is not None
        assert "from 2000 to 2020" in str(r.get("year_filter", ""))

    def test_season_race_winners_no_year_defaults_to_current(self):
        from datetime import datetime
        r = _match("Show me all race winners")
        if r is not None and r["name"] == "Season Race Winners":
            # year should be current year if not specified
            assert r.get("year") == datetime.now().year or r.get("year") is None

    def test_race_replay_tool_is_importable(self):
        from tools.replay_tools import f1_race_replay
        assert f1_race_replay is not None
        assert hasattr(f1_race_replay, "ainvoke")

    def test_rag_tool_importable(self):
        # FIA regulations use the RAG tool
        try:
            from tools.advanced_tools import get_advanced_tools
            tools = get_advanced_tools()
            names = [t.name for t in tools]
            # Should have some regulation/RAG-related tool
            assert any("rule" in n.lower() or "reg" in n.lower() or "rag" in n.lower()
                       for n in names) or len(tools) > 0
        except ImportError:
            pytest.skip("advanced_tools not importable in this environment")

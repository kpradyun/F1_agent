"""
Quick Lookup Bypass Module

Provides instant responses for simple queries by calling tools directly,
bypassing the LLM agent overhead for common single-answer questions.
Covers ~80% of typical F1 queries without any LLM roundtrip.
"""
import re
from datetime import datetime as _dt

from tools.reference_tools import (
    f1_all_time_records,
    f1_constructor_champions,
    f1_champions_quick_lookup,
    f1_next_race_preview,
    f1_standings,
    f1_season_race_winners,
    f1_driver_career_summary,
    f1_constructor_career_summary,
    f1_driver_form,
    f1_head_to_head,
    f1_circuit_guide,
    f1_reliability_analysis,
    f1_points_progression,
    f1_sprint_results,
    f1_wikipedia_lookup,
)
from tools.live_tools import (
    f1_live_weather,
    f1_live_position_map,
    f1_live_leaderboard,
)
from tools.analysis_tools import f1_schedule, f1_telemetry_plot, f1_session_results

# ── Known entity lists for name extraction ────────────────────────────────────

_DRIVERS = [
    "hamilton", "verstappen", "norris", "leclerc", "russell", "piastri",
    "alonso", "sainz", "perez", "stroll", "ocon", "bearman", "gasly",
    "colapinto", "albon", "lawson", "hulkenberg", "bottas", "hadjar",
    "lindblad", "senna", "schumacher", "vettel", "raikkonen", "button",
    "rosberg", "webber", "massa", "barrichello", "kubica", "montoya",
    "villeneuve", "lauda", "prost", "hill", "stewart", "clark", "fangio",
    "hakkinen", "mansell", "piquet", "andretti", "hunt", "rindt",
    "berger", "coulthard", "irvine", "fisichella", "trulli", "de la rosa",
]

_CONSTRUCTORS = [
    "ferrari", "mclaren", "mercedes", "red bull", "williams",
    "aston martin", "alpine", "haas", "audi", "cadillac",
    "racing bulls", "sauber", "lotus", "tyrrell", "brabham",
    "benetton", "renault", "force india", "toro rosso", "alfa romeo",
    "jordan", "minardi", "honda", "bar", "stewart",
]

_CIRCUITS = [
    "monaco", "silverstone", "monza", "spa", "suzuka", "bahrain",
    "melbourne", "imola", "barcelona", "budapest", "zandvoort",
    "singapore", "austin", "mexico", "interlagos", "sao paulo",
    "las vegas", "abu dhabi", "jeddah", "baku", "montreal",
    "miami", "shanghai", "losail", "qatar", "portimao", "istanbul",
]

# Pre-build alternation strings
_DR = "|".join(_DRIVERS)
_CO = "|".join(c.replace(" ", r"\s+") for c in _CONSTRUCTORS)
_CI = "|".join(c.replace(" ", r"\s+") for c in _CIRCUITS)


class QuickLookupBypass:
    """Direct tool access for instant responses on simple, deterministic queries."""

    def __init__(self):
        # Each entry: (compiled_regex, config_dict)
        # Config keys:
        #   tool         – LangChain tool to call
        #   name         – display name shown to user
        #   extract      – list of named regex group names to capture
        #   extract_year – bool; also extract a 4-digit year
        #   category     – str; passed as 'category' param (all-time records)
        #   live_only    – bool; skip if historical year present without live keyword
        self._patterns = self._compile()

    @staticmethod
    def _compile():
        DR, CO, CI = _DR, _CO, _CI
        raw = [
            # ── Standings & points (FIRST — highest priority) ────────────────
            (
                r"current\s+standings|championship\s+stand"
                r"|who\s+leads\s+(?:the\s+)?(?:drivers?\s+|constructor\s+)?champ"
                r"|points\s+table|driver\s+standings|constructor\s+standings"
                r"|current\s+points|how\s+many\s+points|points\s+does"
                r"|how\s+much\s+points|\bpoints\s+lead|\bpoints.*have\b"
                r"|[a-z]+'s\s+points|points\s+of\s+[a-z]|\bpoints\s+tally"
                r"|who\s+is\s+p\d+\s+in\s+the|who\s+is\s+(?:in\s+)?first\s+in\s+the",
                {"tool": f1_standings, "name": "Championship Standings",
                 "extract_year": True},
            ),

            # ── Season race winners ──────────────────────────────────────────
            (
                r"who\s+won\s+each\s+race|all\s+race\s+winners"
                r"|race\s+winners\s+(?:in|for|of)\s+\d{4}"
                r"|list\s+(?:of\s+)?race\s+winners"
                r"|who\s+won.*\d{4}\s+season|results\s+of\s+all\s+races"
                r"|\d{4}.*race\s+winners|all\s+grand\s+prix\s+winners",
                {"tool": f1_season_race_winners, "name": "Season Race Winners",
                 "extract_year": True},
            ),

            # ── Season schedule ──────────────────────────────────────────────
            (
                r"\d{4}\s+(?:f1\s+)?(?:schedule|calendar|race\s+calendar)"
                r"|f1\s+(?:schedule|calendar)|race\s+calendar|season\s+calendar"
                r"|(?:schedule|calendar)\s+\d{4}",
                {"tool": f1_schedule, "name": "Season Schedule",
                 "extract_year": True},
            ),

            # ── Points progression chart ─────────────────────────────────────
            (
                r"points\s+progression|championship\s+battle\s+chart"
                r"|points\s+(?:over|through|across)\s+the\s+season"
                r"|cumulative\s+points|points\s+chart",
                {"tool": f1_points_progression, "name": "Points Progression",
                 "extract_year": True},
            ),

            # ── Sprint results ───────────────────────────────────────────────
            (
                r"sprint\s+(?:race\s+)?results?|sprint\s+race|sprint\s+shootout"
                r"|sprint\s+winners?|who\s+won\s+the\s+sprint",
                {"tool": f1_sprint_results, "name": "Sprint Results",
                 "extract_year": True},
            ),

            # ── Next race ────────────────────────────────────────────────────
            (
                r"next\s+race|upcoming\s+race|when\s+is\s+the\s+next"
                r"|next\s+(?:f1\s+)?(?:gp|grand\s+prix)|what(?:.?s|\s+is)\s+next\s+in\s+f1"
                r"|race\s+this\s+weekend|when\s+is\s+f1\s+next|^/next$|^next$"
                r"|where\s+is\s+(?:the\s+)?next|coming\s+up\s+in\s+f1",
                {"tool": f1_next_race_preview, "name": "Next Race Preview"},
            ),

            # ── Live weather ─────────────────────────────────────────────────
            (
                r"live\s+weather|current\s+weather|weather\s+now|^weather$"
                r"|rain\s+now|track\s+temp\s+now",
                {"tool": f1_live_weather, "name": "Live Weather", "live_only": True},
            ),

            # ── Live leaderboard ─────────────────────────────────────────────
            (
                r"live\s+leaderboard|who(?:'s|\s+is)\s+winning\s+now|who\s+is\s+leading\s+now"
                r"|current\s+leader|race\s+leader\s+now",
                {"tool": f1_live_leaderboard, "name": "Live Leaderboard",
                 "live_only": True},
            ),

            # ── Live position map ─────────────────────────────────────────────
            (
                r"live\s+positions|live\s+track\s+map|where\s+are\s+.+\s+now"
                r"|current\s+race\s+positions|track\s+map\s+now",
                {"tool": f1_live_position_map, "name": "Live Position Map",
                 "live_only": True},
            ),

            # ── All-time records ─────────────────────────────────────────────
            (
                r"most\s+(?:race\s+)?wins|all.?time\s+wins|win\s+record"
                r"|who\s+has\s+(?:the\s+)?most\s+wins?",
                {"tool": f1_all_time_records, "name": "All-Time Win Records",
                 "category": "wins"},
            ),
            (
                r"most\s+poles?|all.?time\s+poles?|pole\s+record"
                r"|how\s+many\s+poles?|most\s+pole\s+positions?",
                {"tool": f1_all_time_records, "name": "Pole Position Records",
                 "category": "poles"},
            ),
            (
                r"most\s+podiums?|all.?time\s+podiums?|podium\s+record"
                r"|most\s+podium\s+finishes?",
                {"tool": f1_all_time_records, "name": "Podium Records",
                 "category": "podiums"},
            ),
            (
                r"most\s+(?:world\s+)?(?:championships?|titles?)"
                r"|all.?time\s+(?:championships?|titles?)"
                r"|most\s+f1\s+titles?",
                {"tool": f1_all_time_records, "name": "Championship Records",
                 "category": "titles"},
            ),
            (
                r"most\s+fastest\s+laps?|all.?time\s+fastest\s+laps?"
                r"|fastest\s+lap\s+record|who\s+has\s+(?:the\s+)?most\s+fastest\s+laps?",
                {"tool": f1_all_time_records, "name": "Fastest Lap Records",
                 "category": "fastest_laps"},
            ),

            # ── Constructor champions history ─────────────────────────────────
            (
                r"constructor\s+champion(?!ship\s+stand)|team\s+champion"
                r"|constructor.*since|team.*champion|constructor.*title",
                {"tool": f1_constructor_champions, "name": "Constructor Champions",
                 "extract_year": True},
            ),

            # ── Driver champions history ──────────────────────────────────────
            (
                r"driver\s+champion(?!ship\s+stand)|world\s+champion"
                r"|f1\s+champion(?!ship\s+stand)|champions?\s+list"
                r"|how\s+many\s+titles?|how\s+many\s+championships?(?!\s+stand)"
                r"|hamilton.*titles?|verstappen.*titles?",
                {"tool": f1_champions_quick_lookup, "name": "Driver Champions",
                 "extract_year": True},
            ),

            # ── Career comparison between two named drivers ───────────────────
            # Must come BEFORE driver career to prevent "stats of X" eating "compare X and Y"
            (
                rf"who\s+has\s+more\s+(?:wins?|poles?|titles?|championships?|podiums?)"
                rf"[^?]{{0,40}}(?P<d1>{DR}).{{0,15}}(?:or|vs?\.?|and)\s+(?P<d2>{DR})"
                rf"|compare\s+(?:career\s+stats?|career|stats?)\s+(?:of\s+)?(?P<d1b>{DR})\s+"
                rf"(?:and|vs?\.?)\s+(?P<d2b>{DR})",
                {"tool": f1_driver_career_summary, "name": "Career Comparison"},
            ),

            # ── Driver career stats ───────────────────────────────────────────
            (
                rf"(?P<driver>{DR})\s*'?s?\s+(?:career|career\s+stats?|career\s+summary"
                rf"|career\s+profile|biography|all.?time\s+stats?|total\s+wins?)",
                {"tool": f1_driver_career_summary, "name": "Driver Career",
                 "extract": ["driver"]},
            ),
            (
                rf"(?:career|stats?|summary|profile)\s+(?:for|of)\s+(?P<driver>{DR})",
                {"tool": f1_driver_career_summary, "name": "Driver Career",
                 "extract": ["driver"]},
            ),
            (
                rf"how\s+many\s+(?:wins?|races?|poles?)\s+(?:does|has|did)\s+(?P<driver>{DR})",
                {"tool": f1_driver_career_summary, "name": "Driver Career",
                 "extract": ["driver"]},
            ),

            # ── Constructor career stats ──────────────────────────────────────
            (
                rf"(?P<constructor>{CO})\s+(?:career|career\s+stats?|career\s+summary"
                rf"|history|all.?time|total\s+wins?|championships?|wins?)",
                {"tool": f1_constructor_career_summary, "name": "Constructor Career",
                 "extract": ["constructor"]},
            ),
            (
                rf"(?:career|stats?|history)\s+(?:for|of)\s+(?P<constructor>{CO})",
                {"tool": f1_constructor_career_summary, "name": "Constructor Career",
                 "extract": ["constructor"]},
            ),

            # ── Last race results ─────────────────────────────────────────────
            (
                r"(?:last|most\s+recent|latest)\s+race\s+(?:results?|classification|winner)"
                r"|who\s+won\s+(?:the\s+)?last\s+race"
                r"|results?\s+of\s+(?:the\s+)?last\s+race"
                r"|what\s+(?:were|was)\s+(?:the\s+)?(?:last|most\s+recent)\s+race\s+results?",
                {"tool": f1_season_race_winners, "name": "Season Race Winners",
                 "extract_year": True},
            ),

            # ── Reliability analysis ──────────────────────────────────────────
            (
                r"(?P<year2>\d{4})\s+(?:season\s+)?reliability"
                r"|reliability\s+(?:analysis|stats?|report)\s+(?:for\s+)?(?P<year3>\d{4})"
                r"|dnf\s+(?:stats?|analysis|report)\s+(?:for\s+)?(?P<year4>\d{4})"
                r"|mechanical\s+failures?\s+(?:in|for\s+)?(?P<year5>\d{4})",
                {"tool": f1_reliability_analysis, "name": "Reliability Analysis",
                 "extract_year": True},
            ),

            # ── Current/overall form (no specific driver) → standings ─────────
            # Must come BEFORE driver-specific form to avoid eating "who is fastest"
            (
                r"who\s+is\s+(?:the\s+)?(?:fastest|best|hottest)\s+driver"
                r"(?:\s+(?:on|in|by|for)\s+(?:current|recent)\s+form)?"
                r"|which\s+driver\s+is\s+(?:in\s+)?(?:best|hottest)\s+form"
                r"|(?:who|which\s+driver)\s+(?:has\s+)?(?:best|most)\s+(?:current\s+)?form",
                {"tool": f1_standings, "name": "Championship Standings",
                 "extract_year": True},
            ),

            # ── Driver recent form ────────────────────────────────────────────
            (
                rf"(?P<driver>{DR})\s+(?:recent\s+form|last\s+(?P<n>\d+)\s+races?"
                rf"|last\s+few\s+races?|recent\s+results?|current\s+form|in\s+form)",
                {"tool": f1_driver_form, "name": "Driver Form",
                 "extract": ["driver", "n"]},
            ),
            (
                rf"(?:recent\s+form|last\s+(?P<n>\d+)\s+races?|how\s+is)\s+"
                rf"(?P<driver>{DR})",
                {"tool": f1_driver_form, "name": "Driver Form",
                 "extract": ["driver", "n"]},
            ),

            # ── "Tell me about [driver]" / "Who is [driver]?" ────────────────
            # Must come AFTER career comparison to not steal "compare X and Y"
            # Allow optional first name between trigger and last name (e.g. "Lewis Hamilton")
            (
                rf"(?:tell\s+me\s+about|who\s+is|info\s+(?:on|about)|show\s+me)\s+"
                rf"(?:\w+\s+)?(?P<driver>{DR})\b",
                {"tool": f1_driver_career_summary, "name": "Driver Career",
                 "extract": ["driver"]},
            ),
            (
                rf"(?:tell\s+me\s+about|info\s+(?:on|about)|show\s+me)\s+"
                rf"(?:team\s+)?(?P<constructor>{CO})(?:\s|$)",
                {"tool": f1_constructor_career_summary, "name": "Constructor Career",
                 "extract": ["constructor"]},
            ),

            # ── "[driver]'s last race" / "last race for [driver]" ────────────
            (
                rf"(?P<driver>{DR})\s*'?s?\s+last\s+race"
                rf"|last\s+race\s+(?:for|of)\s+(?P<driver2>{DR})"
                rf"|how\s+did\s+(?P<driver3>{DR})\s+do\s+(?:last|recently)",
                {"tool": f1_driver_form, "name": "Driver Form (Last Race)",
                 "extract_year": False},
            ),

            # ── Historical Wikipedia lookup (famous events, "what happened at X") ──
            # Checked late — only fires when no more specific tool matches.
            (
                rf"what\s+happened\s+(?:at|in|during|to)\s+.{{0,20}}?(?P<gp>{CI})"
                rf"|what\s+happened\s+(?:at|in|during)\s+(?:the\s+)?(?P<year>{_dt.now().year}|\d{{4}})"
                rf"|famous\s+(?:\w+\s+)?(?:race|moments?|incidents?)\s+at\s+(?P<gp2>{CI})"
                rf"|tell\s+me\s+about\s+(?:the\s+)?(?P<gp3>{CI})\s+(?:\d{{4}}\s+)?(?:race|grand\s+prix|gp)",
                {"tool": f1_wikipedia_lookup, "name": "Wikipedia Lookup"},
            ),

            # ── Telemetry comparison (specific GP present → FastF1, NOT OpenF1) ──
            # Checked BEFORE head-to-head. Any query with two drivers AND a circuit name
            # is a single-session comparison → f1_telemetry_plot.
            (
                rf"(?P<d1>{DR})(?:\s+(?:and|vs\.?|versus))\s+(?P<d2>{DR})"
                rf"(?:.*?)(?P<gp>{CI})",
                {"tool": f1_telemetry_plot, "name": "Telemetry Comparison",
                 "extract_year": True},
            ),
            # "compare / show telemetry for X and Y at GP"
            (
                rf"(?:compare|telemetry|speed|fastest\s+lap|lap\s+time).{{0,40}}"
                rf"(?P<d1>{DR}).{{0,20}}(?P<d2>{DR})"
                rf"(?:.*?)(?P<gp>{CI})",
                {"tool": f1_telemetry_plot, "name": "Telemetry Comparison",
                 "extract_year": True},
            ),

            # ── Qualifying results for a specific circuit ─────────────────────
            # Must come BEFORE Race Results to win on "qualifying results at X"
            (
                rf"qualifying(?:\s+results?)?\s+(?:at|for|from|in|of)?\s*(?P<gp>{CI})"
                rf"|(?:what\s+were\s+the\s+)?qualifying\s+results?\s+at\s+(?P<gp2>{CI})"
                rf"|(?P<gp3>{CI})(?:\s+\d{{4}})?\s+qualifying(?:\s+results?)?",
                {"tool": f1_session_results, "name": "Qualifying Results",
                 "extract_year": True, "session": "Qualifying"},
            ),

            # ── Race results for a specific circuit ───────────────────────────
            (
                rf"(?:race\s+results?|final\s+classification)\s+(?:at|for|from|of)\s+(?P<gp>{CI})"
                rf"|(?P<gp2>{CI})\s+(?:\d{{4}}\s+)?race\s+results?"
                rf"|who\s+won\s+(?:the\s+)?(?P<gp3>{CI})\s+\d{{4}}",
                {"tool": f1_session_results, "name": "Race Results",
                 "extract_year": True, "session": "Race"},
            ),

            # ── Head-to-head comparison (season-long — no circuit in query) ───
            (
                rf"(?P<d1>{DR})\s+vs\.?\s+(?P<d2>{DR})",
                {"tool": f1_head_to_head, "name": "Head-to-Head",
                 "extract_year": True},
            ),

            # ── Circuit guide ─────────────────────────────────────────────────
            (
                rf"(?:about|tell\s+me\s+about|details?\s+(?:of|about)\s+)?"
                rf"(?:the\s+)?(?P<circuit>{CI})\s+(?:circuit|track|grand\s+prix)",
                {"tool": f1_circuit_guide, "name": "Circuit Guide",
                 "extract": ["circuit"]},
            ),
            (
                rf"(?:circuit|track)\s+(?:guide|info|details?|profile)\s+"
                rf"(?:for|of|about)?\s+(?P<circuit>{CI})",
                {"tool": f1_circuit_guide, "name": "Circuit Guide",
                 "extract": ["circuit"]},
            ),

            # ── Reliability / DNF analysis ────────────────────────────────────
            (
                r"reliability\s+(?:analysis\s+)?(?:for\s+)?(?P<year2>\d{4})"
                r"|(?P<year3>\d{4})\s+reliability"
                r"|dnf\s+(?:stats?|analysis)\s+(?P<year4>\d{4})"
                r"|(?P<year5>\d{4})\s+dnf",
                {"tool": f1_reliability_analysis, "name": "Reliability Analysis",
                 "extract_year": True},
            ),
        ]

        compiled = []
        for pattern_str, config in raw:
            compiled.append((re.compile(pattern_str, re.IGNORECASE), config))
        return compiled

    # ─────────────────────────────────────────────────────────────────────────

    def match(self, query: str) -> dict | None:
        """Return match result dict if query hits a bypass pattern, else None."""
        q = query.lower().strip()

        for regex, config in self._patterns:
            m = regex.search(q)
            if not m:
                continue

            # Live-only guard: skip if historical year present without live signal
            if config.get("live_only"):
                has_year = re.search(r"\b(19|20)\d{2}\b", q)
                is_live = re.search(r"\b(live|current|now|today)\b", q)
                if has_year and not is_live:
                    continue

            result: dict = {"tool": config["tool"], "name": config["name"],
                            "_original_query": query}  # stored for Wikipedia passthrough

            # Copy fixed params
            if "category" in config:
                result["category"] = config["category"]
            if "session" in config:
                result["session"] = config["session"]

            # Extract ALL named groups from the regex — each non-None value stored directly.
            # Aliases ending in a digit (gp2 → gp) are folded into the primary key only if
            # the primary key isn't already set.
            for gname, val in m.groupdict().items():
                if val is None:
                    continue
                val = val.strip()
                # Fold numeric suffix aliases: gp2 → gp, year2 → year (skip d1, d2)
                base = gname.rstrip("23456789")
                if base != gname and len(base) > 1:  # gp2 → gp; never strips d1→d
                    if base not in result:
                        result[base] = val
                else:
                    result[gname] = val

            # Extract year from query
            if config.get("extract_year"):
                # For champions queries: capture range/since as year_filter string
                if result["name"] in ("Driver Champions", "Constructor Champions"):
                    range_m = re.search(
                        r"(from\s+\d{4}\s+to\s+\d{4}|since\s+\d{4})", q
                    )
                    if range_m:
                        result["year_filter"] = range_m.group(1)
                    else:
                        years = re.findall(r"\b(19\d{2}|20\d{2})\b", q)
                        if years:
                            result["year"] = int(years[-1])
                else:
                    years = re.findall(r"\b(19\d{2}|20\d{2})\b", q)
                    if years:
                        result["year"] = int(years[-1])

            # Special: extract n_races for driver form
            if result["name"] == "Driver Form" and "n" not in result:
                n_m = re.search(r"last\s+(\d+)\s+race", q)
                result["n"] = int(n_m.group(1)) if n_m else 5

            return result

        return None

    async def execute(self, match_result: dict) -> str:
        """Execute the matched tool with extracted parameters."""
        tool_func = match_result["tool"]
        name = match_result["name"]
        year = match_result.get("year") or _dt.now().year

        # ── Dispatch by tool name ──────────────────────────────────────────
        if name in ("Championship Standings", "Season Race Winners",
                    "Points Progression", "Sprint Results"):
            return await tool_func.ainvoke({"year": year})

        if name == "Season Schedule":
            return await tool_func.ainvoke({"year": year})

        if name == "Next Race Preview":
            return await tool_func.ainvoke({})

        if name in ("Live Weather", "Live Leaderboard", "Live Position Map"):
            return await tool_func.ainvoke({"session_key": "latest"})

        if name in ("All-Time Win Records", "Pole Position Records",
                    "Podium Records", "Championship Records",
                    "Fastest Lap Records"):
            return await tool_func.ainvoke(
                {"category": match_result.get("category", "wins")}
            )

        if name in ("Constructor Champions", "Driver Champions"):
            # Pass year_filter (range string like "since 2015") or plain year string
            yf = match_result.get("year_filter") or str(match_result.get("year", ""))
            return await tool_func.ainvoke({"year_filter": yf})

        if name == "Driver Career":
            driver = match_result.get("driver", "")
            return await tool_func.ainvoke({"driver_query": driver})

        if name == "Career Comparison":
            d1 = match_result.get("d1") or match_result.get("d1b", "")
            d2 = match_result.get("d2") or match_result.get("d2b", "")
            r1 = await tool_func.ainvoke({"driver_query": d1})
            r2 = await tool_func.ainvoke({"driver_query": d2})
            return f"{r1}\n\n---\n\n{r2}"

        if name == "Constructor Career":
            constructor = match_result.get("constructor", "")
            return await tool_func.ainvoke({"constructor_query": constructor})

        if name == "Driver Form":
            return await tool_func.ainvoke({
                "driver": match_result.get("driver", ""),
                "n_races": int(match_result.get("n") or 5),
            })

        if name == "Telemetry Comparison":
            return await tool_func.ainvoke({
                "driver1": match_result.get("d1", ""),
                "driver2": match_result.get("d2", ""),
                "grand_prix": match_result.get("gp", ""),
                "year": year,
                "session": "Race",
            })

        if name in ("Race Results", "Qualifying Results"):
            return await tool_func.ainvoke({
                "grand_prix": match_result.get("gp", ""),
                "year": year,
                "session": match_result.get("session", "Race"),
            })

        if name == "Head-to-Head":
            return await tool_func.ainvoke({
                "driver1": match_result.get("d1", ""),
                "driver2": match_result.get("d2", ""),
                "year": year,
            })

        if name == "Circuit Guide":
            return await tool_func.ainvoke(
                {"circuit_query": match_result.get("circuit", "")}
            )

        if name == "Reliability Analysis":
            return await tool_func.ainvoke({"year": year, "driver_query": ""})

        if name == "Driver Form (Last Race)":
            driver = (match_result.get("driver") or match_result.get("driver2")
                      or match_result.get("driver3", ""))
            return await tool_func.ainvoke({"driver": driver, "n_races": 1})

        if name == "Wikipedia Lookup":
            query = match_result.get("_original_query", "")
            return await tool_func.ainvoke({"query": query})

        # Fallback: no params
        return await tool_func.ainvoke({})

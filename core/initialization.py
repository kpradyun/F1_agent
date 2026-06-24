"""
System Initialization Module
Pre-loads heavy components during startup to avoid first-query delays
"""
from __future__ import annotations
import os
import logging
from dataclasses import dataclass
from typing import Optional, Type
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console

from config.settings import (
    LLM_MODEL, LLM_TEMPERATURE, LLM_PROVIDER,
    GEMINI_MODEL, GEMINI_API_KEY, ensure_directories,
)
from langchain_ollama import ChatOllama
from utils.cache_manager import get_cache

logger = logging.getLogger("F1_Agent")
console = Console()

__all__ = ["initialize_systems", "get_llm", "get_bypass"]


@dataclass
class _AppState:
    llm: Optional[object] = None
    QuickLookupBypass: Optional[Type] = None


_state = _AppState()


def get_llm() -> Optional[object]:
    """Return the initialized LLM instance."""
    return _state.llm


def get_bypass() -> Optional[Type]:
    """Return the QuickLookupBypass class."""
    return _state.QuickLookupBypass


def _initialize_llm(progress, task_id) -> object:
    if LLM_PROVIDER == "gemini":
        return _try_gemini(progress, task_id)

    try:
        candidate = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
        candidate.invoke("ping")
        _state.llm = candidate
        progress.update(task_id, description=f"[green]✓ Ollama ({LLM_MODEL}) connected")
        return _state.llm
    except Exception as e:
        logger.warning(f"Ollama unavailable ({e}), trying Gemini fallback...")
        progress.update(task_id, description="[yellow]⚠ Ollama unavailable — trying Gemini...")
        return _try_gemini(progress, task_id)


def _try_gemini(progress, task_id) -> object:
    if not GEMINI_API_KEY:
        progress.update(task_id, description="[red]✗ No LLM available (set GEMINI_API_KEY in .env)")
        raise RuntimeError(
            "Ollama is not running and GEMINI_API_KEY is not set.\n"
            "  Option A: start Ollama with 'ollama serve'\n"
            "  Option B: add GEMINI_API_KEY=... to your .env file and set LLM_PROVIDER=gemini"
        )
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _state.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=GEMINI_API_KEY,
        )
        progress.update(task_id, description=f"[green]✓ Gemini ({GEMINI_MODEL}) connected")
        return _state.llm
    except Exception as e:
        logger.error(f"Gemini initialization error: {e}")
        progress.update(task_id, description="[red]✗ Gemini connection failed")
        raise RuntimeError(f"Could not connect to any LLM provider: {e}") from e


def initialize_systems() -> tuple:
    """
    Pre-load heavy components during startup to avoid first-query delays.

    Returns:
        tuple: (llm, QuickLookupBypass)
    """
    ensure_directories()

    from utils.quick_lookup import QuickLookupBypass as QLB
    _state.QuickLookupBypass = QLB

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        task1 = progress.add_task("[cyan]Loading regulation database…", total=None)
        try:
            from rag_engine import _initialize_rag
            if _initialize_rag():
                progress.update(task1, description="[green]✓ Regulation database ready")
            else:
                progress.update(task1, description="[yellow]⚠ RAG database not found")
        except Exception as e:
            logger.error(f"RAG initialization error: {e}")
            progress.update(task1, description="[red]✗ RAG initialization failed")

        task2 = progress.add_task("[cyan]Configuring FastF1 cache…", total=None)
        try:
            import fastf1
            cache_dir = os.path.abspath("cache")
            os.makedirs(cache_dir, exist_ok=True)
            fastf1.Cache.enable_cache(cache_dir)
            n_files = len([f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))])
            progress.update(task2, description=f"[green]✓ FastF1 cache ready ({n_files} files)")
        except Exception as e:
            logger.error(f"FastF1 cache error: {e}")
            progress.update(task2, description="[yellow]⚠ FastF1 cache issues")

        task3 = progress.add_task("[cyan]Connecting to LLM…", total=None)
        _initialize_llm(progress, task3)

        task4 = progress.add_task("[cyan]Initialising app cache…", total=None)
        try:
            cache = get_cache()
            stats = cache.get_stats()
            progress.update(
                task4,
                description=(
                    f"[green]✓ App cache ready "
                    f"({stats['total_entries']} entries, {stats['total_size_mb']:.1f} MB)"
                ),
            )
        except Exception as e:
            logger.error(f"Cache initialization error: {e}")
            progress.update(task4, description="[yellow]⚠ Cache system warning")

    return _state.llm, _state.QuickLookupBypass

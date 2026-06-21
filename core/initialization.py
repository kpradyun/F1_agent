"""
System Initialization Module
Pre-loads heavy components during startup to avoid first-query delays
"""
import os
import logging
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console

from config.settings import (
    LLM_MODEL, LLM_TEMPERATURE, LLM_PROVIDER,
    GEMINI_MODEL, GEMINI_API_KEY,
)
from langchain_ollama import ChatOllama
from utils.cache_manager import get_cache

logger = logging.getLogger("F1_Agent")
console = Console()

# Global variables
llm = None
QuickLookupBypass = None

def _initialize_llm(progress, task_id):
    """
    Try Ollama first. If unavailable (or LLM_PROVIDER=gemini), fall back to Gemini.
    Raises RuntimeError if neither provider succeeds.
    """
    global llm

    if LLM_PROVIDER == "gemini":
        return _try_gemini(progress, task_id)

    # Default: try Ollama
    try:
        candidate = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
        # Cheap test call to confirm Ollama is actually reachable
        candidate.invoke("ping")
        llm = candidate
        progress.update(task_id, description=f"[green]✓ Ollama ({LLM_MODEL}) connected")
        return llm
    except Exception as e:
        logger.warning(f"Ollama unavailable ({e}), trying Gemini fallback...")
        progress.update(task_id, description="[yellow]⚠ Ollama unavailable — trying Gemini...")
        return _try_gemini(progress, task_id)


def _try_gemini(progress, task_id):
    """Initialize ChatGoogleGenerativeAI as the LLM."""
    global llm
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
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=GEMINI_API_KEY,
        )
        progress.update(task_id, description=f"[green]✓ Gemini ({GEMINI_MODEL}) connected")
        return llm
    except Exception as e:
        logger.error(f"Gemini initialization error: {e}")
        progress.update(task_id, description="[red]✗ Gemini connection failed")
        raise RuntimeError(f"Could not connect to any LLM provider: {e}") from e


def initialize_systems():
    """
    Pre-load heavy components during startup to avoid first-query delays.
    This dramatically improves UX by making the first interaction instant.
    
    Returns:
        tuple: (llm, QuickLookupBypass) - Initialized components
    """
    global llm, QuickLookupBypass
    
    # Import bypass module
    from utils.quick_lookup import QuickLookupBypass as QLB
    QuickLookupBypass = QLB
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task1 = progress.add_task("[cyan]Loading regulation database...", total=None)
        try:
            from rag_engine import _initialize_rag
            if _initialize_rag():
                progress.update(task1, description="[green]✓ Regulation database ready")
            else:
                progress.update(task1, description="[yellow]⚠ RAG database not found")
        except Exception as e:
            logger.error(f"RAG initialization error: {e}")
            progress.update(task1, description="[red]✗ RAG initialization failed")
        
        task2 = progress.add_task("[cyan]Configuring FastF1 cache...", total=None)
        try:
            import fastf1
            cache_dir = os.path.abspath('cache')
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            fastf1.Cache.enable_cache(cache_dir)
            progress.update(task2, description="[green]✓ FastF1 cache configured")
        except Exception as e:
            logger.error(f"FastF1 cache error: {e}")
            progress.update(task2, description="[yellow]⚠ FastF1 cache issues")
        
        task3 = progress.add_task("[cyan]Connecting to LLM...", total=None)
        llm = _initialize_llm(progress, task3)
        
        task4 = progress.add_task("[cyan]Preparing cache system...", total=None)
        try:
            cache = get_cache()
            stats = cache.get_stats()
            progress.update(
                task4, 
                description=f"[green]✓ Cache ready ({stats['total_entries']} entries, {stats['total_size_mb']:.1f}MB)"
            )
        except Exception as e:
            logger.error(f"Cache initialization error: {e}")
            progress.update(task4, description="[yellow]⚠ Cache system warning")
    
    return llm, QuickLookupBypass

def get_llm():
    """Get the initialized LLM instance"""
    return llm

def get_bypass():
    """Get the QuickLookupBypass class"""
    return QuickLookupBypass

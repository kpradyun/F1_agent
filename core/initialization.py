"""
System Initialization Module
Pre-loads heavy components during startup to avoid first-query delays
"""
import os
import logging
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console

from config.settings import LLM_MODEL, LLM_TEMPERATURE
from langchain_ollama import ChatOllama
from utils.cache_manager import get_cache

logger = logging.getLogger("F1_Agent")
console = Console()

# Global variables
llm = None
QuickLookupBypass = None

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
        try:
            llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
            progress.update(task3, description="[green]✓ LLM connection established")
        except Exception as e:
            logger.error(f"LLM initialization error: {e}")
            progress.update(task3, description="[red]✗ LLM connection failed")
            raise
        
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

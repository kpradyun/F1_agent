"""
RAG Engine for F1 Regulations

Clean tool interface - heavy logic extracted to core modules
"""
import os
import logging
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool

from core.rag_setup import DB_PATH, setup_knowledge_base
from core.rag_search import smart_rag_search

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('f1_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RAG_Engine")

_EMBEDDINGS = None
_VECTORSTORE = None
_RAG_INITIALIZED = False

def _initialize_rag():
    """Initialize RAG components once at module load time."""
    global _EMBEDDINGS, _VECTORSTORE, _RAG_INITIALIZED
    
    if _RAG_INITIALIZED:
        return True
    
    try:
        logger.info("Initializing RAG engine (one-time load)...")
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        if os.path.exists(DB_PATH):
            _VECTORSTORE = FAISS.load_local(
                DB_PATH, 
                _EMBEDDINGS, 
                allow_dangerous_deserialization=True
            )
            logger.info("✓ RAG engine initialized successfully")
            _RAG_INITIALIZED = True
            return True
        else:
            logger.warning("Vector database not found. Building it now...")
            if setup_knowledge_base():
                _VECTORSTORE = FAISS.load_local(
                    DB_PATH, 
                    _EMBEDDINGS, 
                    allow_dangerous_deserialization=True
                )
                logger.info("✓ RAG engine initialized successfully")
                _RAG_INITIALIZED = True
                return True
            else:
                logger.error("Failed to build knowledge base")
                return False
    except Exception as e:
        logger.error(f"Failed to initialize RAG: {e}")
        return False

@lru_cache(maxsize=50)
def cached_rag_search(query: str) -> str:
    """
    Cached wrapper around smart_rag_search.
    Frequently asked regulation questions get instant responses.
    """
    return smart_rag_search(query, _VECTORSTORE, _RAG_INITIALIZED)

def get_rag_tool():
    """Returns the Tool object for the Agent."""
    # Initialize RAG components on first call
    _initialize_rag()

    @tool
    def f1_rules_lookup(query: str) -> str:
        """
        Search Official F1 2026 Regulations (FIA Rulebook).
        
        Use ONLY for questions about:
        - Technical specifications (car dimensions, weight, aerodynamics)
        - Power unit regulations
        - Sporting rules (penalties, procedures, race format)
        - Financial regulations (cost cap, budget)
        - Rule changes and updates
        
        Searches across ALL 6 official regulation documents:
        1. Technical Regulations (Chassis)
        2. Sporting Regulations
        3. Financial Regulations
        4. Power Unit Technical Regulations
        5. Power Unit Sporting Regulations
        6. Power Unit Financial Regulations
        
        Examples of GOOD queries:
        - "What is the minimum weight requirement for 2026?"
        - "What are the penalties for exceeding track limits?"
        - "What's included in the cost cap?"
        - "How many power units can a driver use per season?"
        
        DO NOT use for:
        - Historical facts (use f1_wikipedia_lookup)
        - Current season schedule/results (use f1_schedule or f1_session_results)
        - Live race data (use f1_live_* tools)
        - Driver/team information (use f1_wikipedia_lookup)
        
        Returns:
        Relevant excerpts from the regulations with confidence scores.
        The main agent will synthesize these into a clear answer.
        """
        return cached_rag_search(query)

    return f1_rules_lookup

def test_rag_query(query: str):
    """Test RAG search manually"""
    if not _initialize_rag():
        print("Failed to initialize RAG")
        return
    
    print(f"\nQuery: {query}")
    print("="*80)
    result = smart_rag_search(query, _VECTORSTORE, _RAG_INITIALIZED)
    print(result)

if __name__ == "__main__":
    # Test queries
    test_queries = [
        "What is the minimum weight for the car?",
        "How many power units can a driver use?",
        "What are the penalties for ignoring blue flags?",
        "List all technical regulation changes for 2026"
    ]
    
    print("Testing RAG Engine with sample queries...\n")
    for query in test_queries:
        test_rag_query(query)
        print("\n" + "="*80 + "\n")
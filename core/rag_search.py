"""
RAG Search Logic
Smart retrieval and query processing for F1 regulations
"""
import logging

logger = logging.getLogger("RAG_Engine")

def classify_query_type(query: str) -> str:
    """
    Classify query to determine retrieval strategy.
    
    Args:
        query: User query string
        
    Returns:
        'broad': Needs comprehensive overview (use k=8)
        'specific': Precise question (use k=3)
        'standard': Normal query (use k=5)
    """
    query_lower = query.lower()
    
    # Broad queries
    broad_keywords = ['list', 'all', 'every', 'summary', 'overview', 'explain all']
    if any(kw in query_lower for kw in broad_keywords):
        return 'broad'
    
    # Specific queries
    specific_keywords = ['what is', 'define', 'how many', 'when', 'who', 'specific']
    if any(kw in query_lower for kw in specific_keywords):
        return 'specific'
    
    return 'standard'

def smart_rag_search(query: str, vectorstore, is_initialized: bool) -> str:
    """
    Enhanced RAG search with adaptive retrieval and relevance filtering.
    
    Features:
    - Adaptive k-value based on query type
    - Score-based filtering (only show relevant results)
    - Confidence scores for each excerpt
    - Better formatting and organization
    
    Args:
        query: User query
        vectorstore: FAISS vectorstore instance
        is_initialized: Whether RAG is initialized
        
    Returns:
        Formatted search results
    """
    if not is_initialized:
        return "Error: RAG engine not initialized. Please check logs."
    
    try:
        # Determine retrieval strategy
        query_type = classify_query_type(query)
        k_map = {'broad': 8, 'specific': 3, 'standard': 5}
        k = k_map[query_type]
        
        logger.info(f"Query type: {query_type}, retrieving {k} chunks")
        
        # Semantic search with scores
        docs_with_scores = vectorstore.similarity_search_with_score(query, k=k)
        
        # Filter by relevance score
        # FAISS uses L2 distance (lower is better), typical threshold ~0.5-1.0
        relevance_threshold = 0.8
        relevant_docs = [
            (doc, score) for doc, score in docs_with_scores 
            if score < relevance_threshold
        ]
        
        if not relevant_docs:
            # Fallback: show best matches anyway but note lower confidence
            relevant_docs = docs_with_scores[:3]
            fallback_note = "\n⚠️ Note: No highly confident matches found. Showing best available results.\n"
        else:
            fallback_note = ""
        
        # Format results with confidence scores
        result = "=== OFFICIAL F1 2026 REGULATIONS ===\n"
        result += fallback_note
        result += "\n"
        
        sources_used = set()
        
        for i, (doc, score) in enumerate(relevant_docs, 1):
            src = doc.metadata.get('source_book', 'Unknown')
            pg = doc.metadata.get('page', '?')
            sources_used.add(src)
            
            # Convert score to confidence percentage
            # Lower L2 distance = higher confidence
            confidence = max(0, min(100, int((1 - score) * 100)))
            
            # Visual confidence indicator
            if confidence >= 80:
                conf_indicator = "🟢 HIGH"
            elif confidence >= 60:
                conf_indicator = "🟡 MEDIUM"
            else:
                conf_indicator = "🔴 LOW"
            
            result += f"📄 EXCERPT {i} [{conf_indicator} {confidence}% Relevance]\n"
            result += f"Source: {src} - Page {pg}\n"
            result += f"{'-'*80}\n"
            result += f"{doc.page_content.strip()}\n"
            result += f"{'-'*80}\n\n"
        
        # Summary footer
        result += f"{'='*80}\n"
        result += f"📚 Sources Referenced: {', '.join(sorted(sources_used))}\n"
        result += f"✓ Retrieved {len(relevant_docs)} relevant sections from official FIA regulations\n"
        result += f"\n💡 Tip: The main LLM will synthesize these excerpts into a clear answer for you.\n"
        
        return result
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}", exc_info=True)
        return f"Error searching regulations: {str(e)}"

"""
RAG Knowledge Base Setup
Handles PDF download and vector database creation for F1 regulations
"""
import os
import logging
import requests
import backoff
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger("RAG_Engine")

# F1 2026 Regulation PDFs
PDF_URLS = {
    # 1. Car Design (Chassis)
    "Technical_Regs_2026.pdf": "https://www.fia.com/sites/default/files/fia_2026_formula_1_technical_regulations_issue_8_-_2024-06-24.pdf",
    
    # 2. Race Rules (Penalties, Procedures)
    "Sporting_Regs_2026.pdf": "https://api.fia.com/sites/default/files/fia_2026_f1_regulations_-_section_b_sporting_-_iss02_-_2024-12-11.pdf",
    
    # 3. Money (Team Cost Cap)
    "Financial_Regs_2026.pdf": "https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_d_financial_regulations_-_f1_teams_iss_04_-_2025-12-10_0.pdf",
    
    # 4. Engine Design (PU Technical)
    "PU_Technical_Regs_2026.pdf": " https://www.fia.com/sites/default/files/fia_2026_formula_1_technical_regulations_pu_-_issue_6_-_2024-03-29.pdf",
    
    # 5. Engine Usage Rules (PU Sporting)
    "PU_Sporting_Regs_2026.pdf": "https://api.fia.com/sites/default/files/fia_2026_formula_1_sporting_regulations_pu_-_issue_5_-_2024-03-29_0.pdf",
    
    # 6. Engine Cost Cap (PU Financial)
    "PU_Financial_Regs_2026.pdf": "https://api.fia.com/system/files/documents/fia_formula_1_pu_financial_regulations_-_issue_7_-_2025-06-10.pdf"
}

DB_PATH = "f1_rules_db"

@backoff.on_exception(backoff.expo, requests.RequestException, max_tries=3)
def download_pdf(url: str, path: str) -> bool:
    """
    Download PDF with exponential backoff retry.
    
    Args:
        url: PDF download URL
        path: Local file path to save
        
    Returns:
        True if successful
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(path, 'wb') as f:
        f.write(response.content)
    logger.debug(f"Downloaded {path} successfully")
    return True

def setup_knowledge_base() -> bool:
    """
    Downloads PDFs and builds the Vector DB with error recovery.
    
    Returns:
        True if successful, False otherwise
    """
    documents = []
    
    if not os.path.exists("data"):
        os.makedirs("data")

    logger.info(f"Starting download of {len(PDF_URLS)} regulation books.")
    
    for filename, url in PDF_URLS.items():
        path = f"data/{filename}"
        if not os.path.exists(path):
            logger.info(f"Downloading {filename}...")
            try:
                download_pdf(url, path)
                logger.info(f"✓ Successfully downloaded {filename}")
            except Exception as e:
                logger.error(f"✗ Failed to download {filename} after retries: {e}")
                continue
        else:
            logger.info(f"✓ Found existing {filename}")
        
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            # Tag documents with source
            for doc in docs:
                doc.metadata["source_book"] = filename
            documents.extend(docs)
            logger.info(f"✓ Loaded {len(docs)} pages from {filename}")
        except Exception as e:
            logger.error(f"✗ Error reading {filename}: {e}")

    if not documents:
        logger.error("No documents were loaded. Aborting DB build.")
        return False

    logger.info(f"Processing {len(documents)} pages of text...")
    
    # Optimized chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    splits = text_splitter.split_documents(documents)
    
    logger.info(f"Building FAISS Index with {len(splits)} chunks...")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        vectorstore = FAISS.from_documents(splits, embeddings)
        vectorstore.save_local(DB_PATH)
        logger.info("✓ Knowledge Base built successfully!")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to build vector store: {e}")
        return False

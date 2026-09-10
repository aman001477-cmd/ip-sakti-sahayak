import os
import logging
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from utils import validate_pdf_folder, handle_error, logger

PDF_FOLDER = "data/ayush_docs"
PERSIST_DIR = "vector_db/chroma_data"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

JURISDICTION_KEYWORDS = {
    "india": [
        "patent", "indian", "biodiversity", "india", "ayush", "traditional",
        "ayurveda", "tkdl", "patent rules", "biological diversity", "national biodiversity",
        "state biodiversity", "access and benefit sharing", "prior informed consent"
    ],
    "international": [
        "wipo", "nagoya", "epo", "pct", "international", "treaty", "convention",
        "trips", "wto", "cbd", "abs", "traditional knowledge", "genetic resources",
        "intergovernmental committee", "igc", "plant variety", "uPOV"
    ]
}

SECTION_PATTERNS = {
    "india": [
        r"Section\s+(\d+[a-z]?)",
        r"Rule\s+(\d+[a-z]?)",
        r"Article\s+(\d+[a-z]?)",
        r"Schedule\s+(\w+)",
        r"Chapter\s+(\w+)"
    ],
    "international": [
        r"Article\s+(\d+[a-z]?)",
        r"Rule\s+(\d+[a-z]?)",
        r"Paragraph\s+(\d+[a-z]?)",
        r"Annex\s+(\w+)",
        r"Appendix\s+(\w+)"
    ]
}

def detect_jurisdiction(text: str, filename: str) -> str:
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    india_score = sum(1 for kw in JURISDICTION_KEYWORDS["india"] if kw in text_lower or kw in filename_lower)
    intl_score = sum(1 for kw in JURISDICTION_KEYWORDS["international"] if kw in text_lower or kw in filename_lower)
    
    if intl_score > india_score:
        return "international"
    return "india"

def extract_section(text: str, jurisdiction: str) -> str:
    import re
    patterns = SECTION_PATTERNS.get(jurisdiction, [])
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""

def load_documents():
    if not validate_pdf_folder(PDF_FOLDER):
        return []
    
    all_documents = []
    doc_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(('.pdf', '.txt'))]
    
    for doc_file in doc_files:
        doc_path = os.path.join(PDF_FOLDER, doc_file)
        try:
            if doc_file.endswith('.pdf'):
                loader = PyPDFLoader(doc_path)
            else:
                loader = TextLoader(doc_path, encoding='utf-8')
            
            pages = loader.load()
            
            for page in pages:
                page.metadata["source"] = doc_file
                jurisdiction = detect_jurisdiction(page.page_content, doc_file)
                page.metadata["jurisdiction"] = jurisdiction
                
                section = extract_section(page.page_content, jurisdiction)
                if section:
                    page.metadata["section"] = section
            
            all_documents.extend(pages)
            logger.info(f"Loaded {len(pages)} pages from {doc_file} (jurisdiction: {jurisdiction})")
        except Exception as e:
            handle_error(e, f"Loading {doc_file}")
    
    return all_documents

def chunk_documents(documents: List):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True
    )
    
    chunks = text_splitter.split_documents(documents)
    
    for chunk in chunks:
        if "page" not in chunk.metadata:
            chunk.metadata["page"] = 0
        if "section" not in chunk.metadata:
            chunk.metadata["section"] = ""
    
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks

def create_vector_store(chunks: List):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    
    logger.info(f"Vector database saved to {PERSIST_DIR}")
    return vectorstore

def main():
    logger.info("Starting data ingestion...")
    
    documents = load_documents()
    if not documents:
        logger.error("No documents loaded")
        return False
    
    chunks = chunk_documents(documents)
    if not chunks:
        logger.error("No chunks created")
        return False
    
    create_vector_store(chunks)
    
    logger.info("Data ingestion completed successfully!")
    return True

if __name__ == "__main__":
    main()
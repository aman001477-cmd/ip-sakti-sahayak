import os
import logging
import time
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ip_sakti.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def get_groq_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "gsk_your_api_key_here":
        raise ValueError(
            "GROQ_API_KEY not found in .env file. "
            "Please add your Groq API key from https://console.groq.com/keys"
        )
    return api_key

def handle_error(error: Exception, context: str = "") -> str:
    error_msg = f"{context}: {str(error)}" if context else str(error)
    logger.error(error_msg)
    return f"Error: {error_msg}. Please check configuration and try again."

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator

def validate_pdf_folder(pdf_folder: str) -> bool:
    if not os.path.exists(pdf_folder):
        logger.error(f"Document folder not found: {pdf_folder}")
        return False
    doc_files = [f for f in os.listdir(pdf_folder) if f.endswith(('.pdf', '.txt'))]
    if not doc_files:
        logger.warning(f"No PDF or TXT files found in {pdf_folder}")
        return False
    logger.info(f"Found {len(doc_files)} documents in {pdf_folder}")
    return True

def format_sources(sources: list) -> str:
    if not sources:
        return "No sources available."
    
    lines = []
    for i, src in enumerate(sources, 1):
        page = src.get('page', 'N/A')
        juris = src.get('jurisdiction', 'unknown')
        section = src.get('section', '')
        source = src.get('source', 'Unknown')
        
        line = f"{i}. **{source}** — Page {page}"
        if section:
            line += f" — Section: {section}"
        line += f" — *{juris.upper()}*"
        lines.append(line)
    
    return "\n".join(lines)

def clean_text(text: str) -> str:
    import re
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\;\:\-\(\)\[\]\/\%\$\#\@]', '', text)
    return text.strip()

def truncate_text(text: str, max_length: int = 500) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."

def get_document_stats(pdf_folder: str) -> dict:
    if not os.path.exists(pdf_folder):
        return {"total_files": 0, "pdf_files": 0, "txt_files": 0, "total_size_mb": 0}
    
    files = os.listdir(pdf_folder)
    pdf_files = [f for f in files if f.endswith('.pdf')]
    txt_files = [f for f in files if f.endswith('.txt')]
    total_size = sum(os.path.getsize(os.path.join(pdf_folder, f)) for f in files)
    
    return {
        "total_files": len(files),
        "pdf_files": len(pdf_files),
        "txt_files": len(txt_files),
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }
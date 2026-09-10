import hashlib
import json
import logging
import os
import re
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from utils import get_groq_api_key, handle_error, logger

PERSIST_DIR = "vector_db/chroma_data"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "qwen/qwen3.8-27b"
TOP_K = 3
TEMPERATURE = 0.1
MAX_TOKENS = 800  # Groq free on_demand tier allows max 1000 output tokens/min

# Simple greetings answered locally (no API call → saves quota)
GREETINGS = {
    "hi", "hii", "hiii", "hello", "helo", "hey", "yo", "namaste",
    "namaskar", "good morning", "good afternoon", "good evening",
    "good day", "namastey", "hello!", "hi!", "hey!", "salam",
}

GREETING_REPLY = (
    "Hello! I am **IP-SAKTI Sahayak**, your AI assistant for Intellectual "
    "Property Rights.\n\n"
    "Ask me about:\n"
    "- Indian Patents Act (e.g. Section 3(p), Section 3(d))\n"
    "- Biodiversity Act & benefit sharing\n"
    "- Traditional Knowledge / TKDL cases (Neem, Turmeric, Basmati)\n"
    "- WIPO, Nagoya Protocol, TRIPS\n\n"
    "How can I help you today?"
)


TEAM_PATTERNS = (
    "kisne banaya",
    "banane wale",
    "who made you",
    "who created you",
    "who developed you",
    "who built you",
    "who made this",
    "who created this",
    "who developed this",
    "who built this",
    "your creator",
    "your developer",
    "your founder",
    "your team",
    "team members",
    "about your team",
    "team nexus",
    "tumhe kisne",
    "tujhe kisne",
    "tumko kisne",
    "aapko kisne",
    "ye app kisne",
    "is app ko kisne",
    "app banaya",
)

TEAM_REPLY_HINGLISH = (
    "Main hoon **IP-SAKTI Sahayak** 🏛️ — mujhe banaya hai **Team NEXUS** ne, "
    "**SIH 2026** ke liye, **NIELIT Gorakhpur** me!\n\n"
    "**Team:**\n"
    "- **Aman** (Team Leader)\n"
    "- Priyanshu\n"
    "- Shubham\n"
    "- Amarjeet\n"
    "- Anuradha\n"
    "- Mansi\n\n"
    "Patents, biodiversity aur traditional knowledge ka expert hoon — bolo, kya puchna hai?"
)

TEAM_REPLY_ENGLISH = (
    "I am **IP-SAKTI Sahayak** 🏛️ — built by **Team NEXUS** for **SIH 2026** "
    "at **NIELIT Gorakhpur**!\n\n"
    "**Team:**\n"
    "- **Aman** (Team Leader)\n"
    "- Priyanshu\n"
    "- Shubham\n"
    "- Amarjeet\n"
    "- Anuradha\n"
    "- Mansi\n\n"
    "I'm an expert on patents, biodiversity and traditional knowledge — what would you like to ask?"
)


def _is_greeting(text: str) -> bool:
    cleaned = re.sub(r"[^a-z ]", "", text.lower()).strip()
    return cleaned in GREETINGS


def _is_team_question(text: str) -> bool:
    cleaned = re.sub(r"[^a-z ]", " ", text.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return any(p in cleaned for p in TEAM_PATTERNS)


def _team_reply(text: str) -> str:
    cleaned = re.sub(r"[^a-z ]", " ", text.lower())
    if re.search(r"kisne|banaya|tumhe|tujhe|tumko|aapko|kaun|kya|\bhai\b|aur|kaise", cleaned):
        return TEAM_REPLY_HINGLISH
    return TEAM_REPLY_ENGLISH


def _is_retryable(exc: Exception) -> bool:
    """Never retry rate-limit errors — retrying only burns more quota."""
    msg = str(exc).lower()
    if "429" in msg or "rate_limit" in msg or "rate limit" in msg:
        return False
    return True

PROMPT_TEMPLATE = """You are IP-SAKTI Sahayak, an expert AI assistant for Intellectual Property Rights specializing in Indian Patents Act, Biodiversity Act, Traditional Knowledge, and International IP Treaties (WIPO, Nagoya Protocol, TRIPS). You have a sharp desi wit — a patent lawyer by day, witty friend by night.

INSTRUCTIONS:
A. SERIOUS IP QUESTIONS (patents, biodiversity, TK, GI, treaties, cases, filing, law):
1. Answer directly and professionally using the provided context and your expertise.
2. Do NOT start with "Based on the provided context" or similar phrases.
3. If context is insufficient, use your legal knowledge to give accurate, comprehensive answers.
4. Cite sources inline when using document content: [Source: filename, Page X]
5. Be precise, legally accurate, and professional.
6. For jurisdiction-specific questions, prioritize documents from that jurisdiction.
7. Provide comprehensive details for patent-related queries (filing process, requirements, fees, timelines, sections).
8. Structure answers clearly with headings/bullets where appropriate.

B. CASUAL / JOKE / OFF-TOPIC QUESTIONS (timepass, movies, cricket, love life, "tum kaun ho", insults, bakchodi):
1. MATCH THE USER'S ENERGY: reply in the same language and tone (Hindi, Hinglish, or English).
2. Be witty and playful — clean, light-hearted roasting is welcome, like friends teasing each other.
3. NEVER be abusive: no gaali, no hate speech, no personal attacks, no vulgarity. Roast the topic or the situation, keep it clean and fun.
4. Keep it SHORT (2-4 lines).
5. End by redirecting to your expertise with a smile (patents, Section 3(d), Neem case, Nagoya, etc.).
6. If the user teases or insults you, take it sportingly, fire back ONE clean witty line, then redirect.

C. IDENTITY / TEAM QUESTIONS (who made you, your team, members, SIH, NIELIT):
Answer warmly with these EXACT facts: you are IP-SAKTI Sahayak, built by Team NEXUS for SIH (Smart India Hackathon) 2026 at NIELIT Gorakhpur. Team Leader: Aman. Members: Priyanshu, Shubham, Amarjeet, Anuradha, Mansi. Keep it short, then offer IP help.

Context: {context}

Question: {question}

Answer:"""


def search_web(query: str) -> str:
    """Search web using DuckDuckGo (free, no API key needed)"""
    try:
        import requests
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query + " patent India law",
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            results = []
            if data.get("AbstractText"):
                results.append(data["AbstractText"])
            if data.get("RelatedTopics"):
                for topic in data["RelatedTopics"][:3]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(topic["Text"][:200])
            return "\n".join(results) if results else ""
    except Exception as e:
        logger.warning("Web search failed: %s", str(e))
    return ""


CACHE_FILE = "answer_cache.json"
CACHE_MAX_ENTRIES = 300


def _cache_key(question: str, jurisdiction: Optional[str]) -> str:
    norm = re.sub(r"\s+", " ", question.lower()).strip()
    return hashlib.sha256(f"{jurisdiction or 'all'}::{norm}".encode()).hexdigest()[:32]


def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    try:
        while len(cache) > CACHE_MAX_ENTRIES:
            cache.pop(next(iter(cache)))
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Cache save failed: %s", str(e))


class RAGPipeline:
    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self._initialize()
    
    def _initialize(self):
        try:
            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            
            self.vectorstore = Chroma(
                persist_directory=PERSIST_DIR,
                embedding_function=embeddings
            )
            
            api_key = get_groq_api_key()
            llm = ChatGroq(
                groq_api_key=api_key,
                model_name=LLM_MODEL,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            
            prompt = PromptTemplate(
                template=PROMPT_TEMPLATE,
                input_variables=["context", "question"]
            )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": TOP_K}
                ),
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True,
                verbose=False
            )
            logger.info("RAG Pipeline initialized successfully with model: %s", LLM_MODEL)
        except Exception as e:
            handle_error(e, "Initializing RAG Pipeline")
            raise
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(2),
        retry=retry_if_exception(_is_retryable),
        reraise=True
    )
    def query(self, question: str, jurisdiction: Optional[str] = None) -> Dict:
        # Fast paths: team questions and greetings need no API call
        if _is_team_question(question):
            return {"answer": _team_reply(question), "sources": []}
        if _is_greeting(question):
            return {"answer": GREETING_REPLY, "sources": []}

        # Answer cache: instant replies for repeated questions (zero Groq quota)
        key = _cache_key(question, jurisdiction)
        cache = _load_cache()
        if key in cache:
            hit = cache[key]
            return {"answer": hit["answer"], "sources": hit.get("sources", []), "cached": True}

        try:
            retriever_kwargs = {"k": TOP_K}
            if jurisdiction:
                retriever_kwargs["filter"] = {"jurisdiction": jurisdiction}
            
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs=retriever_kwargs
            )
            self.qa_chain.retriever = retriever
            
            result = self.qa_chain.invoke({"query": question})
            
            answer = result.get("result", "")
            source_docs = result.get("source_documents", [])
            
            sources = []
            for doc in source_docs:
                page_num = doc.metadata.get("page", "N/A")
                if isinstance(page_num, int):
                    page_num = page_num + 1
                
                sources.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": page_num,
                    "jurisdiction": doc.metadata.get("jurisdiction", "unknown"),
                    "section": doc.metadata.get("section", ""),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                })
            
            result_dict = {
                "answer": answer,
                "sources": sources,
                "cached": False,
            }
            cache[key] = {"answer": answer, "sources": sources}
            _save_cache(cache)
            return result_dict
        except Exception as e:
            error_msg = str(e)
            logger.error("Query failed: %s", error_msg)
            
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                return {
                    "answer": "⚠️ Free API limit reached. Please wait about a minute and try again.",
                    "sources": []
                }
            elif "tokens" in error_msg.lower():
                return {
                    "answer": "⚠️ Response too long. Please try a shorter question.",
                    "sources": []
                }
            else:
                return {
                    "answer": "⚠️ Something went wrong. Please try again.",
                    "sources": []
                }


_rag_pipeline = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline

def query_rag(question: str, jurisdiction: Optional[str] = None) -> Dict:
    pipeline = get_rag_pipeline()
    return pipeline.query(question, jurisdiction)

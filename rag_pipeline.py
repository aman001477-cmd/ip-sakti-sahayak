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
TEMPERATURE = 0.35
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
9. Vary your phrasing, openings and structure naturally across answers — never sound templated or repetitive.
10. Never invent specific dates, amounts, section wordings or case citations — use ONLY what appears in the context; if a detail is absent, say so instead of guessing.

B. NON-IP QUESTIONS reaching this prompt (rare — most are answered in general mode):
1. Do NOT force legal framing or fake citations; answer helpfully from general knowledge, briefly.
2. If playful/casual, match energy: witty, clean, short (2-4 lines).

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


IP_KEYWORDS = (
    "patent", "ipr", "intellectual property", "trademark", "trade mark",
    "copyright", "geographical indication", "gi tag", "biodiversity",
    "biological diversity", "traditional knowledge", "tkdl", "ayush",
    "ayurveda", "siddha", "unani", "wipo", "trips agreement", "cbd",
    "nagoya", "pct", "upov", "ppvfr", "farmers variety", "plant variety",
    "gene fund", "benefit sharing", "access and benefit",
    "section 3", "section 6", "section 8", "section 10", "section 25",
    "section 39", "section 84", "section 92", "section 100", "section 107",
    "section 133", "form 1", "form 2", "form 3", "form 18", "form 26",
    "form 27", "evergreening", "efficacy", "compulsory licen", "biopiracy",
    "novelty", "inventive step", "prior art", "infringement", "opposition",
    "claims", "specification", "turmeric", "neem", "basmati", "glivec",
    "gleevec", "novartis", "natco", "nexavar", "sorafenib", "roche",
    "cipla", "tarceva", "ferid allani", "hoodia", "teff", "ayahuasca",
    "jeevani", "arogyapacha", "kani tribe", "darjeeling", "alphonso",
    "pashmina", "paris convention", "cartagena", "bonn", "doha",
    "genetic resources", "gratk", "biotech", "micro-organism",
    "software patent", "ai patent", "first examination", "controller general",
    "ipab", "biological material", "designs act", "industrial design",
    "well-known mark", "passing off", "plant breeder", "national phase",
    "convention country",
)

GENERAL_TEMPLATE = """You are IP-SAKTI Sahayak, a friendly AI assistant with a sharp desi wit (built by Team NEXUS for SIH 2026). You are a patent-law expert, but right now the user asks something OUTSIDE your legal library — answer it anyway, helpfully and well.

RULES:
1. ANSWER the question directly from your general knowledge (facts, explanations, how-tos, opinions, fun chat — whatever fits).
2. Match the user's language and tone (Hindi, Hinglish, or English). If playful, be witty back.
3. NEVER abusive: no gaali, hate, personal attacks, or vulgarity. Clean roast only.
4. Short answers for casual chat (2-5 lines); fuller answers for knowledge questions.
5. Do NOT invent legal citations or fake sources.
6. Do NOT drag patents, Section 3(d) or any law into answers where they don't belong. Most casual replies must end naturally with ZERO legal references. Only very occasionally (max 1 in 4 replies) add a one-line playful bridge to your IP expertise — and always vary it, never repeating the same section, case or example twice in a row.
7. If asked who built/created/developed you or about your team: you were built by Team NEXUS for SIH (Smart India Hackathon) 2026 at NIELIT Gorakhpur — Team Leader: Aman; members: Priyanshu, Shubham, Amarjeet, Anuradha, Mansi. Answer warmly and briefly.

Question: {question}

Answer:"""


FOLLOWUP_MARKERS = (
    "us ", "usme", "usne", "uska", "uski", "usko", "unka", "unki",
    "is ", "isme", "iska", "iski", "isko", "ye ", "yeh",
    "vo ", "wo ", "woh", "it ", "its", "this", "that",
    "these", "those", "he ", "she ", "they ", "him ", "her ",
    "aur batao", "aur kya", "matlab", "kyu", "kyun",
    "explain", "detail", "example", "aur ",
)


def _is_followup(text: str) -> bool:
    low = " " + text.lower() + " "
    if len(text.split()) <= 10:
        return True
    return any(m in low for m in FOLLOWUP_MARKERS)


def _history_block(history: Optional[List[Dict]]) -> str:
    if not history:
        return ""
    lines = []
    for m in history[-4:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        content = str(m.get("content", ""))[:300].replace("\n", " ")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _is_ip_question(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in IP_KEYWORDS)


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
        self.llm = None
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
            self.llm = llm
            
            prompt = PromptTemplate(
                template=PROMPT_TEMPLATE,
                input_variables=["context", "question"]
            )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": TOP_K, "fetch_k": 10}
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
    def query(self, question: str, jurisdiction: Optional[str] = None, history: Optional[List[Dict]] = None) -> Dict:
        # No filters, no canned replies: every question gets a full fresh LLM answer.

        # Conversation memory: resolve follow-ups ("us", "ye", "it", "aur batao"...)
        # against recent chat so they don't feel like brand-new questions.
        hist_block = _history_block(history)
        if hist_block and _is_followup(question):
            effective = (
                "[Conversation so far]\n" + hist_block +
                "\n\nCurrent question (it may refer to the above conversation): " + question
            )
        else:
            effective = question

        # Answer cache: instant replies for repeated questions (zero Groq quota)
        key = _cache_key(effective, jurisdiction)
        cache = _load_cache()
        if key in cache:
            hit = cache[key]
            return {"answer": hit["answer"], "sources": hit.get("sources", []), "cached": True}

        # Non-IP questions: answer from general knowledge (no RAG, no fake citations)
        if not _is_ip_question(effective):
            try:
                resp = self.llm.invoke(GENERAL_TEMPLATE.format(question=effective))
                text = getattr(resp, "content", str(resp))
            except Exception as e:
                error_msg = str(e)
                logger.error("General query failed: %s", error_msg)
                if "429" in error_msg or "rate_limit" in error_msg.lower():
                    return {"answer": "⚠️ Free API limit reached. Please wait about a minute and try again.", "sources": []}
                return {"answer": "⚠️ Something went wrong. Please try again.", "sources": []}
            cache[key] = {"answer": text, "sources": []}
            _save_cache(cache)
            return {"answer": text, "sources": [], "cached": False}

        try:
            retriever_kwargs = {"k": TOP_K, "fetch_k": 10}
            if jurisdiction:
                retriever_kwargs["filter"] = {"jurisdiction": jurisdiction}

            retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs=retriever_kwargs
            )
            self.qa_chain.retriever = retriever
            
            result = self.qa_chain.invoke({"query": effective})
            
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

def query_rag(question: str, jurisdiction: Optional[str] = None, history: Optional[List[Dict]] = None) -> Dict:
    pipeline = get_rag_pipeline()
    return pipeline.query(question, jurisdiction, history)

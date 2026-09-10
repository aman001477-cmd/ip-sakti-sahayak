import os
import logging
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

PROMPT_TEMPLATE = """You are IP-SAKTI Sahayak, an expert AI assistant for Intellectual Property Rights specializing in Indian Patents Act, Biodiversity Act, Traditional Knowledge, and International IP Treaties (WIPO, Nagoya Protocol, TRIPS).

INSTRUCTIONS:
1. Answer directly and professionally using the provided context and your expertise.
2. Do NOT start with "Based on the provided context" or similar phrases.
3. If context is insufficient, use your legal knowledge to give accurate, comprehensive answers.
4. Cite sources inline when using document content: [Source: filename, Page X]
5. Be precise, legally accurate, and professional.
6. For jurisdiction-specific questions, prioritize documents from that jurisdiction.
7. Provide comprehensive details for patent-related queries (filing process, requirements, fees, timelines, sections).
8. Structure answers clearly with headings/bullets where appropriate.

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
                max_tokens=1024
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
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def query(self, question: str, jurisdiction: Optional[str] = None) -> Dict:
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
            
            return {
                "answer": answer,
                "sources": sources
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Query failed: %s", error_msg)
            
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                return {
                    "answer": "⚠️ Too many requests! Please wait a moment and try again.",
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

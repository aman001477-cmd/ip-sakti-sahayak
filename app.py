import streamlit as st
import os
import io
import base64
from html import escape
from datetime import datetime
from rag_pipeline import query_rag
from utils import validate_pdf_folder
from features import (
    generate_patent_report, generate_summary_pdf, create_patent_draft_pdf,
    extract_text_from_image, extract_text_from_pdf, process_uploaded_file,
    get_voice_html, get_voice_controls_html, get_available_features,
    generate_image_prompt_based, generate_diagram_prompt, get_feature_status,
    PDF_AVAILABLE, OCR_AVAILABLE
)

st.set_page_config(page_title="IP-SAKTI Sahayak", page_icon="🏛️", layout="wide", initial_sidebar_state="expanded")

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "jurisdiction" not in st.session_state:
    st.session_state.jurisdiction = "india"
if "voice_mode" not in st.session_state:
    st.session_state.voice_mode = False
if "show_features" not in st.session_state:
    st.session_state.show_features = False
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# Inject voice HTML once
st.components.v1.html(get_voice_html(), height=0)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp { 
        font-family: 'Inter', sans-serif; 
        background: #000000 !important;
    }
    
    .main .block-container {
        max-width: 900px;
        padding: 1rem 2rem 7rem;
        background: transparent;
    }
    
    .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 0;
        border-bottom: 1px solid #2a2a2a;
        margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 1rem; }
    .logo { width: 48px; height: 48px; background: linear-gradient(135deg, #FF9933, #138808); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; }
    .title { font-size: 1.4rem; font-weight: 700; color: #fff; }
    .subtitle { font-size: 0.85rem; color: #888; }
    .juris-badge { padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .juris-india { background: #FFF3E0; color: #E65100; }
    .juris-intl { background: #E3F2FD; color: #1565C0; }
    .feature-btn { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 0.4rem 0.8rem; font-size: 0.75rem; color: #ccc; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 0.4rem; }
    .feature-btn:hover { border-color: #FF9933; background: #222; }
    .feature-btn.active { background: linear-gradient(135deg, #FF9933, #138808); color: white; border: none; }
    
    .msg { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; animation: fadeIn 0.3s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .msg-user { flex-direction: row-reverse; }
    .avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; margin-top: 2px; }
    .avatar-user { background: linear-gradient(135deg, #FF9933, #FF6B00); color: white; }
    .avatar-bot { background: linear-gradient(135deg, #138808, #0D6B06); color: white; }
    .bubble { max-width: 80%; padding: 0.85rem 1.1rem; border-radius: 16px; font-size: 0.95rem; line-height: 1.7; }
    .msg-user .bubble { background: linear-gradient(135deg, #FF9933, #FF7A00); color: white; border-bottom-right-radius: 4px; }
    .msg-bot .bubble { background: #1a1a1a; border: 1px solid #2a2a2a; color: #e0e0e0; border-bottom-left-radius: 4px; }
    
    .sources { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #2a2a2a; }
    .sources-label { font-size: 0.7rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; }
    .source-item { background: #111; border: 1px solid #222; border-left: 3px solid #138808; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 0.4rem; font-size: 0.8rem; }
    .source-file { font-weight: 600; color: #e0e0e0; }
    .source-meta { color: #666; font-size: 0.7rem; margin-top: 2px; display: flex; gap: 8px; flex-wrap: wrap; }
    .source-preview { color: #888; font-size: 0.75rem; margin-top: 4px; font-style: italic; line-height: 1.4; }
    .tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 0.6rem; font-weight: 600; }
    .tag-india { background: #FFF3E0; color: #E65100; }
    .tag-intl { background: #E3F2FD; color: #1565C0; }
    
    .quick-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin: 1.5rem 0; }
    .quick-btn { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; padding: 0.8rem; text-align: center; color: #ccc; font-weight: 500; font-size: 0.8rem; transition: all 0.2s; cursor: pointer; }
    .quick-btn:hover { border-color: #FF9933; background: #222; transform: translateY(-2px); }
    
    .footer { position: fixed; bottom: 0; left: 0; right: 0; background: #0a0a0a; border-top: 1px solid #2a2a2a; padding: 0.6rem; text-align: center; font-size: 0.75rem; color: #666; z-index: 100; }
    .footer strong { color: #fff; }
    .footer .sih { color: #FF9933; }
    
    section[data-testid="stSidebar"] { background: #0a0a0a !important; border-right: 1px solid #2a2a2a !important; }
    .sidebar-header { text-align: center; padding: 1.5rem 1rem 1rem; border-bottom: 1px solid #2a2a2a; margin-bottom: 1rem; }
    .sidebar-logo { width: 56px; height: 56px; background: linear-gradient(135deg, #FF9933, #138808); border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 0.75rem; }
    .sidebar-title { font-weight: 700; color: #e0e0e0; }
    .sidebar-section { padding: 0 1rem 1rem; }
    .sidebar-label { font-size: 0.7rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; display: block; }
    .hist-item { background: #111; border: 1px solid #222; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 0.4rem; font-size: 0.78rem; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .stat-box { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; padding: 0.8rem; text-align: center; margin-bottom: 1rem; }
    .stat-val { font-size: 1.5rem; font-weight: 700; color: #FF9933; }
    .stat-lbl { font-size: 0.65rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.2rem; }
    .file-item { background: #111; border: 1px solid #222; border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.75rem; color: #ccc; display: flex; justify-content: space-between; align-items: center; }
    .file-info { display: flex; align-items: center; gap: 0.5rem; }
    .file-icon { font-size: 1rem; }
    
    .stButton > button { border-radius: 8px !important; font-weight: 500 !important; border: 1px solid #2a2a2a !important; background: #1a1a1a !important; color: #ccc !important; }
    .stButton > button:hover { border-color: #FF9933 !important; }
    .stButton > button[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, #FF9933, #138808) !important; color: white !important; border: none !important; }
    
    .stChatInput { position: fixed !important; bottom: 2.5rem !important; left: 50% !important; transform: translateX(-50%) !important; width: 100% !important; max-width: 900px !important; z-index: 999 !important; }
    .stChatInput > div { border-radius: 24px !important; background: #1a1a1a !important; border: 1px solid #2a2a2a !important; box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important; }
    .stChatInput > div:focus-within { border-color: #FF9933 !important; box-shadow: 0 0 0 3px rgba(255,153,51,0.15), 0 4px 20px rgba(0,0,0,0.4) !important; }
    .stChatInput textarea { color: #e0e0e0 !important; }
    
    .feature-panel { background: #111; border: 1px solid #222; border-radius: 12px; padding: 1rem; margin: 1rem 0; }
    .feature-panel h4 { color: #FF9933; margin-bottom: 0.75rem; font-size: 0.95rem; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.5rem; }
    .feature-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; padding: 0.8rem; text-align: center; transition: all 0.2s; }
    .feature-card:hover { border-color: #FF9933; transform: translateY(-2px); }
    .feature-icon { font-size: 1.5rem; margin-bottom: 0.4rem; }
    .feature-name { font-weight: 600; font-size: 0.8rem; color: #e0e0e0; }
    .feature-desc { font-size: 0.65rem; color: #888; margin-top: 0.2rem; }
    
    .download-btn { display: inline-flex; align-items: center; gap: 0.4rem; background: linear-gradient(135deg, #FF9933, #138808); color: white; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; font-size: 0.8rem; text-decoration: none; margin: 0.25rem; }
    .download-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255,153,51,0.4); }
    
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #FF9933, #138808); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <div class="sidebar-logo">🏛️</div>
        <div class="sidebar-title">IP-SAKTI Sahayak</div>
        <div style="font-size:0.65rem; color:#666; text-transform:uppercase; letter-spacing:0.5px;">Chat History</div>
    </div>
    """, unsafe_allow_html=True)
    
    search = st.text_input("🔍 Search history", placeholder="Search questions...", label_visibility="collapsed")
    
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<span class='sidebar-label'>Recent Questions</span>", unsafe_allow_html=True)
    
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if search:
        user_msgs = [m for m in user_msgs if search.lower() in m["content"].lower()]
    
    if user_msgs:
        for msg in reversed(user_msgs[-15:]):
            q = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            st.markdown(f"<div class='hist-item'>💬 {q}</div>", unsafe_allow_html=True)
    else:
        st.caption("No conversations yet")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    total_q = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-val">{total_q}</div>
        <div class="stat-lbl">Questions Asked</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Jurisdiction
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<span class='sidebar-label'>Jurisdiction</span>", unsafe_allow_html=True)
    juris = st.radio("", ["india", "international"], format_func=lambda x: "🇮🇳 India" if x == "india" else "🌍 International", index=0 if st.session_state.jurisdiction == "india" else 1, label_visibility="collapsed")
    st.session_state.jurisdiction = juris
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Knowledge Base
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<span class='sidebar-label'>Knowledge Base</span>", unsafe_allow_html=True)
    if validate_pdf_folder("data/ayush_docs"):
        files = os.listdir("data/ayush_docs")
        pdfs = len([f for f in files if f.endswith('.pdf')])
        txts = len([f for f in files if f.endswith('.txt')])
        st.caption(f"{pdfs} PDFs • {txts} Text files")
        for f in sorted(files)[:10]:
            name = f.replace('.pdf','').replace('.txt','').replace('_',' ').title()
            st.caption(f"📄 {name[:35]}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Voice Mode (always visible)
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<span class='sidebar-label'>🎤 Voice Assistant</span>", unsafe_allow_html=True)
    voice_label = "🔴 Voice Mode ON" if st.session_state.voice_mode else "🎤 Enable Voice Mode"
    if st.button(voice_label, use_container_width=True, key="toggle_voice"):
        st.session_state.voice_mode = not st.session_state.voice_mode
        st.rerun()
    if st.session_state.voice_mode:
        st.caption("Click 🎤 mic to speak • Click 🔊 to hear answers")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Features Panel
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<span class='sidebar-label'>Advanced Features</span>", unsafe_allow_html=True)
    
    if st.button("🛠️ Feature Panel", use_container_width=True, key="toggle_features"):
        st.session_state.show_features = not st.session_state.show_features
        st.rerun()
    
    if st.session_state.show_features:
        features = get_available_features()
        st.markdown("<div class='feature-panel'>", unsafe_allow_html=True)
        st.markdown("<h4>Available Features</h4>", unsafe_allow_html=True)
        for feat in features:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{feat['icon']}</div>
                <div class="feature-name">{feat['name']}</div>
                <div class="feature-desc">{feat['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Quick action buttons for features
        if PDF_AVAILABLE:
            if st.button("📄 Generate PDF Report", use_container_width=True, key="gen_pdf_report"):
                if st.session_state.messages:
                    last_bot = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
                    if last_bot:
                        pdf_bytes = generate_patent_report(
                            query=st.session_state.messages[-2]["content"] if len(st.session_state.messages) > 1 else "Query",
                            answer=last_bot["content"],
                            sources=last_bot.get("sources", []),
                            jurisdiction=st.session_state.jurisdiction
                        )
                        st.download_button(
                            "⬇️ Download Report",
                            data=pdf_bytes,
                            file_name=f"IP_SAKTI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
juris_class = "juris-india" if st.session_state.jurisdiction == "india" else "juris-intl"
juris_label = "🇮🇳 India" if st.session_state.jurisdiction == "india" else "🌍 International"

voice_btn_class = "feature-btn active" if st.session_state.voice_mode else "feature-btn"
voice_btn_text = "🔴 Voice ON" if st.session_state.voice_mode else "🎤 Voice"

st.markdown(f"""
<style>
    @keyframes blink {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}
    @keyframes shimmer {{
        0% {{ background-position: -200% center; }}
        100% {{ background-position: 200% center; }}
    }}
    @keyframes pulse-glow {{
        0%, 100% {{ 
            box-shadow: 0 0 8px rgba(255, 153, 51, 0.5), 0 0 16px rgba(19, 136, 8, 0.3);
        }}
        50% {{ 
            box-shadow: 0 0 20px rgba(255, 153, 51, 0.8), 0 0 32px rgba(19, 136, 8, 0.6), 0 0 40px rgba(255, 215, 0, 0.5);
        }}
    }}
    @keyframes float-gentle {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-3px); }}
    }}
    .sih-badge {{
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 14px;
        font-weight: 700;
        font-size: 0.8rem;
        color: #1a1a1a;
        background: linear-gradient(135deg, #FFD700, #FFA500, #FF8C00, #FFD700);
        background-size: 300% 300%;
        animation: float-gentle 3s ease-in-out infinite, pulse-glow 2.5s ease-in-out infinite, shimmer 3s ease infinite;
        border: 2px solid rgba(255,215,0,0.5);
        box-shadow: 0 4px 16px rgba(255, 153, 51, 0.3);
        cursor: default;
        transition: all 0.3s ease;
    }}
    .sih-badge:hover {{
        transform: scale(1.05);
        box-shadow: 0 8px 24px rgba(255, 215, 0, 0.5), 0 0 32px rgba(255, 153, 51, 0.4);
    }}
    .sih-badge::before {{
        content: "🏆";
        font-size: 1rem;
        animation: float-gentle 2s ease-in-out infinite;
    }}
    .sih-badge::after {{
        content: "2026";
        background: linear-gradient(135deg, #FF9933, #138808);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        font-size: 0.85rem;
    }}
    @keyframes shimmer {{
        0% {{ background-position: -200% center; }}
        100% {{ background-position: 200% center; }}
    }}
    @keyframes pulse-glow {{
        0%, 100% {{ 
            box-shadow: 0 0 8px rgba(255, 153, 51, 0.5), 0 0 16px rgba(19, 136, 8, 0.3);
        }}
        50% {{ 
            box-shadow: 0 0 20px rgba(255, 153, 51, 0.8), 0 0 32px rgba(19, 136, 8, 0.6), 0 0 40px rgba(255, 215, 0, 0.5);
        }}
    }}
    @keyframes float-gentle {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-3px); }}
    }}
</style>

<div class="header">
    <div class="header-left">
        <div class="logo">🏛️</div>
        <div>
            <div class="title">IP-SAKTI Sahayak</div>
            <div class="subtitle">Ministry of Ayush • Intellectual Property Rights Assistant</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 1rem;">
        <div class="juris-badge {juris_class}">{juris_label}</div>
        <span class="sih-badge" title="Smart India Hackathon 2026 - Team NEXUS">
            SIH
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Voice controls at top
if st.session_state.voice_mode:
    st.components.v1.html(get_voice_controls_html(), height=60)

# ============================================================
# FILE UPLOADER (for OCR/PDF extraction)
# ============================================================
with st.expander("📁 Upload Document for Analysis (PDF/Image/Text)", expanded=False):
    uploaded = st.file_uploader(
        "Upload patent documents, diagrams, or images for text extraction",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded:
        for file in uploaded:
            if file.name not in [f["name"] for f in st.session_state.uploaded_files]:
                with st.spinner(f"Processing {file.name}..."):
                    result = process_uploaded_file(file)
                    st.session_state.uploaded_files.append(result)
        
        st.success(f"Processed {len(uploaded)} file(s)")
    
    # Show processed files
    if st.session_state.uploaded_files:
        st.markdown("**Processed Files:**")
        for f in st.session_state.uploaded_files:
            col1, col2 = st.columns([4, 1])
            with col1:
                icon = "📄" if f["type"] == "application/pdf" else "🖼️" if f["type"].startswith("image/") else "📝"
                st.markdown(f"<div class='file-item'><div class='file-info'><span class='file-icon'>{icon}</span><div>{f['name']} ({f.get('pages', 1)} pages)</div></div></div>", unsafe_allow_html=True)
            with col2:
                if st.button("🗑️", key=f"del_{f['name']}"):
                    st.session_state.uploaded_files = [x for x in st.session_state.uploaded_files if x["name"] != f["name"]]
                    st.rerun()
        
        # Show extracted text
        for f in st.session_state.uploaded_files:
            if f["text"]:
                with st.expander(f"📝 Extracted Text: {f['name']}", expanded=False):
                    st.text_area("", f["text"][:2000] + ("..." if len(f["text"]) > 2000 else ""), height=150, key=f"text_{f['name']}")
                    if st.button("➕ Add to Query Context", key=f"add_{f['name']}"):
                        st.session_state.messages.append({
                            "role": "user",
                            "content": f"[Document: {f['name']}]\n{f['text'][:3000]}"
                        })
                        st.rerun()

# ============================================================
# QUICK ACTIONS (if empty)
# ============================================================
if not st.session_state.messages:
    st.markdown("""
    <div style="text-align:center; padding:2rem 0 1rem;">
        <h3 style="color:#ccc; font-weight:500; margin-bottom:0.3rem;">How can I help you today?</h3>
        <p style="color:#666; font-size:0.9rem;">Ask about patents, biodiversity, traditional knowledge, international treaties...</p>
    </div>
    """, unsafe_allow_html=True)
    
    q1, q2, q3, q4 = st.columns(4)
    questions = [
        ("📜 Section 3(p)", "What is Section 3(p) of the Indian Patents Act?"),
        ("🌿 Neem Patent", "Can I patent a Neem-based formulation?"),
        ("📋 Nagoya Protocol", "What is the Nagoya Protocol?"),
        ("🌱 Biodiversity Act", "What does the Biodiversity Act cover?"),
    ]
    for i, (label, q) in enumerate(questions):
        with [q1,q2,q3,q4][i]:
            if st.button(label, use_container_width=True, key=f"q{i}"):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

# ============================================================
# MESSAGES
# ============================================================
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg msg-user">
            <div class="avatar avatar-user">👤</div>
            <div class="bubble">{escape(msg["content"])}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg msg-bot">
            <div class="avatar avatar-bot">🏛️</div>
            <div class="bubble">{msg["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons for bot messages
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if PDF_AVAILABLE and st.button("📄 Save as PDF", key=f"pdf_{idx}", use_container_width=True):
                user_q = next((m["content"] for m in reversed(st.session_state.messages[:idx]) if m["role"] == "user"), "Query")
                pdf_bytes = generate_patent_report(
                    query=user_q,
                    answer=msg["content"],
                    sources=msg.get("sources", []),
                    jurisdiction=st.session_state.jurisdiction
                )
                st.download_button(
                    "⬇️ Download",
                    data=pdf_bytes,
                    file_name=f"IP_SAKTI_Answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    key=f"dl_{idx}"
                )
        with col2:
            if st.session_state.voice_mode and st.button("🔊 Speak", key=f"speak_{idx}", use_container_width=True):
                st.components.v1.html(f"""
                <script>
                    speakText(`{msg["content"][:500].replace('`', '\\`').replace('"', '\\"')}`);
                </script>
                """, height=0)
        
        if msg.get("sources"):
            st.markdown('<div class="sources"><div class="sources-label">📚 Sources</div>', unsafe_allow_html=True)
            for src in msg["sources"]:
                page = src.get('page', 'N/A')
                juris_val = src.get('jurisdiction', '').upper()
                section = src.get('section', '')
                preview = src.get('content_preview', '')[:140]
                source_name = src.get('source', 'Unknown')
                badge = f'<span class="tag tag-{src.get("jurisdiction","")}">{juris_val}</span>' if juris_val else ''
                sec = f'<span>§ {section}</span>' if section else ''
                
                st.markdown(f"""
                <div class="source-item">
                    <div class="source-file">📄 {source_name}</div>
                    <div class="source-meta">
                        <span>Page {page}</span>
                        {badge}
                        {sec}
                    </div>
                    <div class="source-preview">"{preview}..."</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# CHAT INPUT TOOLBAR
# ============================================================
st.markdown("""
<div style="position: fixed; bottom: 7.5rem; left: 50%; transform: translateX(-50%); 
            width: 100%; max-width: 900px; z-index: 998; 
            display: flex; justify-content: center; gap: 0.5rem; padding: 0 1rem;">
    <button class="toolbar-btn" title="Attach File" onclick="document.getElementById('file_uploader').click()">
        📎
    </button>
    <button class="toolbar-btn" title="Voice Input" onclick="startVoiceInput()">
        🎤
    </button>
    <button class="toolbar-btn" title="New Chat" onclick="window.location.reload()">
        ➕
    </button>
</div>

<style>
.toolbar-btn {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    color: #ccc;
    cursor: pointer;
    transition: all 0.2s;
}
.toolbar-btn:hover {
    border-color: #FF9933;
    background: #222;
    transform: scale(1.05);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CHAT INPUT
# ============================================================
if prompt := st.chat_input("Ask about Patents Act, Biodiversity Act, WIPO, Nagoya Protocol, TKDL..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# ============================================================
# PROCESS USER MESSAGE
# ============================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]["content"]
    
    # Include uploaded file context if any
    file_context = ""
    for f in st.session_state.uploaded_files:
        if f["text"]:
            file_context += f"\n\n[Document: {f['name']}]\n{f['text'][:2000]}"
    
    full_query = last_msg + file_context
    
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            result = query_rag(full_query, st.session_state.jurisdiction)
        st.write(result["answer"])
        
        # Action buttons
        col1, col2 = st.columns([1, 5])
        with col1:
            if PDF_AVAILABLE and st.button("📄 Save as PDF", key="pdf_new", use_container_width=True):
                pdf_bytes = generate_patent_report(
                    query=last_msg,
                    answer=result["answer"],
                    sources=result["sources"],
                    jurisdiction=st.session_state.jurisdiction
                )
                st.download_button(
                    "⬇️ Download Report",
                    data=pdf_bytes,
                    file_name=f"IP_SAKTI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    key="dl_new"
                )
        
        if result["sources"]:
            st.markdown('<div class="sources"><div class="sources-label">📚 Sources</div>', unsafe_allow_html=True)
            for src in result["sources"]:
                page = src.get('page', 'N/A')
                juris_val = src.get('jurisdiction', '').upper()
                section = src.get('section', '')
                preview = src.get('content_preview', '')[:140]
                source_name = src.get('source', 'Unknown')
                badge = f'<span class="tag tag-{src.get("jurisdiction","")}">{juris_val}</span>' if juris_val else ''
                sec = f'<span>§ {section}</span>' if section else ''
                st.markdown(f"""
                <div class="source-item">
                    <div class="source-file">📄 {source_name}</div>
                    <div class="source-meta">
                        <span>Page {page}</span>
                        {badge}
                        {sec}
                    </div>
                    <div class="source-preview">"{preview}..."</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"]
    })
    st.rerun()

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Team NEXUS</strong> | <span class="sih">SIH 2026</span> | Ministry of Ayush
</div>
""", unsafe_allow_html=True)
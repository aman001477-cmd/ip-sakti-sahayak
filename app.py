import streamlit as st
import os
import io
from html import escape
from datetime import datetime
from rag_pipeline import query_rag
from utils import validate_pdf_folder, get_groq_api_key
from features import (
    generate_patent_report, process_uploaded_file,
    get_voice_html, get_available_features,
    PDF_AVAILABLE,
)

try:
    from streamlit_mic_recorder import mic_recorder
    MIC_OK = True
except Exception:
    MIC_OK = False
    mic_recorder = None


def transcribe_audio(data: bytes) -> str:
    """Speech-to-text via Groq Whisper using the existing GROQ_API_KEY."""
    import requests
    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": "Bearer " + get_groq_api_key()},
        files={"file": ("audio.webm", data, "audio/webm")},
        data={"model": "whisper-large-v3"},
        timeout=60,
    )
    resp.raise_for_status()
    return (resp.json().get("text") or "").strip()


INDIAN_VOICE_EN = "en-IN-NeerjaNeural"  # clearest Indian-English neural voice
INDIAN_VOICE_HI = "hi-IN-SwaraNeural"  # clearest Hindi neural voice


def speak_answer(text: str) -> bytes:
    """Indian-accent neural TTS (Edge) with gTTS-India fallback — returns MP3 bytes."""
    import re

    clean = re.sub(r"[*_#`>\[\]()|]", "", text).strip()[:800]
    if not clean:
        raise ValueError("Nothing to speak")
    use_hindi = bool(re.search(r"[\u0900-\u097F]", clean))
    voice = INDIAN_VOICE_HI if use_hindi else INDIAN_VOICE_EN
    try:
        import asyncio

        import edge_tts

        async def _gen():
            chunks = []
            async for ch in edge_tts.Communicate(clean, voice).stream():
                if ch["type"] == "audio":
                    chunks.append(ch["data"])
            return b"".join(chunks)

        data = asyncio.run(_gen())
        if not data:
            raise RuntimeError("empty neural audio")
        return data
    except Exception:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=clean, lang="hi" if use_hindi else "en", tld="co.in", slow=False).write_to_fp(buf)
        buf.seek(0)
        return buf.read()

st.set_page_config(
    page_title="IP-SAKTI Sahayak",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Session state ----------------
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
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = False
if "intro_seen" not in st.session_state:
    st.session_state.intro_seen = False

# Voice engine (browser Speech API helpers)
st.components.v1.html(get_voice_html(), height=0)

# ---------------- Premium design system ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

:root {
    --saffron: #FF9933;
    --saffron-deep: #FF6B00;
    --green: #138808;
    --green-deep: #0D6B06;
    --gold: #FFD700;
    --ink: #000000;
    --panel: #0B0B0D;
    --card: #121214;
    --card-2: #17171A;
    --line: #232327;
    --txt: #F2F2F3;
    --muted: #9A9AA3;
    --faint: #5C5C66;
}

.stApp {
    font-family: 'Inter', sans-serif;
    background: #000000 !important;
    color: var(--txt);
}

.main .block-container {
    max-width: 860px;
    padding: 0 1.5rem 8rem;
    background: transparent;
}

/* ---------- ambient background ---------- */
.orb { position: fixed; border-radius: 50%; filter: blur(110px); pointer-events: none; z-index: 0; }
.orb-a { width: 480px; height: 480px; top: -160px; left: -140px;
    background: radial-gradient(circle, rgba(255,153,51,.14), transparent 70%);
    animation: drift 14s ease-in-out infinite alternate; }
.orb-b { width: 520px; height: 520px; bottom: -200px; right: -160px;
    background: radial-gradient(circle, rgba(19,136,8,.16), transparent 70%);
    animation: drift 18s ease-in-out infinite alternate-reverse; }
.orb-c { width: 300px; height: 300px; top: 40%; left: 55%;
    background: radial-gradient(circle, rgba(255,215,0,.06), transparent 70%);
    animation: drift 22s ease-in-out infinite alternate; }
@keyframes drift {
    from { transform: translate(0,0) scale(1); }
    to { transform: translate(60px, 40px) scale(1.12); }
}

/* ---------- intro splash ---------- */
#intro-splash {
    position: fixed; inset: 0; z-index: 9999;
    background: radial-gradient(ellipse at 50% 35%, #101014 0%, #000 65%);
    display: flex; align-items: center; justify-content: center;
    transition: opacity .8s ease; cursor: pointer;
}
#intro-splash.hide { opacity: 0; pointer-events: none; }
.intro-inner { text-align: center; padding: 2rem; max-width: 560px; }
.intro-emblem { position: relative; width: 110px; height: 110px; margin: 0 auto 1.4rem; }
.intro-ring { position: absolute; inset: 0; border-radius: 50%;
    background: conic-gradient(from 0deg, #FF9933, #FFD700, #138808, #FF9933);
    animation: spin 2.4s linear infinite; filter: saturate(1.2); }
.intro-core { position: absolute; inset: 7px; border-radius: 50%; background: #0a0a0c;
    display: flex; align-items: center; justify-content: center; font-size: 2.6rem;
    box-shadow: inset 0 0 24px rgba(255,153,51,.25); animation: corePulse 2.4s ease-in-out infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes corePulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
.intro-title {
    font-family: 'Fraunces', serif; font-size: 2.4rem; font-weight: 700; letter-spacing: .5px;
    background: linear-gradient(100deg, #fff 20%, #FF9933 40%, #FFD700 50%, #7ddf8e 60%, #fff 80%);
    background-size: 250% auto; -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; animation: shimmer 3s linear infinite;
    margin-bottom: .4rem; }
@keyframes shimmer { to { background-position: 250% center; } }
.intro-sub { color: var(--muted); font-size: .85rem; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 1.8rem; }
.intro-sub b { color: var(--saffron); }
.intro-bar { height: 4px; border-radius: 4px; background: #1c1c20; overflow: hidden; margin: 0 auto 1rem; max-width: 340px; }
.intro-bar span { display: block; height: 100%; width: 0; border-radius: 4px;
    background: linear-gradient(90deg, #FF9933, #FFD700, #138808);
    animation: load 3.4s ease forwards; }
@keyframes load { to { width: 100%; } }
.intro-status { color: var(--faint); font-size: .78rem; animation: statusCycle 3.4s ease forwards; }
@keyframes statusCycle { 0% { opacity: 0; } 15% { opacity: 1; } 85% { opacity: 1; } 100% { opacity: .4; } }
.intro-tap { margin-top: 1.2rem; color: #3d3d46; font-size: .72rem; }

/* ---------- sticky top bar ---------- */
.topbar {
    position: sticky; top: 0; z-index: 900;
    display: flex; align-items: center; justify-content: space-between;
    gap: 1rem; padding: .8rem 1.1rem; margin: 0 -1.5rem 1.4rem;
    background: rgba(5,5,7,.78); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(255,255,255,.07);
}
.brand { display: flex; align-items: center; gap: .8rem; }
.brand-mark { width: 44px; height: 44px; border-radius: 13px;
    background: linear-gradient(135deg, #FF9933, #FF6B00 55%, #138808);
    display: flex; align-items: center; justify-content: center; font-size: 1.35rem;
    box-shadow: 0 6px 22px rgba(255,122,0,.35); transition: transform .25s ease; }
.brand-mark:hover { transform: rotate(-8deg) scale(1.06); }
.brand-name { font-weight: 800; font-size: 1.02rem; letter-spacing: .2px; color: #fff; }
.brand-name em { font-style: normal;
    background: linear-gradient(90deg, #FF9933, #FFD700);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.brand-tag { font-size: .68rem; color: var(--muted); letter-spacing: .4px; }
.top-right { display: flex; align-items: center; gap: .55rem; }
.pill { display: inline-flex; align-items: center; gap: .35rem;
    padding: .34rem .8rem; border-radius: 100px; font-size: .72rem; font-weight: 700; }
.pill-india { background: rgba(255,153,51,.14); color: #FFB25E; border: 1px solid rgba(255,153,51,.35); }
.pill-intl { background: rgba(96,165,250,.12); color: #7FB3FF; border: 1px solid rgba(96,165,250,.35); }
.sih-chip { display: inline-flex; align-items: center; gap: .35rem;
    padding: .34rem .8rem; border-radius: 100px; font-size: .72rem; font-weight: 800;
    color: #1a1200; background: linear-gradient(100deg, #FFD700, #FFA500, #FFD700);
    background-size: 220% auto; animation: shimmer 4s linear infinite;
    box-shadow: 0 0 14px rgba(255,215,0,.35); }

/* ---------- hero ---------- */
.hero { text-align: center; padding: 2.2rem 1rem 1.2rem; animation: rise .7s ease both; }
@keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
.hero-eyebrow { display: inline-flex; align-items: center; gap: .45rem;
    font-size: .68rem; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase;
    color: var(--saffron); border: 1px solid rgba(255,153,51,.35);
    background: rgba(255,153,51,.07); padding: .4rem 1rem; border-radius: 100px; margin-bottom: 1.1rem; }
.hero-eyebrow .dot { width: 7px; height: 7px; border-radius: 50%; background: #4ade80;
    box-shadow: 0 0 10px #4ade80; animation: blink 1.8s ease infinite; }
@keyframes blink { 50% { opacity: .35; } }
.hero h1 { font-family: 'Fraunces', serif; font-size: 2.5rem; line-height: 1.12; margin: 0 0 .6rem; color: #fff; }
.hero h1 .grad { background: linear-gradient(92deg, #FF9933 10%, #FFD700 45%, #7ddf8e 90%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.hero p { color: var(--muted); font-size: .95rem; max-width: 560px; margin: 0 auto; }
.sugg-label { text-align: center; color: var(--faint); font-size: .7rem; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin: 1.6rem 0 .8rem; }
.cap-row { display: flex; justify-content: center; gap: 1.3rem; flex-wrap: wrap;
    margin-top: 1.4rem; color: var(--faint); font-size: .72rem; }
.cap-row span { display: inline-flex; align-items: center; gap: .35rem; }

/* ---------- messages ---------- */
.msg { display: flex; gap: .7rem; margin-bottom: 1.15rem; align-items: flex-start;
    animation: msgIn .45s cubic-bezier(.2,.8,.3,1) both; }
.msg:nth-child(2) { animation-delay: .05s; } .msg:nth-child(3) { animation-delay: .1s; }
@keyframes msgIn { from { opacity: 0; transform: translateY(14px) scale(.985); } to { opacity: 1; transform: none; } }
.msg-user { flex-direction: row-reverse; }
.avatar { width: 34px; height: 34px; border-radius: 12px; flex-shrink: 0; margin-top: 2px;
    display: flex; align-items: center; justify-content: center; font-size: 1rem; transition: transform .2s; }
.avatar:hover { transform: scale(1.12) rotate(-4deg); }
.avatar-user { background: linear-gradient(135deg, #FF9933, #FF6B00); box-shadow: 0 4px 14px rgba(255,122,0,.35); }
.avatar-bot { background: linear-gradient(135deg, #138808, #0a4d04); box-shadow: 0 4px 14px rgba(19,136,8,.4);
    border: 1px solid rgba(125,223,142,.25); }
.bubble { max-width: 80%; padding: .85rem 1.05rem; border-radius: 18px; font-size: .93rem; line-height: 1.7; }
.msg-user .bubble { background: linear-gradient(135deg, #FF9933, #F96A00); color: #fff;
    border-bottom-right-radius: 6px; box-shadow: 0 6px 20px rgba(255,122,0,.25); }
.msg-bot .bubble { background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
    border: 1px solid rgba(255,255,255,.09); color: #EDEDEF;
    border-bottom-left-radius: 6px; box-shadow: 0 8px 24px rgba(0,0,0,.35); }
.bubble strong { color: #fff; }

/* ---------- sources ---------- */
.sources { margin: .7rem 0 0 44px; padding-top: .7rem; border-top: 1px dashed rgba(255,255,255,.12); }
.sources-label { font-size: .66rem; font-weight: 800; color: var(--faint);
    text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: .55rem; }
.source-item { background: linear-gradient(180deg, var(--card-2), var(--card));
    border: 1px solid var(--line); border-left: 3px solid transparent;
    border-image: linear-gradient(180deg, #FF9933, #138808) 1;
    border-radius: 12px; padding: .65rem .85rem; margin-bottom: .45rem;
    transition: transform .2s ease, box-shadow .2s ease; }
.source-item:hover { transform: translateX(4px); box-shadow: 0 8px 20px rgba(0,0,0,.4); }
.source-file { font-weight: 700; font-size: .82rem; color: #fff; }
.source-meta { color: var(--muted); font-size: .7rem; margin-top: 3px;
    display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
.source-preview { color: #8b8b95; font-size: .75rem; margin-top: 5px; font-style: italic; line-height: 1.5; }
.tag { display: inline-block; padding: 1px 7px; border-radius: 5px; font-size: .62rem; font-weight: 800; }
.tag-india { background: rgba(255,153,51,.15); color: #FFB25E; border: 1px solid rgba(255,153,51,.3); }
.tag-international { background: rgba(96,165,250,.14); color: #7FB3FF; border: 1px solid rgba(96,165,250,.3); }

/* ---------- action row ---------- */
.act-row { display: flex; gap: .45rem; margin: .45rem 0 0 44px; }

/* ---------- thinking ---------- */
.thinking { display: flex; align-items: center; gap: .6rem; color: var(--muted); font-size: .82rem; }
.dots { display: inline-flex; gap: 5px; }
.dots span { width: 7px; height: 7px; border-radius: 50%;
    background: linear-gradient(135deg, #FF9933, #138808); animation: pulse 1s ease-in-out infinite; }
.dots span:nth-child(2) { animation-delay: .15s; } .dots span:nth-child(3) { animation-delay: .3s; }
@keyframes pulse { 50% { transform: scale(1.4); opacity: .5; } }

/* ---------- unified chat bar (single bordered box, fixed) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    position: fixed !important; bottom: 2.6rem !important; left: 50% !important;
    transform: translateX(-50%) !important; width: min(860px, calc(100% - 2rem)) !important;
    z-index: 999 !important; background: rgba(18,18,22,.95) !important;
    border: 1px solid rgba(255,255,255,.1) !important; border-radius: 26px !important;
    box-shadow: 0 12px 40px rgba(0,0,0,.55) !important;
    backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important;
    padding: .45rem .55rem !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:focus-within {
    border-color: rgba(255,153,51,.7) !important;
    box-shadow: 0 0 0 3px rgba(255,153,51,.14), 0 12px 40px rgba(0,0,0,.55) !important; }
div[data-testid="stVerticalBlockBorderWrapper"] input {
    border: none !important; background: transparent !important; box-shadow: none !important;
    color: #f2f2f3 !important; font-size: .92rem !important; }
div[data-testid="stVerticalBlockBorderWrapper"] .stTextInput > div { border: none !important; background: transparent !important; }
div[data-testid="stVerticalBlockBorderWrapper"] .stTextInput > div:focus-within { border: none !important; box-shadow: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="secondary"] {
    border: none !important; background: transparent !important; font-size: 1.2rem !important;
    box-shadow: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,.08) !important; transform: none !important; box-shadow: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: linear-gradient(135deg, #FF9933, #138808) !important; color: #fff !important;
    border-radius: 50% !important; width: 42px !important; height: 42px !important;
    min-width: 42px !important; font-size: 1rem !important; padding: 0 !important;
    box-shadow: 0 6px 16px rgba(255,122,0,.4) !important; }

/* chat input now lives inside the bordered chat bar above */

/* ---------- footer ---------- */
.footer { position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
    background: rgba(4,4,6,.9); backdrop-filter: blur(14px);
    border-top: 1px solid rgba(255,255,255,.07);
    text-align: center; padding: .55rem; font-size: .72rem; color: var(--faint); }
.footer strong { color: #fff; } .footer .sih { color: var(--saffron); font-weight: 700; }
.footer .tri { display: inline-block; width: 26px; height: 3px; border-radius: 2px; vertical-align: middle;
    background: linear-gradient(90deg, #FF9933, #fff, #138808); margin: 0 .5rem; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: #070709 !important; border-right: 1px solid rgba(255,255,255,.07) !important; }
.side-hero { text-align: center; padding: 1.6rem 1rem 1.1rem; border-bottom: 1px solid rgba(255,255,255,.07); margin-bottom: 1rem; }
.side-mark { width: 54px; height: 54px; border-radius: 16px; margin: 0 auto .6rem;
    background: linear-gradient(135deg, #FF9933, #FF6B00 55%, #138808);
    display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
    box-shadow: 0 8px 26px rgba(255,122,0,.35); animation: floaty 4s ease-in-out infinite; }
@keyframes floaty { 50% { transform: translateY(-4px); } }
.side-title { font-weight: 800; color: #fff; font-size: .95rem; }
.side-cap { font-size: .62rem; color: var(--faint); text-transform: uppercase; letter-spacing: 2px; margin-top: .15rem; }
.side-sec { padding: 0 1rem 1.1rem; }
.side-lbl { font-size: .64rem; font-weight: 800; color: var(--faint);
    text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: .55rem; display: block; }
.hist { background: #101013; border: 1px solid #1e1e23; border-radius: 10px;
    padding: .55rem .75rem; margin-bottom: .4rem; font-size: .76rem; color: #c9c9d1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: all .2s; }
.hist:hover { border-color: rgba(255,153,51,.5); background: #15151a; transform: translateX(3px); }
.stat { background: linear-gradient(180deg, #141417, #0e0e11); border: 1px solid #222227;
    border-radius: 14px; padding: .9rem; text-align: center; margin-bottom: 1rem; }
.stat-v { font-size: 1.6rem; font-weight: 800;
    background: linear-gradient(90deg, #FF9933, #FFD700);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.stat-l { font-size: .62rem; color: var(--faint); text-transform: uppercase; letter-spacing: 1.6px; margin-top: .2rem; }
.doc { display: flex; align-items: center; gap: .5rem; font-size: .74rem; color: #b9b9c2;
    padding: .35rem .1rem; border-bottom: 1px dashed rgba(255,255,255,.06); }

/* ---------- buttons / inputs ---------- */
.stButton > button { border-radius: 12px !important; font-weight: 600 !important;
    border: 1px solid #26262c !important; background: #131316 !important; color: #d7d7de !important;
    transition: all .2s ease !important; }
.stButton > button:hover { border-color: rgba(255,153,51,.6) !important; transform: translateY(-2px) !important;
    box-shadow: 0 8px 18px rgba(0,0,0,.4) !important; }
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #FF9933, #c25e00 60%, #138808) !important;
    color: #fff !important; border: none !important;
    box-shadow: 0 8px 22px rgba(255,122,0,.35) !important; }
.stTextInput input, .stTextArea textarea { background: #101013 !important; color: #eee !important;
    border: 1px solid #26262c !important; border-radius: 10px !important; }
.feature-card { background: #101013; border: 1px solid #202026; border-radius: 12px;
    padding: .7rem; text-align: center; margin-bottom: .45rem; }
.feature-card .fi { font-size: 1.3rem; } .feature-card .fn { font-weight: 700; font-size: .76rem; color: #fff; }
.feature-card .fd { font-size: .66rem; color: var(--muted); }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #FF9933, #138808); border-radius: 3px; }

@media (max-width: 640px) {
    .hero h1 { font-size: 1.8rem; }
    .bubble { max-width: 88%; }
    .brand-tag { display: none; }
    .topbar { margin: 0 -.75rem 1rem; }
}
</style>
""", unsafe_allow_html=True)

# ---------------- Intro splash (once per session) ----------------
if not st.session_state.intro_seen:
    st.session_state.intro_seen = True
    try:
        _kb_n = len([f for f in os.listdir("data/ayush_docs") if not f.startswith(".")])
    except Exception:
        _kb_n = 29
    _splash = """
    <div id="intro-splash" onclick="this.remove()">
      <div class="boot">
        <div class="boot-head">SAHAYAK<span>.OS</span><em>v2.0</em></div>
        <div class="boot-lines">
          <div>> Initializing legal core <b class="ok">OK</b></div>
          <div>> Mounting knowledge base — __DOCS__ sources <b class="ok">OK</b></div>
          <div>> Linking neural engine (Groq) <b class="ok">OK</b></div>
          <div>> Calibrating IN / INTL filters <b class="ok">OK</b></div>
          <div>> All systems nominal — welcome, counsellor <b class="blink">▊</b></div>
        </div>
        <div class="boot-bar"><span></span></div>
        <div class="boot-tap">tap anywhere to skip</div>
      </div>
    </div>
    <style>
      #intro-splash{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:#020203;transition:opacity .7s ease;cursor:pointer}
      #intro-splash.hide{opacity:0;pointer-events:none}
      .boot{width:min(520px,88vw);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;text-align:left}
      .boot-head{font-size:1.1rem;font-weight:800;letter-spacing:4px;color:#fff;margin-bottom:1.1rem}
      .boot-head span{background:linear-gradient(90deg,#FF9933,#FFD700);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
      .boot-head em{font-style:normal;font-size:.68rem;color:#555;letter-spacing:2px;margin-left:.5rem}
      .boot-lines div{opacity:0;color:#9a9aa3;font-size:.82rem;margin:.45rem 0;animation:bin .3s ease forwards}
      .boot-lines div:nth-child(1){animation-delay:.2s}.boot-lines div:nth-child(2){animation-delay:.8s}
      .boot-lines div:nth-child(3){animation-delay:1.5s}.boot-lines div:nth-child(4){animation-delay:2.1s}
      .boot-lines div:nth-child(5){animation-delay:2.7s;color:#e8e8ec}
      @keyframes bin{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
      .boot-lines .ok{color:#4ade80}.boot-lines .blink{color:#FF9933;animation:blink 1s steps(1) infinite}
      @keyframes blink{50%{opacity:0}}
      .boot-bar{height:3px;background:#15151a;border-radius:3px;margin-top:1.2rem;overflow:hidden}
      .boot-bar span{display:block;height:100%;width:0;background:linear-gradient(90deg,#FF9933,#FFD700,#138808);animation:load 3.6s ease forwards}
      @keyframes load{to{width:100%}}
      .boot-tap{margin-top:.9rem;color:#3a3a42;font-size:.7rem;font-family:Inter,sans-serif}
    </style>
    <script>
      setTimeout(function(){var s=document.getElementById('intro-splash');if(s){s.classList.add('hide');setTimeout(function(){s.remove();},750);}},4600);
    </script>
    """.replace("__DOCS__", str(_kb_n))
    st.components.v1.html(_splash, height=0)

# ---------------- Ambient background ----------------
st.markdown(
    '<div class="orb orb-a"></div><div class="orb orb-b"></div><div class="orb orb-c"></div>'
    '<div class="aurora"></div><div class="gridlines"></div>',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* ===== futuristic layer ===== */
::selection { background: rgba(255,153,51,.45); color: #fff; }
.stApp { background: #000 !important; }
.aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(900px 500px at 12% -5%, rgba(255,122,0,.10), transparent 60%),
      radial-gradient(800px 500px at 88% 8%, rgba(20,160,60,.10), transparent 60%),
      radial-gradient(700px 700px at 50% 110%, rgba(255,215,0,.05), transparent 60%); }
.gridlines { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: .55;
    background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: radial-gradient(ellipse 90% 70% at 50% 20%, #000 30%, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse 90% 70% at 50% 20%, #000 30%, transparent 75%); }
.orb { z-index: 0; }
.main .block-container, section[data-testid="stSidebar"] { position: relative; z-index: 1; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80;
    box-shadow: 0 0 0 0 rgba(74,222,128,.6); animation: ringpulse 2s ease-out infinite; }
@keyframes ringpulse { 70% { box-shadow: 0 0 0 9px rgba(74,222,128,0); } 100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); } }
.sys-chip { display: inline-flex; align-items: center; gap: .4rem; padding: .34rem .8rem;
    border-radius: 100px; font-size: .7rem; font-weight: 600; color: #b9b9c2;
    background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.09); }
.sys-chip b { color: #fff; }
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem;
    margin: 1.4rem auto 0; max-width: 620px; }
.stat-card { position: relative; overflow: hidden; border-radius: 16px; padding: .9rem .5rem;
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.015));
    border: 1px solid rgba(255,255,255,.09); transition: transform .25s ease, box-shadow .25s ease; }
.stat-card:hover { transform: translateY(-3px);
    box-shadow: 0 14px 30px rgba(0,0,0,.5), 0 0 0 1px rgba(255,153,51,.25); }
.stat-card::after { content: ''; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
    background: linear-gradient(100deg, transparent, rgba(255,255,255,.09), transparent);
    transform: skewX(-18deg); animation: shine 5s ease infinite; }
@keyframes shine { 0%,60% { left: -60%; } 100% { left: 160%; } }
.stat-num { font-size: 1.45rem; font-weight: 800;
    background: linear-gradient(90deg,#FF9933,#FFD700);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.stat-cap { font-size: .62rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1.4px; margin-top: .15rem; }
.ai-head { display: flex; align-items: center; gap: .5rem; margin-bottom: .55rem; padding-bottom: .55rem;
    border-bottom: 1px solid rgba(255,255,255,.08); font-size: .68rem; font-weight: 800;
    letter-spacing: 1.6px; color: #8f8f99; }
.ai-head .live { margin-left: auto; display: inline-flex; align-items: center; gap: .3rem;
    font-size: .62rem; color: #4ade80; letter-spacing: 1px; }
.ai-head .live i { width: 6px; height: 6px; border-radius: 50%; background: #4ade80;
    box-shadow: 0 0 8px #4ade80; animation: blink 1.6s ease infinite; }
.msg-meta { margin-top: .6rem; font-size: .64rem; color: var(--faint); display: flex; gap: .6rem; align-items: center; }
.msg-meta .model { padding: 1px 7px; border-radius: 5px; background: rgba(255,153,51,.1);
    border: 1px solid rgba(255,153,51,.25); color: #FFB25E; font-weight: 700; }
.source-item { position: relative; counter-increment: src; }
.sources { counter-reset: src; }
.source-item::before { content: '0' counter(src); position: absolute; right: .7rem; top: .45rem;
    font-size: .68rem; font-weight: 800; color: rgba(255,255,255,.14); letter-spacing: 1px; }
.rel { height: 3px; border-radius: 3px; background: #222228; margin-top: .5rem; overflow: hidden; }
.rel span { display: block; height: 100%; border-radius: 3px;
    background: linear-gradient(90deg, #FF9933, #138808); animation: relfill 1s ease both; }
@keyframes relfill { from { width: 0 !important; } }
.hist { position: relative; margin-left: .55rem !important; padding-left: .9rem !important;
    border: none !important; border-left: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 0 !important; background: transparent !important; }
.hist::before { content: ''; position: absolute; left: -3.5px; top: 50%; width: 6px; height: 6px;
    border-radius: 50%; background: #2c2c32; transform: translateY(-50%); transition: all .2s; }
.hist:hover { background: rgba(255,153,51,.06) !important; }
.hist:hover::before { background: var(--saffron); box-shadow: 0 0 10px var(--saffron); }
div[data-testid="stRadio"] div[role="radiogroup"] { gap: .4rem; }
div[data-testid="stRadio"] label { background: #101013 !important; border: 1px solid #222228 !important;
    border-radius: 10px !important; padding: .45rem .6rem !important; transition: all .2s !important; }
div[data-testid="stRadio"] label:hover { border-color: rgba(255,153,51,.5) !important; }
.stButton > button:active { transform: scale(.96) !important; }
:focus-visible { outline: 2px solid rgba(255,153,51,.7) !important; outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: .001s !important; transition-duration: .001s !important; }
}
@media (max-width: 640px) {
    .stat-grid { gap: .4rem; }
    .sys-chip.hide-m { display: none; }
}
</style>
""", unsafe_allow_html=True)

@st.dialog("📲 Install IP-SAKTI as an App")
def _install_dialog():
    try:
        st.image("assets/icon-192.png", width=96)
    except Exception:
        pass
    st.markdown("""
    **Android (Chrome):**
    1. Tap **⋮ menu** → **Add to Home screen** → **Install**
    2. The IP-SAKTI icon appears on your home screen and opens full-screen, just like an app.

    **iPhone (Safari):**
    1. Tap **Share** → **Add to Home Screen** → **Add**
    """)
    if st.button("Got it! 👍", key="install_ok"):
        st.rerun()


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("""
    <div class="side-hero">
        <div class="side-mark">🏛️</div>
        <div class="side-title">IP-SAKTI Sahayak</div>
        <div class="side-cap">Chat History</div>
    </div>
    """, unsafe_allow_html=True)

    search = st.text_input("Search", placeholder="🔍 Search questions...", label_visibility="collapsed")

    st.markdown("<div class='side-sec'><span class='side-lbl'>Recent Questions</span>", unsafe_allow_html=True)
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if search:
        user_msgs = [m for m in user_msgs if search.lower() in m["content"].lower()]
    if user_msgs:
        for h_idx, msg in enumerate(reversed(user_msgs[-15:])):
            q = msg["content"][:48] + "…" if len(msg["content"]) > 48 else msg["content"]
            if st.button(f"💬 {q}", key=f"hist_{h_idx}", use_container_width=True, help=msg["content"][:300]):
                st.session_state.messages.append({"role": "user", "content": msg["content"]})
                st.rerun()
    else:
        st.caption("No conversations yet")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("<div class='side-sec'>", unsafe_allow_html=True)
    total_q = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-val">{total_q}</div>
        <div class="stat-lbl">Questions Asked</div>
    </div>
    """, unsafe_allow_html=True)
    fb = st.session_state.get("feedback", {})
    up = sum(1 for v in fb.values() if v == 1)
    dn = sum(1 for v in fb.values() if v == -1)
    if up or dn:
        st.caption(f"👍 {up} • 👎 {dn}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='side-sec'><span class='side-lbl'>Jurisdiction</span>", unsafe_allow_html=True)
    juris = st.radio(
        "", ["india", "international"],
        format_func=lambda x: "🇮🇳 India" if x == "india" else "🌍 International",
        index=0 if st.session_state.jurisdiction == "india" else 1,
        label_visibility="collapsed",
    )
    st.session_state.jurisdiction = juris
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("📲 Install App", use_container_width=True, key="open_install"):
        _install_dialog()
        st.rerun()
    st.markdown("<div class='side-sec'><span class='side-lbl'>🎤 Voice</span>", unsafe_allow_html=True)
    st.caption("🎤 mic in the chat bar = speak • 🔊 on answers = listen")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='side-sec'><span class='side-lbl'>Knowledge Base</span>", unsafe_allow_html=True)
    if validate_pdf_folder("data/ayush_docs"):
        files = os.listdir("data/ayush_docs")
        pdfs = len([f for f in files if f.endswith(".pdf")])
        txts = len([f for f in files if f.endswith(".txt")])
        st.caption(f"{pdfs} PDFs • {txts} Text files • 500+ chunks")
        for f in sorted(files)[:10]:
            name = f.replace(".pdf", "").replace(".txt", "").replace("_", " ").title()
            st.markdown(f"<div class='doc'>📄 {escape(name[:36])}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='side-sec'><span class='side-lbl'>Advanced Features</span>", unsafe_allow_html=True)
    if st.button("🛠️ Feature Panel", use_container_width=True, key="toggle_features"):
        st.session_state.show_features = not st.session_state.show_features
        st.rerun()

    if st.session_state.show_features:
        for feat in get_available_features():
            st.markdown(f"""
            <div class="feature-card">
                <div class="fi">{feat['icon']}</div>
                <div class="fn">{feat['name']}</div>
                <div class="fd">{feat['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

        if PDF_AVAILABLE and st.button("📄 Generate PDF Report", use_container_width=True, key="gen_pdf_report"):
            last_bot = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
            if last_bot:
                pdf_bytes = generate_patent_report(
                    query=st.session_state.messages[-2]["content"] if len(st.session_state.messages) > 1 else "Query",
                    answer=last_bot["content"],
                    sources=last_bot.get("sources", []),
                    jurisdiction=st.session_state.jurisdiction,
                )
                st.download_button(
                    "⬇️ Download Report",
                    data=pdf_bytes,
                    file_name=f"IP_SAKTI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Sticky top bar ----------------
is_india = st.session_state.jurisdiction == "india"
pill_cls = "pill-india" if is_india else "pill-intl"
pill_txt = "🇮🇳 India" if is_india else "🌍 International"
try:
    _kb_docs = len([f for f in os.listdir("data/ayush_docs") if not f.startswith(".")])
except Exception:
    _kb_docs = 29
st.markdown(
    '<div class="topbar">'
    '<div class="brand"><div class="brand-mark">🏛️</div>'
    '<div><div class="brand-name">IP-SAKTI <em>Sahayak</em></div>'
    '<div class="brand-tag">Ministry of Ayush • IPR Assistant</div></div></div>'
    f'<div class="top-right"><span class="sys-chip hide-m"><span class="status-dot"></span>LIVE</span>'
    f'<span class="sys-chip hide-m">⚡ <b>{_kb_docs}</b>&nbsp;sources</span>'
    f'<span class="pill {pill_cls}">{pill_txt}</span>'
    '<span class="sih-chip">🏆 SIH 2026</span></div>'
    "</div>",
    unsafe_allow_html=True,
)

if not st.session_state.get("install_popup_seen", False):
    st.session_state.install_popup_seen = True
    _install_dialog()

# ---------------- Document upload ----------------
with st.expander("📁 Upload Document for Analysis (PDF / Image / Text)", expanded=st.session_state.show_uploader):
    uploaded = st.file_uploader(
        "Upload patent documents, diagrams, or images for text extraction",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        accept_multiple_files=True,
        key="file_uploader",
    )
    if uploaded:
        for file in uploaded:
            if file.name not in [f["name"] for f in st.session_state.uploaded_files]:
                with st.spinner(f"Processing {file.name}..."):
                    st.session_state.uploaded_files.append(process_uploaded_file(file))
        st.success(f"Processed {len(uploaded)} file(s)")

    for f in st.session_state.uploaded_files:
        c1, c2 = st.columns([5, 1])
        with c1:
            icon = "📄" if f["type"] == "application/pdf" else ("🖼️" if f["type"].startswith("image/") else "📝")
            st.markdown(f"<div class='doc'><span>{icon}</span><span>{escape(f['name'])} ({f.get('pages', 1)} pages)</span></div>", unsafe_allow_html=True)
        with c2:
            if st.button("🗑️", key=f"del_{f['name']}"):
                st.session_state.uploaded_files = [x for x in st.session_state.uploaded_files if x["name"] != f["name"]]
                st.rerun()
        if f.get("text"):
            with st.expander(f"📝 Extracted: {f['name']}", expanded=False):
                st.text_area("", f["text"][:2000] + ("..." if len(f["text"]) > 2000 else ""), height=150, key=f"text_{f['name']}")

# ---------------- Hero (empty state) ----------------
if not st.session_state.messages:
    st.markdown(f"""
    <div class="hero">
        <div class="hero-eyebrow"><span class="dot"></span> RAG + Groq • Live Knowledge Base</div>
        <h1>Justice, <span class="grad">decoded.</span></h1>
        <p>Patents, biodiversity &amp; traditional knowledge — answered in seconds with cited sources.</p>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-num">{_kb_docs}</div><div class="stat-cap">Legal Sources</div></div>
            <div class="stat-card"><div class="stat-num">1.7K+</div><div class="stat-cap">Knowledge Chunks</div></div>
            <div class="stat-card"><div class="stat-num">2</div><div class="stat-cap">Jurisdictions</div></div>
        </div>
    </div>
    <div class="sugg-label">Try asking</div>
    """, unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    questions = [
        ("📜 Section 3(p)", "What is Section 3(p) of the Indian Patents Act?"),
        ("🌿 Neem Patent", "Can I patent a Neem-based formulation?"),
        ("📋 Nagoya Protocol", "What is the Nagoya Protocol?"),
        ("🌱 Biodiversity Act", "What does the Biodiversity Act cover?"),
    ]
    for i, (label, q) in enumerate(questions):
        with [q1, q2, q3, q4][i]:
            if st.button(label, use_container_width=True, key=f"q{i}"):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

    st.markdown("""
    <div class="cap-row">
        <span>🎤 Voice input</span><span>📄 PDF reports</span>
        <span>🖼️ Image OCR</span><span>📚 Cited sources</span>
    </div>
    """, unsafe_allow_html=True)


def render_sources(sources):
    st.markdown('<div class="sources"><div class="sources-label">📚 Sources</div>', unsafe_allow_html=True)
    for rank, src in enumerate(sources):
        page = src.get("page", "N/A")
        jkey = src.get("jurisdiction", "")
        jval = jkey.upper()
        section = src.get("section", "")
        preview = src.get("content_preview", "")[:140]
        source_name = src.get("source", "Unknown")
        badge = f'<span class="tag tag-{jkey}">{jval}</span>' if jval else ""
        sec = f"<span>§ {escape(section)}</span>" if section else ""
        rel_w = max(58, 97 - rank * 9)
        st.markdown(
            '<div class="source-item">'
            f'<div class="source-file">📄 {escape(source_name)}</div>'
            f'<div class="source-meta"><span>Page {escape(str(page))}</span>{badge}{sec}</div>'
            f'<div class="source-preview">"{escape(preview)}..."</div>'
            f'<div class="rel"><span style="width:{rel_w}%"></span></div>'
            "</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


FOLLOWUP_MAP = [
    (["3(d)", "novartis", "glivec", "gleevec", "evergreening", "efficacy"], [
        "What is evergreening in pharma patents?",
        "What was the Bayer Nexavar compulsory licence case?",
        "What is Section 3(p) of the Indian Patents Act?",
    ]),
    (["compulsory", "nexavar", "section 84", "sorafenib", "natco"], [
        "What is Section 92 national emergency licence?",
        "What is the Bolar provision under Section 107A?",
        "What was the Novartis Glivec judgment?",
    ]),
    (["nagoya", "benefit sharing", "abs", "bmc", "gene fund"], [
        "What is the Jeevani case? How did the Kani tribe benefit?",
        "CBD vs Nagoya Protocol — what's the difference?",
        "What does the Biodiversity Act cover?",
    ]),
    (["darjeeling", "basmati", "geographical indication", "pashmina", "alphonso", "gi tag"], [
        "What is TKDL and how does it prevent biopiracy?",
        "Can I patent a Neem-based formulation?",
        "What is the Turmeric patent case?",
    ]),
    (["neem", "turmeric", "tkdl", "biopiracy", "hoodia", "teff"], [
        "What is the Jeevani benefit-sharing model?",
        "What is the WIPO GRATK treaty 2024?",
        "What is Section 3(p) of the Indian Patents Act?",
    ]),
    (["software", "3(k)", "cri", "computer programme", "ai patent"], [
        "What was the Ferid Allani judgment?",
        "Can microorganisms be patented? Section 3(j)?",
        "How do I file a patent in India? Steps and forms?",
    ]),
    (["pct", "international filing", "national phase"], [
        "How do I file a patent in India? Steps and forms?",
        "What is Section 39 foreign filing permission?",
        "What is the TRIPS Agreement?",
    ]),
    (["file a patent", "filing", "form 18", "fer", "examination", "opposition", "fees"], [
        "What is pre-grant opposition under Section 25?",
        "What is the 31-month RFE deadline?",
        "What is Section 39 foreign filing permission?",
    ]),
    (["biodiversity", "nba", "sbb"], [
        "What changed in the 2023 Biodiversity Amendment?",
        "What is the Jeevani case?",
        "What is benefit sharing under Nagoya?",
    ]),
    (["trips", "wto", "doha"], [
        "What is the Doha Declaration on public health?",
        "What is Section 92A export licence?",
        "WIPO GRATK treaty 2024 — what changed?",
    ]),
]


def get_followups(question: str, answer: str) -> list:
    text = f"{question} {answer}".lower()
    for keywords, suggestions in FOLLOWUP_MAP:
        if any(k in text for k in keywords):
            return suggestions[:3]
    return [
        "What is Section 3(p) of the Indian Patents Act?",
        "Can I patent a Neem-based formulation?",
        "What is the Nagoya Protocol?",
    ]


def log_feedback(question: str, rating: int):
    import json

    if "feedback" not in st.session_state:
        st.session_state.feedback = {}
    st.session_state.feedback[question] = rating
    try:
        with open("feedback_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"ts": datetime.now().isoformat(timespec="seconds"),
                 "q": question[-300:], "rating": rating},
                ensure_ascii=False,
            ) + "\n")
    except Exception:
        pass


# ---------------- Messages ----------------
last_asst_idx = max(
    [i for i, m in enumerate(st.session_state.messages) if m["role"] == "assistant"],
    default=-1,
)
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(
            '<div class="msg msg-user"><div class="avatar avatar-user">👤</div>'
            f'<div class="bubble">{escape(msg["content"])}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        mtime = escape(msg.get("time", ""))
        time_html = f"<span>🕐 {mtime}</span>" if mtime else ""
        st.markdown(
            '<div class="msg msg-bot"><div class="avatar avatar-bot">🏛️</div>'
            f'<div class="bubble"><div class="ai-head">SAHAYAK AI<span class="live"><i></i>LIVE</span></div>{msg["content"]}'
            f'<div class="msg-meta"><span class="model">qwen · groq</span>{time_html}</div></div></div>',
            unsafe_allow_html=True,
        )
        b1, b2, _ = st.columns([1.2, 1.2, 5])
        with b1:
            if PDF_AVAILABLE and st.button("📄 PDF", key=f"pdf_{idx}", use_container_width=True):
                user_q = next((m["content"] for m in reversed(st.session_state.messages[:idx]) if m["role"] == "user"), "Query")
                pdf_bytes = generate_patent_report(
                    query=user_q, answer=msg["content"],
                    sources=msg.get("sources", []), jurisdiction=st.session_state.jurisdiction,
                )
                st.download_button(
                    "⬇️ Download", data=pdf_bytes,
                    file_name=f"IP_SAKTI_Answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf", key=f"dl_{idx}",
                )
        with b2:
            if st.button("🔊 Listen", key=f"speak_{idx}", use_container_width=True):
                with st.spinner("Generating voice…"):
                    try:
                        st.session_state[f"audio_{idx}"] = speak_answer(msg["content"])
                    except Exception as e:
                        st.error(f"Voice failed: {e}")
                st.rerun()
        akey = f"audio_{idx}"
        if st.session_state.get(akey):
            st.audio(st.session_state[akey], format="audio/mp3")
        if msg.get("sources"):
            render_sources(msg["sources"])

        if idx == last_asst_idx:
            f1, f2, f3 = st.columns([1, 1, 6])
            with f1:
                if st.button("👍", key=f"fb_up_{idx}", help="Good answer", use_container_width=True):
                    user_q = next((m["content"] for m in reversed(st.session_state.messages[:idx]) if m["role"] == "user"), "")
                    log_feedback(user_q, 1)
                    st.toast("Thanks! 👍 Noted.")
            with f2:
                if st.button("👎", key=f"fb_dn_{idx}", help="Bad answer", use_container_width=True):
                    user_q = next((m["content"] for m in reversed(st.session_state.messages[:idx]) if m["role"] == "user"), "")
                    log_feedback(user_q, -1)
                    st.toast("Noted 👎 — we'll improve.")
            st.markdown("<div style='font-size:.72rem;color:#666;margin:.4rem 0 .3rem;'>💡 Go deeper:</div>", unsafe_allow_html=True)
            fq = get_followups(
                next((m["content"] for m in reversed(st.session_state.messages[:idx]) if m["role"] == "user"), ""),
                msg["content"],
            )
            fq_cols = st.columns(3)
            for j, suggestion in enumerate(fq):
                with fq_cols[j]:
                    if st.button(suggestion, key=f"fq_{idx}_{j}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": suggestion})
                        st.rerun()

# ---------------- Unified chat bar: attach + input + mic + send in ONE box ----------------
with st.container(border=True):
    cb1, cb2, cb3 = st.columns([1, 10, 1], gap="small")
    with cb1:
        if st.button("📎", use_container_width=True, key="cb_attach", help="Attach PDF / image / text"):
            st.session_state.show_uploader = not st.session_state.show_uploader
            st.rerun()
    with cb2:
        with st.form("chatbar", clear_on_submit=True, border=False):
            fi, fs = st.columns([10, 1], gap="small")
            with fi:
                typed = st.text_input(
                    "Message",
                    placeholder="Ask about Patents Act, Biodiversity, WIPO, TKDL…",
                    label_visibility="collapsed",
                    key="chat_text",
                )
            with fs:
                sent = st.form_submit_button("➤", use_container_width=True, help="Send")
    with cb3:
        if MIC_OK:
            audio = mic_recorder(
                start_prompt="🎤", stop_prompt="⏹",
                just_once=True, use_container_width=True,
                key="chat_mic", format="webm",
            )
        else:
            audio = None
            if st.button("🎤", use_container_width=True, key="cb_mic_na", help="Voice recorder unavailable"):
                st.toast("Voice recorder not installed on server")

if sent and typed and typed.strip():
    st.session_state.messages.append({"role": "user", "content": typed.strip()})
    st.rerun()

if audio and isinstance(audio, dict) and audio.get("bytes"):
    import hashlib
    h = hashlib.md5(audio["bytes"]).hexdigest()
    if st.session_state.get("last_audio_hash") != h:
        st.session_state["last_audio_hash"] = h
        with st.spinner("🎤 Transcribing your voice…"):
            try:
                said = transcribe_audio(audio["bytes"])
            except Exception as e:
                st.error(f"Voice transcribe failed: {e}")
                said = ""
        if said:
            st.session_state.messages.append({"role": "user", "content": said})
            st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]["content"]
    file_context = "".join(
        f"\n\n[Document: {f['name']}]\n{f['text'][:2000]}"
        for f in st.session_state.uploaded_files if f.get("text")
    )
    with st.chat_message("assistant"):
        st.markdown(
            '<div class="thinking"><span class="dots"><span></span><span></span><span></span></span>'
            "Searching knowledge base…</div>",
            unsafe_allow_html=True,
        )
        result = query_rag(last_msg + file_context, st.session_state.jurisdiction)
        if result.get("cached"):
            st.caption("⚡ Instant answer — served from cache, zero API cost")

        def _stream_words(text):
            import time as _t
            for _w in text.split(" "):
                yield _w + " "
                _t.sleep(0.012)

        try:
            st.write_stream(_stream_words(result["answer"]))
        except Exception:
            st.write(result["answer"])
        if PDF_AVAILABLE and st.button("📄 Save as PDF", key="pdf_new", use_container_width=True):
            pdf_bytes = generate_patent_report(
                query=last_msg, answer=result["answer"],
                sources=result["sources"], jurisdiction=st.session_state.jurisdiction,
            )
            st.download_button(
                "⬇️ Download Report", data=pdf_bytes,
                file_name=f"IP_SAKTI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf", key="dl_new",
            )
        if result["sources"]:
            render_sources(result["sources"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "cached": result.get("cached", False),
        "time": datetime.now().strftime("%H:%M"),
    })
    st.rerun()

# ---------------- Footer ----------------
st.markdown("""
<div class="footer">
    <strong>Team NEXUS</strong><span class="tri"></span><span class="sih">SIH 2026</span><span class="tri"></span>Ministry of Ayush
</div>
""", unsafe_allow_html=True)

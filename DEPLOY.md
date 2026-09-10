# IP-SAKTI Sahayak - Deployment Guide

## 📦 Quick Deploy to Streamlit Cloud (Free)

### 1. Push to GitHub
```bash
cd "D:\btech\Hackathon2026 btech 1st sem sih"
git init
git add .
git commit -m "IP-SAKTI Sahayak - SIH 2026"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ip-sakti-sahayak.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repo
4. Repository: `YOUR_USERNAME/ip-sakti-sahayak`
5. Branch: `main`
6. Main file path: `app.py`
7. Click **Advanced settings** → Add secrets:
   ```
   GROQ_API_KEY = "PASTE_YOUR_GROQ_API_KEY_HERE"
   ```
8. Click **Deploy!**

---

## 🔧 Local Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install Tesseract OCR (for image text extraction)
- **Windows:** Download from https://github.com/UB-Mannheim/tesseract/wiki
- **Mac:** `brew install tesseract`
- **Linux:** `sudo apt-get install tesseract-ocr`

### Run Locally
```bash
streamlit run app.py
```

---

## 📁 Project Structure
```
ip-sakti-sahayak/
├── app.py                 # Main Streamlit app
├── rag_pipeline.py        # RAG pipeline with Groq
├── data_ingestion.py      # Document processing
├── features.py            # Advanced features (PDF, OCR, Voice)
├── utils.py               # Utilities
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── .streamlit/
│   ├── config.toml       # Streamlit config
│   └── secrets.toml      # API keys (NOT in git)
├── data/
│   └── ayush_docs/       # Knowledge base documents
└── vector_db/            # ChromaDB vector store
```

---

## 🔐 Environment Variables

Create `.streamlit/secrets.toml` (local) or add in Streamlit Cloud:

```toml
GROQ_API_KEY = "your_groq_api_key"
HF_TOKEN = "your_huggingface_token"  # Optional
OPENAI_API_KEY = "your_openai_key"    # Optional for image gen
```

---

## 🌐 Deployment Options

| Platform | Cost | Difficulty | Best For |
|----------|------|------------|----------|
| **Streamlit Cloud** | Free | ⭐ Easy | Demo, sharing |
| **Hugging Face Spaces** | Free | ⭐⭐ Easy | ML demos |
| **Railway** | $5/mo | ⭐⭐ Medium | Production |
| **Render** | Free tier | ⭐⭐ Medium | Production |
| **VPS (DigitalOcean/AWS)** | $4-20/mo | ⭐⭐⭐ Hard | Full control |

---

## 🚀 Streamlit Cloud Deploy Steps (Detailed)

1. **Fork/Clone this repo** to your GitHub
2. **Go to** https://share.streamlit.io
3. **Sign in** with GitHub
4. **Click "New app"**
5. **Fill in:**
   - Repository: `your-username/ip-sakti-sahayak`
   - Branch: `main`
   - Main file: `app.py`
6. **Advanced settings** → **Secrets:**
   ```toml
   GROQ_API_KEY = "PASTE_YOUR_GROQ_API_KEY_HERE"
   ```
7. **Click Deploy** - Wait 2-3 minutes
8. **Your app is live!** 🎉

---

## 📝 Notes for SIH 2026 Demo

- **Groq API** is already configured with valid key
- **Knowledge base** includes: Indian Patents Act, Biodiversity Act, TKDL, WIPO, Nagoya, TRIPS
- **Features:** Chat, Voice, PDF Export, OCR, File Upload, Dark/Light mode
- **Works offline** (except Groq API calls)

---

## 🛠 Troubleshooting

| Issue | Fix |
|-------|-----|
| Tesseract not found | Install tesseract-ocr system package |
| ChromaDB errors | Delete `vector_db/` and re-run `data_ingestion.py` |
| Groq rate limit | Reduce `max_tokens` in `rag_pipeline.py` |
| Port in use | Change port in `.streamlit/config.toml` |

---

## 📞 Support

For SIH 2026 demo issues:
- Check Groq API key is valid
- Ensure vector_db exists (run `python data_ingestion.py`)
- Verify all requirements installed

**Team NEXUS | SIH 2026 | Ministry of Ayush**
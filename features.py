"""
Advanced Features Module for IP-SAKTI Sahayak
- Voice (Speech-to-Text, Text-to-Speech)
- PDF Generation
- Image Generation
- OCR (Image to Text)
- PDF Text Extraction
"""

import os
import io
import base64
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# PDF GENERATION
# ============================================================
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("fpdf2 not available - PDF generation disabled")

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract/PIL not available - OCR disabled")


class IPPDF(FPDF):
    """Custom PDF class for IP-SAKTI documents"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
    
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 5, 'IP-SAKTI Sahayak | Ministry of Ayush | Team NEXUS', align='C')
        self.ln(8)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')
    
    def add_title_page(self, title: str, subtitle: str = ""):
        self.add_page()
        self.ln(40)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(0, 51, 102)
        self.multi_cell(0, 12, title, align='C')
        self.ln(10)
        if subtitle:
            self.set_font('Helvetica', '', 14)
            self.set_text_color(80)
            self.multi_cell(0, 8, subtitle, align='C')
        self.ln(15)
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(128)
        self.cell(0, 6, f'Generated on {datetime.now().strftime("%B %d, %Y")}', align='C')
        self.ln(8)
        self.cell(0, 6, 'IP-SAKTI Sahayak | Ministry of Ayush | SIH 2026', align='C')
    
    def add_section(self, title: str, content: str):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(255, 153, 51)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(30)
        self.multi_cell(0, 5.5, content)
        self.ln(6)
    
    def add_bullet_list(self, items: List[str]):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(30)
        for item in items:
            self.cell(5)
            self.cell(4, 5.5, chr(8226))
            self.multi_cell(0, 5.5, f' {item}')
        self.ln(4)
    
    def add_table(self, headers: List[str], data: List[List[str]], col_widths: Optional[List[float]] = None):
        if not col_widths:
            col_widths = [self.epw / len(headers)] * len(headers)
        
        # Header
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, border=1, fill=True, align='C')
        self.ln()
        
        # Data
        self.set_font('Helvetica', '', 9)
        self.set_text_color(30)
        fill = False
        for row in data:
            if fill:
                self.set_fill_color(240, 245, 250)
            else:
                self.set_fill_color(255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell), border=1, fill=True, align='L')
            self.ln()
            fill = not fill
        self.ln(6)


def generate_patent_report(query: str, answer: str, sources: List[Dict], jurisdiction: str = "india") -> bytes:
    """Generate a professional patent/IP report PDF"""
    if not PDF_AVAILABLE:
        raise ImportError("fpdf2 not installed")
    
    pdf = IPPDF()
    pdf.alias_nb_pages()
    
    # Title page
    pdf.add_title_page(
        "IP-SAKTI Sahayak Report",
        f"Query: {query[:80]}{'...' if len(query) > 80 else ''}\nJurisdiction: {jurisdiction.title()}"
    )
    
    # Query section
    pdf.add_page()
    pdf.add_section("Your Query", query)
    
    # Answer section
    pdf.add_section("Response", answer)
    
    # Sources section
    if sources:
        pdf.add_section("Source Documents", "")
        for i, src in enumerate(sources, 1):
            src_text = f"{i}. {src.get('source', 'Unknown')}"
            if src.get('page') and src['page'] != 'N/A':
                src_text += f" | Page {src['page']}"
            if src.get('section'):
                src_text += f" | Section: {src['section']}"
            src_text += f" | Jurisdiction: {src.get('jurisdiction', 'Unknown').upper()}"
            if src.get('content_preview'):
                src_text += f"\n   Preview: {src['content_preview'][:200]}..."
            pdf.add_section("", src_text)
    
    # Footer info
    pdf.add_section("Disclaimer", 
        "This report is generated by IP-SAKTI Sahayak, an AI-powered assistant for "
        "Intellectual Property Rights. The information provided is based on the knowledge "
        "base and should be verified with official sources. This does not constitute legal advice. "
        "Please consult a qualified IP attorney for legal matters.")
    
    # Output
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()


def generate_summary_pdf(title: str, sections: Dict[str, str]) -> bytes:
    """Generate a summary PDF with multiple sections"""
    if not PDF_AVAILABLE:
        raise ImportError("fpdf2 not installed")
    
    pdf = IPPDF()
    pdf.alias_nb_pages()
    pdf.add_title_page(title)
    
    for section_title, content in sections.items():
        pdf.add_section(section_title, content)
    
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()


# ============================================================
# OCR (IMAGE TO TEXT)
# ============================================================
def extract_text_from_image(image_bytes: bytes, lang: str = 'eng') -> str:
    """Extract text from image using OCR"""
    if not OCR_AVAILABLE:
        return "OCR not available. Install pytesseract and tesseract-ocr."
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return f"OCR Error: {str(e)}"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"PDF extraction error: {str(e)}"
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"PDF extraction error: {str(e)}"


# ============================================================
# IMAGE GENERATION (placeholder for API integration)
# ============================================================
def generate_image_prompt_based(prompt: str, style: str = "professional") -> Dict[str, Any]:
    """
    Generate image based on prompt.
    Note: This is a placeholder. For actual image generation, integrate with:
    - DALL-E API (OpenAI)
    - Stable Diffusion (local or API)
    - Midjourney API
    - Hugging Face Inference API
    """
    # Return a placeholder response
    return {
        "success": False,
        "message": "Image generation requires API integration (DALL-E, Stable Diffusion, etc.)",
        "prompt": prompt,
        "suggested_apis": [
            "OpenAI DALL-E 3 API",
            "Stable Diffusion (local/Replicate/HuggingFace)",
            "Midjourney API",
            "Leonardo.ai API"
        ]
    }


def generate_diagram_prompt(topic: str) -> str:
    """Generate a prompt for creating patent/IP related diagrams"""
    prompts = {
        "patent_process": f"Professional flowchart showing Indian patent filing process: "
            f"Prior Art Search -> Drafting -> Filing -> Publication -> Examination -> "
            f"First Examination Report -> Response -> Grant. Clean corporate style, "
            f"saffron and green color scheme, Ministry of Ayush branding.",
        
        "biodiversity_flow": f"Diagram showing Biodiversity Act access and benefit sharing flow: "
            f"Application -> NBA/SBB Review -> Prior Informed Consent -> Mutually Agreed Terms -> "
            f"Approval -> Benefit Sharing. Professional government document style.",
        
        "tkdl_protection": f"Illustration showing TKDL preventing biopiracy: "
            f"Traditional Knowledge -> TKDL Database -> Patent Office Search -> Prior Art Found -> "
            f"Patent Rejected. Indian government style with saffron/white/green colors.",
        
        "ip_rights": f"Infographic showing types of IP rights in India: Patents, Trademarks, "
            f"Copyrights, Designs, Geographical Indications, Plant Varieties. "
            f"Clean professional style with icons."
    }
    return prompts.get(topic, f"Professional diagram about {topic} for Indian IP law context")


# ============================================================
# VOICE FEATURES (Browser-based via JavaScript)
# ============================================================
def get_voice_html() -> str:
    """Return HTML/JS for voice features in Streamlit"""
    return """
    <div id="voice-container">
        <script>
        // Speech Recognition (Voice to Text)
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let isListening = false;
        
        function startVoiceInput() {
            if (!SpeechRecognition) {
                alert('Speech recognition not supported in this browser. Use Chrome/Edge.');
                return;
            }
            
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-IN';
            
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('voice-btn').innerHTML = '🔴 Listening...';
                document.getElementById('voice-btn').style.background = '#ff4444';
            };
            
            recognition.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                document.getElementById('voice-input').value = transcript;
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
            };
            
            recognition.onend = () => {
                isListening = false;
                document.getElementById('voice-btn').innerHTML = '🎤 Voice Input';
                document.getElementById('voice-btn').style.background = '';
            };
            
            recognition.start();
        }
        
        function stopVoiceInput() {
            if (recognition && isListening) {
                recognition.stop();
            }
        }
        
        // Text to Speech
        function speakText(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'en-IN';
                utterance.rate = 1;
                utterance.pitch = 1;
                utterance.volume = 1;
                
                // Try to use Indian English voice
                const voices = speechSynthesis.getVoices();
                const indianVoice = voices.find(v => 
                    v.lang.includes('en-IN') || v.lang.includes('en-GB') || v.name.includes('India')
                );
                if (indianVoice) utterance.voice = indianVoice;
                
                speechSynthesis.speak(utterance);
            } else {
                alert('Text-to-speech not supported in this browser.');
            }
        }
        
        function stopSpeaking() {
            if ('speechSynthesis' in window) {
                speechSynthesis.cancel();
            }
        }
        
        // Make functions globally available
        window.startVoiceInput = startVoiceInput;
        window.stopVoiceInput = stopVoiceInput;
        window.speakText = speakText;
        window.stopSpeaking = stopSpeaking;
        
        // Load voices
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = () => {};
        }
        </script>
        
        <style>
        .voice-btn {
            background: linear-gradient(135deg, #FF9933, #FF6B00);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .voice-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 107, 0, 0.4);
        }
        .voice-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .voice-btn.active {
            background: linear-gradient(135deg, #ff4444, #cc0000);
        }
        .speak-btn {
            background: linear-gradient(135deg, #138808, #0D6B06);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .speak-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(19, 136, 8, 0.4);
        }
        </style>
    </div>
    """


def get_voice_controls_html(input_key: str = "voice-input", button_id: str = "voice-btn") -> str:
    """Get voice control buttons HTML"""
    return f"""
    <div style="display: flex; gap: 0.5rem; margin: 0.5rem 0;">
        <button id="{button_id}" class="voice-btn" onclick="startVoiceInput()" title="Click to speak your question">
            🎤 Voice Input
        </button>
        <button class="speak-btn" onclick="speakText(document.getElementById('{input_key}').value)" title="Read the answer aloud">
            🔊 Speak Answer
        </button>
        <button class="speak-btn" onclick="stopSpeaking()" style="background: #666;" title="Stop speaking">
            ⏹️ Stop
        </button>
    </div>
    <script>{get_voice_html()}</script>
    """


# ============================================================
# DOCUMENT PROCESSING UTILITIES
# ============================================================
def process_uploaded_file(uploaded_file) -> Dict[str, Any]:
    """Process uploaded file (PDF, image, text) and extract content"""
    result = {
        "filename": uploaded_file.name,
        "type": uploaded_file.type,
        "text": "",
        "pages": 0,
        "error": None
    }
    
    try:
        file_bytes = uploaded_file.read()
        
        if uploaded_file.type == "application/pdf":
            result["text"] = extract_text_from_pdf(file_bytes)
            # Count pages
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                result["pages"] = len(doc)
                doc.close()
            except:
                result["pages"] = 1
                
        elif uploaded_file.type.startswith("image/"):
            result["text"] = extract_text_from_image(file_bytes)
            result["pages"] = 1
            
        elif uploaded_file.type == "text/plain":
            result["text"] = file_bytes.decode('utf-8', errors='ignore')
            result["pages"] = 1
            
        else:
            result["error"] = f"Unsupported file type: {uploaded_file.type}"
            
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"File processing failed: {e}")
    
    return result


def create_patent_draft_pdf(invention_title: str, description: str, claims: List[str], 
                            abstract: str, inventors: List[str]) -> bytes:
    """Create a patent draft PDF"""
    if not PDF_AVAILABLE:
        raise ImportError("fpdf2 not installed")
    
    pdf = IPPDF()
    pdf.alias_nb_pages()
    pdf.add_title_page("Patent Draft", invention_title)
    
    # Abstract
    pdf.add_section("Abstract", abstract)
    
    # Description
    pdf.add_section("Description", description)
    
    # Claims
    pdf.add_section("Claims", "")
    for i, claim in enumerate(claims, 1):
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(30)
        pdf.multi_cell(0, 5.5, f"{i}. {claim}")
        pdf.ln(3)
    
    # Inventors
    pdf.add_section("Inventors", ", ".join(inventors))
    
    # Footer
    pdf.add_section("Disclaimer", 
        "This is a draft document generated by IP-SAKTI Sahayak. "
        "This is not a filed patent application. Consult a registered patent agent "
        "for actual filing.")
    
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()


# ============================================================
# FEATURE STATUS CHECK
# ============================================================
def get_feature_status() -> Dict[str, bool]:
    """Check which features are available"""
    return {
        "pdf_generation": PDF_AVAILABLE,
        "ocr": OCR_AVAILABLE,
        "pdf_extraction": True,  # pypdf is available
        "voice_browser": True,   # Always available via browser APIs
        "image_generation": False,  # Requires external API
    }


# ============================================================
# MAIN INTEGRATION FUNCTION
# ============================================================
def get_available_features() -> List[Dict[str, str]]:
    """Get list of available features for UI"""
    status = get_feature_status()
    features = []
    
    if status["pdf_generation"]:
        features.append({
            "name": "PDF Report Generation",
            "desc": "Generate professional IP/patent reports as PDF",
            "icon": "📄"
        })
    
    if status["ocr"]:
        features.append({
            "name": "Image OCR",
            "desc": "Extract text from images (patent docs, diagrams)",
            "icon": "🖼️"
        })
    
    features.append({
        "name": "PDF Text Extraction",
        "desc": "Extract text from uploaded PDF documents",
        "icon": "📖"
    })
    
    features.append({
        "name": "Voice Input (STT)",
        "desc": "Speak your questions using browser speech recognition",
        "icon": "🎤"
    })
    
    features.append({
        "name": "Voice Output (TTS)",
        "desc": "Listen to answers using browser text-to-speech",
        "icon": "🔊"
    })
    
    features.append({
        "name": "Patent Draft Generator",
        "desc": "Create structured patent draft documents",
        "icon": "📝"
    })
    
    features.append({
        "name": "Image Generation",
        "desc": "Generate diagrams (requires API integration)",
        "icon": "🎨"
    })
    
    return features
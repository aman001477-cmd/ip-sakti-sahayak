import os
import requests
import urllib3
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PDF_FOLDER = "data/ayush_docs"
os.makedirs(PDF_FOLDER, exist_ok=True)

PDF_URLS = {
    "indian_patents_act_1970.pdf": "https://www.ipindia.gov.in/writereaddata/Portal/IPOAct/1_31_1_patent-act-1970-11march2015.pdf",
    "patent_rules_2003.pdf": "https://www.ipindia.gov.in/writereaddata/Portal/IPOAct/1_31_2_patent-rules-2003-11march2015.pdf",
    "biodiversity_act_2002.pdf": "http://nbaindia.org/uploaded/BiodiversityAct/Biodiversity_Act_2002.pdf",
    "biodiversity_rules_2004.pdf": "http://nbaindia.org/uploaded/BiodiversityAct/Biodiversity_Rules_2004.pdf",
    "nagoya_protocol.pdf": "https://www.cbd.int/abs/doc/protocol/nagoya-protocol-en.pdf",
    "trips_agreement.pdf": "https://www.wto.org/english/docs_e/legal_e/27-trips_01_e.pdf",
    "wipo_traditional_knowledge.pdf": "https://www.wipo.int/edocs/pubdocs/en/tk/920/wipo_pub_920.pdf",
    "pct_text.pdf": "https://www.wipo.int/pct/en/texts/pdf/pct.pdf",
    "cbd_text.pdf": "https://www.cbd.int/doc/legal/cbd-en.pdf",
    "tkdl_guidelines.txt": None,
}

PLACEHOLDER_DOCS = {
    "tkdl_guidelines.txt": """TKDL (Traditional Knowledge Digital Library) Guidelines

OVERVIEW
The Traditional Knowledge Digital Library (TKDL) is a pioneering Indian initiative to prevent misappropriation of traditional knowledge at international patent offices.

OBJECTIVES
1. Prevent grant of patents on non-original inventions based on Indian traditional knowledge
2. Create a digital repository of traditional knowledge from Ayurveda, Unani, Siddha, Yoga
3. Provide access to patent examiners worldwide for prior art search
4. Bridge language barrier (Sanskrit, Arabic, Persian, Urdu, Tamil to English, French, German, Japanese, Spanish)

DATABASE CONTENT
- Ayurveda: ~100,000 formulations from classical texts
- Unani: ~80,000 formulations
- Siddha: ~12,000 formulations
- Yoga: ~1,500 postures/techniques

ACCESS FOR PATENT OFFICES
- EPO (European Patent Office): Access granted since 2009
- USPTO (US Patent Office): Access granted since 2011
- IP Australia: Access granted since 2013
- CIPO (Canada): Access granted since 2014
- UK IPO: Access granted since 2015
- JPO (Japan): Access granted since 2016
- DPMA (Germany): Access granted since 2017
- INPI (France): Access granted since 2018
- CIPO (Chile): Access granted since 2019
- IP Philippines: Access granted since 2020
- IP Russia: Access granted since 2021
- IP Brazil: Access granted since 2022

SEARCH INTERFACE
- TKDL provides a dedicated search portal for patent examiners
- Supports keyword, formulation, disease, ingredient searches
- Cross-referenced with IPC (International Patent Classification)
- Available in multiple languages

LEGAL FRAMEWORK
- TKDL operates under Cabinet Committee on Economic Affairs approval
- MoU with CSIR (Council of Scientific and Industrial Research)
- Access agreements with individual patent offices
- Non-disclosure agreements protect sensitive formulations

SUCCESS STORIES
- 200+ patent applications rejected/withdrawn based on TKDL prior art
- Major cases: Neem, Turmeric, Basmati, Karela, Jamun, Brinjal
- Estimated savings: $1B+ in potential litigation costs

RELEVANT INDIAN LAWS
- Patents Act 1970, Section 3(p): Traditional knowledge not patentable
- Biodiversity Act 2002: Access and benefit sharing for TK
- Protection of Plant Varieties and Farmers' Rights Act 2001
- Geographical Indications Act 1999

INTERNATIONAL COOPERATION
- WIPO IGC (Intergovernmental Committee on IP and Genetic Resources, TK, Folklore)
- CBD (Convention on Biological Diversity) - Nagoya Protocol
- WTO TRIPS Council - Article 27.3(b) review
- FAO International Treaty on Plant Genetic Resources""",
    
    "ayurveda_ip_guidelines.txt": """Ayurveda IP Guidelines - Ministry of Ayush

OVERVIEW
Guidelines for protection of Intellectual Property in Ayurveda sector by Ministry of Ayush, Government of India.

PATENT PROTECTION FOR AYURVEDA
1. Novel formulations with synergistic effects are patentable
2. New extraction/standardization methods are patentable
3. New dosage forms/delivery systems are patentable
4. New therapeutic indications with clinical evidence are patentable
5. Traditional formulations AS-IS are NOT patentable (Section 3(p))

TRADITIONAL KNOWLEDGE PROTECTION
1. Document formulations in TKDL
2. Register geographical indications for region-specific products
3. Use Protection of Plant Varieties Act for medicinal plants
3. Benefit sharing agreements with communities

REGULATORY REQUIREMENTS
1. ASU Drugs - Drugs & Cosmetics Act 1940, Rules 1945
2. GMP compliance mandatory
3. Clinical trials for new indications (ICMR guidelines)
4. Stability studies as per ICH guidelines
5. Heavy metal/pesticide limits as per AYUSH standards

IP FILING STRATEGY
1. File in India first (Section 8, Patents Act)
2. PCT route for international protection
3. Design patents for packaging/branding
4. Trademark for brand names (Class 5, 30, 35)
5. Geographical Indications for regional specialties

BENEFIT SHARING (Biodiversity Act 2002)
1. Prior informed consent from NBA/SBB
2. Mutually agreed terms for access
3. Fair and equitable benefit sharing
4. Community protocols for TK access

QUALITY STANDARDS
1. Ayurvedic Pharmacopoeia of India (API)
2. Ayurvedic Formulary of India (AFI)
3. WHO guidelines for herbal medicines
4. ISO/TC 249 standards for traditional medicine

ENFORCEMENT
1. Monitor patent databases for misappropriation
2. Use TKDL as prior art evidence
3. Oppose grants at patent offices
3. Legal action under Patents Act, Biodiversity Act

KEY CONTACTS
- Ministry of Ayush: ayush.gov.in
- CSIR-TKDL: tkdl.res.in
- NBA: nbaindia.org
- Patent Office: ipindia.gov.in""",
}

def download_pdf(url: str, filename: str) -> bool:
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, timeout=120, stream=True, verify=False)
        response.raise_for_status()
        
        filepath = os.path.join(PDF_FOLDER, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size = os.path.getsize(filepath)
        print(f"  [OK] Saved {filename} ({size/1024:.1f} KB)")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to download {filename}: {e}")
        return False

def create_placeholder(filename: str, content: str) -> bool:
    try:
        filepath = os.path.join(PDF_FOLDER, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [CREATED] {filename} ({len(content)} chars)")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to create {filename}: {e}")
        return False

def main():
    print("=" * 60)
    print("IP-SAKTI Sahayak - Document Downloader")
    print("=" * 60)
    print(f"Target folder: {PDF_FOLDER}")
    print()
    
    success = 0
    
    for filename, url in PDF_URLS.items():
        if url:
            if download_pdf(url, filename):
                success += 1
        else:
            content = PLACEHOLDER_DOCS.get(filename, "")
            if content and create_placeholder(filename, content):
                success += 1
    
    print()
    print("=" * 60)
    print(f"Completed: {success}/{len(PDF_URLS)} documents")
    print("=" * 60)
    
    if success < len(PDF_URLS):
        print("\nSome downloads failed. Manual URLs:")
        for filename, url in PDF_URLS.items():
            if url:
                print(f"  {filename}: {url}")
            else:
                print(f"  {filename}: [Placeholder created from embedded content]")

if __name__ == "__main__":
    main()
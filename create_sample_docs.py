import os

PDF_FOLDER = "data/ayush_docs"
os.makedirs(PDF_FOLDER, exist_ok=True)

SAMPLE_DOCS = {
    "indian_patents_act_1970.txt": """THE PATENTS ACT, 1970

ARRANGEMENT OF SECTIONS

CHAPTER I: PRELIMINARY
Section 1: Short title, extent and commencement
Section 2: Definitions
Section 3: What are not inventions

CHAPTER II: INVENTIONS NOT PATENTABLE
Section 3(p): Traditional knowledge - An invention which in effect, is traditional knowledge or which is an aggregation or duplication of known properties of traditionally known component or components.

Section 3(d): The mere discovery of a new form of a known substance which does not result in the enhancement of the known efficacy of that substance or the mere discovery of any new property or new use for a known substance or of the mere use of a known process, machine or apparatus unless such known process results in a new product or employs at least one new reactant.

Section 3(j): Plants and animals in whole or any part thereof other than micro-organisms but including seeds, varieties and species and essentially biological processes for production or propagation of plants and animals.

CHAPTER III: APPLICATIONS FOR PATENTS
Section 6: Persons entitled to apply for patents
Section 7: Form of application
Section 8: Information and undertaking regarding foreign applications

CHAPTER IV: PUBLICATION AND EXAMINATION OF APPLICATIONS
Section 11A: Publication of application
Section 11B: Request for examination
Section 12: Examination of application

CHAPTER V: OPPOSITION PROCEEDINGS
Section 25: Opposition to grant of patent

CHAPTER X: PATENT OF ADDITION
Section 54: Patent of addition

SCHEDULE: FEES""",
    
    "biodiversity_act_2002.txt": """THE BIOLOGICAL DIVERSITY ACT, 2002

ARRANGEMENT OF SECTIONS

CHAPTER I: PRELIMINARY
Section 1: Short title, extent and commencement
Section 2: Definitions
- "biological resources" means plants, animals and micro-organisms or parts thereof, their genetic material and by-products
- "commercial utilization" means end uses of biological resources for commercial utilization such as drugs, industrial enzymes, food flavours, fragrance, cosmetics, emulsifiers, oleoresins, colours, extracts and genes used for improving crops and livestock through genetic intervention

CHAPTER II: REGULATION OF ACCESS TO BIOLOGICAL DIVERSITY
Section 3: Certain persons not to undertake biodiversity related activities without approval of National Biodiversity Authority
Section 4: Results of research not to be transferred to certain persons without approval
Section 5: Application for intellectual property rights not to be made without approval of National Biodiversity Authority
Section 6: Prior intimation to State Biodiversity Board for obtaining biological resource for certain purposes

CHAPTER III: NATIONAL BIODIVERSITY AUTHORITY
Section 8: Establishment of National Biodiversity Authority
Section 9: Composition of National Biodiversity Authority
Section 18: Functions and powers of National Biodiversity Authority
- Regulate access to biological resources
- Advise Central Government on conservation of biodiversity
- Advise State Governments on selection of biodiversity heritage sites
- Perform such other functions as may be necessary

CHAPTER IV: STATE BIODIVERSITY BOARDS
Section 22: Establishment of State Biodiversity Boards
Section 23: Functions of State Biodiversity Boards

CHAPTER V: LOCAL BIODIVERSITY FUNDS
Section 27: Local Biodiversity Funds

CHAPTER XII: PENALTIES
Section 55: Penalties
- Contravention of Section 3, 4, 5, or 6: imprisonment up to 5 years or fine up to 10 lakh rupees, or both
""",
    
    "wipo_ipr_basics.txt": """WIPO INTELLECTUAL PROPERTY HANDBOOK

CHAPTER 1: INTRODUCTION TO INTELLECTUAL PROPERTY
Intellectual property (IP) refers to creations of the mind: inventions, literary and artistic works, and symbols, names, images, and designs used in commerce.

Industrial Property includes:
- Patents for inventions
- Trademarks
- Industrial designs
- Geographical indications

Copyright includes:
- Literary and artistic works
- Rights related to copyright

CHAPTER 2: PATENTS
A patent is an exclusive right granted for an invention, which is a product or a process that provides a new way of doing something, or offers a new technical solution to a problem.

Requirements for patentability:
1. Novelty - The invention must be new
2. Inventive step - Non-obvious to a person skilled in the art
3. Industrial applicability - Capable of being made or used in industry

Patent Cooperation Treaty (PCT):
- International patent filing system
- Single application for multiple countries
- Administered by WIPO

CHAPTER 3: TRADITIONAL KNOWLEDGE AND GENETIC RESOURCES
Traditional knowledge (TK) refers to knowledge, know-how, skills and practices developed by indigenous and local communities.

Key issues:
- Protection of TK against misappropriation
- Benefit-sharing from commercialization
- Documentation and databases
- Prior informed consent

WIPO Intergovernmental Committee (IGC) on Intellectual Property and Genetic Resources, Traditional Knowledge and Folklore.
""",
    
    "neem_patent_case.txt": """NEEM PATENT CASE STUDY

Background:
In 1995, the US Department of Agriculture and W.R. Grace Company obtained a European Patent (EP 0436257) for a method of controlling fungi on plants using neem oil.

Indian Challenge:
India challenged this patent on grounds of:
1. Lack of novelty - Neem has been used in India for centuries as a fungicide
2. Traditional knowledge - The properties of neem are documented in ancient Indian texts
3. Biopiracy - Misappropriation of traditional knowledge

Legal Proceedings:
- 1995: Patent granted by European Patent Office (EPO)
- 2000: Legal opposition filed by India (RFSTE, IFOAM, Ms. Magda Aelvoet)
- 2005: EPO revoked the patent - lack of novelty and inventive step
- 2010: W.R. Grace appealed, EPO upheld revocation

Key Legal Principles Established:
1. Traditional knowledge documented in ancient texts constitutes prior art
2. Mere discovery of known properties is not patentable
3. Benefit-sharing required for commercialization of TK
4. India's Biodiversity Act requires prior approval for IP on biological resources

Relevance to Section 3(p) Patents Act:
The Neem case illustrates why Section 3(p) excludes traditional knowledge from patentability.
""",
}

def main():
    print("Creating sample documents for testing...")
    for filename, content in SAMPLE_DOCS.items():
        filepath = os.path.join(PDF_FOLDER, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Created {filename}")
    print("Done! Note: These are .txt files for testing. Replace with actual PDFs for production.")

if __name__ == "__main__":
    main()
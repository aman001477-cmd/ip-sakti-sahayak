from fpdf import FPDF
import os

PDF_FOLDER = "data/ayush_docs"
os.makedirs(PDF_FOLDER, exist_ok=True)

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 8, 'GOVERNMENT OF INDIA', 0, 1, 'C')
        self.set_font('Arial', 'B', 9)
        self.cell(0, 6, 'MINISTRY OF COMMERCE & INDUSTRY', 0, 1, 'C')
        self.cell(0, 6, 'CONTROLLER GENERAL OF PATENTS, DESIGNS & TRADE MARKS', 0, 1, 'C')
        self.ln(4)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

patents_act_content = """THE PATENTS ACT, 1970
(39 of 1970)
[As amended by the Patents (Amendment) Act, 2005]

ARRANGEMENT OF SECTIONS

CHAPTER I: PRELIMINARY
Section 1: Short title, extent and commencement
Section 2: Definitions
Section 3: What are not inventions

CHAPTER II: INVENTIONS NOT PATENTABLE
Section 3(a): An invention which is frivolous or which claims anything obviously contrary to well established natural laws
Section 3(b): An invention the primary or intended use or commercial exploitation of which could be contrary to public order or morality
Section 3(c): The mere discovery of a scientific principle or the formulation of an abstract theory
Section 3(d): The mere discovery of a new form of a known substance which does not result in the enhancement of the known efficacy of that substance
Section 3(e): A substance obtained by a mere admixture resulting only in the aggregation of the properties of the components thereof
Section 3(f): The mere arrangement or re-arrangement or duplication of known devices each functioning independently of one another in a known way
Section 3(g): Omitted
Section 3(h): A method of agriculture or horticulture
Section 3(i): Any process for the medicinal, surgical, curative, prophylactic diagnostic, therapeutic or other treatment of human beings or animals
Section 3(j): Plants and animals in whole or any part thereof other than micro-organisms but including seeds, varieties and species and essentially biological processes for production or propagation of plants and animals
Section 3(k): A mathematical or business method or a computer programme per se or algorithms
Section 3(l): A literary, dramatic, musical or artistic work or any other aesthetic creation whatsoever
Section 3(m): A mere scheme or rule or method of performing mental act or method of playing game
Section 3(n): A presentation of information
Section 3(o): Topography of integrated circuits
Section 3(p): An invention which in effect, is traditional knowledge or which is an aggregation or duplication of known properties of traditionally known component or components

CHAPTER III: APPLICATIONS FOR PATENTS
Section 6: Persons entitled to apply for patents
Section 7: Form of application
Section 8: Information and undertaking regarding foreign applications
Section 9: Provisional and complete specifications

CHAPTER IV: PUBLICATION AND EXAMINATION OF APPLICATIONS
Section 11A: Publication of application
Section 11B: Request for examination
Section 12: Examination of application

CHAPTER V: OPPOSITION PROCEEDINGS TO GRANT OF PATENTS
Section 25: Opposition to grant of patent

SCHEDULE: FEES"""

biodiversity_act_content = """THE BIOLOGICAL DIVERSITY ACT, 2002
(18 of 2003)
[As amended by the Biological Diversity (Amendment) Act, 2023]

ARRANGEMENT OF SECTIONS

CHAPTER I: PRELIMINARY
Section 1: Short title, extent and commencement
Section 2: Definitions
In this Act, unless the context otherwise requires:
(a) "biological diversity" means the variability among living organisms from all sources and the ecological complexes of which they are part
(b) "biological resources" means plants, animals and micro-organisms or parts thereof, their genetic material and by-products (excluding value added products)
(c) "commercial utilization" means end uses of biological resources for commercial utilization such as drugs, industrial enzymes, food flavours, fragrance, cosmetics, emulsifiers, oleoresins, colours, extracts and genes used for improving crops and livestock through genetic intervention

CHAPTER II: REGULATION OF ACCESS TO BIOLOGICAL DIVERSITY
Section 3: Certain persons not to undertake biodiversity related activities without approval of National Biodiversity Authority
Section 4: Results of research not to be transferred to certain persons without approval
Section 5: Application for intellectual property rights not to be made without approval of National Biodiversity Authority
Section 6: Prior intimation to State Biodiversity Board for obtaining biological resource for certain purposes

CHAPTER III: NATIONAL BIODIVERSITY AUTHORITY
Section 8: Establishment of National Biodiversity Authority
Section 9: Composition of National Biodiversity Authority
Section 18: Functions and powers of National Biodiversity Authority
(a) Regulate access to biological resources
(b) Advise Central Government on conservation of biodiversity
(c) Advise State Governments on selection of biodiversity heritage sites

CHAPTER IV: STATE BIODIVERSITY BOARDS
Section 22: Establishment of State Biodiversity Boards
Section 23: Functions of State Biodiversity Boards

CHAPTER XII: PENALTIES
Section 55: Penalties
Whoever contravenes any of the provisions of this Act shall be punishable with imprisonment for a term which may extend to five years, or with fine which may extend to ten lakh rupees, or with both."""

trips_content = """AGREEMENT ON TRADE-RELATED ASPECTS OF INTELLECTUAL PROPERTY RIGHTS (TRIPS)
PART I: GENERAL PROVISIONS AND BASIC PRINCIPLES
Article 1: Nature and Scope of Obligations
Article 2: Intellectual Property Conventions
Article 3: National Treatment
Article 4: Most-Favoured-Nation Treatment

PART II: STANDARDS CONCERNING THE AVAILABILITY, SCOPE AND USE OF INTELLECTUAL PROPERTY RIGHTS
Section 1: Copyright and Related Rights
Article 9: Relation to the Berne Convention
Article 10: Computer Programmes and Compilations of Data

Section 5: Patents
Article 27: Patentable Subject Matter
1. Subject to the provisions of paragraphs 2 and 3, patents shall be available for any inventions, whether products or processes, in all fields of technology, provided that they are new, involve an inventive step and are capable of industrial application.
2. Members may exclude from patentability inventions, the prevention within their territory of the commercial exploitation of which is necessary to protect ordre public or morality, including to protect human, animal or plant life or health or to avoid serious prejudice to the environment.
3. Members may also exclude from patentability:
(a) diagnostic, therapeutic and surgical methods for the treatment of humans or animals;
(b) plants and animals other than micro-organisms, and essentially biological processes for the production of plants or animals other than non-biological and microbiological processes.

Article 27.3(b): Protection of Plant Varieties
Members shall provide for the protection of plant varieties either by patents or by an effective sui generis system or by any combination thereof."""

def create_pdf(title, content, filename):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.multi_cell(0, 8, title, align='C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, content)
    pdf.output(os.path.join(PDF_FOLDER, filename))
    print(f"Created {filename}")

create_pdf("THE PATENTS ACT, 1970", patents_act_content, "indian_patents_act_1970.pdf")
create_pdf("THE BIOLOGICAL DIVERSITY ACT, 2002", biodiversity_act_content, "biodiversity_act_2002.pdf")
create_pdf("TRIPS AGREEMENT", trips_content, "trips_agreement.pdf")

print("All PDFs created with page numbers!")
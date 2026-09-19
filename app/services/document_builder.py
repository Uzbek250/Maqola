"""
Yakuniy maqolani Word (.docx) formatida, manbalar ro'yxati bilan tayyorlaydi.
"""
from docx import Document
from docx.shared import Pt
import io


def _format_reference(source: dict, index: int, style: str = "vancouver") -> str:
    authors = ", ".join(source.get("authors", [])[:6]) or "Author unknown"
    year = source.get("year", "n.d.")
    title = source.get("title", "")
    journal = source.get("journal", "")
    doi = source.get("doi", "")

    if style == "vancouver":
        ref = f"{index}. {authors}. {title}. {journal}. {year}."
        if doi:
            ref += f" doi:{doi}"
        return ref
    else:  # APA-ga yaqin
        ref = f"{authors} ({year}). {title}. {journal}."
        if doi:
            ref += f" https://doi.org/{doi}"
        return ref


def build_docx(title: str, article_text: str, sources: list[dict], citation_style: str = "vancouver") -> bytes:
    doc = Document()

    heading = doc.add_heading(title, level=1)

    for paragraph in article_text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Sarlavha qatorlarini (masalan "1. Kirish") qalin qilib ajratish
        if len(paragraph) < 60 and (paragraph[0].isdigit() or paragraph.isupper()):
            p = doc.add_heading(paragraph, level=2)
        else:
            p = doc.add_paragraph(paragraph)
            p.style.font.size = Pt(11)

    doc.add_page_break()
    doc.add_heading("References", level=2)
    for i, source in enumerate(sources, start=1):
        ref_text = _format_reference(source, i, citation_style)
        doc.add_paragraph(ref_text)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

"""
Yakuniy maqolani Word (.docx) formatida, manbalar ro'yxati bilan tayyorlaydi.
"""
import re
import io

from docx import Document
from docx.shared import Pt


def _clean_inline(text: str) -> str:
    """Markdown belgilarini olib tashlaydi: **qalin**, *kursiv*, `kod`."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    return text.replace("`", "").strip()


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

    doc.add_heading(_clean_inline(title), level=1)

    for raw in article_text.split("\n\n"):
        block = raw.strip()
        if not block:
            continue

        # Markdown sarlavha: "# ...", "## ..." -> Word sarlavhasi
        m = re.match(r"^(#{1,6})\s+(.*)$", block, re.S)
        if m:
            level = min(len(m.group(1)), 4)
            # Maqola ko'pincha "# Sarlavha" bilan boshlanadi — u hujjat sarlavhasini
            # takrorlaydi, shuning uchun tashlab ketiladi.
            heading_text = _clean_inline(m.group(2))
            if not (level == 1 and heading_text.lower() == _clean_inline(title).lower()):
                doc.add_heading(heading_text, level=level)
            continue

        # Qalin yozilgan "sarlavha" qatorlari (eski format): "1. Kirish"
        if len(block) < 60 and (block[0].isdigit() or block.isupper()):
            doc.add_heading(_clean_inline(block), level=2)
            continue

        # Markdown ro'yxati
        lines = [l for l in block.split("\n") if l.strip()]
        if lines and all(re.match(r"^\s*[-*•]\s+", l) for l in lines):
            for l in lines:
                doc.add_paragraph(_clean_inline(re.sub(r"^\s*[-*•]\s+", "", l)),
                                  style="List Bullet")
            continue

        p = doc.add_paragraph(_clean_inline(block))
        p.style.font.size = Pt(11)

    doc.add_page_break()
    doc.add_heading("References", level=2)
    for i, source in enumerate(sources, start=1):
        ref_text = _format_reference(source, i, citation_style)
        doc.add_paragraph(ref_text)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

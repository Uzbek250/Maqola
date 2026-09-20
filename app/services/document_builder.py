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


def _clean_journal(journal: str) -> str:
    """
    PubMed jurnal nomini tozalaydi:
      - "International journal of obesity (2005)" -> "International Journal of Obesity"
        (qavsdagi yil nashr nomini ajratish uchun qo'shilgan, maqola yiliga aloqasi yo'q —
         o'quvchi uni nashr yili deb o'qishi mumkin)
      - nuqta/bo'shliq ortiqchaligini tozalaydi (title oxirida "." bo'lsa ".." bo'lib qoladi)
    """
    j = re.sub(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$", "", (journal or "").strip())
    return re.sub(r"\s+", " ", j).strip(" .")


def _clean_sentence(s: str) -> str:
    """Ortiqcha nuqta va bo'shliqlarni tozalaydi: 'Title.. 2024' -> 'Title. 2024'."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"\.\s*\.", ".", s)          # ".." -> "."
    return s.strip()


def _format_reference(source: dict, index: int, style: str = "vancouver") -> str:
    authors = ", ".join(source.get("authors", [])[:6]) or "Author unknown"
    year = source.get("year", "n.d.")
    title = _clean_sentence(source.get("title", ""))
    journal = _clean_journal(source.get("journal", ""))
    doi = (source.get("doi") or "").strip()

    if style == "vancouver":
        ref = f"{index}. {authors}. {title}. {journal}. {year}."
        if doi:
            ref += f" doi:{doi}"
        return _clean_sentence(ref)
    else:  # APA-ga yaqin
        ref = f"{authors} ({year}). {title}. {journal}."
        if doi:
            ref += f" https://doi.org/{doi}"
        return _clean_sentence(ref)


def build_docx(title: str, article_text: str, sources: list[dict], citation_style: str = "vancouver") -> bytes:
    doc = Document()

    # Maqolaning O'Z H1 sarlavhasi bo'lsa — hujjat sarlavhasi sifatida shuni ishlatamiz.
    # Sabab: foydalanuvchi kiritgan mavzu bir tilda, maqola matni boshqa tilda bo'lishi
    # mumkin (masalan o'zbekcha mavzu + inglizcha maqola) — natijada aralash hujjat chiqardi.
    blocks = [b.strip() for b in article_text.split("\n\n") if b.strip()]
    doc_title = _clean_inline(title)
    body_blocks = blocks
    if blocks:
        m0 = re.match(r"^#\s+(.*)$", blocks[0], re.S)
        if m0:
            h1 = _clean_inline(m0.group(1))
            if h1:
                doc_title = h1
                body_blocks = blocks[1:]

    doc.add_heading(doc_title, level=1)

    for block in body_blocks:
        # Markdown sarlavha: "# ...", "## ..." -> Word sarlavhasi
        m = re.match(r"^(#{1,6})\s+(.*)$", block, re.S)
        if m:
            level = min(len(m.group(1)), 4)
            doc.add_heading(_clean_inline(m.group(2)), level=level)
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

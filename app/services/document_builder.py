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


AI_DISCLOSURE_TEXT = [
    "This manuscript was prepared with the assistance of artificial intelligence "
    "tools. The authors used [TOOL NAME, version] ([MANUFACTURER]) on [DATE(S)] to "
    "assist with drafting and structuring this narrative review and with language "
    "editing. The authors have reviewed and edited all AI-assisted content and take "
    "full responsibility for the accuracy, integrity, and originality of the entire "
    "manuscript. No AI tool is listed as an author, and no AI tool was used to "
    "generate or format the reference list: all citations were retrieved from "
    "bibliographic databases (PubMed, Semantic Scholar) and their digital object "
    "identifiers (DOIs) were verified against Crossref. This statement is provided "
    "in accordance with ICMJE and COPE guidance on the use of AI in publishing.",

    "Note to the author: replace the bracketed fields above with the actual tool "
    "name, version, manufacturer and dates of use, and report the same information "
    "in the cover letter at submission. Check your target journal's instructions for "
    "authors, as a small number of journals prohibit AI-assisted drafting entirely. "
    "Delete this note before submission.",
]


def build_docx(title: str, article_text: str, sources: list[dict],
               citation_style: str = "vancouver", ai_disclosure: bool = False) -> bytes:
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

    # ICMJE/COPE talabi: AI ishlatilgani ochiq deklaratsiya qilinishi SHART.
    # Deklaratsiya qilinmasa — maqola rad etilishi yoki chop etilgandan keyin
    # qaytarib olinishi (retraction) mumkin. Shuning uchun standart holatda qo'shiladi.
    if ai_disclosure:
        doc.add_heading("Acknowledgment: Use of Artificial Intelligence", level=2)
        for para in AI_DISCLOSURE_TEXT:
            note = doc.add_paragraph(para)
            note.style.font.size = Pt(10)

    doc.add_page_break()
    doc.add_heading("References", level=2)
    for i, source in enumerate(sources, start=1):
        ref_text = _format_reference(source, i, citation_style)
        doc.add_paragraph(ref_text)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# O'zbek jurnali shabloni: UDK + uch tilli sarlavha/annotatsiya + muallif bloki
# ---------------------------------------------------------------------------

def _add_body(doc, article_text: str) -> None:
    """Maqola matnini Word'ga joylaydi (## -> sarlavha, qator -> paragraf)."""
    for block in article_text.split("\n"):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", block)
        if m:
            doc.add_heading(_clean_inline(m.group(2)), level=min(len(m.group(1)), 3))
            continue
        # Jadval qatori (| bilan boshlanadigan) — oddiy matn sifatida
        p = doc.add_paragraph(_clean_inline(block))
        p.style.font.size = Pt(11)


def build_uz_docx(article_text: str, sources: list[dict], tri: dict,
                  citation_style: str = "vancouver", udk: str = "",
                  author: dict | None = None, ai_disclosure: bool = False) -> bytes:
    """
    O'zbek jurnali talab qiladigan to'liq qo'lyozma:
      UDK -> sarlavha (3 tilda) -> muallif bloki -> 3 tildagi annotatsiya va
      kalit so'zlar -> asosiy matn -> adabiyotlar ro'yxati.

    `tri` — uz_template.build_trilingual() natijasi.
    `author` — {name, affiliation, city, country, email, orcid} (bo'sh bo'lsa joy egallovchi).
    """
    doc = Document()
    tri = tri or {}
    author = author or {}
    titles = tri.get("title") or {}
    abstracts = tri.get("abstract") or {}
    keywords = tri.get("keywords") or {}

    # --- UDK
    if udk:
        p = doc.add_paragraph(f"UDK: {udk}")
        p.style.font.size = Pt(11)
        p.runs[0].bold = True

    # --- Sarlavha 3 tilda
    for key in ("uz", "ru", "en"):
        t = (titles.get(key) or "").strip()
        if not t:
            continue
        h = doc.add_paragraph(t)
        h.runs[0].bold = True
        h.runs[0].font.size = Pt(14 if key == "uz" else 12)
        h.alignment = 1  # markazga

    doc.add_paragraph()

    # --- Muallif bloki
    name = author.get("name") or "[MUALLIF F.I.SH.]"
    doc.add_paragraph(name).runs[0].bold = True
    for line in (author.get("affiliation"), author.get("city"), author.get("email")):
        if line:
            doc.add_paragraph(line)
    if author.get("orcid"):
        doc.add_paragraph(f"ORCID: {author['orcid']}")

    doc.add_paragraph()

    # --- Uch tilli annotatsiya
    labels = {
        "uz": ("Annotatsiya.", "Kalit soʻzlar"),
        "ru": ("Аннотация.", "Ключевые слова"),
        "en": ("Abstract.", "Keywords"),
    }
    for key in ("uz", "ru", "en"):
        txt = (abstracts.get(key) or "").strip()
        if not txt:
            continue
        head, kw_label = labels[key]
        p = doc.add_paragraph()
        r = p.add_run(f"{head} ")
        r.bold = True
        p.add_run(txt).font.size = Pt(10)
        kw = keywords.get(key) or []
        if kw:
            kp = doc.add_paragraph()
            kr = kp.add_run(f"{kw_label}: ")
            kr.bold = True
            kp.add_run(", ".join(str(k) for k in kw)).font.size = Pt(10)

    doc.add_page_break()

    # --- Asosiy matn
    _add_body(doc, article_text)

    # --- AI deklaratsiyasi (standart: o'chiq)
    if ai_disclosure:
        doc.add_heading("Acknowledgment: Use of Artificial Intelligence", level=2)
        for para in AI_DISCLOSURE_TEXT:
            doc.add_paragraph(para).style.font.size = Pt(10)

    # --- Adabiyotlar
    doc.add_page_break()
    doc.add_heading("FOYDALANILGAN ADABIYOTLAR ROʻYXATI", level=2)
    for i, source in enumerate(sources, start=1):
        doc.add_paragraph(_format_reference(source, i, citation_style))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

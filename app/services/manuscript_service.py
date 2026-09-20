"""
Qo'lyozma paketi — zanjirning OXIRINI yopadi.

Hozirgacha ilova faqat maqola tanasini berardi. Jurnalga topshirish uchun esa
yana bir qancha fayl kerak bo'ladi: structured abstract, kalit so'zlar, ma'lumot
ajratish jadvali, title page, bayonotlar, cover letter, referens menejeri fayli.

Bu modul shularni yasaydi. Arxitektura qoidasi (ROADMAP.md):
  - LLM ko'rmagan raqamni YOZMAYDI — "Not reported" / "NR" deb qo'yadi.
  - BibTeX/RIS KOD tomonidan yasaladi (LLM emas), shunda referens to'qilmaydi.
"""
import io
import json
import logging
import re
import zipfile

from app.services import gpt_service
from app.services.document_builder import _clean_journal

logger = logging.getLogger("app.services.manuscript")


# ---------------------------------------------------------------- JSON yordamchi

def _parse_json(text: str) -> dict:
    """LLM javobidan JSON ajratib oladi (```json to'siqlari va ortiqcha matn bilan ham)."""
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        t = t[start:end + 1]
    try:
        return json.loads(t)
    except (ValueError, TypeError) as e:
        logger.warning("Paket JSON'ini o'qib bo'lmadi: %s | matn: %s", e, text[:200])
        return {}


# ------------------------------------------------------- LLM: paket metama'lumoti

_PACKAGE_SYSTEM = """You are a medical journal manuscript editor preparing a submission package.
You work ONLY from the provided abstract texts. If a value is not stated in the sources, write "NR"
(not reported) — NEVER guess or invent a number, sample size, or finding.

Return ONLY valid JSON (no markdown fences), exactly this shape:
{
  "structured_abstract": {"background": "...", "methods": "...", "results": "...", "conclusions": "..."},
  "keywords": ["...", "..."],
  "highlights": ["...", "..."],
  "study_table": [
    {"authors": "First author et al.", "year": 2024, "design": "RCT|cohort|case report|review|NR",
     "n": "the sample size exactly as reported, or NR",
     "population": "who was studied, or NR",
     "key_finding": "one sentence, only what the source states"}
  ],
  "cover_letter": "3 short paragraphs: what the manuscript is, why it matters, and the standard
                   declarations (not published elsewhere, no competing interests). Use [TARGET JOURNAL]
                   as a placeholder for the journal name."
}
Rules:
- structured_abstract must be 200-280 words total, in the manuscript language.
- keywords: 5-6 terms, MeSH-like where possible.
- highlights: 3-5 bullets, max 85 characters each.
- study_table: one row per numbered source, in the SAME ORDER as given.
- cover_letter: 200-280 words.
- Write everything in the requested language."""


async def build_package_meta(topic: str, article_text: str, sources: list[dict],
                             language: str = "en", journal_profile: dict | None = None) -> dict:
    """
    Bitta LLM chaqiruvida paket uchun hamma matnni yasaydi (xarajatni kamaytirish uchun
    bir necha kichik chaqiruv o'rniga bitta katta chaqiruv).

    `journal_profile` berilsa — abstract va kalit so'zlar JURNAL LIMITIGA mos yasaladi.
    Bu muhim: aks holda ilova o'zi yaratgan matn o'zi tekshiradigan talabdan o'tmaydi
    (sinovda Heliyon uchun abstract 271 so'z chiqdi, limit 250 edi).
    """
    lang_name = {"uz": "Uzbek (Latin script)", "en": "English", "ru": "Russian"}.get(language, "English")

    # Jurnal limitlari — abstract va kalit so'zlar uchun aniq chegara
    jp = journal_profile or {}
    limits = []
    ab_limit = jp.get("abstract_word_limit")
    if ab_limit:
        limits.append(f"- The structured abstract MUST NOT exceed {ab_limit} words "
                      f"(aim for {int(ab_limit * 0.9)} words).")
    ab_chars = jp.get("abstract_char_limit")
    if ab_chars:
        limits.append(f"- The abstract MUST NOT exceed {ab_chars} characters.")
    kmin, kmax = jp.get("keywords_min"), jp.get("keywords_max")
    if kmin or kmax:
        limits.append(f"- Provide exactly {kmin or 3}-{kmax or 10} keywords.")
    if jp.get("abstract_type") == "unstructured":
        limits.append("- The target journal wants an UNSTRUCTURED abstract: return the abstract "
                      "as a single 'text' field (still keep the JSON keys, but content flows as "
                      "one paragraph without subheadings).")
    jp_block = ("\nJOURNAL LIMITS (obey exactly):\n" + "\n".join(limits)) if limits else ""

    src_block = []
    for i, s in enumerate(sources, start=1):
        auth = ", ".join(s.get("authors", [])[:3]) or "Unknown"
        abstract = (s.get("abstract") or "").strip()[:2500] or "(abstract not available)"
        src_block.append(
            f"[{i}] {auth} ({s.get('year', 'n.d.')}). {s.get('title', '')}\n"
            f"    Journal: {s.get('journal', '')}\n"
            f"    Abstract: {abstract}"
        )

    user_prompt = (
        f"Manuscript topic: {topic}\n"
        f"Language for all output: {lang_name}\n"
        f"{jp_block}\n\n"
        f"The manuscript body (for context only):\n{article_text[:6000]}\n\n"
        f"SOURCES ({len(sources)}):\n" + "\n\n".join(src_block) +
        "\n\nReturn the JSON described in the system prompt."
    )

    try:
        raw = await gpt_service._call_gpt(_PACKAGE_SYSTEM, user_prompt, 0.3, 4000)
        data = _parse_json(raw)
    except Exception as e:
        logger.exception("Paket metama'lumotini yasab bo'lmadi: %s", e)
        data = {}

    # Har bir maydon mavjudligini kafolatlaymiz — paket har qanday holatda yig'ilsin
    return {
        "structured_abstract": data.get("structured_abstract") or {},
        "keywords": data.get("keywords") or [],
        "highlights": data.get("highlights") or [],
        "study_table": data.get("study_table") or [],
        "cover_letter": data.get("cover_letter") or "",
    }


# ------------------------------------------------- referens menejeri fayllari (kod)

def _cite_key(source: dict, index: int) -> str:
    authors = source.get("authors") or []
    surname = "anon"
    if authors:
        surname = re.sub(r"[^A-Za-z]", "", authors[0].split(",")[0].split()[-1] or "anon")
    year = re.sub(r"\D", "", str(source.get("year") or "")) or "nd"
    return f"{surname.lower()}{year}_{index}"


def _bib_escape(s: str | None) -> str:
    return re.sub(r"[{}]", "", str(s or "")).replace("&", r"\&")


def _clean_title(s: str | None) -> str:
    """Sarlavhadagi oxirgi nuqtani olib tashlaydi — BibTeX'da keraksiz."""
    return _bib_escape(s).strip().rstrip(".")


def build_bibtex(sources: list[dict]) -> str:
    """
    Crossref/PubMed metadatasidan BibTeX yasaydi. Ataylab KOD tomonidan —
    LLM referens yasasa, mavjud bo'lmagan ishlarni to'qib qo'yishi mumkin.
    """
    entries = []
    for i, s in enumerate(sources, start=1):
        authors = " and ".join(s.get("authors") or []) or "Unknown"
        fields = [
            ("author", authors),
            ("title", _clean_title(s.get("title"))),
            ("journal", _bib_escape(_clean_journal(s.get("journal") or ""))),
            ("year", str(s.get("year") or "")),
            ("volume", str(s.get("volume") or "")),
            ("number", str(s.get("issue") or "")),
            ("pages", str(s.get("pages") or "")),
            ("doi", str(s.get("doi") or "")),
            ("url", str(s.get("url") or "")),
        ]
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
        entries.append(f"@article{{{_cite_key(s, i)},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


def build_ris(sources: list[dict]) -> str:
    """RIS — EndNote/Zotero/Mendeley import qiladi."""
    out = []
    for s in sources:
        lines = ["TY  - JOUR"]
        for a in (s.get("authors") or []):
            lines.append(f"AU  - {a}")
        if s.get("title"):
            lines.append(f"TI  - {_clean_title(s['title'])}")
        if s.get("journal"):
            lines.append(f"JO  - {_clean_journal(s['journal'])}")
        if s.get("year"):
            lines.append(f"PY  - {s['year']}")
        if s.get("volume"):
            lines.append(f"VL  - {s['volume']}")
        if s.get("issue"):
            lines.append(f"IS  - {s['issue']}")
        if s.get("pages"):
            lines.append(f"SP  - {s['pages']}")
        if s.get("doi"):
            lines.append(f"DO  - {s['doi']}")
        if s.get("url"):
            lines.append(f"UR  - {s['url']}")
        lines.append("ER  - ")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


# ------------------------------------------------------------------ bayonotlar

STATEMENT_TEMPLATES = [
    ("Author Contributions",
     "[INITIALS] conceived the study and designed the review. [INITIALS] acquired and "
     "screened the literature. [INITIALS] drafted the manuscript. [INITIALS] critically "
     "revised it for important intellectual content. All authors approved the final "
     "version and agree to be accountable for all aspects of the work."),
    ("Funding",
     "This research received no specific grant from any funding agency in the public, "
     "commercial, or not-for-profit sectors. [If funded, replace with: This work was "
     "supported by <FUNDER> under grant number <GRANT ID>.]"),
    ("Conflict of Interest",
     "The authors declare that they have no known competing financial interests or "
     "personal relationships that could have appeared to influence the work reported "
     "in this paper. [Disclose any relationship or state 'none'.]"),
    ("Data Availability",
     "No new data were created or analysed in this study. All data analysed are "
     "published and are cited in the reference list."),
    ("Ethics Statement",
     "Ethical approval was not required for this narrative review, as it involved no "
     "human participants or animal subjects and analysed previously published data."),
    ("Title Page (fill in before submission)",
     "Title: <MANUSCRIPT TITLE>\n"
     "Authors: [FULL NAME, highest degree]1,2, [FULL NAME, highest degree]1\n"
     "Affiliations: 1<Department, Institution, City, Country>. "
     "2<Department, Institution, City, City, Country>.\n"
     "Corresponding author: [FULL NAME], <full postal address>, "
     "email: [EMAIL], ORCID: [0000-0000-0000-0000]\n"
     "Word count (main text): <N>    Tables: 1    Figures: 0    References: <N>"),
]


def build_checklist(word_count: int, source_count: int, meta: dict) -> str:
    """
    Inson qo'lda tekshirishi kerak bo'lgan narsalar ro'yxati.
    Bu ilovaning emas, muallifning javobgarligi — aniq yozilgan bo'lishi kerak.
    """
    n_nr = sum(1 for r in meta.get("study_table", [])
               if str(r.get("n", "")).strip().upper() in ("NR", "N/A", "", "NOT REPORTED"))
    return f"""# Tekshirish ro'yxati (topshirishdan oldin qo'lda bajariladi)

Ilova ishning ~90% ini qildi. Quyidagilar **majburiy** — muallif javobgar.

## 1. Raqamlar va faktlar (eng muhim)
- [ ] Maqoladagi har bir raqam, `p` qiymati, ishonch oralig'i asl manbada aynan shundaymi?
- [ ] Ma'lumot ajratish jadvalidagi `n` (namuna soni) har bir manbaning abstraktidagi
      raqamga mos keladimi? {n_nr} qatorda "NR" (manbada ko'rsatilmagan) turibdi —
      to'liq matndan topib to'ldiring.
- [ ] Sarlavha va xulosa dalilga mos keladimi (bitta kichik tadqiqotdan umumiy xulosa
      chiqarilmaganmi)?

## 2. Manbalar
- [ ] Har bir havola to'liq matnini o'qidingizmi? ({source_count} ta manba)
- [ ] Iqtibos qilingan joyda manba haqiqatan shuni aytadimi?
- [ ] Hech bir muhim manba tushib qolmaganmi (qo'lda yana bir qidiruv qiling)?
- [ ] `references.bib` / `references.ris` ni Zotero/EndNote'ga import qilib,
      jurnal uslubida qayta formatlang.

## 3. Muallif ma'lumotlari
- [ ] `statements.md` dagi barcha `[QAVS]` joylar to'ldirildi.
- [ ] Funding, Conflict of Interest, Ethics — haqiqiy holatga moslashtirildi.
- [ ] ORCID, affiliation, corresponding author to'g'ri.

## 4. Jurnal talablari
- [ ] So'z soni: {word_count} (jurnal limitiga sig'adi?)
- [ ] Abstract turi (structured/unstructured) jurnal talabiga mosmi?
- [ ] Kalit so'zlar soni va turi to'g'rimi?
- [ ] Jurnal AI/LLM siyosatini o'qing — ba'zi jurnallar cheklaydi.

## 5. Topshirish
- [ ] Cover letter jurnallning haqiqiy nomiga moslashtirildi (`[TARGET JOURNAL]` almashtirildi).
- [ ] Barcha fayllar jurnal talab qilgan formatda.
"""


# ------------------------------------------------------------------- ZIP paket

def build_zip(article_markdown: str, sources: list[dict], meta: dict,
              docx_bytes: bytes, checklist: str, word_count: int,
              compliance_markdown: str = "") -> bytes:
    """Topshirishga kerak bo'lgan hamma faylni bitta ZIP'ga yig'adi."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manuscript.docx", docx_bytes)
        z.writestr("manuscript.md", article_markdown)
        z.writestr("references.bib", build_bibtex(sources))
        z.writestr("references.ris", build_ris(sources))
        z.writestr("statements.md", "\n\n".join(f"## {t}\n\n{b}" for t, b in STATEMENT_TEMPLATES))
        z.writestr("cover_letter.md", meta.get("cover_letter") or "[cover letter not generated]")
        if compliance_markdown:
            z.writestr("COMPLIANCE.md", compliance_markdown)

        front = {
            "structured_abstract": meta.get("structured_abstract"),
            "keywords": meta.get("keywords"),
            "highlights": meta.get("highlights"),
            "word_count": word_count,
            "source_count": len(sources),
        }
        z.writestr("front_matter.json", json.dumps(front, ensure_ascii=False, indent=2))
        z.writestr("study_table.json", json.dumps(meta.get("study_table") or [],
                                                  ensure_ascii=False, indent=2))
        z.writestr("CHECKLIST.md", checklist)
        z.writestr("README.txt",
                   "Maqola qo'lyozma paketi\n"
                   "=====================\n\n"
                   "manuscript.docx  — asosiy qo'lyozma (jurnalga yuboriladi)\n"
                   "references.bib   — Zotero/EndNote uchun (jurnal uslubida formatlang)\n"
                   "references.ris   — EndNote/Mendeley uchun\n"
                   "statements.md    — title page, bayonotlar (qavslarni to'ldiring)\n"
                   "cover_letter.md  — cover letter (jurnal nomini almashtiring)\n"
                   "front_matter.json— abstract, kalit so'zlar, highlights\n"
                   "study_table.json — ma'lumot ajratish jadvali\n"
                   "COMPLIANCE.md    — jurnal talablariga muvofiqlik tekshiruvi\n"
                   "CHECKLIST.md     — QO'LDA tekshirish ro'yxati (majburiy)\n\n"
                   f"Manbalar: {len(sources)} | So'z: {word_count}\n")
    return buf.getvalue()

"""
O'zbek jurnali shabloni — uch tilli qo'lyozma qismi.

Nega kerak: mahalliy jurnallar (va ko'plab xalqaro) maqolani "faqat matn" emas,
balki tayyor qo'lyozma ko'rinishida talab qiladi:
    UDK
    Sarlavha — 3 tilda (o'zbek / rus / ingliz)
    Muallif, muassasa, email, ORCID
    Annotatsiya / Аннотация / Abstract + Kalit so'zlar / Ключевые слова / Keywords
    Asosiy matn (KIRISH, METODOLOGIYA, NATIJALAR VA MUHOKAMA, XULOSA)
    Foydalanilgan adabiyotlar

Bu modul shu qismlarni yasaydi. Asosiy matnni esa gpt_service yozadi.
"""
import json
import logging
import re

from app.services import gpt_service

logger = logging.getLogger("app.services.uz_template")

# UDK ning umumiy sinflari — model faqat shu doiradan tanlaydi, o'zi to'qimaydi.
# (Aniq raqamni muallif jurnal bilan tasdiqlashi kerak — shuning uchun hisobotда
#  "tasdiqlang" deb belgilanadi.)
_UDK_SYSTEM = """You are a librarian assigning a UDC (UDK) classification code.
Return ONLY JSON: {"udk": "37.013", "reason": "why this class fits, one short sentence"}.
Pick from these common classes ONLY (do not invent a code outside this list):
  001 Science and knowledge in general
  004 Computer science
  1 Philosophy. Psychology
  2 Religion. Theology
  3 Social sciences
  37 Education. Pedagogy  (37.013 general pedagogy; 37.013.74 comparative pedagogy)
  39 Ethnography. Folklore
  81 Linguistics. Languages
  82 Literature. Literary criticism
  93/94 History (94(575.1) History of Uzbekistan)
  61 Medicine
  33 Economics
If the topic is a literary/historical study, prefer 82 or 94 with the national qualifier.
Answer with the code only in the "udk" field."""

_TRILINGUAL_SYSTEM = """You are a bilingual academic editor preparing the front matter of a
manuscript for an Uzbek journal. You produce the title, abstract and keywords in THREE
languages: Uzbek (Latin script), Russian, and English.

Return ONLY valid JSON, exactly this shape:
{
  "title":    {"uz": "...", "ru": "...", "en": "..."},
  "abstract": {"uz": "...", "ru": "...", "en": "..."},
  "keywords": {"uz": ["...", "..."], "ru": ["...", "..."], "en": ["...", "..."]}
}

Rules:
- The three titles must be faithful translations of the same title, not different titles.
- Each abstract: 150-220 words, a single paragraph, no subheadings. Write it as a
  self-contained summary of the manuscript: what was studied, how, what was found, what it means.
- Each abstract must correspond to the ACTUAL manuscript text you are given. Do not add
  results, numbers, sample sizes or findings that are not present in the text. If the
  manuscript contains no empirical data, do not invent any — describe what the work does.
- Keywords: 5-7 per language, the same concepts in all three languages, ordered the same way.
- Uzbek must use Latin script (oʻ, gʻ), Russian in Cyrillic, English in English."""


def _parse_json(text: str) -> dict:
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    s, e = t.find("{"), t.rfind("}")
    if s >= 0 and e > s:
        t = t[s:e + 1]
    try:
        return json.loads(t)
    except (ValueError, TypeError) as ex:
        logger.warning("Uch tilli JSON'ni o'qib bo'lmadi: %s | %s", ex, text[:200])
        return {}


async def build_udk(topic: str, article_text: str) -> dict:
    """Mavzuga mos UDK sinfini taklif qiladi (aniq raqamni muallif tasdiqlaydi)."""
    prompt = (f"Topic: {topic}\n\nManuscript (first 2500 characters):\n{article_text[:2500]}\n\n"
              f"Return the JSON.")
    try:
        raw = await gpt_service._call_gpt(_UDK_SYSTEM, prompt, 0.1, 200)
        data = _parse_json(raw)
        code = str(data.get("udk") or "").strip()
        return {"udk": code, "reason": str(data.get("reason") or "").strip()}
    except Exception as e:
        logger.warning("UDK aniqlamadi: %s", e)
        return {"udk": "", "reason": ""}


async def build_trilingual(topic: str, article_text: str, language: str = "uz") -> dict:
    """
    Sarlavha, annotatsiya va kalit so'zlarni 3 tilda yasaydi.
    Xato bo'lsa bo'sh tuzilma qaytadi — qo'lyozma shunga qaramay yig'iladi.
    """
    prompt = (
        f"Manuscript topic (as supplied by the author): {topic}\n"
        f"Main language of the manuscript: {language}\n\n"
        f"MANUSCRIPT TEXT:\n{article_text[:9000]}\n\n"
        f"Return the JSON described in the system prompt."
    )
    try:
        raw = await gpt_service._call_gpt(_TRILINGUAL_SYSTEM, prompt, 0.3, 3000)
        data = _parse_json(raw)
    except Exception as e:
        logger.exception("Uch tilli qismni yasab bo'lmadi: %s", e)
        data = {}

    def _langs(field: str) -> dict:
        v = data.get(field) or {}
        return {k: (v.get(k) or ([] if field == "keywords" else "")) for k in ("uz", "ru", "en")}

    return {
        "title": _langs("title"),
        "abstract": _langs("abstract"),
        "keywords": _langs("keywords"),
    }


def word_counts(meta: dict) -> dict:
    """Nazorat uchun: har bir tildagi annotatsiya so'z soni."""
    out = {}
    for lang, txt in (meta.get("abstract") or {}).items():
        out[lang] = len(str(txt).split())
    return out

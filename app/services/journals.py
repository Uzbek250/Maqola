"""
Jurnal profillari (Bosqich 2).

Har bir jurnal o'z qoidalariga ega: so'z limiti, abstract turi, havola uslubi,
majburiy bo'limlar. Ilova maqsadli jurnalni bilib yozsa, qo'lyozma topshirishga
mos keladi va muvofiqlik tekshiruvi mazmunli bo'ladi.

MUHIM: bu yerdagi qiymatlar jurnallarning RASMIY "author guidelines" sahifalaridan
olingan va `source_url` da ko'rsatilgan. Jurnal qoidalari o'zgarib turadi —
topshirishdan oldin har doim manbani tekshiring.

Qiymat `None` bo'lsa — tekshiruv o'sha band bo'yicha o'tkazib yuboriladi
("aniqlanmagan"), noto'g'ri xulosa chiqarilmaydi.
"""

GENERIC: dict = {
    "key": "generic",
    "name": "Umumiy (aniq jurnal tanlanmagan)",
    "field": "medical",                    # medical | general | law | pedagogy | ...
    "word_limit_main_text": None,
    "abstract_type": None,
    "abstract_sections": [],
    "abstract_word_limit": None,
    "reference_style": "vancouver",
    "max_references": None,
    "required_sections": ["Introduction", "Methods", "Discussion", "Conclusion"],
    "keywords_min": None,
    "keywords_max": None,
    "accepts_reviews": None,
    "apc_usd": None,
    "ai_policy": None,
    "source_url": None,
    # Indekslash va IF haqiqiyligi — mijozni himoya qiluvchi maydonlar.
    # `indexing=None`  -> tekshirilmagan (tekshiruv o'tkazib yuboriladi)
    # `indexing=[]`    -> tekshirildi va hech qanday rasmiy indeksda YO'Q (❌)
    "indexing": None,
    "claimed_if": None,
    "if_verified": None,                   # True (JCR/Scopus) | False (faqat jurnal o'zi) | None
    "predatory_signals": [],
    "notes": "Standart profil: faqat umumiy tuzilma tekshiriladi.",
}

# --- Jurnal profillari -------------------------------------------------------
# Kalit: jurnal identifikatori. Qiymatlar rasmiy author guidelines'dan
# (2026-09-20 da tekshirilgan). Har birida `source_url` va izoh bor.
#
# MUHIM TOPILMA: 8 jurnaldan 3 tasi narrative review QABUL QILMAYDI
# (Medicine Baltimore — 2025-01-14 dan yopilgan; PLOS ONE; BMJ Open).
# Bu `accepts_reviews: False` bilan belgilanadi va muvofiqlik hisobotida
# qizil ❌ bo'lib chiqadi.
#
# `word_limit_main_text: None` — jurnal limit QO'YMAGAN (tekshirilmagan emas).
# `apc_usd: None` — jurnal USD narx e'lon qilmagan (CHF/GBP da beriladi);
# haqiqiy summa `apc_note` da.

JOURNALS: dict[str, dict] = {}


def _reg(p: dict) -> None:
    JOURNALS[p["key"]] = p


_reg({
    "key": "cureus",
    "name": "Cureus",
    "word_limit_main_text": None,          # jurnal limit qo'ymaydi
    "abstract_type": "unstructured",
    "abstract_sections": [],
    "abstract_word_limit": None,           # limit 3500 BELGI, so'z emas
    "abstract_char_limit": 3500,
    "reference_style": "Cureus house style (raqamli, kvadrat qavsda, DOI majburiy)",
    "max_references": None,                # sharhlarga limit qo'yilmagan
    "required_sections": ["Introduction", "Conclusions"],
    "structure_note": "Abstract, Introduction and Background, Review, Conclusions, References",
    "keywords_min": 5,
    "keywords_max": 10,
    "accepts_reviews": True,
    "apc_usd": None,
    "apc_note": "Universal APC yo'q, LEKIN har bir sharh maqolasi pullik 'Preferred Editing' "
                "talab qiladi (o'rtacha ~$400, maksimum $1,400).",
    "ai_policy": "LLM muallif bo'la olmaydi. LLM ishlatilgani Methods bo'limida (Methods bo'lmasa "
                 "Acknowledgements'da) hujjatlashtirilishi shart. Faqat til tahriri (grammatika, "
                 "uslub) oshkor qilinmasa ham bo'ladi, lekin matn uchun inson javobgar.",
    "source_url": "https://www.cureus.com/author_guide/overview/accepted-article-types",
    "notes": "Narrative review aniq qabul qilinadi. Abstract tuzilmasi faqat original maqolalarda "
             "bo'ladi. Manba: Cureus author guide + references + AI siyosati sahifalari.",
})

_reg({
    "key": "frontiers_medicine",
    "name": "Frontiers in Medicine",
    "word_limit_main_text": 12000,         # Review turi uchun
    "abstract_type": "structured",
    "abstract_sections": [],
    "abstract_word_limit": 350,
    "reference_style": "Vancouver (raqamli, qavsda)",
    "max_references": None,
    "required_sections": ["Introduction", "Discussion"],
    "structure_note": "Abstract, Introduction, mavzuga oid bo'limlar, Discussion",
    "keywords_min": 5,
    "keywords_max": 8,
    "accepts_reviews": True,
    "apc_usd": None,
    "apc_note": "CHF 3,150 (Review — A-type); USD e'lon qilinmagan (~$3,825).",
    "ai_policy": "Generativ AI muallif bo'la olmaydi. AI bilan yaratilgan/tahrir qilingan har qanday "
                 "matn yoki rasm Acknowledgements'da oshkor qilinishi shart (vosita nomi, versiyasi, "
                 "modeli). Muallif faktlar va havolalarning to'g'riligiga javobgar.",
    "source_url": "https://www.frontiersin.org/journals/medicine/for-authors/article-types",
    "notes": "Review turi maksimum 12,000 so'z. Abstract 350 so'z (jurnalning article-type "
             "jadvalidan). Abstract uchun majburiy kichik sarlavhalar e'lon qilinmagan.",
})

_reg({
    "key": "heliyon",
    "name": "Heliyon",
    "word_limit_main_text": None,
    "abstract_type": "structured",
    "abstract_sections": [],
    "abstract_word_limit": 250,
    "reference_style": "Raqamli (Elsevier numbered; Vancouver'ga o'xshash)",
    "max_references": 120,                 # Sharh maqolalari uchun
    "required_sections": ["Introduction", "Methods", "Discussion"],
    "structure_note": "Title, Abstract, Keywords, Introduction, Materials and methods, Results, "
                      "Discussion and/or Conclusions",
    "keywords_min": 4,
    "keywords_max": 8,
    "accepts_reviews": True,
    "apc_usd": 2270,
    "apc_note": None,
    "ai_policy": "Generativ AI ishlatilgani topshirishda deklaratsiya qilinishi shart. Havolalar "
                 "ro'yxatidan oldin alohida bo'lim: 'Declaration of generative AI and AI-assisted "
                 "technologies in the manuscript preparation process'. AI muallif bo'la olmaydi.",
    "source_url": "https://www.cell.com/heliyon/guide-for-authors",
    "notes": "Jurnal uzunlikka limit qo'ymaydi. Sharh maqolalari uchun havolalar 120 tadan "
             "oshmasligi kerak (tadqiqot 60, keys 25).",
})

_reg({
    "key": "jcm",
    "name": "Journal of Clinical Medicine (MDPI)",
    "word_limit_main_text": None,
    "abstract_type": "unstructured",
    "abstract_sections": [],
    "abstract_word_limit": 200,            # Review turi uchun
    "reference_style": "Raqamli, matnda paydo bo'lish tartibida (MDPI/ACS uslubi)",
    "max_references": None,
    "required_sections": ["Introduction", "Discussion", "Conclusions"],
    "structure_note": "Title, Author list, Affiliations, Abstract, Keywords, Introduction, "
                      "Relevant Sections, Discussion, Conclusions, Future Directions, "
                      "Author Contributions, Acknowledgments, Conflicts of Interest, References",
    "keywords_min": 3,
    "keywords_max": 10,
    "accepts_reviews": True,
    "apc_usd": None,
    "apc_note": "CHF 2,600 (USD e'lon qilinmagan, ~$3,000).",
    "ai_policy": "GenAI muallif bo'la olmaydi. Ishlatilgan bo'lsa: topshirishda deklaratsiya + "
                 "Material va Metodlarda qanday ishlatilgani + Acknowledgments'da vosita "
                 "ma'lumotlari. Faqat yuzaki tahrir (grammatika, imlo) oshkor qilinmaydi.",
    "source_url": "https://www.mdpi.com/journal/jcm/instructions",
    "notes": "JCM uzunlikka cheklov qo'ymaydi. Review turi: 200 so'zlik TUZILMASIZ abstract. "
             "Asl tadqiqotlar uchun 250 so'zlik tuzilgan abstract talab qilinadi.",
})

_reg({
    "key": "nutrients",
    "name": "Nutrients (MDPI)",
    "word_limit_main_text": None,
    "abstract_type": "unstructured",
    "abstract_sections": [],
    "abstract_word_limit": 200,            # MDPI layout guide umumiy chegarasi
    "reference_style": "Raqamli, kvadrat qavsda, paydo bo'lish tartibida (MDPI/ACS)",
    "max_references": None,
    "required_sections": ["Introduction", "Discussion", "Conclusions"],
    "structure_note": "Title, Author list, Affiliations, Abstract, Keywords, mantiqiy bo'limlarga "
                      "ajratilgan adabiyot sharhi, Author Contributions, Acknowledgments, "
                      "Conflicts of Interest, References",
    "keywords_min": 3,
    "keywords_max": 10,
    "accepts_reviews": True,
    "apc_usd": None,
    "apc_note": "CHF 2,900 (USD e'lon qilinmagan, ~$3,300).",
    "ai_policy": "GenAI muallif bo'la olmaydi. Ishlatilgan bo'lsa: topshirishda deklaratsiya + "
                 "Material va Metodlarda tafsilot + Acknowledgments'da vosita ma'lumotlari. "
                 "Yuzaki tahrir oshkor qilinmaydi.",
    "source_url": "https://www.mdpi.com/journal/nutrients/instructions",
    "notes": "Jurnal uzunlikka cheklov qo'ymaydi. DIQQAT: 250 so'zlik tuzilgan abstract talabi "
             "faqat tizimli sharhlar va asl tadqiqotlarga tegishli — narrative sharh uchun "
             "tasdiqlanmagan, shuning uchun umumiy MDPI chegarasi (200 so'z, tuzilmasiz) olingan.",
})

_reg({
    "key": "medicine_baltimore",
    "name": "Medicine (Baltimore)",
    "word_limit_main_text": None,
    "abstract_type": "structured",
    "abstract_sections": [],
    "abstract_word_limit": 350,
    "reference_style": "AMA Manual of Style (JAMA uslubi; yuqori indeksdagi raqamlar)",
    "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion"],
    "structure_note": "Tegishli hisobot qo'llanmasiga (EQUATOR/PRISMA/CONSORT) mos bo'lishi kerak",
    "keywords_min": None,
    "keywords_max": None,
    "accepts_reviews": False,              # <-- eng muhim: yopilgan
    "apc_usd": 2250,
    "apc_note": "Original Studies $2,250; Narrative Review $1,750 (endi ahamiyatsiz).",
    "ai_policy": "AI muallif bo'la olmaydi. AI ishlatilgani maqolada oshkor qilinishi shart. "
                 "Muallif AI yaratgan qismlar uchun ham to'liq javobgar.",
    "source_url": "https://journals.lww.com/md-journal/pages/instructions-for-authors.aspx",
    "notes": "KRITIK: 'Medicine(R) is no longer accepting new narrative review submissions as of "
             "January 14, 2025 and they will be rejected without review.' Tizimli sharhlar va "
             "meta-analizlar hali ham qabul qilinadi.",
})

_reg({
    "key": "plos_one",
    "name": "PLOS ONE",
    "word_limit_main_text": None,
    "abstract_type": "unstructured",
    "abstract_sections": [],
    "abstract_word_limit": 300,
    "reference_style": "Vancouver (raqamli / citation-sequence, ICMJE)",
    "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion"],
    "structure_note": "Title page, Abstract, Introduction, Materials and Methods, Results, "
                      "Discussion, Conclusions (majburiy emas), Acknowledgments, References",
    "keywords_min": None,
    "keywords_max": None,
    "accepts_reviews": False,
    "apc_usd": 2477,
    "apc_note": None,
    "ai_policy": "AI hissasi Methods'da alohida bo'limda oshkor qilinishi shart (vosita nomi, "
                 "qanday ishlatilgani, natijalar qanday tekshirilgani). Matn uchun muallif "
                 "javobgar; AI ma'lumot to'qishi qabul qilinmaydi (rad etish/retraction).",
    "source_url": "https://journals.plos.org/plosone/s/submission-guidelines",
    "notes": "Sharhlarni qabul qILMAYDI: 'We will not consider: Reviews... Any other type of "
             "secondary literature.' Faqat taklif qilingan Collection Reviews. Kalit so'zlar "
             "talab qilinmaydi (PLOS Subject Areas ishlatiladi). Uzunlikka limit yo'q.",
})

_reg({
    "key": "bmj_open",
    "name": "BMJ Open",
    "word_limit_main_text": None,
    "abstract_type": "structured",
    "abstract_sections": ["objectives", "design", "setting", "participants", "results", "conclusions"],
    "abstract_word_limit": None,
    "reference_style": "Vancouver (BMJ uslubi, kvadrat qavsda yoki yuqori indeksda)",
    "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion"],
    "structure_note": "Title, Structured abstract, 'Strengths and limitations', Introduction, "
                      "Methods, Results, Discussion (5 paragrafdan oshmasligi tavsiya etiladi), "
                      "Funding, Competing interests, Author contributions, Data availability",
    "keywords_min": None,
    "keywords_max": None,
    "accepts_reviews": False,
    "apc_usd": None,
    "apc_note": "GBP 2,535 (USD e'lon qilinmagan, ~$3,400).",
    "ai_policy": "BMJ AI ishlatilishini ko'rib chiqadi, tamoyil — oshkoralik. Contributor "
                 "bo'limida AI ishlatilgani aytilishi shart; tadqiqot jarayonida ishlatilgan "
                 "bo'lsa Methods'da to'liq tavsif. AI muallif bo'la olmaydi. Oshkor qilinmagan "
                 "AI rad etish yoki retraction sabab bo'lishi mumkin.",
    "source_url": "https://bmjopen.bmj.com/pages/authors",
    "notes": "BMJ Open'da 'Review' maqola turi YO'Q. Faqat: Original research, Protocol, Cohort "
             "profile, Communication, Supplement. O'xshash jurnallarda limit bor: BMJ Open "
             "Gastroenterology Review — 4,000 so'z / 300 so'zlik abstract; BMJ Open Diabetes "
             "Research & Care Review — 5,000 so'z / 250 so'zlik abstract / 65 havola.",
})


def list_profiles() -> list[dict]:
    """Mavjud profillar ro'yxati (frontend/API uchun qisqa ko'rinish)."""
    out = [{"key": GENERIC["key"], "name": GENERIC["name"],
            "word_limit": None, "apc_usd": None, "accepts_reviews": None,
            "field": GENERIC.get("field"), "indexing": None}]
    for p in JOURNALS.values():
        idx = p.get("indexing")
        out.append({
            "key": p["key"],
            "name": p["name"],
            "field": p.get("field"),
            "word_limit": p.get("word_limit_main_text"),
            "abstract_type": p.get("abstract_type"),
            "reference_style": p.get("reference_style"),
            "apc_usd": p.get("apc_usd"),
            "apc_note": p.get("apc_note"),
            "accepts_reviews": p.get("accepts_reviews"),
            # indexing_status: "verified" (ro'yxatda bor) | "none" (tekshirildi, yo'q)
            #                  | None (tekshirilmagan)
            "indexing": idx,
            "indexing_status": (None if idx is None else ("verified" if idx else "none")),
            "if_verified": p.get("if_verified"),
            "claimed_if": p.get("claimed_if"),
            "source_url": p.get("source_url"),
        })
    return sorted(out, key=lambda x: (x.get("field") or "", x["name"]))


def get_profile(key: str | None) -> dict:
    """Profilni oladi. Noma'lum kalit uchun umumiy profil qaytadi (xato bermaydi)."""
    if not key or key == GENERIC["key"]:
        return GENERIC
    return JOURNALS.get(key, GENERIC)

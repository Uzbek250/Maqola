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

# =============================================================================
# FOYDALANUVCHI BERGAN 12 JURNAL (2026-09-20 da tekshirildi)
# =============================================================================
# TEKSHIRUV NATIJASI: bu 12 jurnalning HECH BIRI rasmiy indeksda yo'q.
# DOAJ API, Clarivate Master Journal List, SCImago, Crossref va OpenAlex
# bo'yicha 0 natija. IF raqamlari Clarivate JCR yoki Scopus'dan EMAS —
# jurnalning o'zi yoki ResearchBib (o'zi "impact factor" beradigan bepul
# agregator) tomonidan e'lon qilingan.
#
# Shuning uchun bu profillarda:
#   indexing = []            -> tekshirildi, hech qayerda yo'q (❌ hisobotda)
#   if_verified = False      -> IF JCR/Scopus'da tasdiqlanmagan (❌ hisobotda)
#   claimed_if = <raqam>     -> mijoz aytgan raqam (ma'lumot uchun saqlanadi)
#   predatory_signals = [...]-> aniq dalillar (⚠️ hisobotda)
#
# Bu jurnallar mavjud va ishlaydi, lekin mijoz buni BILIB turishi kerak:
# bunday nashr ba'zi tashkilotlarda ilmiy ish sifatida hisobga olinmaydi.
# Ilova qaror qabul qilmaydi — faktlarni ko'rsatadi, qaror muallifniki.

# --- Mahalliy (O'zbekiston) — hammasi bitta nashriyot: "Worldly Knowledge", Andijon
_UZ_TEMPLATE = ("ANNOTATSIYA, KALIT SO'ZLAR, KIRISH, MATERIALLAR VA USLUBLAR, "
                "NATIJALAR VA MUHOKAMALAR, XULOSA, FOYDALANILGAN ADABIYOTLAR "
                "(nashriyotning namunaviy maqola shabloni)")

_reg({
    "key": "iqro", "name": "Iqro jurnali", "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": _UZ_TEMPLATE,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": None,
    "apc_usd": 0, "apc_note": "O'zbekiston slib.uz portali: nashr BEPUL.",
    "ai_policy": None, "indexing": [], "claimed_if": 8.245, "if_verified": False,
    "predatory_signals": [
        "IF 8.245 hech qayerda rasmiy emas — faqat Telegram/Instagram e'lonlarida",
        "Jurnal o'z PDF'larida boshqa raqam bosadi (ResearchBib 9.145, SJIF 5.431)",
        "Scopus, Web of Science, DOAJ (ISSN 2181-4341), PubMed — hech birida yo'q",
        "'Indekslash' ro'yxati faqat ResearchBib, SJIFactor, EuroPub kabi agregatorlar",
        "2023 da boshlanib 2026 da 23-jild; har oyda 100+ qisqa maqola, barcha sohalar",
        "Telegram orqali pullik 'tezkor nashr' va maqola yozib berish xizmati sotiladi",
    ],
    "source_url": "https://wordlyknowledge.uz/index.php/iqro",
    "notes": "Mavjud, ishlaydigan OJS sayti bor (ISSN 2181-4341, 2023, oylik). Tahririyat "
             "shakllangan, lekin xalqaro indekslarda yo'q. O'zbekiston OAK ro'yxatida "
             "bo'lishi mumkin (mahalliy ro'yxat) — bu xalqaro indeks emas. Nashr bepul.",
})
_reg({
    "key": "ijsresearchers", "name": "International Journal of Scientific Researchers",
    "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": _UZ_TEMPLATE,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": None,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 8.293, "if_verified": False,
    "predatory_signals": [
        "'Impact factor: 8,293' jurnalning O'Z PDF har bir sahifasida bosilgan — JCR/Scopus emas",
        "Scopus, Web of Science, DOAJ (ISSN 3030-332X), PubMed — hech birida yo'q",
        "Nomi haqiqiy jurnallarga juda o'xshash (IJSR India, IJ Science and Research)",
        "Boshqa Worldly Knowledge jurnallari bilan bir xil nashriyot va marketing",
        "Maqolalar bir nechta domenga 'Google Scholar' uchun ko'chirib qo'yiladi",
    ],
    "source_url": "https://worldlyjournals.com/index.php/IJSR",
    "notes": "Foydalanuvchi bergan 'International Journal of Scientific Researchs' — imlo "
             "xatosi. Aniqlangan jurnal: 'International Journal of Scientific Researchers' "
             "(ISSN 3030-332X), aynan 8,293 raqamini olib yurgan yagona nom. Xuddi shu "
             "nashriyot (Worldly Knowledge).",
})
_reg({
    "key": "ilmfan_xabarnomasi", "name": "Ilm-fan xabarnomasi", "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": _UZ_TEMPLATE,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": None,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 7.241, "if_verified": False,
    "predatory_signals": [
        "IF 7.241 jurnalning o'z saytida ham, PDF'ida ham yo'q — faqat reklamalarda",
        "ResearchBib boshqa raqam ko'rsatadi (8.841/2025)",
        "Scopus, Web of Science, DOAJ (ISSN 3030-3931), PubMed — hech birida yo'q",
        "'Index Copernicus' logotipi bor, lekin ishlaydigan havolasi yo'q",
        "2024 da boshlanib 2026 da 15-jild — hajm haqiqiy peer review'ga mos emas",
    ],
    "source_url": "https://worldlyjournals.com/index.php/Yangiizlanuvchi",
    "notes": "Mavjud OJS sayti (ISSN 3030-3931, 2024, oylik). Worldly Knowledge nashriyoti. "
             "Nashr narxi hech qayerda e'lon qilinmagan.",
})
_reg({
    "key": "pedagogik_tadqiqotlar", "name": "Pedagogik tadqiqotlar jurnali",
    "field": "pedagogy",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": _UZ_TEMPLATE,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": None,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 7.212, "if_verified": False,
    "predatory_signals": [
        "2024 da tashkil etilgan jurnal uchun IF 7.212 — JCR/Scopus'da bunday raqam yo'q",
        "Scopus, Web of Science (MJL), DOAJ, Crossref, OpenAlex — hammasida 0 natija",
        "Indekslash ro'yxatidagi ResearchBib havolasi BOSHQA jurnal ISSN'iga olib boradi",
        "Yiliga 12 son, har bir maqola ~99 000 so'mdan sotiladi, 5 ish kunida nashr",
        "Mualliflar uchun qo'llanma umuman yo'q (so'z/abstract/havola qoidalari)",
    ],
    "source_url": "https://wosjournals.com/index.php/ptj",
    "notes": "Mavjud, ISSN 3060-4923. Tahririyat hay'ati haqiqiy va nomlangan (o'zbek "
             "akademiklari) — bu yagona ijobiy belgi. Qolgan hamma narsa tekshirilmagan. "
             "Qo'llanma e'lon qilinmagan, shuning uchun faqat umumiy tuzilma qo'llanadi.",
})
_reg({
    "key": "akademik_tadqiqotlar", "name": "Akademik tadqiqotlar jurnali (ATJ)",
    "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": _UZ_TEMPLATE,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 15.7, "if_verified": False,
    "predatory_signals": [
        "IF 15.7 — Nature darajasidan yuqori; jurnalning o'zi 2026 da boshlangan",
        "Raqam faqat ResearchBib va reklamadan, JCR/Scopus'dan emas",
        "ISSN chalkash: saytda 3003-9178 (mavjud emas), ro'yxatda 3093-9178, "
        "reklamada 3093-978X (bu nemis jurnali)",
        "Scopus, Web of Science, DOAJ, Crossref, OpenAlex — hammasida 0 natija",
        "Xalqaro deb e'lon qilinadi, lekin tahririyat deyarli butunlay Andijon/Samarqand",
    ],
    "source_url": "https://wkscientificbulletin.com/index.php/atj",
    "notes": "Mavjud, ISSN 3093-9178. Sayt ikki tomonlama ko'r taqriz va COPE'ga amal "
             "qilishni e'lon qiladi, sharh maqolalarini qabul qiladi (o'z bayonotiga ko'ra). "
             "15.7 raqami tasdiqlanmagan. Qo'llanma e'lon qilinmagan.",
})

# --- Xalqaro ro'yxat
_reg({
    "key": "bg_pulse", "name": "BG Pulse Journal", "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 15.37, "if_verified": False,
    "predatory_signals": [
        "IF 15.37 faqat o'z saytida va ResearchBib'da — JCR/Scopus'da yo'q",
        "Raqam ISSN portaliga havola qilingan, portalda esa IF haqida hech narsa yo'q",
        "Tahririyat hay'ati sahifasi BO'SH — bosh muharrir ham yo'q",
        "Mualliflar uchun qo'llanma sahifasi BO'SH",
        "Email 'bgpulsejournal@info.com' — jurnal domenida emas, manzil 'Chicago,United State' (imlo xato)",
        "Scopus, Web of Science, DOAJ, Crossref, OpenAlex — hammasida 0 natija",
    ],
    "source_url": "http://www.bgpulseusa.com/",
    "notes": "ISSN 1947-2536 (AQSh). Sayt ishlaydi, lekin qo'llanma va tahririyat e'lon "
             "qilinmagan — formatlash uchun haqiqiy qoida yo'q.",
})
_reg({
    "key": "ij_law", "name": "International Journal of Law", "field": "law",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": "Raqamli (Vancouver uslubida kuzatilgan)",
    "max_references": None,
    "required_sections": ["Introduction", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 15.57, "if_verified": False,
    "predatory_signals": [
        "IF 15.57 faqat ResearchBib'da — JCR'da hech bir huquq jurnali bunga yaqin emas",
        "ISSN 1694-2442 — Mauritius'da ro'yxatga olingan, mazmuni deyarli butunlay o'zbek",
        "Tahririyat hay'ati sahifasi BO'SH, aloqa sahifasida ism/email/manzil yo'q",
        "Scopus, DOAJ, Web of Science, PubMed — hech birida yo'q",
        "'2 kun qaror, 3 kun nashr' — haqiqiy taqrizga mos emas",
        "Arabian Journal of Science va HSR London bilan BIR XIL shablon va server",
    ],
    "source_url": "https://ijl-apm.com/index.php/ijl",
    "notes": "DIQQAT: bu nom bilan 3 xil jurnal bor. 15.57 raqami faqat Mauritius'dagi "
             "ISSN 1694-2442 ga tegishli. Haqiqiy jurnallar: 'Int. J. of Law, Crime and "
             "Justice' (Elsevier, IF ~1.4) va 'Int. J. of Law in Context' (Cambridge). "
             "Qo'llanma e'lon qilinmagan.",
})
_reg({
    "key": "arabian_j_science", "name": "Arabian Journal of Science", "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": "Raqamli, kvadrat qavsda (kuzatilgan)",
    "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": 0, "apc_note": "Bepul — bu o'zi shubhali belgi (hajm bilan pul ishlash modeli).",
    "ai_policy": None, "indexing": [], "claimed_if": 13.5, "if_verified": False,
    "predatory_signals": [
        "'IF 13.5' o'z saytida va ResearchBib'da — JCR/Scopus'da yo'q",
        "Nomi Springer'ning HAQIQIY 'Arabian Journal for Science and Engineering' "
        "(ISSN 2193-567X, IF 3.1) jurnaliga o'xshab qo'yilgan",
        "ISSN 2308-5703 — Avstriyada, mazmuni Markaziy Osiyodan",
        "Tahririyat hay'ati BO'SH; etika bayonoti va manzil yo'q",
        "'2 kun qaror, 3 kun nashr' e'lon qilingan",
        "Scopus, DOAJ, Web of Science, PubMed — hech birida yo'q",
    ],
    "source_url": "http://www.arabianjournalofscience.com/index.php/AJSI",
    "notes": "Springer'ning shu nomga o'xshash jurnali HAQIQIY va indekslangan — "
             "aralashtirmaslik kerak. 13.5 raqami faqat Avstriyadagi ushbu nomga tegishli.",
})
_reg({
    "key": "hsr_london", "name": "HSR London – Houghton Street Review", "field": "general",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Discussion", "Conclusion"],
    "structure_note": "Title, Author information, Abstract, Keywords, Main text, Conclusion, References",
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": 0, "apc_note": "Bepul e'lon qilingan, lekin indekssiz + 3 kunlik nashr.",
    "ai_policy": None, "indexing": [], "claimed_if": 15.9, "if_verified": False,
    "predatory_signals": [
        "NOMI TANILGAN MUASSASAGA TAYANADI: Houghton Street — London School of "
        "Economics (LSE) manzili. Bu jurnalning LSE bilan aloqasi YO'Q",
        "'IF 15.9' faqat ResearchBib'ga havola — JCR/Scopus'da yo'q",
        "Tahririyat hay'ati sahifasida HECH KIM yo'q",
        "Indekslash bo'limi BO'SH sarlavha — hech qanday indeks sanalmagan",
        "Scopus, DOAJ (ISSN 2058-5519), Web of Science, PubMed — hech birida yo'q",
        "Cheksiz ko'p soha (tibbiyot, huquq, muhandislik, turizm) — haqiqiy jurnalda bo'lmaydi",
        "'2 kun qaror, 3 kun nashr'",
    ],
    "source_url": "https://houghtonstreetreview.com/index.php/hsr",
    "notes": "LSE'ning o'z talabalik nashrlari 'Houghton Street Press' nomi bilan chiqadi — "
             "bu jurnal ular bilan bog'liq emas. Eng kuchli qizil bayroq — nomning LSE "
             "manziliga tayanishi.",
})
_reg({
    "key": "ij_lls", "name": "International Journal of Literature and Language Studies",
    "field": "literature",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 13.77, "if_verified": False,
    "predatory_signals": [
        "'IF 13.77' faqat ResearchBib'da — Clarivate MJL'da ISSN 2828-6235 uchun 0 natija",
        "Tahririyat hay'ati sahifasi BO'SH — birorta muharrir ismi yo'q",
        "Aloqa ma'lumotlari ziddiyatli: Indoneziya muharriri + Pokiston telefon raqami; "
        "qo'llab-quvvatlash uchun 'professor' + Hindistonning namunaviy raqami (+91 98765 21438)",
        "Domen jiujournal.org 2026-05-14 da ro'yxatga olingan; sayt o'zini ijujournal.org deb yozadi",
        "Scopus, DOAJ, Crossref, Web of Science — hech birida yo'q",
        "Bir xil server (167.235.222.200) va registrar — 3 ta jurnal bir kunda ro'yxatga olingan",
    ],
    "source_url": "https://jiujournal.org/index.php/ijlls",
    "notes": "ISSN 2828-6235 haqiqiy va Indoneziyada ro'yxatga olingan, 2021-2023 maqolalari "
             "Garuda'da bor. Lekin hozirgi sayt (domen 2026-mayda qayta olingan) "
             "tekshirilmaydigan operatsiya.",
})
_reg({
    "key": "ij_tar", "name": "International Journal of Technology and Academic Research",
    "field": "technology",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": None,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 14.91, "if_verified": False,
    "predatory_signals": [
        "Raqamlar O'ZIGA ZID: ResearchBib 14.91, jurnalning o'z PDF shabloni 15.9 — "
        "ikkalasi ham JCR/Scopus'da emas",
        "Tahririyat hay'ati sahifasi BO'SH — hech kim nomlanmagan",
        "Aloqa: shaxsiy pochta (Ahmedresearcher@outlook.com) — institutsional email emas",
        "Scopus, DOAJ, Crossref, OpenAlex, Web of Science — hammasida 0 natija",
        "Domen 2026-05-14 da ro'yxatga olingan, bir xil serverda 3 ta jurnal bilan",
        "'About' Pokiston deb yozadi, maqolalar mualliflari deyarli butunlay o'zbek",
    ],
    "source_url": "http://waerasia.org/index.php/ijtar",
    "notes": "ISSN 2224-6878 haqiqiy va nomning tarixi bor (2011 da Pokiston, WAER "
             "nashriyoti, ikki oylik). Hozirgi sayt (domen 2026-mayda qayta olingan) "
             "nashriyotni, muharrirlarni va narxni ko'rsatmaydi.",
})
_reg({
    "key": "emj_nrc", "name": "Egyptian Medical Journal of the National Research Center",
    "field": "medical",
    "word_limit_main_text": None, "abstract_type": None, "abstract_sections": [],
    "abstract_word_limit": None, "reference_style": None, "max_references": None,
    "required_sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
    "structure_note": None,
    "keywords_min": None, "keywords_max": None, "accepts_reviews": True,
    "apc_usd": None, "apc_note": None, "ai_policy": None,
    "indexing": [], "claimed_if": 12.3, "if_verified": False,
    "predatory_signals": [
        "NOMI HAQIQIY DAVLAT MUASSASASIGA TAYANADI: Misr Milliy Tadqiqot Markazi (NRC, Qohira). "
        "Hozirgi saytda NRC bilan aloqa, NRC muharrirlari yoki NRC manzili YO'Q",
        "Shu nomdagi HAQIQIY jurnal 2010 atrofida to'xtagan (NLM katalogi)",
        "IF o'z ichida zid: PDF shablonida 12.3, About sahifasida 16,87 — ikkalasi ham tasdiqlanmagan",
        "Scopus, Web of Science, DOAJ, Crossref (DOI yo'q), PubMed, OpenAlex — hammasida 0 natija",
        "Tahririyat hay'ati BO'SH; aloqa sahifasida mas'ul shaxs 'ssa' deb yozilgan (ism/email yo'q)",
        "Domen 2026-05-15 da ro'yxatga olingan — bir xil server va registrar",
        "Oylik jurnal uchun juda katta hajm; mualliflar deyarli butunlay o'zbek",
    ],
    "source_url": "http://www.mjnrc.com/index.php/emjn/",
    "notes": "Bu nom bilan haqiqiy jurnal bo'lgan: ISSN 1687-1278, NIDOC/Akademiya, Qohira, "
             "IMEMR ro'yxatida. U 2010 atrofida to'xtagan. Hozirgi onlayn ISSN 2090-5386 "
             "(2023) saytga bog'langan, sayt esa 2026-mayda qayta ro'yxatga olingan. "
             "'NRC nashri, IF 12.3' da'vosini tasdiqlanmagan deb hisoblash kerak.",
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

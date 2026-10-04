"""
Bo'lim-bo'lim yozish arxitekturasi.

NEGA KERAK: butun maqolani bitta so'rovda so'rash ishlamadi. Sinov ko'rsatdi —
promptda "3-5 mavzu ochma", "har bo'limda 3 manba", "taqqosla" deb yozsak ham,
model 10 ta bo'lim ochdi, 4 tasida 3 dan kam manba bo'ldi, taqqoslash iboralari
kamaydi. Sabab: bitta uzun so'rovda model ko'rsatmalarni "yumshoq maslahat"
sifatida qabul qiladi.

YECHIM — arxitektura, model emas:
  1. Mavzular KOD tomonidan tekshiriladi: 3-5 ta mavzu, har birida >=3 manba.
     Model taklif qiladi, kod tuzatadi (kichik mavzular birlashtiriladi).
  2. Har bir bo'lim ALOHIDA so'rovda yoziladi — model faqat o'sha mavzuning
     3-5 manbasini ko'radi. Ko'p manba ko'rmaydi, shuning uchun "sanab chiqish"
     qilolmaydi, taqqoslashga majbur bo'ladi.
  3. Methods bo'limi KOD tomonidan quriladi — haqiqiy qidiruv raqamlaridan.
     Model umuman yozmaydi, shuning uchun to'qib bo'lmaydi.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from app.services import gpt_service

logger = logging.getLogger(__name__)

# Bo'lim turlari (kod nazorat qiladi, model emas)
INTRO, METHODS, THEME, DISCUSSION, LIMITATIONS, CONCLUSION = (
    "intro", "methods", "theme", "discussion", "limitations", "conclusion",
)

MAX_THEMES = 5
MIN_SOURCES_PER_THEME = 3

# Promptga sig'adigan chegaralar. 25 manbaning to'liq matni ~800 000 belgi
# bo'lishi mumkin — bitta so'rovga sig'maydi va API xato beradi.
MAX_FULLTEXT_CHARS = 6000      # har bir manbadan eng ko'pi shuncha belgi
MAX_PROMPT_SOURCES = 8         # bitta so'rovda ko'pi bilan shuncha manba

# Uzunlik ulushlari (jami nishonga nisbatan)
SHARES = {INTRO: 0.13, METHODS: 0.07, DISCUSSION: 0.16, LIMITATIONS: 0.06, CONCLUSION: 0.04}

# Bo'lim sarlavhalari (3 tilda) — kod beradi, model emas
TITLES = {
    "uz": {"intro": "KIRISH", "methods": "TADQIQOT METODOLOGIYASI",
           "discussion": "UMUMIY MUHOKAMA", "limitations": "CHEKLOVLAR VA KEYINGI TADQIQOTLAR",
           "conclusion": "XULOSA"},
    "en": {"intro": "Introduction", "methods": "Methods: Search Strategy",
           "discussion": "Discussion", "limitations": "Limitations and Future Directions",
           "conclusion": "Conclusion"},
    "ru": {"intro": "ВВЕДЕНИЕ", "methods": "МЕТОДОЛОГИЯ ИССЛЕДОВАНИЯ",
           "discussion": "ОБСУЖДЕНИЕ", "limitations": "ОГРАНИЧЕНИЯ И ПЕРСПЕКТИВЫ",
           "conclusion": "ЗАКЛЮЧЕНИЕ"},
}

LANG_NAMES = {"uz": "o'zbek", "en": "ingliz", "ru": "rus"}

# Har bir bo'lim uchun umumiy qat'iy qoidalar (kod tomonidan qo'shiladi)
SECTION_RULES = """
QAT'IY QOIDALAR — buzilishi mumkin emas:
1. FAQAT quyida berilgan manbalarga tayan. Boshqa manba, kitob, raqam yoki
   fakt O'YLAB TOPMA.
2. Manbalar birin-ketin aytib chiqilmasin. Mana bu XATO:
     "Smith [3] found X. Jones [4] found Y. Ali [5] found Z."
   To'g'ri uslub — manbalarni bog'lab, TAQQOSLAB yozish:
     "Smith [3] reported X, but Jones [4], using a larger cohort, found no such
      effect; the difference may reflect the shorter follow-up in [3]."
3. Kamida bitta gap ikki yoki undan ortiq manbani ANIQ taqqoslasin (mos kelishi
   yoki zid bo'lishi) va sababini ko'rsatsin.
4. Bo'lim oxirida SINTEZ jumlasi bo'lsin: bu dalillar birgalikda nimani anglatadi.
5. Berilgan manbalarning KAMIDA UCHTASINI ishlat — bittasi yoki ikkitasi bilan
   cheklanma.
6. Namuna hajmi (n) yoki tadqiqot dizayni manbada ko'rsatilmagan bo'lsa, o'sha
   joyda bir marta ayt va undan MARKAZIY xulosa chiqarma — kontekst sifatida
   ishlat. Ogohlantirishni takrorlab, har gapga qalqon qilma.
7. Sarlavha qo'yma (bo'lim sarlavhasi beriladi), kirish so'zi yozma — to'g'ridan
   to'g'ri mazmunga kir.
8. Faqat bo'lim matnini qaytar, izoh yoki izohli sarlavha qo'shma.
"""


def _assign_sources_by_id(sources: list[dict], ids: list[int]) -> list[dict]:
    """Manba raqamlari (1-based) -> manba obyektlari."""
    out = []
    for i in ids:
        if 1 <= i <= len(sources):
            out.append(sources[i - 1])
    return out


def _merge_title(a: str, b: str) -> str:
    """Birlashtirilgan mavzu nomi. Uzun nomlarni ketma-ket qo'shib tashlamaymiz."""
    a, b = a.strip(), b.strip()
    if not a:
        return b
    if not b:
        return a
    if a.lower() in b.lower():
        return b[:110]
    if b.lower() in a.lower():
        return a[:110]
    return (a if len(a) >= len(b) else b)[:110]


def _merge_into_shape(themes: list[dict], total_sources: int) -> list[dict]:
    """
    Mavzularni KOD tomonidan talab shakliga keltiradi (modelning xohishidan
    qat'i nazar):
      - har bir mavzuda >=MIN_SOURCES_PER_THEME manba;
      - mavzular soni <=MAX_THEMES;
      - hech bir manba tashqarida qolmaydi.
    """
    items = [{"title": t["title"], "ids": list(t["ids"])} for t in themes if t.get("ids")]

    if not items:
        return [{"title": "Umumiy tahlil", "ids": list(range(1, total_sources + 1))}]

    if len(items) == 1:
        items[0]["ids"] = list(range(1, total_sources + 1))
        return items

    # 1) Kichik mavzularni JUFTLAB birlashtiramiz (eng kichik ikkitasi),
    #    toki hammasi >=MIN bo'lgunicha.
    while len(items) > 1:
        items.sort(key=lambda x: len(x["ids"]))
        if len(items[0]["ids"]) >= MIN_SOURCES_PER_THEME:
            break
        a = items.pop(0)
        b = items.pop(0)
        items.append({"title": _merge_title(b["title"], a["title"]),
                      "ids": sorted(set(a["ids"]) | set(b["ids"]))})

    # 2) MAX_THEMES dan ko'p bo'lsa — eng kichigini eng kattasiga qo'shamiz.
    while len(items) > MAX_THEMES:
        items.sort(key=lambda x: len(x["ids"]))
        a = items.pop(0)
        items[-1]["ids"] = sorted(set(items[-1]["ids"]) | set(a["ids"]))

    # 3) Ishlatilmagan manbalarni eng katta mavzuga qo'shamiz.
    used: set[int] = set()
    for t in items:
        used |= set(t["ids"])
    missing = [i for i in range(1, total_sources + 1) if i not in used]
    if missing:
        items.sort(key=lambda x: -len(x["ids"]))
        items[0]["ids"] = sorted(set(items[0]["ids"]) | set(missing))

    items.sort(key=lambda x: -len(x["ids"]))
    return items


def _normalize_themes(themes: list[dict], sources: list[dict]) -> list[dict]:
    """
    Model taklif qilgan mavzularni KOD tomonidan tekshiradi va tuzatadi.
    Model buzuq/bo'sh javob bersa ham natija TO'G'RI shaklda bo'ladi.
    """
    valid: list[dict] = []
    used_ids: set[int] = set()
    for t in themes:
        name = str(t.get("title") or t.get("theme") or "").strip()
        raw = t.get("sources") or t.get("source_ids") or t.get("refs") or t.get("ids") or []
        ids = []
        for r in raw:
            m = re.match(r"^\s*(\d+)", str(r))
            if m:
                v = int(m.group(1))
                if 1 <= v <= len(sources) and v not in used_ids:
                    ids.append(v)
                    used_ids.add(v)
        if name and ids:
            valid.append({"title": name[:110], "ids": sorted(ids)})

    if not valid:
        # Model ishlamadi — kod o'zi guruhlaydi. Bu yerga qayta kirmaydi
        # (_fallback_themes _normalize_themes ni chaqirmaydi — rekursiya yo'q).
        return _fallback_themes(sources)

    return _merge_into_shape(valid, len(sources))


def _fallback_themes(sources: list[dict]) -> list[dict]:
    """
    Model ishlamasa: manbalarni sarlavhadagi kalit so'zlarga qarab kod o'zi
    guruhlaydi. `_normalize_themes` ni QAYTA CHAQIRMAYDI (cheksiz rekursiya
    bo'lmasligi uchun) — to'g'ridan-to'g'ri `_merge_into_shape` dan o'tadi.
    """
    groups: dict[str, list[int]] = {}
    for i, s in enumerate(sources, 1):
        title = (s.get("title") or "").lower()
        words = [w for w in re.findall(r"[a-z]{4,}", title) if w not in _STOP]
        key = words[0] if words else "general"
        groups.setdefault(key, []).append(i)

    themes = [{"title": k.capitalize(), "ids": v} for k, v in groups.items()]
    return _merge_into_shape(themes, len(sources))


_STOP = {"this", "that", "with", "from", "study", "among", "effect", "effects",
         "role", "analysis", "review", "case", "report", "based", "using",
         "patients", "results", "randomized", "trial", "cohort", "associated"}


async def plan_themes(topic: str, sources: list[dict], language: str = "en") -> list[dict]:
    """
    1-qadam: manbalarni 3-5 mavzuga guruhlaydi.
    Model taklif qiladi, KOD tekshiradi va tuzatadi — shu bilan "har bo'limda
    >=3 manba" va "3-5 mavzu" qoidalari KAFOLATLANADI (modelning xohishiga
    bog'liq emas).
    """
    listing = "\n".join(
        f"[{i}] {(s.get('title') or '')[:150]} | {(s.get('journal') or '')[:50]} | {(s.get('pub_date') or '')[:4]}"
        for i, s in enumerate(sources, 1)
    )
    lang_name = LANG_NAMES.get(language, "ingliz")
    system_prompt = (
        "Sen ilmiy muharrirsan. Manbalarni mavzular bo'yicha guruhlaysan. "
        "Faqat JSON qaytarasan, boshqa matn yo'q."
    )
    user_prompt = f"""Mavzu: {topic}

MANBALAR ({len(sources)} ta):
{listing}

Bu manbalarni {MIN_SOURCES_PER_THEME} tadan {MAX_THEMES} tagacha MAVZUGA guruhla.
Har bir mavzu shu maqolaning mustaqil bo'limi bo'ladi.

QOIDALAR:
- Har bir mavzuda KAMIDA {MIN_SOURCES_PER_THEME} manba bo'lsin (bu qat'iy talab).
- Mavzular soni {MAX_THEMES} tadan OSHMASIN. Keng mavzuni ko'p bo'lakka bo'lma —
  {MIN_SOURCES_PER_THEME}-{MAX_THEMES} ta chuqur mavzu yaxshi.
- Har bir manba kamida bitta mavzuda bo'lsin.
- Mavzu nomi qisqa va aniq bo'lsin (ilmiy, 3-8 so'z).
- MAVZU NOMLARI {lang_name.upper()} TILIDA bo'lsin (maqola shu tilda yoziladi).

Faqat shu JSON formatda qaytar:
{{"themes": [{{"title": "mavzu nomi", "sources": [1, 5, 9, 14]}}, ...]}}"""

    try:
        raw = await gpt_service._call_gpt(system_prompt, user_prompt, temperature=0.3, max_tokens=1200)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else json.loads(raw)
        themes = data.get("themes") or []
    except Exception:
        logger.exception("Mavzular rejasi olinmadi — kod o'zi guruhlaydi")
        themes = []

    normalized = _normalize_themes(themes, sources)
    logger.info("Mavzular: %s", [(t["title"], len(t["ids"])) for t in normalized])
    return normalized


def build_methods_section(
    search_stats: dict, search_query: str, databases: list[str],
    search_date: str, selected: int, language: str = "en",
    per_theme: list[dict] | None = None,
) -> str:
    """
    Methods bo'limi TO'LIQ KOD tomonidan quriladi — haqiqiy qidiruv raqamlaridan.
    Model bu bo'limni yozmaydi, shuning uchun raqam to'qishi mumkin emas.
    """
    s = search_stats or {}
    per_db = s.get("per_database") or {}
    raw = s.get("retrieved_raw", 0)
    dedup = s.get("duplicates_removed", 0)
    after = s.get("after_screening", raw)
    db_txt = ", ".join(databases) if databases else "PubMed"
    per_db_txt = "; ".join(f"{k}: {v}" for k, v in per_db.items()) if per_db else f"{db_txt}: {raw}"

    if language == "uz":
        return (
            f"Ushbu sharh {search_date} sanasida {db_txt} ma'lumotlar bazasida "
            f"quyidagi so'rov bo'yicha o'tkazilgan qidiruvga asoslanadi: "
            f"\"{search_query}\". Qidiruv natijasida {per_db_txt} — jami {raw} ta yozuv "
            f"topildi. Takrorlanuvchi yozuvlar olib tashlangandan so'ng {after} ta "
            f"noyob yozuv qoldi ({dedup} ta dublikat chiqarib tashlandi). Shundan "
            f"{selected} tasi mavzuga mosligi, annotatsiyaning to'liqligi va "
            f"nashr yangiligiga ko'ra tanlab olindi va tahlilga kiritildi.\n\n"
            f"Metodologik izoh: bu TANLAB OLINGAN (narrative) sharh bo'lib, tizimli "
            f"sharh emas. PRISMA oqimi qo'llanilmagan va qidiruv bayonnomasi oldindan "
            f"ro'yxatdan o'tkazilmagan; shuning uchun natijalar tizimli sharh "
            f"darajasidagi to'liqlikni talab qilmaydi va nashr tarafkashligi "
            f"(publication bias) ehtimoli cheklanmagan. Manbalar oldindan belgilangan "
            f"bir xil mezon bo'yicha saralanmagan, balki mutaxassis tanlovi asosida "
            f"tanlangan; bu sharhning asosiy cheklovi sifatida hisobga olinishi kerak."
        )
    if language == "ru":
        return (
            f"Настоящий обзор основан на поиске, проведённом {search_date} в базе "
            f"{db_txt} по следующему запросу: \"{search_query}\". В результате поиска "
            f"найдено {per_db_txt} — всего {raw} записей. После удаления дубликатов "
            f"осталось {after} уникальных записей (исключено {dedup}). Из них "
            f"отобрано {selected} по соответствию теме, полноте аннотации и новизне "
            f"публикации.\n\n"
            f"Методологическое примечание: это ВЫБОРОЧНЫЙ (нарративный) обзор, а не "
            f"систематический. Схема PRISMA не применялась, протокол поиска не "
            f"регистрировался предварительно; поэтому результаты не претендуют на "
            f"полноту систематического обзора, а риск публикационного смещения не "
            f"контролировался. Источники отбирались по экспертному решению, а не по "
            f"единым предварительно заданным критериям, что следует учитывать как "
            f"основное ограничение."
        )
    return (
        f"This review is based on a search conducted on {search_date} in {db_txt} "
        f"using the following query: \"{search_query}\". The search returned "
        f"{per_db_txt} — {raw} records in total. After removal of duplicates, {after} "
        f"unique records remained ({dedup} duplicates excluded). Of these, {selected} "
        f"were selected on the basis of topical relevance, completeness of the "
        f"abstract, and recency of publication, and were included in the analysis.\n\n"
        f"Methodological note: this is a SELECTIVE (narrative) review, not a "
        f"systematic review. No PRISMA flow was applied and the search protocol was "
        f"not registered in advance; the findings therefore do not claim the "
        f"completeness of a systematic review, and the risk of publication bias was "
        f"not controlled. Sources were chosen by expert selection rather than by "
        f"uniform pre-specified criteria, which should be regarded as the principal "
        f"limitation of this review."
    )


async def write_section(
    section_title: str, instruction: str, theme_sources: list[dict],
    topic: str, language: str, word_target: int, context: str = "",
    all_source_count: int | None = None,
) -> str:
    """
    Bitta bo'limni yozadi. Model FAQAT shu mavzuning manbalarini ko'radi —
    shuning uchun "har bir manbani sanab chiqish" qilolmaydi va taqqoslashga
    majbur bo'ladi.
    """
    sources_block = gpt_service._format_sources_for_prompt(theme_sources)
    lang = LANG_NAMES.get(language, "ingliz")
    ctx = f"\n\nMAQOLA KONTEXSTI (boshqa bo'limlarda nima yoritilgan):\n{context}\n" if context else ""

    system_prompt = (
        f"Sen tajribali ilmiy muallifsan. {lang} tilida ilmiy maqola bo'limini "
        f"yozasan. Faqat berilgan manbalarga tayanasan.\n" + SECTION_RULES
    )
    user_prompt = f"""MAQOLA MAVZUSI: {topic}
BO'LIM: {section_title}
{ctx}
SHU BO'LIMDA ISHLATILADIGAN MANBALAR ({len(theme_sources)} ta — boshqa manba YO'Q):
{sources_block}

VAZIFA: {instruction}

Hajm: taxminan {word_target} so'z.
Bo'lim {lang} tilida yozilsin. Manbalar [1], [2] kabi raqamlar bilan
iqtibos qilinsin — YUQORIDAGI ro'yxatdagi raqamlar bilan (boshqa raqam ishlatma).

Faqat bo'lim matnini yoz."""

    return await gpt_service._call_gpt(system_prompt, user_prompt, temperature=0.7, max_tokens=3000)


def section_budgets(themes: list[dict], source_count: int,
                    journal_limit: int | None = None) -> dict:
    """
    Har bir bo'limga so'z byudjetini KOD belgilaydi.

    Printsip: mavzu bo'limi o'z manbalarining har biriga ~130 so'z ajratadi
    (5 manba -> ~650 so'z). Shu bilan "yuzaki sanab o'tish" oldini olinadi.
    Jurnal limiti oshib ketsa — hammasi proporsional qisqartiriladi.
    """
    per_source = 130
    theme_b = [max(350, len(th["ids"]) * per_source) for th in themes] or [900]
    b = {
        "themes": theme_b,
        "intro": max(400, int(source_count * 15)),
        "discussion": max(450, int(source_count * 25)),
        "limitations": 260,
        "conclusion": 160,
    }
    total = sum(theme_b) + b["intro"] + b["discussion"] + b["limitations"] + b["conclusion"]
    if journal_limit and total > journal_limit:
        k = journal_limit / total
        b["themes"] = [max(200, int(x * k)) for x in theme_b]
        b["intro"] = max(250, int(b["intro"] * k))
        b["discussion"] = max(300, int(b["discussion"] * k))
        b["limitations"] = max(120, int(b["limitations"] * k))
        b["conclusion"] = max(100, int(b["conclusion"] * k))
    return b


async def write_article_structured(
    topic: str, sources: list[dict], language: str = "en",
    journal_profile: dict | None = None, search_stats: dict | None = None,
    search_query: str = "", databases: list[str] | None = None,
    search_date: str = "", route=None,
) -> tuple[str, list[dict]]:
    """
    Maqolani bo'lim-bo'lim yozadi va birlashtiradi.

    Qaytaradi: (to'liq markdown matn, mavzular ro'yxati)
    """
    jp = journal_profile or {}
    t = TITLES.get(language, TITLES["en"])

    # 1) Mavzular (kod nazorat qiladi)
    themes = await plan_themes(topic, sources, language)

    # So'z byudjeti — KOD belgilaydi (manba soniga qarab), model emas
    budgets = section_budgets(themes, len(sources), jp.get("word_limit_main_text"))
    logger.info("So'z byudjeti: mavzular=%s, kirish=%s, muhokama=%s (jami ~%s)",
                budgets["themes"], budgets["intro"], budgets["discussion"],
                sum(budgets["themes"]) + budgets["intro"] + budgets["discussion"]
                + budgets["limitations"] + budgets["conclusion"])

    # Manbalarni [1..N] global raqamlash uchun xarita
    global_idx = {id(s): i for i, s in enumerate(sources, 1)}

    def relabel(theme_sources: list[dict]) -> list[dict]:
        """
        Mavzu manbalarini GLOBAL raqamlar bilan qaytaradi ([1..N] saqlanadi).

        To'liq matn QISQARTIRILADI: 25 manbaning to'liq matni ~800 000 belgi
        bo'lishi mumkin — bu bitta so'rovning kontekstiga sig'maydi va API xato
        beradi (natijada butun maqola eski usulga qaytib ketardi). Har bir
        manbadan eng muhim qismini olamiz.
        """
        out = []
        for s in theme_sources[:MAX_PROMPT_SOURCES]:
            c = dict(s)
            c["_global_no"] = global_idx.get(id(s))
            ft = (c.get("full_text") or "").strip()
            if len(ft) > MAX_FULLTEXT_CHARS:
                c["full_text"] = ft[:MAX_FULLTEXT_CHARS] + "\n[... matn qisqartirildi ...]"
            out.append(c)
        return out

    # 2) Kirish
    intro_sources = relabel(sources[:min(len(sources), 12)])
    intro = await _guarded(
        "intro",
        write_section,
        t["intro"],
        "Kirish: mavzuning dolzarbligi, nima ma'lum va nima noma'lum ekani. "
        "OXIRIDA aniq tadqiqot savoli/maqsadi va bu sharh mavjud bilimga nima "
        "qo'shishi bo'lsin. Umumiy darslik uslubida yozma.",
        intro_sources, topic, language, budgets["intro"],
        all_source_count=len(sources),
    )

    # 3) Methods — KOD tomonidan
    methods = build_methods_section(
        search_stats or {}, search_query, databases or ["PubMed"],
        search_date, len(sources), language, themes,
    )

    # 4) Mavzu bo'limlari — har biri alohida so'rovda
    theme_blocks = []
    for i, th in enumerate(themes, 1):
        ts = relabel(_assign_sources_by_id(sources, th["ids"]))
        if not ts:
            continue
        body = await _guarded(
            f"theme{i}",
            write_section,
            th["title"],
            f"«{th['title']}» mavzusini chuqur yorit. Berilgan {len(ts)} ta manbani "
            f"O'ZARO taqqoslab yoz, kamida uchtasini ishlat. Manbalar orasida zid "
            f"natijalar bo'lsa, shuni aniq ayt va mumkin bo'lgan sababini ko'rsat.",
            ts, topic, language, budgets["themes"][i - 1],
            context="; ".join(x["title"] for x in themes if x is not th),
            all_source_count=len(sources),
        )
        if body:
            theme_blocks.append((th, body))

    # 5) Muhokama (barcha mavzular ustidan sintez)
    disc_sources = relabel(sources[:min(len(sources), 18)])
    discussion = await _guarded(
        "discussion",
        write_section,
        t["discussion"],
        "Umumiy muhokama: bo'limlardagi dalillarni BIRGALIKDA talqin qil. "
        "Qarama-qarshiliklarni hal qilishga harakat qil, klinik/amaliy ahamiyatini "
        "ko'rsat, dalil kuchini baholang (dalil kuchli yoki zaif, nima uchun).",
        disc_sources, topic, language, budgets["discussion"],
        context="; ".join(x["title"] for x in themes),
        all_source_count=len(sources),
    )

    # 6) Cheklovlar
    lim_sources = relabel(sources[:min(len(sources), 10)])
    limitations = await _guarded(
        "limitations",
        write_section,
        t["limitations"],
        "Cheklovlar: bu sharhning cheklovlari (tanlab olingan, manba soni, "
        "heterogenlik) va keyingi tadqiqotlar uchun yo'nalishlar.",
        lim_sources, topic, language, budgets["limitations"],
        all_source_count=len(sources),
    )

    # 7) Xulosa
    conclusion = await _guarded(
        "conclusion",
        write_section,
        t["conclusion"],
        "Xulosa: 3-5 gap. Faqat matnda allaqachon aytilgan dalillardan kelib "
        "chiqib, asosiy xulosani ber. Yangi fakt yoki yangi manba kiritma.",
        relabel(sources[:min(len(sources), 10)]), topic, language,
        budgets["conclusion"],
        all_source_count=len(sources),
    )

    # 8) Birlashtirish
    parts = [f"## {t['intro']}\n\n{intro}".rstrip()]
    if methods:
        parts.append(f"## {t['methods']}\n\n{methods}")
    for th, body in theme_blocks:
        parts.append(f"## {th['title']}\n\n{body}".rstrip())
    if discussion:
        parts.append(f"## {t['discussion']}\n\n{discussion}".rstrip())
    if limitations:
        parts.append(f"## {t['limitations']}\n\n{limitations}".rstrip())
    if conclusion:
        parts.append(f"## {t['conclusion']}\n\n{conclusion}".rstrip())

    article = "\n\n".join(parts)
    return article, themes


async def _guarded(tag: str, fn, *args, **kwargs) -> str:
    """Bitta bo'lim yiqilsa butun maqola yiqilmasin."""
    for attempt in (1, 2):
        try:
            out = await fn(*args, **kwargs)
            if out and out.strip():
                return out.strip()
        except Exception as e:
            logger.warning("'%s' bo'limi urinish %s da yiqildi: %s", tag, attempt, str(e)[:160])
            if attempt == 1:
                await asyncio.sleep(3)
    logger.error("'%s' bo'limi umuman yozilmadi", tag)
    return ""

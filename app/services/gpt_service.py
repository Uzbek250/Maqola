"""
GPT API: 3 bosqichli yozish tizimi.
1) Outline (reja) - avval maqolaning skeletini tuzadi
2) To'liq maqola - outline asosida, faqat berilgan manbalarga tayanib yozadi
3) Rewrite - Gemini tanqidi asosida qayta yozadi (kerak bo'lganda, 2 martagacha)

MUHIM: har bosqichda "faqat berilgan manbalarga tayan, hech narsa to'qima" qat'iy ta'kidlanadi.
"""
import logging

import httpx
from app.config import OPENAI_API_KEY, GPT_MODEL

logger = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Yangi GPT-5.x / o-seriya "reasoning" modellari eski parametrlarni qabul qilmaydi:
#   - "max_tokens" o'rniga "max_completion_tokens"
#   - "temperature" faqat standart (1) qiymatda ishlaydi, boshqa qiymat 400 beradi
# Shuning uchun so'rov tanasi modelga qarab yig'iladi.
REASONING_PREFIXES = ("gpt-5", "gpt-6", "o1", "o3", "o4")

# Asosiy model 400/404 bersa, navbat bilan shular sinaladi
FALLBACK_GPT_MODELS = ["gpt-5.1", "gpt-5", "gpt-4.1"]


def is_reasoning_model(model: str) -> bool:
    return model.lower().startswith(REASONING_PREFIXES)


def _word_count(text: str) -> int:
    return len(text.split())


def _build_payload(model: str, system_prompt: str, user_prompt: str,
                   temperature: float, max_tokens: int) -> dict:
    """Modelga mos so'rov tanasini yig'adi (eski va yangi GPT'lar uchun)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if is_reasoning_model(model):
        # Reasoning modellar "o'ylash"ga ham token sarflashi mumkin, shuning uchun
        # keng chegara beramiz. Bu qo'shimcha xarajat emas — max_completion_tokens
        # bu SHART, cheklov; faqat model haqiqatda yaratgan token uchun to'lanadi.
        payload["max_completion_tokens"] = max(max_tokens * 3, 8000)
        # temperature qo'llab-quvvatlanmaydi — umuman yuborilmaydi
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = temperature
    return payload

# Til nomini promptga to'g'ri yozish uchun
LANGUAGE_NAMES = {
    "uz": "o'zbek",
    "en": "ingliz (English)",
    "ru": "rus (русский)",
}

# AI-klishelar - bularni ishlatish qat'iyan taqiqlanadi
BANNED_PHRASES_EN = [
    "it is important to note that", "in conclusion, it is clear that", "delve into",
    "in today's world", "plays a crucial role", "furthermore,", "moreover,",
    "it is worth noting", "in the realm of", "navigating the complexities",
    "a testament to", "underscores the importance", "shedding light on",
    "paves the way for", "in an era of", "at the forefront of",
]
BANNED_PHRASES_UZ = [
    "shuni ta'kidlash joizki", "xulosa qilib aytganda", "zamonaviy dunyoda",
    "muhim rol o'ynaydi", "bundan tashqari,", "shu bilan birga,",
    "ta'kidlash lozimki", "yorug'lik sochadi", "yo'l ochadi",
]
BANNED_PHRASES_RU = [
    "важно отметить, что", "в заключение можно сказать", "в современном мире",
    "играет важную роль", "кроме того,", "стоит отметить",
]

MIN_WORDS = 1800
MAX_WORDS = 2500


def _format_sources_for_prompt(sources: list[dict]) -> str:
    lines = []
    for i, s in enumerate(sources, start=1):
        authors = ", ".join(s.get("authors", [])[:3]) or "muallif noma'lum"
        year = s.get("year") or "y.y."
        doi_text = s.get("doi") or "yo'q"
        citation_count = s.get("citation_count")
        citation_note = f", {citation_count} marta iqtibos qilingan" if citation_count else ""
        title = s.get("title", "")
        journal = s.get("journal", "")
        abstract = s.get("abstract", "")

        # To'liq matn bo'lsa — shuni ishlatamiz (Bosqich 3). Model qaysi manba
        # to'liq o'qilganini va qaysi biri faqat abstract ekanini bilishi kerak:
        # abstract'dan aniqlik talab qilib bo'lmaydi.
        full_text = (s.get("full_text") or "").strip()
        if full_text:
            detail = f"    FULL TEXT (open access — primary source of detail):\n{full_text}"
            mark = " [FULL TEXT]"
        else:
            detail = f"    Abstract: {abstract}"
            mark = " [ABSTRACT ONLY]"

        lines.append(
            f'[{i}] {authors} ({year}). "{title}". '
            f"{journal}{citation_note}. DOI: {doi_text}{mark}\n"
            f"{detail}"
        )
    return "\n\n".join(lines)


def _banned_phrases_block(language: str) -> str:
    phrases = {
        "en": BANNED_PHRASES_EN,
        "uz": BANNED_PHRASES_UZ,
        "ru": BANNED_PHRASES_RU,
    }.get(language, BANNED_PHRASES_EN)
    return ", ".join(f'"{p}"' for p in phrases)


# Token narxlari (1 million token uchun, AQSH dollari).
# Manba: OpenAI narxlar jadvali, gpt-5.6 oilasi — 2026-yil 30-iyuldagi pasaytirishdan keyin
# (Luna 80%, Terra 20% arzonlashgan; Sol o'zgarmagan).
PRICING_PER_M = {
    "gpt-5.6-terra": {"in": 2.00, "out": 12.00},
    "gpt-5.6-sol":   {"in": 5.00, "out": 30.00},
    "gpt-5.6-luna":  {"in": 0.20, "out": 1.20},
    "gpt-5.5":       {"in": 5.00, "out": 30.00},
    "gpt-5.4":       {"in": 2.50, "out": 15.00},
    "gpt-5.1":       {"in": 1.25, "out": 10.00},
    "gpt-5":         {"in": 1.25, "out": 10.00},
    "gpt-4.1":       {"in": 2.00, "out": 8.00},
}
DEFAULT_PRICE = {"in": 2.00, "out": 8.00}

# Sarf statistikasi. FAQAT server logiga yoziladi — mijozga qaytarilmaydi,
# chunki bu sizning tannarxingiz (mijoz ko'rmasligi kerak).
USAGE_STATS: dict = {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                     "cost_usd": 0.0, "by_model": {}}


def _price_for(model: str) -> dict:
    """Model nomiga mos narxni topadi. Uzunroq moslik ustun (gpt-5.6 vs gpt-5)."""
    for name in sorted(PRICING_PER_M, key=len, reverse=True):
        if model.startswith(name):
            return PRICING_PER_M[name]
    return DEFAULT_PRICE


def _record_usage(model: str, usage: dict) -> float:
    """Token sarfini hisoblab statistikaga qo'shadi va shu chaqiruv narxini qaytaradi."""
    in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    price = _price_for(model)
    cost = in_tok / 1_000_000 * price["in"] + out_tok / 1_000_000 * price["out"]

    USAGE_STATS["calls"] += 1
    USAGE_STATS["input_tokens"] += in_tok
    USAGE_STATS["output_tokens"] += out_tok
    USAGE_STATS["cost_usd"] += cost

    per = USAGE_STATS["by_model"].setdefault(model, {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
    per["calls"] += 1
    per["in"] += in_tok
    per["out"] += out_tok
    per["cost"] += cost

    logger.info("GPT (%s): %s kirish + %s chiqish token = $%.4f (maqola jami: $%.4f)",
                model, in_tok, out_tok, cost, USAGE_STATS["cost_usd"])
    return cost


async def _call_gpt(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    """
    GPT'ni chaqiradi. Model eski parametrlarni qabul qilmasa (400) yoki model
    topilmasa (404), avtomatik ravishda zaxira modelga o'tadi.
    Xato bo'lsa — sabab serverga log qilinadi, lekin mijozga ko'rsatilmaydi.
    """
    last_error = None
    models = [GPT_MODEL] + [m for m in FALLBACK_GPT_MODELS if m != GPT_MODEL]

    async with httpx.AsyncClient(timeout=180.0) as client:
        for model in models:
            payload = _build_payload(model, system_prompt, user_prompt, temperature, max_tokens)
            try:
                resp = await client.post(
                    OPENAI_URL,
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json=payload,
                )
            except httpx.RequestError as e:
                logger.warning("GPT (%s) tarmoq xatosi: %s", model, e)
                last_error = e
                continue

            if resp.status_code >= 400:
                # Xatoning HAQIQIY sababini server logiga yozamiz
                logger.error("GPT (%s) HTTP %s: %s", model, resp.status_code, resp.text[:500])
                if resp.status_code in (400, 404, 422):
                    last_error = RuntimeError(f"{model}: HTTP {resp.status_code}")
                    continue  # model/parametr muammosi — zaxirani sinab ko'ramiz
                resp.raise_for_status()

            try:
                content = resp.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError) as e:
                logger.error("GPT (%s) javobi kutilgan shaklda emas: %s", model, resp.text[:300])
                last_error = e
                continue

            # Token sarfi va xarajatni hisobga olamiz (logga yoziladi)
            try:
                _record_usage(model, resp.json().get("usage") or {})
            except Exception:
                logger.warning("Token sarfini hisoblab bo'lmadi (model=%s)", model)

            if content and content.strip():
                if model != GPT_MODEL:
                    logger.info("Javob zaxira GPT modeli orqali olindi: %s", model)
                return content

            logger.warning("GPT (%s) bo'sh javob qaytardi (finish_reason=%s)",
                           model, resp.json().get("choices", [{}])[0].get("finish_reason"))
            last_error = RuntimeError(f"{model}: bo'sh javob")

    raise RuntimeError(f"GPT javob bermadi (barcha modellar sinaldi): {last_error}")


async def generate_outline(topic: str, sources: list[dict], language: str = "en") -> str:
    """
    1-bosqich: to'liq maqoladan oldin qisqa reja (outline) tuziladi.
    Bu yozish jarayonini tuzilishli qiladi va GPT'ning "mavzudan chetga chiqishi"
    yoki manbalarni noto'g'ri ishlatishi ehtimolini kamaytiradi.
    """
    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    sources_block = _format_sources_for_prompt(sources)

    system_prompt = (
        "Sen tajribali ilmiy muharrirsan. Vazifang - maqola yozishdan oldin aniq, "
        "mantiqiy reja (outline) tuzish. Faqat berilgan manbalarga tayaning."
    )
    user_prompt = f"""Mavzu: {topic}

MANBALAR:
{sources_block}

Yuqoridagi manbalarni tahlil qilib, ilmiy maqola uchun batafsil outline (reja) tuz.
Outline {lang_name} tilida bo'lsin.

Har bir bo'lim uchun:
- Bo'lim nomi
- Nima haqida yozilishi (2-3 gap bilan)
- Qaysi manbalar ([1], [2] kabi raqamlar bilan) shu bo'limda ishlatiladi

Bo'limlar: Kirish, Adabiyotlar sharhi, Muhokama, Xulosa.
Faqat outline'ni yoz, to'liq matn emas."""

    return await _call_gpt(system_prompt, user_prompt, temperature=0.6, max_tokens=1200)


async def write_article(
    topic: str,
    sources: list[dict],
    citation_style: str = "vancouver",
    language: str = "en",
    outline: str | None = None,
    search_query: str | None = None,
    databases: list[str] | None = None,
    journal_profile: dict | None = None,
) -> str:
    """
    2-bosqich: outline asosida to'liq ilmiy maqola yoziladi.
    Uzunlik 1800-2500 so'z bilan cheklanadi, AI-klishelar qat'iy taqiqlanadi.

    `journal_profile` berilsa — maqola nishon jurnal talabiga mos yoziladi
    (so'z limiti, majburiy bo'limlar, havola soni) — Bosqich 2.
    """
    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    sources_block = _format_sources_for_prompt(sources)
    banned = _banned_phrases_block(language)

    # Nishon jurnal talablari. So'z limiti jurnal talabidan kelib chiqib toraytiriladi:
    # jurnal 2000 so'z desa, 2500 yozish muvofiqlikni buzadi.
    jp = journal_profile or {}
    eff_min, eff_max = MIN_WORDS, MAX_WORDS
    jl = jp.get("word_limit_main_text")
    if jl and jl < eff_max:
        eff_max = int(jl)
        eff_min = min(eff_min, int(jl * 0.8))

    jlines = []
    if jp.get("name") and jp.get("key") not in (None, "generic"):
        jlines.append(f"- Nishon jurnal: {jp['name']}")
    if jl:
        jlines.append(f"- Asosiy matn so'z limiti: {jl} so'z — BUNDAN OSHMASIN")
    if jp.get("required_sections"):
        jlines.append(
            "- Bu bo'limlar MAJBURIY va sarlavhalari AYNAN quyidagicha yozilsin "
            "(boshqa nom bermang, birlashtirmang, tashlab ketmang): "
            + " / ".join(jp["required_sections"])
        )
    if jp.get("abstract_type") == "structured" and jp.get("abstract_sections"):
        jlines.append("- Abstract tuzilmasi: " + ", ".join(jp["abstract_sections"]))
    if jp.get("max_references"):
        jlines.append(f"- Havolalar soni {jp['max_references']} tadan oshmasin. "
                      f"Senga {len(sources)} ta manba berilgan — ortiqchasini ishlatma, "
                      f"keraksizlarini tashlab ket.")
    journal_block = ("\n\nNISHON JURNAL TALABLARI (bularga qat'iy amal qil):\n"
                     + "\n".join(jlines)) if jlines else ""

    outline_block = f"\n\nTAYYORLANGAN OUTLINE (shu rejaga qat'iy amal qil):\n{outline}" if outline else ""

    # Metodologiya bo'limi HAQIQIY ma'lumotga tayanishi kerak — to'qilmasin
    db_list = ", ".join(databases or ["PubMed", "Semantic Scholar"])
    method_block = f"""
MAJBURIY "Methods / Search Strategy" BO'LIMI:
Maqolaga manbalar qanday topilganini yozuvchi qisqa bo'lim qo'sh (Kirishdan keyin).
FAQAT quyidagi HAQIQIY ma'lumotlarni ishlat:
- Ma'lumot bazalari: {db_list}
- Qidiruv so'rovi (inglizcha kalit so'zlar): {search_query or topic}
- Tanlangan manbalar soni: {len(sources)} ta
- Saralash mezoni: mavzuga moslik, abstract to'liqligi va manbaning yangiligi
Bu bo'limda aniq raqamlar (nechta topildi/tanlandi) faqat yuqoridagilar bo'lsin —
o'zingdan qo'shimcha son, sana yoki baza O'YLAB TOPMA.""" if search_query else ""

    system_prompt = f"""Sen 15 yillik tajribaga ega ilmiy muallifsan, ko'plab jurnallarda nashr etilgan
maqolalar yozgansan. Yozish uslubing tabiiy, ekspert darajasida va HECH QACHON AI matniga
o'xshamaydi.

QAT'IY QOIDALAR:
1. Faqat senga berilgan manbalarga tayaning. Hech qanday manba, statistika, tadqiqot natijasini
   O'YLAB TOPMA (hallucination qat'iyan taqiqlanadi). Agar fikringni tasdiqlovchi manba bo'lmasa,
   uni umumiy tarzda yoz yoki umuman yozma.
2. Quyidagi klishe iboralarni HECH QACHON ishlatma: {banned}
3. Gaplar uzunligi va tuzilishi XILMA-XIL bo'lsin. Ketma-ket bir xil uzunlikdagi yoki bir xil
   grammatik tuzilishdagi gaplar yozish taqiqlanadi - bu AI matniga xos belgi.
4. Paragraflar orasida tabiiy o'tish bo'lsin, mexanik ravishda emas.
5. Maqola {eff_min}-{eff_max} so'z oralig'ida bo'lishi SHART; nishon ~{(eff_min+eff_max)//2} so'z.
   Oraliqdan OSHIB KETSANGIZ matn rad etiladi va qayta ishlanadi - bo'lim sonini ko'paytirib
   uzaytirmang, keraksiz takror yozmang. Yozib bo'lgach so'z sonini o'zingiz tekshiring.
6. SARLAVHA HALOLLIGI: sarlavha maqolada HAQIQATDA bor narsani va'da qilsin. Agar manbalar
   biror mexanizmni bevosita ko'rsatmasa, sarlavhada "Potential", "Possible", "Hypothetical",
   "Implications" kabi ehtiyotkor so'zlarni ishlat - to'g'ridan-to'g'ri dalil borga o'xshab
   ko'rsatma. Mashhur atamani (masalan, dori yoki signal yo'lini) sarlavhaga maqolada u haqda
   yetarli ma'lumot bo'lmasa qo'yma.
7. MEXANIZM CHUQURDGI: mexanizm qismida, agar manbalarda aytilgan bo'lsa, ANIQ molekulyar
   yo'llarni nomla (retseptorlar, fermentlar, genlar, sitokinlar, metabolitlar - masalan
   "SCFA -> FFAR2/3", "bile acids -> TGR5", "AMPK", "mTOR", "circadian clock genlari").
   Manbalarda bu darajadagi ma'lumot bo'lmasa, umumiy gap bilan cheklan va buni ochiq ayt.
8. ZIDDIYATLARNI MUHOKAMA QIL: manbalar bir-biriga qarama-qarshi natija bersa (birida
   yaxshilanish bor, boshqasida farq yo'q), buni YASHIRMA - alohida paragrafda ochiq
   solishtir: nima uchun farq bo'lishi mumkin (dizayn, populyatsiya, davomiylik, doza).
   Faqat "bir ovozdan" ko'rinish berish ilmiy noaniqlikni yashiradi.
9. CHEKLOVLARNI OCHIQ YOZ: "Xulosa"dan oldin, agar mavjud bo'lsa, dalillarning zaif joylarini
   (kichik namuna, qisqa kuzatuv, heterojenlik) alohida belgila.
10. Maqolani BITTA markdown H1 sarlavha bilan boshla (# Sarlavha), keyin bo'limlar H2 (##) bilan
    bo'lsin. Sarlavha va butun matn {lang_name} tilida bo'lishi SHART - sarlavhani boshqa
    tilda yozma.
11. DALIL KUCHIGA MOS BO'L: har bir asosiy da'vo qanday tadqiqotga tayanishini aniq yoz -
    dizayn (RCT, kohort, meta-analiz, crossover) va ISHTIROKCHILAR SONI (n). Agar maqolaning
    MARKAZIY xulosasi BITTA kichik tadqiqotga (n < 100) tayansa, buni XULOSADA ham,
    SARLAVHADA ham ochiq tan ol - bitta kichik tadqiqotdan keng umumiy xulosa chiqarma.
    "Bir nechta mustaqil tadqiqotlar tasdiqlaydi" deb yozma, agar aslida bitta bo'lsa.
12. TAKRORLANISHDAN SAQLAN: ehtiyotkorlik iboralarini ("does not establish", "cannot determine",
    "does not demonstrate", "remains unclear") bir xil shaklda qayta-qayta ishlatma. Har xil
    ifoda ishlat ("the data are insufficient to conclude", "this finding should be read with
    caution", "the evidence base is too narrow to generalise", "no such effect was observed",
    "the trial was not powered to detect...") - va ularni faqat HAQIQATAN kerak joyda
    ishlat, har paragrafga qo'shma.
13. OXIRIDA IKKI BO'LIM QO'SH (jurnal talab qiladi):
    "## Conflicts of Interest" - "The author declares no conflicts of interest." (agar
    manbalarda boshqacha ma'lumot bo'lmasa shu standart jumla)
    "## Funding" - "This work received no specific grant from any funding agency." (agar
    manbalarda grant haqida ma'lumot bo'lmasa shu standart jumla)
    Bu bo'limlarga o'zingdan grant raqami yoki tashkilot nomi O'YLAB TOPMA."""

    user_prompt = f"""Mavzu: {topic}

MANBALAR:
{sources_block}
{outline_block}
{method_block}
{journal_block}

Maqolani {lang_name} tilida, {citation_style} sitata usulida yoz.

Tuzilma:
1. Kirish - mavzuning dolzarbligi, maqsad
2. Methods / Search Strategy - manbalar qanday topilgani (yuqoridagi MAJBURIY blokka qarang)
3. Adabiyotlar sharhi - berilgan manbalarni tahlil qilib, taqqoslab
4. Muhokama - manbalardagi natijalarni solishtirish, farq va o'xshashliklarni ko'rsatish
5. Xulosa - asosiy topilmalar, cheklovlar, kelajakdagi tadqiqot yo'nalishlari
6. Conflicts of Interest va Funding bo'limlari (oxirida)

Matn ichida [1], [2] kabi raqamli izohlar bilan manbaga ishora qil (bu raqamlar yuqoridagi
manbalar tartibiga mos keladi). Manbalar ro'yxatini o'zing yozma - buni tizim alohida qo'shadi.

ESLATMA: maqola so'z soni {MIN_WORDS} dan kam va {MAX_WORDS} dan ko'p bo'lmasligi kerak."""

    return await _call_gpt(system_prompt, user_prompt, temperature=0.85, max_tokens=4000)


async def rewrite_article(
    original_text: str,
    review_feedback: dict,
    sources: list[dict],
    language: str = "en",
) -> str:
    """
    3-bosqich: Gemini'ning tanqidiy fikri asosida GPT maqolani qayta yozadi.
    """
    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    sources_block = _format_sources_for_prompt(sources)
    banned = _banned_phrases_block(language)
    issues = "\n".join(f"- {p}" for p in review_feedback.get("topilgan_muammolar", []))
    suggestions = "\n".join(f"- {s}" for s in review_feedback.get("tuzatish_tavsiyalari", []))

    system_prompt = f"""Sen ilmiy matnni retsenzent fikri asosida tuzatuvchi tajribali muharrirsan.
Klishe iboralarni ishlatma: {banned}
Maqola {MIN_WORDS}-{MAX_WORDS} so'z oralig'ida qolishi kerak."""

    user_prompt = f"""Quyidagi maqolani retsenzent tanqid qildi. Muammolarni TO'LIQ tuzatib,
matnni {lang_name} tilida qayta yoz. Faqat berilgan manbalarga tayan, hech qanday yangi
manba to'qima.

ASL MATN:
{original_text}

MANBALAR:
{sources_block}

RETSENZENT TOPGAN MUAMMOLAR:
{issues}

TUZATISH TAVSIYALARI:
{suggestions}

Yuqoridagi barcha muammolarni hisobga olib, to'liq tuzatilgan matnni yoz."""

    return await _call_gpt(system_prompt, user_prompt, temperature=0.75, max_tokens=4000)


async def adjust_length(
    article_text: str,
    sources: list[dict],
    language: str = "en",
    min_words: int = 1800,
    max_words: int = 2500,
    max_attempts: int = 3,
) -> str:
    """
    Maqolani belgilangan so'z oralig'iga keltiradi.

    Nega takroriy: bir marta so'rash yetarli emas — model ko'pincha talabni to'liq
    bajarmaydi (kuzatildi: 2742 so'z). Shuning uchun bir necha marta urinamiz va
    faqat YAXSHILANGAN natijani saqlaymiz; natija yaxshilanmasa to'xtaymiz.
    """
    current = _word_count(article_text)
    if min_words <= current <= max_words:
        return article_text

    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    target = (min_words + max_words) // 2

    for attempt in range(1, max_attempts + 1):
        over = current > max_words
        action = "qisqartir" if over else "kengaytir"
        delta = abs(current - target)

        system_prompt = (
            f"Sen ilmiy matn muharririsan. Vazifang - matnni {action}ish, mazmunini "
            f"o'zgartirmasdan. Yangi fakt, raqam yoki manba QO'SHMA."
        )
        extra = (
            f"\n- Matn {delta} so'zga {action}ilsin. Buning uchun eng kam muhim "
            f"kichik bo'limlarni BIRLASHTIR yoki olib tashla; jumlalarni ichidan "
            f"takrorlarni olib tashla. Bo'lim sonini kamaytirish mumkin."
            if over else ""
        )
        user_prompt = f"""Quyidagi ilmiy maqola {current} so'zdan iborat ({attempt}-urinish).
Uni {action}ib, ANIQ {target} so'zga keltir (ruxsat etilgan oraliq: {min_words}-{max_words}).

QAT'IY TALABLAR:
- Matn {lang_name} tilida qolsin (tarjima qilma).
- Markdown sarlavhalar (#, ##, ###) saqlansin.
- [1], [2] kabi manba havolalari saqlansin va to'g'ri joyda qolsin.
- Yangi fakt, raqam, statistika QO'SHMA. Faqat mavjudini ixchamlashtir.{extra}

MANBALAR (faqat shularga tayan):
{_format_sources_for_prompt(sources)}

MAQOLA:
{article_text}

Endi {action}ilgan TO'LIQ matnni yoz (izoh, kirish so'zi qo'shma)."""

        try:
            result = await _call_gpt(system_prompt, user_prompt, temperature=0.3, max_tokens=4000)
        except Exception:
            logger.exception("Uzunlikni moslashtirish urinishi muvaffaqiyatsiz (%s-urinish)", attempt)
            break

        new_count = _word_count(result)
        logger.info("Uzunlik moslashuvi %s-urinish: %s -> %s so'z (nishon %s)",
                    attempt, current, new_count, target)

        # Faqat yaxshilangan natijani qabul qilamiz
        if abs(new_count - target) < abs(current - target):
            article_text, current = result, new_count
        else:
            logger.warning("Uzunlik yaxshilanmadi — oldingi matn saqlanadi")
            break

        if min_words <= current <= max_words:
            break

    return article_text

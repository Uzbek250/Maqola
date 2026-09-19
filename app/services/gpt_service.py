"""
GPT API: 3 bosqichli yozish tizimi.
1) Outline (reja) - avval maqolaning skeletini tuzadi
2) To'liq maqola - outline asosida, faqat berilgan manbalarga tayanib yozadi
3) Rewrite - Gemini tanqidi asosida qayta yozadi (kerak bo'lganda, 2 martagacha)

MUHIM: har bosqichda "faqat berilgan manbalarga tayan, hech narsa to'qima" qat'iy ta'kidlanadi.
"""
import httpx
from app.config import OPENAI_API_KEY, GPT_MODEL

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

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
        lines.append(
            f'[{i}] {authors} ({year}). "{title}". '
            f"{journal}{citation_note}. DOI: {doi_text}\n"
            f"    Abstract: {abstract}"
        )
    return "\n\n".join(lines)


def _banned_phrases_block(language: str) -> str:
    phrases = {
        "en": BANNED_PHRASES_EN,
        "uz": BANNED_PHRASES_UZ,
        "ru": BANNED_PHRASES_RU,
    }.get(language, BANNED_PHRASES_EN)
    return ", ".join(f'"{p}"' for p in phrases)


async def _call_gpt(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": GPT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


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
) -> str:
    """
    2-bosqich: outline asosida to'liq ilmiy maqola yoziladi.
    Uzunlik 1800-2500 so'z bilan cheklanadi, AI-klishelar qat'iy taqiqlanadi.
    """
    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    sources_block = _format_sources_for_prompt(sources)
    banned = _banned_phrases_block(language)

    outline_block = f"\n\nTAYYORLANGAN OUTLINE (shu rejaga qat'iy amal qil):\n{outline}" if outline else ""

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
5. Maqola {MIN_WORDS}-{MAX_WORDS} so'z oralig'ida bo'lishi SHART. Bundan qisqa yoki uzun bo'lmasin."""

    user_prompt = f"""Mavzu: {topic}

MANBALAR:
{sources_block}
{outline_block}

Maqolani {lang_name} tilida, {citation_style} sitata uslubida yoz.

Tuzilma:
1. Kirish - mavzuning dolzarbligi, maqsad
2. Adabiyotlar sharhi - berilgan manbalarni tahlil qilib, taqqoslab
3. Muhokama - manbalardagi natijalarni solishtirish, farq va o'xshashliklarni ko'rsatish
4. Xulosa - asosiy topilmalar, cheklovlar, kelajakdagi tadqiqot yo'nalishlari

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

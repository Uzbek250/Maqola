"""
Gemini API: 1) mavzu generatsiyasi  2) yakuniy maqolani QATTIQ tekshirish/tanqid qilish
"""
import logging

import httpx
import json
from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Google modelni o'chirsa yoki 503 ("high demand") bersa, navbat bilan shular sinaladi.
FALLBACK_GEMINI_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

LANGUAGE_NAMES = {"uz": "o'zbek", "en": "ingliz (English)", "ru": "rus (русский)"}


async def _call_gemini(prompt: str, temperature: float = 0.7) -> str:
    """
    Gemini'ni chaqiradi. Model o'chirilgan (404), yuklangan (503) yoki kvota
    tugagan (429) bo'lsa — avtomatik zaxira modelga o'tadi.

    MUHIM: API kalit URL ichida EMAS, `x-goog-api-key` sarlavhasida yuboriladi.
    Ilgari kalit URL'da edi va httpx xatosi matni bilan birga MIJOZGA ochiq
    ko'rinardi (kalit oqib ketardi).
    """
    last_error = None
    models = [GEMINI_MODEL] + [m for m in FALLBACK_GEMINI_MODELS if m != GEMINI_MODEL]

    async with httpx.AsyncClient(timeout=120.0) as client:
        for model in models:
            url = GEMINI_URL_TMPL.format(model=model)
            try:
                resp = await client.post(
                    url,
                    headers={"x-goog-api-key": GEMINI_API_KEY},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": temperature},
                    },
                )
            except httpx.RequestError as e:
                logger.warning("Gemini (%s) tarmoq xatosi: %s", model, e)
                last_error = e
                continue

            if resp.status_code >= 400:
                # Haqiqiy sabab server logiga yoziladi, mijozga ko'rsatilmaydi
                logger.error("Gemini (%s) HTTP %s: %s", model, resp.status_code, resp.text[:400])
                last_error = RuntimeError(f"{model}: HTTP {resp.status_code}")
                if resp.status_code in (400, 403, 404, 429, 500, 502, 503, 504):
                    continue  # keyingi modelni sinab ko'ramiz
                resp.raise_for_status()

            try:
                data = resp.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
            except (KeyError, IndexError, ValueError, TypeError) as e:
                logger.error("Gemini (%s) javobi kutilgan shaklda emas: %s", model, resp.text[:300])
                last_error = e
                continue

            if text:
                if model != GEMINI_MODEL:
                    logger.info("Javob zaxira Gemini modeli orqali olindi: %s", model)
                return text

            logger.warning("Gemini (%s) bo'sh javob qaytardi (finish_reason=%s)",
                           model, data.get("candidates", [{}])[0].get("finishReason"))
            last_error = RuntimeError(f"{model}: bo'sh javob")

    raise RuntimeError(f"Gemini javob bermadi (barcha modellar sinaldi): {last_error}")


async def generate_topics(direction: str) -> list[str]:
    prompt = f"""Sen ilmiy tadqiqot yo'nalishlari bo'yicha ekspertsan.

Yo'nalish: {direction}

Shu yo'nalishda hozirgi kunda dolzarb, lekin hali keng yoritilmagan 10 ta TOR (aniq, keng bo'lmagan) ilmiy maqola mavzusini taklif qil.

FAQAT quyidagi JSON formatida javob ber, boshqa hech narsa yozma (izoh, markdown belgilar ham kerak emas):
{{"topics": ["mavzu 1", "mavzu 2", ...]}}
"""
    raw = await _call_gemini(prompt, temperature=0.9)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(raw)
        return parsed.get("topics", [])
    except json.JSONDecodeError:
        return [line.strip("- ").strip() for line in raw.split("\n") if line.strip()][:10]


def _word_count(text: str) -> int:
    return len(text.split())


async def review_article(
    article_text: str,
    sources: list[dict],
    language: str = "en",
    min_words: int = 1800,
    max_words: int = 2500,
) -> dict:
    """
    Gemini yozilgan maqolani QATTIQ tekshiradi - retsenzent kabi, yumshoq baho bermaydi.
    Manbalarga moslik, mantiq, uslub, uzunlik va klishe borligini tekshiradi.
    """
    lang_name = LANGUAGE_NAMES.get(language, "ingliz")
    unknown_year = "yil noma'lum"
    sources_summary = "\n".join(
        f"- [{i+1}] {s['title']} ({s.get('year') or unknown_year}) - {s['abstract'][:200]}..."
        for i, s in enumerate(sources)
    )
    word_count = _word_count(article_text)

    prompt = f"""Sen QATTIQQO'L ilmiy jurnal muharriri va retsenzentsan (peer reviewer). Sening
vazifang - maqolani iloji boricha tanqidiy va halol baholash. Yengil yoki "hammasi yaxshi"
degan baho berish SENING VAZIFANGA ZID - agar kamchilik topmasang, buni alohida tekshirib chiq,
chunki AI yozgan matnda deyarli har doim tuzatiladigan narsa bo'ladi.

MANBALAR (maqola FAQAT shularga asoslanishi kerak edi):
{sources_summary}

MAQOLA MATNI ({lang_name} tilida bo'lishi kerak edi, {word_count} so'zdan iborat,
talab qilingan uzunlik {min_words}-{max_words} so'z):
{article_text}

QATTIQ TEKSHIR:
1. HALLUCINATION: maqoladagi HAR BIR da'vo, raqam, statistika berilgan manbalarda bormi?
   Manbada yo'q narsa aytilgan bo'lsa - bu ENG JIDDIY muammo, alohida ko'rsat.
2. Manbalarga to'g'ri ishora qilinganmi ([1], [2] raqamlari mantiqan to'g'ri joyda ishlatilganmi)?
3. Mantiqiy uzilish yoki qarama-qarshilik bormi?
4. Til: matn chindan ham {lang_name} tilida yozilganmi, aralash til yo'qmi?
5. Uzunlik: {word_count} so'z, talab {min_words}-{max_words}. Agar bu oraliqdan tashqarida
   bo'lsa, buni "topilgan_muammolar"ga aniq yoz.
6. AI-klishe iboralar bormi (masalan "shuni ta'kidlash joizki", "it is important to note",
   "важно отметить" kabi umumiy, mazmunsiz iboralar)?
7. Uslub jonli va ekspert darajasidami, yoki mexanik/shablon ko'rinishidami?

FAQAT quyidagi JSON formatida javob ber:
{{
  "manbalarga_moslik": "yaxshi/qoniqarli/yomon",
  "hallucination_topildi": true yoki false,
  "uzunlik_muammosi": true yoki false,
  "topilgan_muammolar": ["muammo 1", "muammo 2", ...],
  "tuzatish_tavsiyalari": ["tavsiya 1", "tavsiya 2", ...],
  "umumiy_baho": "qisqa umumiy xulosa"
}}
"""
    raw = await _call_gemini(prompt, temperature=0.2)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(raw)
        result.setdefault("hallucination_topildi", False)
        result.setdefault("uzunlik_muammosi", False)
        return result
    except json.JSONDecodeError:
        return {
            "manbalarga_moslik": "noma'lum",
            "hallucination_topildi": False,
            "uzunlik_muammosi": False,
            "topilgan_muammolar": [],
            "tuzatish_tavsiyalari": [],
            "umumiy_baho": raw,
        }


def needs_rewrite(review: dict) -> bool:
    """
    Majburiy qayta yozish shartlari:
    - manbalarga moslik "yomon"
    - hallucination topilgan bo'lsa
    - uzunlik muammosi bo'lsa
    - 3 tadan ko'p muammo topilgan bo'lsa
    """
    return (
        review.get("manbalarga_moslik") == "yomon"
        or review.get("hallucination_topildi") is True
        or review.get("uzunlik_muammosi") is True
        or len(review.get("topilgan_muammolar", [])) >= 3
    )

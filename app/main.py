from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import asyncio
import io
import logging
import os
import time
import uuid

from app.services import sources as sources_service
from app.services import gemini_service
from app.services import gpt_service
from app.services import document_builder

# Xatolarning haqiqiy sababi Render loglarida ko'rinishi uchun
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

app = FastAPI(title="Maqola Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo uchun; productionda aniq domenga cheklang
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")

SESSION_STORE: dict[str, dict] = {}

# Fon vazifalari (job) holati. /generate 60-285 soniya davom etgani uchun HTTP
# so'rovni shuncha ushlab turish yomon: proksi/browser timeout beradi va mijoz
# "ishlamayapti" deb o'ylaydi. Endi so'rov darhol job_id qaytaradi, natija
# /jobs/{id} orqali so'rab olinadi.
JOBS: dict[str, dict] = {}
MAX_JOBS = 100          # xotira o'smasligi uchun eng oxirgi 100 ta job saqlanadi
JOB_TTL_SECONDS = 3600  # 1 soatdan keyin eski joblar o'chiriladi


def _prune_jobs() -> None:
    """Eski/tugagan joblarni tozalaydi — xotira cheksiz o'smasin."""
    now = time.time()
    stale = [jid for jid, j in JOBS.items()
             if j.get("finished_at") and now - j["finished_at"] > JOB_TTL_SECONDS]
    for jid in stale:
        JOBS.pop(jid, None)

    if len(JOBS) > MAX_JOBS:
        done = sorted((kv for kv in JOBS.items() if kv[1].get("finished_at")),
                      key=lambda kv: kv[1]["finished_at"])
        for jid, _ in done[:len(JOBS) - MAX_JOBS]:
            JOBS.pop(jid, None)


async def _progress(job: dict | None, percent: int, step: str) -> None:
    """Job progressini yangilaydi (job=None bo'lsa — sinxron rejim, hech narsa qilmaydi)."""
    if job is None:
        return
    # Faqat oldinga siljiydi — parallel bosqichlar orqaga qaytarmasin
    job["progress"] = max(job.get("progress", 0), percent)
    job["step"] = step
    logger.info("Job %s: %s%% — %s", job.get("id"), job["progress"], step)
    await asyncio.sleep(0)  # event loop'ga boshqa so'rovlarni bajarish imkonini ber

MIN_WORDS = 1800
MAX_WORDS = 2500
MAX_REWRITE_ATTEMPTS = 2  # majburiy qayta yozish - 2 martagacha


class TopicRequest(BaseModel):
    direction: str


class GenerateRequest(BaseModel):
    topic: str
    is_medical: bool = True
    citation_style: str = "vancouver"  # "vancouver" yoki "apa"
    language: str = "en"  # "uz", "en", "ru"


@app.get("/")
async def root():
    return FileResponse(FRONTEND_PATH)


@app.get("/health")
async def health():
    return {"status": "ishlayapti"}


@app.post("/topics")
async def get_topics(req: TopicRequest):
    """Yo'nalish bo'yicha 10 ta mavzu taklifi (Gemini)."""
    try:
        topics = await gemini_service.generate_topics(req.direction)
        return {"topics": topics}
    except Exception as e:
        # Ichki tafsilot (kalit, URL) mijozga chiqmasligi uchun logga yozamiz
        logger.exception("Mavzu generatsiyasida xato")
        raise HTTPException(
            status_code=502,
            detail="AI xizmatiga ulanib bo'lmadi. Bir ozdan keyin qayta urinib ko'ring.",
        )


async def _run_pipeline(req: GenerateRequest, job: dict | None = None) -> dict:
    """
    To'liq oqim (fon vazifasida ham, sinxron rejimda ham ishlatiladi):
    1. Haqiqiy manbalarni topish (PubMed/Semantic Scholar) - yangilik va citation
       soni bo'yicha saralangan eng sifatli manbalar
    2. Outline (reja) tuzish (GPT)
    3. Outline asosida to'liq maqola yozish (GPT)
    4. Gemini bilan qattiq tekshirish
    5. Agar muammo topilsa - GPT bilan qayta yozish (2 martagacha, har safar qayta tekshiriladi)
    6. Session'ga saqlash (docx yuklab olish uchun)

    `job` berilsa — har bosqichda progress yangilanadi. Xatolar HTTPException
    ko'rinishida ko'tariladi; fon vazifasi ularni ushlab, job holatiga yozadi.
    """
    if req.language not in ("uz", "en", "ru"):
        raise HTTPException(status_code=400, detail="language 'uz', 'en' yoki 'ru' bo'lishi kerak")

    await _progress(job, 5, "Mavzu tahlil qilinmoqda")

    # Mavzu o'zbek/rus tilida bo'lishi mumkin, lekin PubMed faqat inglizchani indekslaydi.
    # Shuning uchun avval mavzuni inglizcha kalit so'zlarga aylantiramiz — aks holda
    # butun o'zbekcha jumla qidirilib, 0 natija qaytadi.
    search_query = await gemini_service.to_search_query(req.topic)
    logger.info("Qidiruv so'rovi: %r -> %r", req.topic[:80], search_query)

    await _progress(job, 15, "Ilmiy manbalar qidirilmoqda")

    found_sources = await sources_service.find_sources(
        search_query, prefer_medical=req.is_medical, max_results=10
    )

    # Topilmasa — yanada kengroq (kamroq kalit so'zli) so'rov bilan bir marta qayta urinamiz
    if not found_sources:
        wider = " ".join(search_query.split()[:3])
        if wider and wider != search_query:
            logger.info("Manba topilmadi — kengroq so'rov sinaladi: %r", wider)
            found_sources = await sources_service.find_sources(
                wider, prefer_medical=req.is_medical, max_results=10
            )

    if not found_sources:
        raise HTTPException(
            status_code=404,
            detail=("Bu mavzu bo'yicha ilmiy manba topilmadi. Mavzuni soddaroq yoki "
                    "umumiyroq yozib ko'ring (masalan: \"type 2 diabetes glucose "
                    "monitoring\")."),
        )

    await _progress(job, 25, "Manba ma'lumotlari tekshirilmoqda (DOI)")

    # DOI si yo'q manbalar uchun sarlavha bo'yicha DOI topamiz (ro'yxat bir xil
    # ko'rinishda bo'lsin), keyin mavjudlarni Crossref orqali tekshiramiz.
    try:
        found_sources = await sources_service.backfill_missing_dois(found_sources)
        found_sources = await sources_service.validate_dois(found_sources)
    except Exception:
        logger.exception("DOI tekshiruvi ishlamadi — DOI lar tekshirilmasdan qoldiriladi")

    # Metodologiya bo'limi haqiqiy ma'lumotga tayanishi uchun
    databases = sorted({str(s.get("source")) for s in found_sources if s.get("source")})
    logger.info("Manbalar: %s ta | bazalar: %s | so'rov: %r",
                len(found_sources), databases, search_query)

    await _progress(job, 35, "Maqola rejasi tuzilmoqda")

    try:
        outline = await gpt_service.generate_outline(req.topic, found_sources, req.language)

        await _progress(job, 45, "Maqola yozilmoqda")
        article_text = await gpt_service.write_article(
            req.topic, found_sources, req.citation_style, req.language, outline=outline,
            search_query=search_query, databases=databases,
        )
    except Exception:
        logger.exception("Maqola yozishda xato (mavzu=%r)", req.topic)
        raise HTTPException(
            status_code=502,
            detail="Maqola yozishda AI xizmatida xatolik yuz berdi. Qayta urinib ko'ring.",
        )

    # Tekshirish bosqichi. MUHIM: bu bosqich yiqilsa ham maqola YO'QOLMASLIGI kerak —
    # matn allaqachon yozilgan, foydalanuvchiga yetkazilishi shart.
    await _progress(job, 70, "AI sifat tekshiruvi")
    review = None
    try:
        review = await gemini_service.review_article(
            article_text, found_sources, req.language, MIN_WORDS, MAX_WORDS
        )
    except Exception:
        logger.exception("Gemini tekshiruvi ishlamadi — maqola tekshiruvsiz qaytariladi")

    rewrite_count = 0
    if review is not None:
        while gemini_service.needs_rewrite(review) and rewrite_count < MAX_REWRITE_ATTEMPTS:
            await _progress(job, 78 + rewrite_count * 4,
                            f"Qayta yozilmoqda ({rewrite_count + 1}/{MAX_REWRITE_ATTEMPTS})")
            try:
                article_text = await gpt_service.rewrite_article(
                    article_text, review, found_sources, req.language
                )
                review = await gemini_service.review_article(
                    article_text, found_sources, req.language, MIN_WORDS, MAX_WORDS
                )
            except Exception:
                logger.exception("Qayta yozish/tekshirishda xato — mavjud matn saqlanadi")
                break
            rewrite_count += 1

    if review is None:
        review = {
            "manbalarga_moslik": "tekshirilmadi",
            "hallucination_topildi": False,
            "uzunlik_muammosi": False,
            "topilgan_muammolar": [],
            "tuzatish_tavsiyalari": [],
            "umumiy_baho": "AI tekshiruvi vaqtincha ishlamadi, maqola tekshiruvsiz berildi.",
        }

    # So'z soni talabdan tashqarida bo'lsa — aniq raqam bilan alohida moslashtirish.
    # Umumiy "qayta yozish" ko'rsatmasi buni ishonchli bajarmaydi (tekshirildi:
    # 2693 so'z chiqdi, 2500 limitidan oshdi va 2 marta qayta yozish ham tushirmadi).
    before = len(article_text.split())
    if not (MIN_WORDS <= before <= MAX_WORDS):
        await _progress(job, 90, "So'z soni moslanmoqda")
        try:
            article_text = await gpt_service.adjust_length(
                article_text, found_sources, req.language, MIN_WORDS, MAX_WORDS
            )
            after = len(article_text.split())
            logger.info("So'z soni moslandi: %s -> %s", before, after)
            review["uzunlik_muammosi"] = not (MIN_WORDS <= after <= MAX_WORDS)
        except Exception:
            logger.exception("Uzunlikni moslashtirib bo'lmadi — mavjud matn qoldiriladi")

    # session_id oxiriga qisqa unikal qism qo'shamiz — bir xil mavzuni ikki mijoz
    # yaratsa, ikkinchisi birinchisining sessiyasini ustiga yozib qo'ymasin.
    session_id = f"{req.topic[:40].replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
    SESSION_STORE[session_id] = {
        "topic": req.topic,
        "article_text": article_text,
        "sources": found_sources,
        "review": review,
        "citation_style": req.citation_style,
        "language": req.language,
    }

    payload = {
        "session_id": session_id,
        "article_text": article_text,
        "word_count": len(article_text.split()),
        "rewrite_attempts": rewrite_count,
        "sources": [
            {"title": s["title"], "year": s["year"], "citation_count": s.get("citation_count"), "url": s["url"]}
            for s in found_sources
        ],
        "review_summary": review,
    }
    await _progress(job, 100, "Tayyor")
    return payload


async def _run_job(job_id: str, req: GenerateRequest) -> None:
    """Fon vazifasi: oqimni ishga tushiradi va natija/xatoni job holatiga yozadi."""
    job = JOBS.get(job_id)
    if job is None:
        return
    job["status"] = "running"
    job["started_at"] = time.time()
    try:
        job["result"] = await _run_pipeline(req, job)
        job["status"] = "done"
        job["progress"] = 100
        job["step"] = "Tayyor"
    except HTTPException as e:
        # HTTPException fon vazifasida mijozga yetib bormaydi — holatga yozamiz
        job["status"] = "error"
        job["error"] = str(e.detail)
        logger.warning("Job %s HTTP xato: %s", job_id, e.detail)
    except Exception:
        logger.exception("Job %s kutilmagan xato", job_id)
        job["status"] = "error"
        job["error"] = "Kutilmagan xatolik. Qayta urinib ko'ring."
    finally:
        job["finished_at"] = time.time()
        elapsed = job["finished_at"] - job["started_at"]
        logger.info("Job %s tugadi: %s (%.1f soniya)", job_id, job["status"], elapsed)
        _prune_jobs()


@app.post("/generate")
async def generate_article(req: GenerateRequest):
    """
    Sinxron rejim: natija tayyor bo'lguncha kutadi (eski mijozlar uchun saqlanadi).
    Yangi mijozlar uchun /jobs tavsiya etiladi — u darhol javob qaytaradi.
    """
    return await _run_pipeline(req)


@app.post("/jobs", status_code=202)
async def create_job(req: GenerateRequest):
    """
    Fon vazifasini boshlaydi va DARHOL job_id qaytaradi (202).
    Natijani /jobs/{job_id} orqali so'rab olinadi (progress bilan).
    """
    _prune_jobs()
    job_id = uuid.uuid4().hex[:16]
    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "step": "Navbatda",
        "topic": req.topic,
        "created_at": time.time(),
        "finished_at": None,
        "result": None,
        "error": None,
    }
    asyncio.create_task(_run_job(job_id, req))
    return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Job holati va natijasi. status: queued | running | done | error."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi (yoki muddati o'tgan).")

    resp = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "step": job.get("step", ""),
        "topic": job.get("topic", ""),
    }
    if job["status"] == "done":
        resp["result"] = job["result"]
    elif job["status"] == "error":
        resp["error"] = job.get("error") or "Noma'lum xatolik."
    elif job.get("started_at"):
        resp["elapsed_seconds"] = round(time.time() - job["started_at"], 1)
    return resp


@app.get("/download/{session_id}")
async def download_docx(session_id: str):
    """Yakuniy maqolani Word (.docx) formatida yuklab olish."""
    data = SESSION_STORE.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi. Avval /generate chaqiring.")

    docx_bytes = document_builder.build_docx(
        title=data["topic"],
        article_text=data["article_text"],
        sources=data["sources"],
        citation_style=data["citation_style"],
    )

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.docx"'},
    )

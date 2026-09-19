from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.services import sources as sources_service
from app.services import gemini_service
from app.services import gpt_service
from app.services import document_builder

app = FastAPI(title="Maqola Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo uchun; productionda aniq domenga cheklang
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_STORE: dict[str, dict] = {}

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
    return {"status": "ishlayapti"}


@app.post("/topics")
async def get_topics(req: TopicRequest):
    """Yo'nalish bo'yicha 10 ta mavzu taklifi (Gemini)."""
    try:
        topics = await gemini_service.generate_topics(req.direction)
        return {"topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mavzu generatsiyasida xato: {e}")


@app.post("/generate")
async def generate_article(req: GenerateRequest):
    """
    To'liq oqim:
    1. Haqiqiy manbalarni topish (PubMed/Semantic Scholar) - yangilik va citation
       soni bo'yicha saralangan eng sifatli manbalar
    2. Outline (reja) tuzish (GPT)
    3. Outline asosida to'liq maqola yozish (GPT)
    4. Gemini bilan qattiq tekshirish
    5. Agar muammo topilsa - GPT bilan qayta yozish (2 martagacha, har safar qayta tekshiriladi)
    6. Session'ga saqlash (docx yuklab olish uchun)
    """
    if req.language not in ("uz", "en", "ru"):
        raise HTTPException(status_code=400, detail="language 'uz', 'en' yoki 'ru' bo'lishi kerak")

    found_sources = await sources_service.find_sources(
        req.topic, prefer_medical=req.is_medical, max_results=10
    )
    if not found_sources:
        raise HTTPException(
            status_code=404,
            detail="Bu mavzu bo'yicha haqiqiy ilmiy manba topilmadi. Mavzuni kengroq yoki boshqacha yozib ko'ring.",
        )

    outline = await gpt_service.generate_outline(req.topic, found_sources, req.language)

    article_text = await gpt_service.write_article(
        req.topic, found_sources, req.citation_style, req.language, outline=outline
    )

    review = await gemini_service.review_article(
        article_text, found_sources, req.language, MIN_WORDS, MAX_WORDS
    )

    rewrite_count = 0
    while gemini_service.needs_rewrite(review) and rewrite_count < MAX_REWRITE_ATTEMPTS:
        article_text = await gpt_service.rewrite_article(
            article_text, review, found_sources, req.language
        )
        review = await gemini_service.review_article(
            article_text, found_sources, req.language, MIN_WORDS, MAX_WORDS
        )
        rewrite_count += 1

    session_id = req.topic[:40].replace(" ", "_")
    SESSION_STORE[session_id] = {
        "topic": req.topic,
        "article_text": article_text,
        "sources": found_sources,
        "review": review,
        "citation_style": req.citation_style,
        "language": req.language,
    }

    return {
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

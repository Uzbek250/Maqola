import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")  # ixtiyoriy, PubMed uchun (bo'lmasa ham ishlaydi, sekinroq)
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "example@example.com")  # NCBI talab qiladi

# Ixtiyoriy: Semantic Scholar API kaliti. Bo'lmasa ham ishlaydi, lekin kalitsiz
# barcha foydalanuvchilar bilan bitta umumiy limit bo'lishiladi va 429 olinadi.
# Kalit olish: https://www.semanticscholar.org/product/api#api-key
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

GPT_MODEL = os.getenv("GPT_MODEL", "gpt-5.6-luna")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

if not OPENAI_API_KEY:
    print("OGOHLANTIRISH: OPENAI_API_KEY topilmadi (.env fayliga qo'shing)")
if not GEMINI_API_KEY:
    print("OGOHLANTIRISH: GEMINI_API_KEY topilmadi (.env fayliga qo'shing)")

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
    "notes": "Standart profil: faqat umumiy tuzilma tekshiriladi.",
}

# --- Jurnal profillari -------------------------------------------------------
# Kalit: jurnal identifikatori. Qiymatlar rasmiy author guidelines'dan.
JOURNALS: dict[str, dict] = {}


def register(profile: dict) -> None:
    """Profil qo'shadi. Mijoz o'z jurnalini ham shu yo'l bilan qo'shishi mumkin."""
    JOURNALS[profile["key"]] = profile


def list_profiles() -> list[dict]:
    """Mavjud profillar ro'yxati (frontend/API uchun qisqa ko'rinish)."""
    out = [{"key": GENERIC["key"], "name": GENERIC["name"],
            "word_limit": None, "apc_usd": None}]
    for p in JOURNALS.values():
        out.append({
            "key": p["key"],
            "name": p["name"],
            "word_limit": p.get("word_limit_main_text"),
            "abstract_type": p.get("abstract_type"),
            "reference_style": p.get("reference_style"),
            "apc_usd": p.get("apc_usd"),
            "source_url": p.get("source_url"),
        })
    return sorted(out, key=lambda x: x["name"])


def get_profile(key: str | None) -> dict:
    """Profilni oladi. Noma'lum kalit uchun umumiy profil qaytadi (xato bermaydi)."""
    if not key or key == GENERIC["key"]:
        return GENERIC
    return JOURNALS.get(key, GENERIC)

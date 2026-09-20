"""
Muvofiqlik tekshiruvi (Bosqich 2).

Nega kerak: hozir mijoz maqolani olib, jurnal talabiga mos kelishini O'ZI
tekshirardi — so'z soni, havola soni, majburiy bo'limlar, abstract turi.
Taqrizchi buni birinchi qarashda ko'radi va mos kelmasa qo'lyozmani qaytaradi.

Bu modul maqolani jurnal profiliga solishtiradi va aniq hisobot beradi.
Hech narsani "tuzatmaydi" — faqat aytadi, chunki qaror muallifniki.
"""
import logging
import re

logger = logging.getLogger("app.services.compliance")

# Holat belgilari
OK, WARN, FAIL, NA = "ok", "warn", "fail", "na"


def _count_words(text: str) -> int:
    return len(text.split())


def _section_titles(article_text: str) -> list[str]:
    """Maqoladagi sarlavhalarni oladi (# va ## bilan boshlanadigan qatorlar)."""
    titles = []
    for line in article_text.split("\n"):
        m = re.match(r"^\s*#{1,4}\s+(.+?)\s*$", line)
        if m:
            titles.append(m.group(1).strip())
    return titles


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _find_section(titles: list[str], wanted: str) -> bool:
    """Bo'lim bor-yo'qligini tekshiradi (so'zlar tartibi muhim emas, qism mosligi yetarli)."""
    w = _norm(wanted)
    for t in titles:
        n = _norm(t)
        if w and (w in n or n.startswith(w[:max(5, len(w) // 2)])):
            return True
    return False


def check_compliance(article_text: str, sources: list[dict], meta: dict,
                     journal: dict) -> dict:
    """
    Maqolani jurnal profiliga solishtiradi.

    journal — `journals.get_profile()` natijasi. Qiymat `None` bo'lsa o'sha
    tekshiruv o'tkazib yuboriladi (`na`), "0" deb hisoblanmaydi.
    """
    checks: list[dict] = []
    titles = _section_titles(article_text)
    word_count = _count_words(article_text)

    def add(cid: str, label: str, status: str, detail: str) -> None:
        checks.append({"id": cid, "label": label, "status": status, "detail": detail})

    # ---- So'z soni
    limit = journal.get("word_limit_main_text")
    if limit:
        # ±10% toqat qilinadi (jurnallar odatda shunday qabul qiladi)
        if word_count <= limit:
            add("word_count", "Asosiy matn so'z soni", OK,
                f"{word_count} so'z (limit {limit})")
        elif word_count <= limit * 1.1:
            add("word_count", "Asosiy matn so'z soni", WARN,
                f"{word_count} so'z — limit {limit} dan oshgan, lekin 10% ichida. "
                f"Qisqartirish tavsiya etiladi.")
        else:
            add("word_count", "Asosiy matn so'z soni", FAIL,
                f"{word_count} so'z — limit {limit} dan {word_count - limit} so'z ko'p. "
                f"Qisqartirish SHART.")
    else:
        add("word_count", "Asosiy matn so'z soni", NA, f"{word_count} so'z (limit aniqlanmagan)")

    # ---- Havolalar soni
    ref_count = len(sources)
    max_refs = journal.get("max_references")
    if max_refs:
        if ref_count <= max_refs:
            add("references", "Havolalar soni", OK, f"{ref_count} ta (limit {max_refs})")
        else:
            add("references", "Havolalar soni", FAIL,
                f"{ref_count} ta — limit {max_refs} dan ko'p. Kamaytirish SHART.")
    else:
        add("references", "Havolalar soni", NA, f"{ref_count} ta (limit aniqlanmagan)")

    # ---- Majburiy bo'limlar
    # Muhim: umumiy profilda "majburiy" — bizning tavsiyamiz, jurnal talabi emas.
    # Shuning uchun u yerda WARN (ogohlantirish), aniq jurnal tanlanganda esa FAIL.
    # FAIL faqat jurnalning RASMIY talabi buzilganda qo'yiladi.
    is_generic = (journal.get("key") or "generic") == "generic"
    required = journal.get("required_sections") or []
    if required:
        missing = [s for s in required if not _find_section(titles, s)]
        found = ", ".join(titles[:10]) if titles else "(sarlavha topilmadi)"
        if missing:
            add("sections", "Majburiy bo'limlar", WARN if is_generic else FAIL,
                f"Yetishmayapti: {', '.join(missing)}. "
                f"Maqolada bor bo'limlar: {found}")
        else:
            add("sections", "Majburiy bo'limlar", OK,
                f"{len(required)} ta bo'lim joyida: {', '.join(required)}")
    else:
        add("sections", "Majburiy bo'limlar", NA, "Jurnal talabi aniqlanmagan")

    # ---- Abstract
    abstract = meta.get("structured_abstract") or {}
    ab_type = journal.get("abstract_type")
    if ab_type == "structured":
        need = journal.get("abstract_sections") or []
        have = [k for k, v in abstract.items() if str(v or "").strip()]
        if not have:
            add("abstract", "Abstract", FAIL, "Structured abstract yasalmagan")
        elif need:
            missing = [s for s in need if s.lower() not in [h.lower() for h in have]]
            if missing:
                add("abstract", "Abstract", WARN,
                    f"Structured, lekin kutilgan bo'limlar yo'q: {', '.join(missing)}. "
                    f"Mavjud: {', '.join(have)}")
            else:
                add("abstract", "Abstract", OK,
                    f"Structured, barcha bo'limlar bor: {', '.join(have)}")
        else:
            add("abstract", "Abstract", OK, f"Structured: {', '.join(have)}")
    elif ab_type == "unstructured":
        if abstract:
            add("abstract", "Abstract", OK, "Structured abstract yasalgan (jurnal oddiy abstract so'raydi)")
        else:
            add("abstract", "Abstract", FAIL, "Abstract yasalmagan")
    else:
        add("abstract", "Abstract", NA,
            "Structured abstract yasalgan" if abstract else "Abstract yasalmagan")

    # ---- Abstract so'z limiti
    ab_limit = journal.get("abstract_word_limit")
    if ab_limit and abstract:
        ab_words = _count_words(" ".join(str(v) for v in abstract.values()))
        if ab_words <= ab_limit:
            add("abstract_words", "Abstract so'z soni", OK, f"{ab_words} so'z (limit {ab_limit})")
        else:
            add("abstract_words", "Abstract so'z soni", WARN,
                f"{ab_words} so'z — limit {ab_limit} dan {ab_words - ab_limit} so'z ko'p")
    else:
        add("abstract_words", "Abstract so'z soni", NA, "Limit aniqlanmagan")

    # ---- Kalit so'zlar
    kws = meta.get("keywords") or []
    kmin, kmax = journal.get("keywords_min"), journal.get("keywords_max")
    if kws and (kmin or kmax):
        lo, hi = kmin or 0, kmax or 999
        if lo <= len(kws) <= hi:
            add("keywords", "Kalit so'zlar", OK, f"{len(kws)} ta (talab {lo}-{hi})")
        else:
            add("keywords", "Kalit so'zlar", WARN,
                f"{len(kws)} ta — talab {lo}-{hi}. To'g'rilash tavsiya etiladi.")
    elif kws:
        add("keywords", "Kalit so'zlar", NA, f"{len(kws)} ta (talab aniqlanmagan)")
    else:
        add("keywords", "Kalit so'zlar", FAIL, "Kalit so'zlar yasalmagan")

    # ---- Qabul qilinadimi
    accepts = journal.get("accepts_reviews")
    if accepts is True:
        add("accepts_reviews", "Jurnal sharh maqolasini qabul qiladi", OK, "Ha")
    elif accepts is False:
        add("accepts_reviews", "Jurnal sharh maqolasini qabul qiladi", FAIL,
            "YO'Q — bu jurnal sharh maqolalarini qabul qilmaydi. Boshqa jurnal tanlang.")
    else:
        add("accepts_reviews", "Jurnal sharh maqolasini qabul qiladi", NA, "Aniqlanmagan")

    # ---- AI siyosati (faqat eslatma — qaror muallifniki)
    if journal.get("ai_policy"):
        add("ai_policy", "Jurnalning AI siyosati", WARN, journal["ai_policy"])

    summary = {"ok": 0, "warn": 0, "fail": 0, "na": 0}
    for c in checks:
        summary[c["status"]] += 1

    return {
        "journal": journal.get("name") or "Aniqlanmagan",
        "journal_key": journal.get("key"),
        "source_url": journal.get("source_url"),
        "checks": checks,
        "summary": summary,
        "passed": summary["fail"] == 0,
        "word_count": word_count,
        "reference_count": ref_count,
    }


def compliance_to_markdown(report: dict) -> str:
    """Hisobotni o'qish uchun qulay matn ko'rinishiga o'giradi (ZIP ichiga qo'shiladi)."""
    icon = {OK: "✅", WARN: "⚠️", FAIL: "❌", NA: "➖"}
    verdict = "O'TKAZDI" if report["passed"] else "O'TKARMADI"
    lines = [
        f"# Muvofiqlik tekshiruvi — {report['journal']}",
        "",
        f"Natija: **{verdict}** "
        f"(✅ {report['summary']['ok']} | ⚠️ {report['summary']['warn']} | ❌ {report['summary']['fail']})",
        "",
    ]
    for c in report["checks"]:
        lines.append(f"{icon.get(c['status'], '?')} **{c['label']}** — {c['detail']}")
    if report.get("source_url"):
        lines += ["", f"Manba: {report['source_url']}"]
    lines += ["", "_Bu avtomatik tekshiruv. Yakuniy javobgarlik muallifda._"]
    return "\n".join(lines)

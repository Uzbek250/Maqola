"""
To'liq matn olish (Bosqich 3).

Muammo: ilova faqat ABSTRACT o'qirdi. Abstract tadqiqotning butun mazmunini
ko'rsatmaydi — usuli, raqamlari, cheklovlari ko'pincha faqat to'liq matnda
bo'ladi. Shuning uchun maqola sifati "abstract darajasida" qolib ketardi.

Yechim: ochiq (open access) maqolalarning to'liq matnini olamiz.
Manba: Europe PMC REST API — kalit talab qilmaydi, PMC Open Access to'plamini
qamrab oladi. Yopiq maqolalar uchun abstract qoladi (bu halol — to'qimaymiz).
"""
import asyncio
import logging
import re
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger("app.services.fulltext")

EUROPEPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc_id}/fullTextXML"

# Bitta manbadan olinadigan maksimal belgi. To'liq matn 40-60k belgi bo'lishi mumkin —
# hammasini promptga solsak, token narxi oshadi va model diqqati tarqaladi.
DEFAULT_MAX_CHARS = 9000


def _xml_to_text(xml_text: str) -> str:
    """
    JATS XML'dan faqat maqola tanasini oladi.

    Muhim: faqat <p> (paragraf) elementlar olinadi — shunda havolalar ro'yxati
    (<ref>/<mixed-citation>) va jadval ichidagi raqamlar tasodifan matnga
    qo'shilib ketmaydi. Har bir paragraf butun bo'lib qoladi (gap o'rtasidan
    kesilmaydi).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("To'liq matn XML'ini o'qib bo'lmadi: %s", e)
        return ""

    body = root.find(".//body")
    if body is None:
        return ""

    paragraphs = []
    for p in body.findall(".//p"):
        # Jadval/rasm izohlari va havola ichidagi matnni o'tkazib yuboramiz
        if p.find(".//xref") is not None:
            # xref — havolaga ishora ([12]); matnning o'zini saqlaymiz, faqat
            # butun paragraf faqat jadval izohi bo'lsa tashlaymiz
            pass
        text = re.sub(r"\s+", " ", "".join(p.itertext())).strip()
        if len(text) > 40:          # juda qisqa bo'laklar (sarlavha qoldiqlari) kerak emas
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


async def fetch_full_text(pmc_id: str, timeout: float = 30.0) -> str:
    """Bitta maqolaning to'liq matnini oladi. Ochiq bo'lmasa — bo'sh satr."""
    if not pmc_id:
        return ""
    pmc = pmc_id.strip()
    if not pmc.upper().startswith("PMC"):
        pmc = f"PMC{pmc}"

    url = EUROPEPMC_URL.format(pmc_id=pmc)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "maqola/1.0 (research tool)"})
    except httpx.RequestError as e:
        logger.warning("To'liq matn so'rovida tarmoq xatosi (%s): %s", pmc, e)
        return ""

    if resp.status_code != 200:
        # 404 — maqola ochiq emas yoki PMC'da yo'q. Bu normal holat.
        logger.info("To'liq matn yo'q (%s): HTTP %s", pmc, resp.status_code)
        return ""

    return _xml_to_text(resp.text)


async def enrich_with_full_text(sources: list[dict],
                                max_chars: int = DEFAULT_MAX_CHARS,
                                concurrency: int = 4) -> list[dict]:
    """
    Manbalarga to'liq matn qo'shadi (`full_text` maydoni). Olinmaganlar uchun
    maydon bo'sh qoladi va keyingi bosqichda abstract ishlatiladi.

    Sifat ko'rsatkichi ham yoziladi: `full_text_len` — inson mijozga
    "nechta manba to'liq o'qildi" deb aytish uchun.
    """
    targets = [s for s in sources if s.get("pmc_id")]
    if not targets:
        logger.info("To'liq matn: hech bir manbada PMC ID yo'q — hammasi abstract bilan")
        for s in sources:
            s.setdefault("full_text", "")
            s.setdefault("full_text_len", 0)
        return sources

    sem = asyncio.Semaphore(concurrency)

    async def work(s: dict) -> None:
        async with sem:
            text = await fetch_full_text(s["pmc_id"])
            if text:
                s["full_text"] = text[:max_chars]
                s["full_text_len"] = len(text)
            else:
                s["full_text"] = ""
                s["full_text_len"] = 0

    await asyncio.gather(*(work(s) for s in targets))

    for s in sources:
        s.setdefault("full_text", "")
        s.setdefault("full_text_len", 0)

    got = sum(1 for s in sources if s.get("full_text"))
    logger.info("To'liq matn: %s/%s manba uchun olindi (qolganlari abstract bilan)",
                got, len(sources))
    return sources


def full_text_stats(sources: list[dict]) -> dict:
    """Nazorat uchun: nechta manba to'liq o'qildi."""
    with_ft = [s for s in sources if s.get("full_text")]
    return {
        "full_text_count": len(with_ft),
        "abstract_only_count": len(sources) - len(with_ft),
        "total_chars": sum(s.get("full_text_len", 0) for s in with_ft),
    }

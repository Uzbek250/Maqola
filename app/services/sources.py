"""
Haqiqiy ilmiy manbalarni topish servisi.
MUHIM: bu modul AI'dan mustaqil ishlaydi. Hech qachon AI'ga "manba to'qi" demaymiz -
avval shu yerdan HAQIQIY maqolalarni topamiz, keyin AI'ga faqat shularni beramiz.

Sifat siyosati:
- Yangi maqolalar ustuvor (so'nggi bir necha yil, aks holda mavzu bo'yicha eskirgan bo'lishi mumkin)
- Semantic Scholar uchun citation soni bo'yicha saralanadi (ko'proq iqtibos = ko'proq ishonchli manba)
- Abstract'i yo'q yoki juda qisqa manbalar chiqarib tashlanadi (AI'ga foyda bermaydi)
"""
import logging
import re

import httpx
import math
from datetime import datetime
from app.config import NCBI_API_KEY, NCBI_EMAIL, SEMANTIC_SCHOLAR_API_KEY

logger = logging.getLogger(__name__)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

MIN_ABSTRACT_LENGTH = 200  # bundan qisqa abstract AI uchun deyarli foydasiz
RECENCY_YEARS = 6  # shundan eski maqolalar "eskirgan" deb hisoblanadi (chiqarilmaydi, faqat pastroq saralanadi)


async def _pubmed_get(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    """
    PubMed'ga so'rov yuboradi. Kalit rad etilgan bo'lsa (NCBI HTTP 400 qaytaradi),
    KALITSIZ qayta urinadi — shunda ilova butunlay ishlamay qolmaydi.
    """
    resp = await client.get(url, params=params)

    if resp.status_code == 400 and params.get("api_key"):
        logger.warning("NCBI 400 qaytardi — API kalit rad etilgan bo'lishi mumkin. "
                       "Kalitsiz qayta urinilmoqda (limit sekundiga 3 ta).")
        without_key = {k: v for k, v in params.items() if k != "api_key"}
        resp = await client.get(url, params=without_key)

    resp.raise_for_status()

    # Ba'zi holatlarda NCBI xatoni 200 bilan birga tana ichida qaytaradi
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("error"):
            logger.warning("NCBI javobida xato: %s", body.get("error"))
    except Exception:
        pass
    return resp


async def search_pubmed(query: str, max_results: int = 15) -> list[dict]:
    """
    PubMed'dan (tibbiyot/biomeditsina uchun eng ishonchli, bepul, kalitsiz) qidiradi.
    max_results kattaroq so'raladi, chunki keyin filtrlab-saralab, eng yaxshilarini tanlaymiz.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
            "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            search_params["api_key"] = NCBI_API_KEY

        resp = await _pubmed_get(client, PUBMED_SEARCH_URL, search_params)
        payload = resp.json()
        ids = payload.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "rettype": "abstract",
            "retmode": "xml",
            "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY

        fetch_resp = await _pubmed_get(client, PUBMED_FETCH_URL, fetch_params)
        fetch_resp.raise_for_status()

        return _parse_pubmed_xml(fetch_resp.text)


def _text(el) -> str:
    """Elementning barcha matnini yig'adi (ichma-ich teglar ham: <i>, <sup>)."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    results = []

    for article in root.findall(".//PubmedArticle"):
        try:
            # MUHIM: faqat ANIQ yo'llar ishlatiladi (".//" EMAS).
            # ".//ArticleId" yozuv ichidagi ReferenceList (maqolaning o'z
            # adabiyotlar ro'yxati) elementlarini ham topib, IQTIBOS QILINGAN
            # boshqa maqolaning DOI'sini olib qo'yardi — natijada manbalar
            # ro'yxatida jurnal va DOI bir-biriga mos kelmasdi.
            # PubMed XML tuzilishi:
            #   MedlineCitation/Article/...            <- maqolaning O'ZI
            #   PubmedData/ArticleIdList/ArticleId     <- maqolaning O'Z ID lari
            #   PubmedData/ReferenceList/...           <- iqtiboslar (bizga kerak emas)

            pmid = _text(article.find("MedlineCitation/PMID"))

            art = article.find("MedlineCitation/Article")
            if art is None:
                continue

            title = _text(art.find("ArticleTitle"))

            abstract_parts = art.findall("Abstract/AbstractText")
            abstract = " ".join(_text(a) for a in abstract_parts).strip()

            authors = []
            for author in art.findall("AuthorList/Author"):
                last = _text(author.find("LastName"))
                initials = _text(author.find("Initials"))
                if last:
                    authors.append(f"{last} {initials}".strip())

            journal = _text(art.find("Journal/Title"))
            if not journal:  # ba'zi yozuvlarda faqat qisqartma bo'ladi
                journal = _text(article.find("MedlineCitation/MedlineJournalInfo/MedlineTA"))

            pubdate = art.find("Journal/JournalIssue/PubDate")
            year_text = _text(pubdate.find("Year")) if pubdate is not None else ""
            if not year_text and pubdate is not None:
                medline_date = _text(pubdate.find("MedlineDate"))
                year_text = medline_date[:4] if medline_date else ""

            # DOI — faqat maqolaning o'z ArticleIdList'idan
            doi = ""
            for el_id in article.findall("PubmedData/ArticleIdList/ArticleId"):
                if el_id.get("IdType") == "doi":
                    doi = _text(el_id)
                    break
            # Zaxira joy: ba'zi yozuvlarda DOI faqat ELocationID da bo'ladi
            if not doi:
                for el in article.findall("MedlineCitation/Article/ELocationID"):
                    if el.get("EIdType") == "doi":
                        doi = _text(el)
                        break

            if title and len(abstract) >= MIN_ABSTRACT_LENGTH:
                results.append({
                    "source": "PubMed",
                    "id": pmid,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal,
                    "year": year_text,
                    "doi": doi,
                    "citation_count": None,  # PubMed bu ma'lumotni bermaydi
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
        except Exception:
            continue

    return results


async def search_semantic_scholar(query: str, max_results: int = 15) -> list[dict]:
    """
    Semantic Scholar'dan qidiradi. citationCount ham so'raladi - bu manba sifatini
    baholashda muhim mezon (ko'p iqtibos qilingan maqola ko'proq ishonch uyg'otadi).

    API kalit bo'lsa `x-api-key` sarlavhasida yuboriladi — aks holda kalitsiz
    foydalanuvchilar bilan umumiy limit bo'lishilib, 429 (Too Many Requests) olinadi.
    """
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,venue,externalIds,url,citationCount",
        }
        resp = await client.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for paper in data:
            abstract = paper.get("abstract") or ""
            if len(abstract) < MIN_ABSTRACT_LENGTH:
                continue
            results.append({
                "source": "Semantic Scholar",
                "id": paper.get("paperId", ""),
                "title": paper.get("title", ""),
                "abstract": abstract,
                "authors": [a.get("name", "") for a in paper.get("authors", [])],
                "journal": paper.get("venue", ""),
                "year": str(paper.get("year", "")) if paper.get("year") else "",
                "doi": paper.get("externalIds", {}).get("DOI", ""),
                "citation_count": paper.get("citationCount"),
                "url": paper.get("url", ""),
            })
        return results


def _quality_score(source: dict) -> float:
    """
    Manbani saralash uchun bitta ball hisoblaydi. Yuqoriroq ball = yuqoriroq ustuvorlik.
    - Yangilik: joriy yildan qancha uzoq bo'lsa, ball shuncha kamayadi
    - Citation soni: ko'proq iqtibos = qo'shimcha ball (log shkala, bitta "viral" maqola
      hammasini bosib ketmasligi uchun)
    """
    current_year = datetime.now().year
    score = 0.0

    try:
        year = int(source.get("year") or 0)
        age = max(current_year - year, 0)
        recency_score = max(0.0, 1.0 - (age / (RECENCY_YEARS * 2)))
        score += recency_score * 10
    except (ValueError, TypeError):
        pass

    citations = source.get("citation_count")
    if citations is not None and citations > 0:
        score += math.log10(citations + 1) * 3

    return score


def _norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


async def backfill_missing_dois(sources: list[dict], timeout: float = 25.0) -> list[dict]:
    """
    DOI si yo'q manbalar uchun Crossref'dan SARLAVHA bo'yicha DOI topadi.

    Nega: manba bazalari (ayniqsa Semantic Scholar) ba'zi maqolalar uchun DOI
    bermaydi, natijada ro'yxatda bir manbada DOI bor, boshqasida yo'q — taqrizchi
    buni "tekshirilmagan manba" deb hisoblashi mumkin. Sarlavha bo'yicha topib,
    ro'yxatni bir xil ko'rinishga keltiramiz.
    """
    import asyncio

    targets = [s for s in sources
               if not (s.get("doi") or "").strip() and len((s.get("title") or "")) > 20]
    if not targets:
        return sources

    sem = asyncio.Semaphore(3)
    # Preprint serverlari — nashr etilgan maqola emas, ularni QABUL QILMAYMIZ.
    # (Aks holda sarlavha bo'yicha qidiruv jurnal DOI si o'rniga preprint DOI sini
    #  topib qo'yadi — bu maqolaning boshqa versiyasiga ishora qiladi.)
    PREPRINT_TYPES = {"posted-content"}
    PREPRINT_PREFIXES = ("10.20944/", "10.21203/", "10.1101/", "10.31219/", "10.22541/")

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def find(s):
            async with sem:
                items = []
                for attempt in (1, 2):
                    try:
                        r = await client.get(
                            "https://api.crossref.org/works",
                            params={"query.bibliographic": s["title"], "rows": 5,
                                    "select": "DOI,title,type",
                                    "mailto": NCBI_EMAIL},   # Crossref "polite pool"
                        )
                    except Exception as e:
                        logger.warning("DOI qidiruvida xato (%s): %s", s["title"][:40], e)
                        return
                    if r.status_code == 200:
                        items = r.json().get("message", {}).get("items", [])
                        break
                    logger.warning("Crossref qidiruvi HTTP %s (%s)", r.status_code, s["title"][:40])
                    if attempt == 1:
                        await asyncio.sleep(2.0)
                if not items:
                    return

                target = _norm_text(s["title"])[:60]
                for it in items:
                    t = it.get("title") or [""]
                    t = t[0] if t else ""
                    doi = (it.get("DOI") or "").strip()
                    if not doi:
                        continue
                    # Preprint va nomaqbul turlarni o'tkazib yuboramiz
                    if (it.get("type") or "").lower() in PREPRINT_TYPES:
                        logger.info("Preprint o'tkazib yuborildi (%s): %s", doi, t[:40])
                        continue
                    if doi.lower().startswith(PREPRINT_PREFIXES):
                        logger.info("Preprint serveri o'tkazib yuborildi: %s", doi)
                        continue
                    nt = _norm_text(t)
                    # Faqat sarlavhaning boshi aniq mos kelsa qabul qilamiz
                    if nt[:60] == target and len(nt) > 20:
                        s["doi"] = doi
                        s["doi_source"] = "crossref-title-lookup"
                        logger.info("DOI topildi (sarlavha bo'yicha, %s): %s",
                                    s["title"][:40], doi)
                        return
                logger.info("DOI topilmadi (sarlavha bo'yicha): %s", s["title"][:50])

        await asyncio.gather(*(find(s) for s in targets))

    found = sum(1 for s in sources if s.get("doi_source") == "crossref-title-lookup")
    logger.info("DOI to'ldirish: %s ta manba uchun DOI topildi", found)
    return sources


async def validate_dois(sources: list[dict], timeout: float = 25.0) -> list[dict]:
    """
    Har bir manbaning DOI sini Crossref orqali tekshiradi.

    MUHIM: DOI FAQAT aniq "topilmadi" (404) javobida o'chiriladi. Vaqtinchalik
    xatolar (429 limit, 5xx, tarmoq uzilishi, timeout) DOI ni O'CHIRMAYDI —
    aks holda bitta vaqtinchalik limit butun ro'yxatdagi haqiqiy DOI larni
    yo'q qiladi (aynan shunday bo'lgan: bir manbaning DOI si yo'qolgan edi).
    """
    import asyncio

    targets = [s for s in sources if (s.get("doi") or "").strip()]
    if not targets:
        return sources

    # Kichik parallellik + kichik pauza: Crossref limitiga urilmaslik uchun
    sem = asyncio.Semaphore(3)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def check(s):
            doi = s["doi"].strip()
            async with sem:
                for attempt in (1, 2):
                    try:
                        r = await client.get(f"https://api.crossref.org/works/{doi}",
                                             params={"mailto": NCBI_EMAIL})  # polite pool
                    except Exception as e:
                        logger.warning("DOI tekshiruvida tarmoq xatosi (%s): %s — DOI saqlanadi", doi, e)
                        s["doi_verified"] = None      # noaniq: DOI ni o'chirmaymiz
                        return

                    if r.status_code == 200:
                        s["doi_verified"] = True
                        return
                    if r.status_code == 404:
                        logger.warning("DOI mavjud emas (%s): 404 — ro'yxatdan olib tashlandi", doi)
                        s["doi"] = ""
                        s["doi_verified"] = False
                        return
                    # 429 / 5xx — vaqtinchalik, bir marta kutib qayta urinamiz
                    logger.warning("DOI tekshiruvi vaqtincha xato (%s): HTTP %s", doi, r.status_code)
                    if attempt == 1:
                        await asyncio.sleep(2.0)
                        continue

            # Ikki urinishdan keyin ham noaniq — DOI ni SAQLAYMIZ (ehtiyotkorlik)
            logger.warning("DOI tasdiqlanmadi, lekin saqlanadi (%s)", doi)
            s["doi_verified"] = None

        await asyncio.gather(*(check(s) for s in targets))

    ok = sum(1 for s in sources if s.get("doi_verified") is True)
    gone = sum(1 for s in sources if s.get("doi_verified") is False)
    unknown = sum(1 for s in sources if s.get("doi_verified") is None)
    logger.info("DOI tekshiruvi: %s tasdiqlandi, %s mavjud emas (olib tashlandi), "
                "%s noaniq (saqlandi)", ok, gone, unknown)
    return sources


async def find_sources(
    query: str,
    prefer_medical: bool = True,
    max_results: int = 10,
) -> list[dict]:
    """
    Asosiy funksiya: manbalarni yig'adi, sifat bo'yicha saralaydi, eng yaxshilarini qaytaradi.
    Ko'proq so'raladi (zaxira bilan), keyin saralab eng yaxshilari tanlanadi - shunda
    "birinchi topilgan" emas, "eng sifatli" manbalar AI'ga beriladi.
    """
    raw_pool_size = max_results * 2
    results = []

    if prefer_medical:
        try:
            results = await search_pubmed(query, raw_pool_size)
        except Exception as e:
            print(f"PubMed xatosi: {e}")

    if len(results) < raw_pool_size:
        try:
            extra = await search_semantic_scholar(query, raw_pool_size - len(results))
            results.extend(extra)
        except Exception as e:
            print(f"Semantic Scholar xatosi: {e}")

    seen_titles = set()
    unique_results = []
    for r in results:
        key = r["title"].strip().lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_results.append(r)

    unique_results.sort(key=_quality_score, reverse=True)
    return unique_results[:max_results]

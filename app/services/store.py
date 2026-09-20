"""
Sessiya va vazifalarni diskka saqlash.

MUAMMO: SESSION_STORE va JOBS xotirada (dict) saqlanadi. Server qayta ishga
tushsa (deploy, crash, Render texnik xizmati) — hammasi yo'qoladi:
  - tugagan vazifaning natijasi yo'qoladi -> mijoz "vazifa topilmadi" oladi
  - yaratilgan maqolani yuklab bo'lmaydi -> mijoz ishini yo'qotadi

YECHIM: har bir sessiya/vazifa tugagach diskka yoziladi va server ishga
tushganda qayta o'qiladi. Deploy paytida BOSHLANGAN ish baribir yo'qoladi
(buni saqlab bo'lmaydi), lekin TUGAGAN ishlar saqlanib qoladi.

Yozish atomik (tmp fayl + rename) — yozish paytida uzilish faylni buzmaydi.
"""
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger("app.services.store")

# Render'da konteyner ildizi yoziladigan bo'lishi kerak; kerak bo'lsa env bilan
# o'zgartiriladi (masalan doimiy disk ulangan bo'lsa).
DATA_DIR = Path(os.getenv("MAQOLA_DATA_DIR", "data"))
SESSIONS_FILE = DATA_DIR / "sessions.json"
JOBS_FILE = DATA_DIR / "jobs.json"

MAX_SESSIONS = int(os.getenv("MAQOLA_MAX_SESSIONS", "50"))
MAX_JOBS = int(os.getenv("MAQOLA_MAX_JOBS", "50"))

_lock = threading.Lock()


def _read(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        # Buzilgan fayl butun ilovani to'xtatmasin
        logger.warning("Saqlangan faylni o'qib bo'lmadi (%s): %s", path, e)
        return {}


def _write(path: Path, data: dict) -> None:
    """Atomik yozish: avval tmp faylga, keyin rename."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        logger.warning("Saqlab bo'lmadi (%s): %s", path, e)


def _newest(d: dict, limit: int, ts_key: str) -> dict:
    """Eng oxirgi `limit` ta yozuvni qoldiradi (fayl cheksiz o'smasin)."""
    if len(d) <= limit:
        return d
    def ts(v):
        if isinstance(v, dict):
            return v.get(ts_key) or v.get("created_at") or 0
        return 0
    items = sorted(d.items(), key=lambda kv: ts(kv[1]), reverse=True)
    return dict(items[:limit])


def load_sessions() -> dict:
    """Server ishga tushganda sessiyalarni diskdan o'qiydi."""
    with _lock:
        sessions = _read(SESSIONS_FILE)
    if sessions:
        logger.info("Diskdan %s ta sessiya yuklandi", len(sessions))
    return sessions


def save_sessions(sessions: dict) -> None:
    """Sessiyalarni diskka yozadi (eng oxirgi MAX_SESSIONS tasi)."""
    with _lock:
        _write(SESSIONS_FILE, _newest(sessions, MAX_SESSIONS, "saved_at"))


def load_jobs() -> dict:
    """Tugagan vazifalarni diskdan o'qiydi (davom etayotganlar saqlanmaydi)."""
    with _lock:
        jobs = _read(JOBS_FILE)
    done = {k: v for k, v in jobs.items() if v.get("status") in ("done", "error")}
    if done:
        logger.info("Diskdan %s ta tugagan vazifa yuklandi", len(done))
    return done


def save_jobs(jobs: dict) -> None:
    """
    Faqat TUGAGAN vazifalarni saqlaydi.
    Davom etayotgan vazifa qayta ishga tushgandan keyin davom ettirilmaydi
    (pipeline qaytadan boshlanmaydi) — shuning uchun ular saqlanmaydi.
    """
    finished = {k: v for k, v in jobs.items() if v.get("status") in ("done", "error")}
    with _lock:
        _write(JOBS_FILE, _newest(finished, MAX_JOBS, "finished_at"))


def stamp() -> float:
    return time.time()

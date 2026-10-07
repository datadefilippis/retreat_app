"""I FILE delle lezioni — AU (8/10/2026): audio mp3 e allegati.

Storage PRIVATO su disco, fuori da `uploads/` (che e' montato statico):
    backend/private_uploads/lezioni/{org_id}/{course_id}/{lesson_id}/{genere}-{uuid}.{ext}

Nessun file si raggiunge per URL diretto: lo studente passa dal router
(/platform/me/corsi/...) con un PASS firmato a tempo in query — un <audio>
non sa mandare header, come per i master di Aurya Sound — e il pubblico
dalle anteprime (/public/corso/.../anteprima/...). La consegna gestisce il
Range (206) a mano, perche' la FileResponse di Starlette lo ignora e il
seek dell'<audio> ricomincerebbe da capo (lezione del 26/8 sui master).

Limiti: audio 50 MB (mp3, m4a, aac, wav, ogg); allegati 20 MB, 10 per
lezione (pdf, office, testo, immagini, audio, zip). Le estensioni sono
decise da noi, i nomi su disco sono nostri: mai il nome dell'utente.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND_DIR / "private_uploads" / "lezioni"
_SAFE = re.compile(r"^[a-zA-Z0-9_\-]+$")

AUDIO_MAX_BYTES = int(os.environ.get("LEZIONE_AUDIO_MAX_BYTES", 50 * 1024 * 1024))
ALLEGATO_MAX_BYTES = int(os.environ.get("LEZIONE_ALLEGATO_MAX_BYTES", 20 * 1024 * 1024))
ALLEGATI_MAX_PER_LEZIONE = 10
PASS_TTL_SEC = 6 * 3600

AUDIO_EXT = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/aac", "wav": "audio/wav",
             "ogg": "audio/ogg", "oga": "audio/ogg"}
ALLEGATO_EXT = {"pdf": "application/pdf", "doc": "application/msword",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "ppt": "application/vnd.ms-powerpoint",
                "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "xls": "application/vnd.ms-excel",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "txt": "text/plain", "md": "text/markdown", "png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "webp": "image/webp", "zip": "application/zip", **AUDIO_EXT}


def _seg(v: str, campo: str) -> str:
    if not v or not _SAFE.match(v):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{campo} non valido")
    return v


def _cartella(org_id: str, course_id: str, lesson_id: str) -> Path:
    return _ROOT / _seg(org_id, "org") / _seg(course_id, "corso") / _seg(lesson_id, "lezione")


def estensione(filename: Optional[str], ammesse: Dict[str, str]) -> str:
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext not in ammesse:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"code": "formato_non_ammesso",
                                    "message": "Formato non ammesso: " + ", ".join(sorted(ammesse))})
    return ext


async def salva(org_id: str, course_id: str, lesson_id: str, upload: UploadFile, *,
                genere: str, max_bytes: int, ammesse: Dict[str, str], sostituisce: Optional[str] = None) -> Dict[str, object]:
    """Scrive il file a pezzi di 1 MB e restituisce {filename, size_bytes,
    mime_type, original_name}. `sostituisce` = il file precedente da togliere."""
    ext = estensione(upload.filename, ammesse)
    cartella = _cartella(org_id, course_id, lesson_id)
    cartella.mkdir(parents=True, exist_ok=True)
    nome = f"{genere}-{uuid.uuid4().hex}.{ext}"
    dest = cartella / nome
    scritti = 0
    try:
        with open(dest, "wb") as out:
            while True:
                pezzo = await upload.read(1024 * 1024)
                if not pezzo:
                    break
                scritti += len(pezzo)
                if scritti > max_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                        detail={"code": "file_troppo_grande",
                                                "message": f"Il file supera i {max_bytes // (1024 * 1024)} MB."})
                out.write(pezzo)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    if scritti == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File vuoto")
    if sostituisce:
        cancella(org_id, course_id, lesson_id, sostituisce)
    return {"filename": nome, "size_bytes": scritti, "mime_type": ammesse[ext],
            "original_name": (upload.filename or nome)[:200]}


def percorso(org_id: str, course_id: str, lesson_id: str, filename: str) -> Path:
    if not filename or "/" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File non trovato")
    p = _cartella(org_id, course_id, lesson_id) / filename
    if not p.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File non trovato")
    return p


def cancella(org_id: str, course_id: str, lesson_id: str, filename: Optional[str]) -> None:
    if not filename or "/" in filename or ".." in filename:
        return
    try:
        (_cartella(org_id, course_id, lesson_id) / filename).unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("lezioni_file: %s non cancellato: %s", filename, exc)


def cancella_lezione(org_id: str, course_id: str, lesson_id: str) -> None:
    try:
        shutil.rmtree(_cartella(org_id, course_id, lesson_id), ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("lezioni_file: cartella lezione %s non cancellata: %s", lesson_id, exc)


# ── il pass ─────────────────────────────────────────────────────────────

def firma_pass(scope: str, **claims) -> str:
    """JWT HS256 a tempo, scoped: {scope, ...claims, exp}."""
    import jwt as _jwt
    return _jwt.encode({"scope": scope, **claims, "exp": int(time.time()) + PASS_TTL_SEC},
                       os.environ["JWT_SECRET_KEY"], algorithm="HS256")


def verifica_pass(token: Optional[str], scope: str, **attesi) -> bool:
    if not token:
        return False
    try:
        import jwt as _jwt
        payload = _jwt.decode(token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"])
    except Exception:
        return False
    if payload.get("scope") != scope:
        return False
    return all(payload.get(k) == v for k, v in attesi.items())


# ── la consegna (Range a mano) ───────────────────────────────────────────

def risposta_file(p: Path, request: Request, mime: str, *, scarica_come: Optional[str] = None):
    """Il seek dell'<audio> vive di Range (206). Un Range malformato ripiega
    sul file intero. `scarica_come` = allegato (Content-Disposition)."""
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}
    if scarica_come:
        sicuro = re.sub(r"[^A-Za-z0-9._ \-]", "_", scarica_come)[:120] or "file"
        headers["Content-Disposition"] = f'attachment; filename="{sicuro}"'
    intervallo = (request.headers.get("range") or "").strip()
    m = re.match(r"bytes=(\d*)-(\d*)$", intervallo)
    totale = p.stat().st_size
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            inizio = int(m.group(1))
            fine = int(m.group(2)) if m.group(2) else totale - 1
        else:
            inizio = max(0, totale - int(m.group(2)))
            fine = totale - 1
        fine = min(fine, totale - 1)
        if 0 <= inizio <= fine:
            with open(p, "rb") as f:
                f.seek(inizio)
                pezzo = f.read(fine - inizio + 1)
            return Response(content=pezzo, status_code=206, media_type=mime,
                            headers={**headers, "Content-Range": f"bytes {inizio}-{fine}/{totale}",
                                     "Content-Length": str(len(pezzo))})
        return Response(status_code=416, headers={"Content-Range": f"bytes */{totale}"})
    return FileResponse(str(p), media_type=mime, headers=headers)

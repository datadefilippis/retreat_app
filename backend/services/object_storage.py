"""Object storage per gli upload (R3, docs/PRODUCTION_PLAN.md).

PROBLEMA (audit scalabilita' 10/7): gli upload vivono sul filesystem
locale (backend/uploads + backend/private_uploads) — zero replica,
impossibile multi-istanza. QUESTO modulo e' l'adapter: S3-compatibile
quando configurato (Hetzner/Scaleway/R2/AWS), filesystem locale
altrimenti (dev, o produzione single-instance ai volumi del lancio).

Attivazione via env (tutte richieste):
    S3_BUCKET       nome bucket
    S3_ENDPOINT     endpoint S3-compatibile (es. https://fsn1.your-objectstorage.com)
    S3_ACCESS_KEY / S3_SECRET_KEY
    S3_PUBLIC_URL   base URL pubblica del bucket (CDN o endpoint diretto)

Contratto:
  - save_public_upload(category, filename, content, content_type) -> url
      Asset PUBBLICI (immagini prodotti, cover, loghi). In S3 la chiave
      e' uploads/{category}/{filename} con ACL public-read; in locale
      identico a prima (/uploads/{category}/{filename} via StaticFiles).
  - I file DIGITALI (a pagamento) restano su services/digital_storage
      (filesystem privato): la migrazione S3-privato con streaming e'
      un passo separato, tracciato nel piano — non un bloccante finche'
      si deploya single-instance.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_UPLOADS_ROOT = Path(__file__).resolve().parent.parent / "uploads"

_S3_VARS = ("S3_BUCKET", "S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_PUBLIC_URL")


def is_s3_enabled() -> bool:
    return all(os.environ.get(v) for v in _S3_VARS)


_s3_client = None


def _client():
    """Client boto3 lazy e cache-ato (thread-safe per uso FastAPI)."""
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            endpoint_url=os.environ["S3_ENDPOINT"],
            aws_access_key_id=os.environ["S3_ACCESS_KEY"],
            aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        )
    return _s3_client


# S6 (SEO_MASTER_PLAN, Core Web Vitals) — le foto vendono i ritiri ma
# pesano: al momento dell'UPLOAD (una volta per sempre, non on-the-fly)
# jpeg/png vengono ridimensionati a max 1600px e convertiti in WebP
# (qualità 82 ≈ -60/70% di peso a parità visiva). Fail-safe: qualsiasi
# errore → si salva l'originale com'era.
#
# PV1 (PROFILO_VERIFICATO_PIANO) — heic/heif (iPhone) entrano nella
# pipeline via pillow-heif e vengono SEMPRE convertiti (i browser non
# renderizzano HEIC, quindi "teniamo l'originale" non è un'opzione).
try:  # pillow-heif è un wheel puro: se manca si degrada senza HEIC
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_ENABLED = True
except Exception:  # noqa: BLE001
    HEIF_ENABLED = False

_OPTIMIZE_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif"}
# Formati che il browser non sa mostrare: conversione obbligata anche
# se il WebP risultasse più pesante dell'originale.
_FORCE_CONVERT_TYPES = {"image/heic", "image/heif"}
_MAX_DIMENSION = 1600
_WEBP_QUALITY = 82

# PV1 — MIME canonici per estensione: i chiamanti NON devono più fare
# f"image/{ext}" (produce "image/jpg", che non è un MIME e faceva
# saltare l'ottimizzazione alla foto più comune del mondo).
_EXT_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def content_type_for_ext(ext: str) -> str:
    """MIME canonico da un'estensione ('.jpg' o 'jpg')."""
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return _EXT_CONTENT_TYPES.get(ext, "application/octet-stream")


def _optimize_image(filename: str, content: bytes,
                    content_type: Optional[str]):
    if content_type not in _OPTIMIZE_TYPES:
        return filename, content, content_type
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        if img.mode in ("P", "LA"):
            img = img.convert("RGBA")
        if max(img.size) > _MAX_DIMENSION:
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION))
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=_WEBP_QUALITY, method=4)
        data = out.getvalue()
        if (len(data) >= len(content)
                and content_type not in _FORCE_CONVERT_TYPES):
            return filename, content, content_type  # non ci guadagniamo
        base = filename.rsplit(".", 1)[0]
        return f"{base}.webp", data, "image/webp"
    except Exception as exc:  # noqa: BLE001 — mai bloccare un upload
        logger.debug("object_storage: ottimizzazione saltata (%s): %s",
                     filename, exc)
        return filename, content, content_type


def save_public_upload(category: str, filename: str, content: bytes,
                       content_type: Optional[str] = None) -> str:
    """Salva un asset pubblico e ritorna l'URL da persistere sul documento.

    category: products | logos | occurrences | covers (nessuna validazione
    rigida: e' un namespace, non input utente — i chiamanti passano
    costanti). filename: gia' sanitizzato dai chiamanti (uuid + ext).
    """
    filename, content, content_type = _optimize_image(
        filename, content, content_type)
    key = f"uploads/{category}/{filename}"
    if is_s3_enabled():
        _client().put_object(
            Bucket=os.environ["S3_BUCKET"],
            Key=key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
            ACL="public-read",
            CacheControl="public, max-age=31536000, immutable",
        )
        return f"{os.environ['S3_PUBLIC_URL'].rstrip('/')}/{key}"

    # Fallback locale (dev / single-instance): identico al comportamento
    # storico — StaticFiles serve /uploads/*.
    target = _UPLOADS_ROOT / category
    target.mkdir(parents=True, exist_ok=True)
    (target / filename).write_bytes(content)
    return f"/uploads/{category}/{filename}"


def delete_public_uploads(category: str, prefix: str,
                          pattern: Optional[str] = None,
                          keep: Optional[str] = None) -> int:
    """PV1 — cleanup best-effort dei file di una category che iniziano
    con `prefix` (es. i vecchi cover `{org_id}-*` quando se ne carica
    una nuova col suffisso random). Simmetrico S3/filesystem, MAI
    bloccante: un fallimento qui non deve far fallire l'upload.

    SW4b — due filtri opzionali sul NOME del file, perché il prefisso da
    solo è una scure: con nomi versionati `{slug}-{hash}.webp` il
    prefisso "yoga-" prenderebbe dentro anche "yoga-e-respiro-ab12cd34".
      pattern  regex che il nome del file deve soddisfare PER INTERO
               (fullmatch): fuori da lì non si tocca niente;
      keep     il nome appena scritto, che non va mai rimosso.

    Ritorna il numero di file rimossi (0 se niente da rimuovere o su
    errore). I vecchi URL già persistiti nei documenti restano validi
    finché non vengono sovrascritti dai chiamanti.
    """
    if not prefix:  # guardia: mai svuotare un'intera category
        return 0
    import re
    rx = re.compile(pattern) if pattern else None

    def _da_rimuovere(name: str) -> bool:
        if keep and name == keep:
            return False
        return rx.fullmatch(name) is not None if rx else True

    removed = 0
    try:
        if is_s3_enabled():
            bucket = os.environ["S3_BUCKET"]
            key_prefix = f"uploads/{category}/{prefix}"
            client = _client()
            token = None
            while True:
                kwargs = {"Bucket": bucket, "Prefix": key_prefix}
                if token:
                    kwargs["ContinuationToken"] = token
                resp = client.list_objects_v2(**kwargs)
                keys = [{"Key": o["Key"]} for o in resp.get("Contents", [])
                        if _da_rimuovere(o["Key"].rsplit("/", 1)[-1])]
                if keys:
                    client.delete_objects(Bucket=bucket,
                                          Delete={"Objects": keys})
                    removed += len(keys)
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
            return removed
        target = _UPLOADS_ROOT / category
        if target.is_dir():
            for path in target.glob(f"{prefix}*"):
                if not _da_rimuovere(path.name):
                    continue
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed
    except Exception as exc:  # noqa: BLE001 — best-effort per contratto
        logger.warning("object_storage: cleanup %s/%s* fallito: %s",
                       category, prefix, exc)
        return removed

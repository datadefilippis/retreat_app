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


def save_public_upload(category: str, filename: str, content: bytes,
                       content_type: Optional[str] = None) -> str:
    """Salva un asset pubblico e ritorna l'URL da persistere sul documento.

    category: products | logos | occurrences | covers (nessuna validazione
    rigida: e' un namespace, non input utente — i chiamanti passano
    costanti). filename: gia' sanitizzato dai chiamanti (uuid + ext).
    """
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

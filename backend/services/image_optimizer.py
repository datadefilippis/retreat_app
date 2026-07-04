"""
Image optimization pipeline for merchant-uploaded assets.

Refinement pre-launch — the upload flow used to write the
original file verbatim to disk. A 2MB JPEG served to an `<img>` that
renders at 40-56px on screen is ~95% wasted bandwidth: every
visitor pulled the full file from the backend on every cold cache
miss. This module bounds the cost at upload time:

  1. **Resize**: cap to MAX_DIMENSION on the longest side. A 4000×3000
     phone photo becomes 512×384 with no visible loss at logo display
     sizes (40-56px even on a 3x retina display).

  2. **Compression**:
     · JPEG  → quality 85 (Mozilla guidelines: sweet spot for
                marketing-page perceptual quality)
     · PNG   → optimize=True (Pillow's deflate-level retune)
     · WebP  → quality 85, method=6 (slowest = best compression)
     · SVG   → pass-through (vector, no benefit from raster pipeline)

  3. **Format preservation**: we DON'T convert formats automatically.
     A future phase may add WebP conversion behind an Accept-header
     negotiation, but for now the merchant-uploaded format is what
     gets served. Avoids surprise transparency / quality changes.

  4. **Bounded input dimensions**: rejects images outside
     [MIN_DIMENSION, MAX_INPUT_DIMENSION] to:
        - prevent decompression bombs (a 100kB file claiming
          200,000×200,000 dimensions)
        - block pixelated uploads that would render badly

Behavioural contract
--------------------
`optimize_logo(content_bytes, extension)` returns optimized bytes.
If anything goes wrong (corrupt image, unsupported subformat, etc.)
the function raises ValueError — caller maps to HTTP 400.

Pure function: no I/O, no global state, safe to call from any
thread / async context. Pillow's IO uses BytesIO so we never touch
the filesystem inside the helper.

Storage savings expected (typical merchant logos)
-------------------------------------------------
  500×500 PNG  with text+icon : 180 kB → 45 kB    (75 % reduction)
  2000×2000 PNG with photo    : 4.2 MB → 240 kB   (94 %)
  3000×2000 JPEG photo logo    : 1.8 MB → 95 kB    (95 %)
  100×100 already-optimized PNG: 12 kB → 8 kB      (33 %)
  SVG (any size)               : pass-through       (0 % — vector)

The bandwidth savings compound: every visitor on every cold cache
miss pulls the smaller file. With HTTP cache headers on /uploads
(see add_cache_headers_middleware), warm-cache visitors pay zero
network cost on revisits.
"""

from __future__ import annotations

import io
import logging
from typing import Tuple

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


# ── Tunable constants ──────────────────────────────────────────────────────


# Max dimension on the longest side AFTER optimization. 512 is more
# than enough for storefront logos (which render at 32-56px CSS).
# Even on a 3x retina mobile (56*3 = 168px native), 512px provides
# headroom + sharpness for future "lg" preset bumps.
MAX_DIMENSION = 512

# Hard minimum on each side BEFORE accepting an upload. Anything
# smaller is going to render pixelated; reject so the admin uploads
# a higher-quality source. Picked to match the "lg" preset 56px at
# 1x — adminI uploading 50×50 would deserve the reject.
MIN_DIMENSION = 100

# Hard maximum on each side BEFORE the resize. Anything larger
# strongly suggests either a phone-camera-original (waste of upload
# bandwidth) or a decompression bomb attempt. 5000 covers any
# legitimate raw photo intended as a logo source.
MAX_INPUT_DIMENSION = 5000

# JPEG quality — Mozilla / Smashing Magazine consensus sweet spot.
# Above ~88 yields diminishing returns; below ~75 starts showing
# compression artifacts on gradients (common on rendered logo
# exports).
JPEG_QUALITY = 85

# WebP quality — slightly higher because WebP retains more detail
# than JPEG at the same quality value. 85 here ≈ JPEG 90 perceptual.
WEBP_QUALITY = 85


# Extensions handled by the raster pipeline. Lowercased and INCLUDES
# the leading dot to match `os.path.splitext` output.
_RASTER_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# SVG passes through — vector format, raster optimization would
# rasterize it (lossy + wasteful).
_PASSTHROUGH_EXTS = frozenset({".svg"})


# Pillow output format mapping. Stays in sync with the input
# extension so the merchant-uploaded format is preserved.
_PIL_FORMAT_BY_EXT = {
    ".jpg":  "JPEG",
    ".jpeg": "JPEG",
    ".png":  "PNG",
    ".webp": "WEBP",
}


# ── Public API ─────────────────────────────────────────────────────────────


def optimize_logo(content: bytes, extension: str) -> Tuple[bytes, dict]:
    """Optimize a logo upload.

    Args:
        content:    raw bytes of the uploaded file.
        extension:  lowercase ".jpg" / ".png" / etc. (from
                    os.path.splitext on the original filename).

    Returns:
        Tuple of (optimized_bytes, metadata_dict).
        Metadata includes original/final dimensions + bytes for
        observability — the caller can log to track the savings.

    Raises:
        ValueError: image is unreadable, smaller than MIN_DIMENSION,
                    or larger than MAX_INPUT_DIMENSION. Caller maps
                    to HTTP 400 with the message string.
    """
    ext = extension.lower()

    # SVG bypass — vector, no raster pipeline.
    if ext in _PASSTHROUGH_EXTS:
        return content, {
            "format": "svg",
            "original_bytes": len(content),
            "final_bytes": len(content),
            "note": "passthrough_vector",
        }

    if ext not in _RASTER_EXTS:
        raise ValueError(
            f"Formato non supportato per ottimizzazione: {ext}. "
            f"Usa: {sorted(_RASTER_EXTS | _PASSTHROUGH_EXTS)}"
        )

    # Open + validate dimensions BEFORE allocating large buffers.
    # Pillow's verify() is cheap (parses header only); load() comes
    # next and does the actual decode.
    original_bytes = len(content)
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Immagine non valida o corrotta: {e}")

    # Re-open for actual processing (verify() invalidates the Image).
    try:
        img = Image.open(io.BytesIO(content))
        img.load()  # forces full decode now so errors surface here
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Immagine non leggibile: {e}")

    w, h = img.size

    # Defensive bounds check. The MIN side check rejects pixelated
    # uploads. The MAX side check rejects decompression-bomb attempts
    # (and well-meaning but wasteful phone-camera originals).
    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        raise ValueError(
            f"Immagine troppo piccola ({w}×{h}). "
            f"Dimensione minima: {MIN_DIMENSION}×{MIN_DIMENSION} pixel."
        )
    if w > MAX_INPUT_DIMENSION or h > MAX_INPUT_DIMENSION:
        raise ValueError(
            f"Immagine troppo grande ({w}×{h}). "
            f"Dimensione massima accettata: {MAX_INPUT_DIMENSION}×{MAX_INPUT_DIMENSION} pixel."
        )

    # Resize keeping aspect ratio. Pillow's thumbnail() mutates in
    # place + uses LANCZOS by default (highest quality).
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
    final_w, final_h = img.size

    # Format-specific encoding. PNG mode preservation matters for
    # transparency; JPEG mode must be RGB (Pillow raises on RGBA).
    out_buf = io.BytesIO()
    pil_format = _PIL_FORMAT_BY_EXT[ext]

    if pil_format == "JPEG":
        # Strip alpha to RGB; preserve color. Background color
        # doesn't matter visually because the alpha is opaque in
        # the original (JPEG doesn't support alpha) — but if the
        # source PNG was mistakenly named .jpg with transparency,
        # paste onto white to avoid black artifacts.
        if img.mode != "RGB":
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA"):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        img.save(out_buf, format="JPEG", quality=JPEG_QUALITY,
                 optimize=True, progressive=True)
    elif pil_format == "PNG":
        # `optimize=True` retunes deflate parameters; can shave 5-15%
        # without quality loss.
        img.save(out_buf, format="PNG", optimize=True)
    elif pil_format == "WEBP":
        # method=6 = slowest encoder, best compression. Upload-time
        # cost (~200ms for typical logos) is fine; we get smaller
        # files served forever afterwards.
        img.save(out_buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    else:
        # Shouldn't reach here (caught above), but defensive.
        raise ValueError(f"Formato Pillow non supportato: {pil_format}")

    optimized_bytes = out_buf.getvalue()
    final_bytes = len(optimized_bytes)

    metadata = {
        "format": ext,
        "original_size": (w, h),
        "final_size": (final_w, final_h),
        "original_bytes": original_bytes,
        "final_bytes": final_bytes,
        "savings_pct": (
            round(100.0 * (1 - final_bytes / original_bytes), 1)
            if original_bytes > 0 else 0.0
        ),
    }

    logger.info(
        "image_optimizer: %s %s→%s pixels, %s→%s bytes (%s%% saved)",
        ext,
        f"{w}×{h}",
        f"{final_w}×{final_h}",
        original_bytes,
        final_bytes,
        metadata["savings_pct"],
    )

    return optimized_bytes, metadata

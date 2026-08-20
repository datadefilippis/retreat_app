"""Aurya Sound — importa la libreria di basi sonore della piattaforma (SL, 20/8/2026).

Due tempi, perche' la preparazione dell'audio e' un lavoro da postazione
(serve `afconvert`, che e' macOS) mentre l'importazione deve poter girare
anche sul server:

    prepare   sorgenti pesanti (wav/mp3 lunghi) → m4a AAC 128k
              NORMALIZZATI, piu' un indice JSON. Uscita in una cartella
              di staging che si puo' rsync-are ovunque.
    import    legge lo staging, copia i file in uploads/audio/ e scrive
              i metadati in Mongo. Idempotente per `source_file`.

Perche' normalizzare: le sorgenti stanno in 32 dB di differenza (da
-45 dB rms a -13 dB). Una libreria di BASI da mescolare sotto le
frequenze deve partire da un volume confrontabile, altrimenti ogni
scelta dell'operatore comincia con una correzione di volume. Il target
e' -20 dBFS rms con tetto di picco a -1 dBFS: chi e' gia' forte non
viene toccato, chi e' percussivo (campane, salite) resta dinamico
perche' e' il picco a fermare il guadagno, non l'rms.

Uso:
    venv/bin/python -m scripts.seed_sound_library_sl prepare ~/Desktop/sound/new
    venv/bin/python -m scripts.seed_sound_library_sl import
    venv/bin/python -m scripts.seed_sound_library_sl import --dry-run
"""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import wave
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

STAGING = BACKEND_DIR / "uploads" / "_staging_sounds"
AUDIO_DIR = BACKEND_DIR / "uploads" / "audio"
INDEX_NAME = "index.json"

TARGET_RMS_DB = -20.0        # volume di riferimento della libreria
PEAK_CEILING_DB = -1.0       # tetto: niente clipping, dinamica intatta
BITRATE = 128000
KEEP_AS_IS_BYTES = 20 * 1024 * 1024   # gia' leggero e gia' compresso: non si ritocca

CC0_HOLIZNA = "CC0 · HoliznaCC0"
CC0_BARTMANN = "CC0 · John Bartmann"
# Materiale arrivato dal founder senza licenza allegata: si annota la
# provenienza vera invece di dichiarare un CC0 che nessuno ha verificato.
def _aurya(original):
    return f"Fornito da Aurya · da confermare · file originale: {original}"


# (percorso relativo alla cartella sorgente, titolo, categoria)
#
# I titoli NON riportano piu' le frequenze che comparivano nei nomi dei
# file: l'analisi spettrale (20/8) dice che non ci sono. «Be_Light_-_741_Hz»
# ha il suo picco a 220 Hz, «Sleep_-_285_Hz» a 52/104 Hz, «Deep_silence_-_174_Hz»
# a 295 Hz. Sono brani, non toni: scriverci sopra un numero di hertz
# sarebbe una dichiarazione tecnica falsa. Il nome originale resta nella
# nota di licenza, cosi' nulla si perde.
MANIFEST = [
    # ── Ambient: atmosfere e tappeti su cui appoggiare le frequenze
    ("Ambience/ambience_dunes.wav", "Dune", "ambient", None),
    ("Ambience/angelic_sound.wav", "Coro angelico", "ambient", None),
    ("Ambience/John Bartmann - Water Forest.mp3", "Water Forest", "ambient",
     CC0_BARTMANN),
    ("meditazioni/HoliznaCC0 - 20 Minute Meditation 6.mp3",
     "Venti minuti · uno", "ambient", CC0_HOLIZNA),
    ("meditazioni/HoliznaCC0 - 20 Minute Meditation 11.mp3",
     "Venti minuti · due", "ambient", CC0_HOLIZNA),
    ("meditazioni/HoliznaCC0 - Rain _ Sleep _ Meditation.mp3",
     "Pioggia e sonno", "ambient", CC0_HOLIZNA),
    ("meditazioni/HoliznaCC0 - Too Brief A Time To Be Anything.mp3",
     "Too Brief A Time To Be Anything", "ambient", CC0_HOLIZNA),
    ("meditazioni/meditazioni/Meditazione_zen.wav", "Tappeto zen", "ambient", None),
    ("meditazioni/meditazioni/Meditazione_Celestial_Ascension.wav",
     "Ascensione celeste", "ambient", None),

    # ── Droni: toni tenuti, il letto piu' semplice sotto una sessione
    ("meditazioni/meditazioni/Deep_silence_-_174_Hz.wav",
     "Silenzio profondo", "droni", None),
    ("meditazioni/meditazioni/Sleep_-_285_Hz.wav", "Sonno", "droni", None),
    ("meditazioni/meditazioni/Be_hearth_-_396_Hz.wav", "Calore", "droni", None),
    ("meditazioni/meditazioni/Be_water_-_417_Hz.wav", "Acqua", "droni", None),
    ("meditazioni/meditazioni/Be_Light_-_741_Hz.wav", "Luce", "droni", None),
    ("meditazioni/meditazioni/meditazione_love_frequency.wav",
     "Tenerezza", "droni", None),

    # ── Corpo: una serie sola, dalla radice alla testa, in ordine
    ("meditazioni/meditazioni/radice.wav", "1 · Radice", "corpo", None),
    ("meditazioni/meditazioni/Centro.wav", "2 · Centro", "corpo", None),
    ("meditazioni/meditazioni/Cuore.wav", "3 · Cuore", "corpo", None),
    ("meditazioni/meditazioni/Gola.wav", "4 · Gola", "corpo", None),
    ("meditazioni/meditazioni/Sguardo.wav", "5 · Sguardo", "corpo", None),
    ("meditazioni/meditazioni/Testa.wav", "6 · Testa", "corpo", None),

    # ── Natura
    ("nature/birds_singing.mp3", "Uccelli al mattino", "natura", None),
    ("nature/birds_singing_april.mp3", "Uccelli d'aprile", "natura", None),
    ("nature/ocean_waves.wav", "Onde lunghe", "natura", None),
    ("nature/relaxing_water.wav", "Acqua che scorre", "natura", None),
    ("nature/temporale_in_forest.mp3", "Temporale nel bosco", "natura", None),
    ("nature/ululato_vento.ogg", "Vento", "natura", None),

    # ── Campane e metalli
    ("strumenti/campana_tibetana.wav", "Campana tibetana", "campane", None),
    ("strumenti/campana_tibetana_2.wav", "Campana tibetana lunga", "campane", None),
    ("strumenti/wind_chimes.wav", "Campane a vento", "campane", None),

    # ── Ritmi: il passo del corpo
    ("nature/battito_cuore.wav", "Battito del cuore", "ritmi", None),
    ("meditazioni/meditazioni/respiro.wav", "Respiro", "ritmi", None),
    ("meditazioni/meditazioni/meditazione_repsirazione_coerente.wav",
     "Respirazione coerente", "ritmi", None),

    # ── Voce
    ("voce/aum.mp3", "Aum", "voce", None),
    ("voce/voce_eterea.mp3", "Voce eterea", "voce", None),

    # ── Transizioni: passaggi brevi tra due momenti della sessione
    ("uplifter/ulifter1.wav", "Salita lunga", "transizioni", None),
    ("uplifter/uplifter2.wav", "Salita breve", "transizioni", None),
]

MIME_BY_EXT = {"m4a": "audio/mp4", "mp3": "audio/mpeg",
               "ogg": "audio/ogg", "wav": "audio/wav"}


# ── preparazione (macOS: afconvert + numpy) ─────────────────────────────

def _real_ext(src: Path):
    """Estensione VERA, letta dai primi byte: fra le sorgenti c'e' un
    wav che si chiama .mp3, e afconvert si fida del nome."""
    head = src.read_bytes()[:16]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if head[4:8] == b"ftyp":
        return "m4a"
    return src.suffix.lstrip(".").lower()


def _decode_to_wav(src: Path, dst: Path):
    """Sorgente qualsiasi → wav 16 bit, per misurare e riscalare."""
    real = _real_ext(src)
    if real != src.suffix.lstrip(".").lower():
        # afconvert va per estensione: gli si passa una copia onesta
        honest = dst.with_name(f"src.{real}")
        shutil.copyfile(src, honest)
        src = honest
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", str(src), str(dst)],
                   check=True, capture_output=True)


def _measure_and_gain(path: Path):
    """(durata, guadagno in dB) per portare il file al volume di libreria."""
    import numpy as np
    with wave.open(str(path), "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        peak, squares, taken = 0.0, 0.0, 0
        for k in range(1, 10):                       # 9 finestre da 4 s
            w.setpos(min(int(n * k / 10), max(0, n - sr * 4)))
            a = np.frombuffer(w.readframes(min(sr * 4, n)),
                              dtype=np.int16).astype(np.float32) / 32768
            if not len(a):
                continue
            if ch == 2:
                a = a.reshape(-1, 2)
            peak = max(peak, float(np.abs(a).max()))
            squares += float((a ** 2).mean())
            taken += 1
    import math
    rms = math.sqrt(squares / taken) if taken else 0.0
    db = lambda x: 20 * math.log10(max(x, 1e-9))
    gain = min(TARGET_RMS_DB - db(rms), PEAK_CEILING_DB - db(peak))
    return n / sr, round(gain, 1)


def _apply_gain(src: Path, dst: Path, gain_db: float):
    import numpy as np
    with wave.open(str(src), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    a = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    a *= 10 ** (gain_db / 20)
    np.clip(a, -32768, 32767, out=a)
    with wave.open(str(dst), "wb") as o:
        o.setparams(params)
        o.writeframes(a.astype(np.int16).tobytes())


def prepare(source_dir: Path):
    STAGING.mkdir(parents=True, exist_ok=True)
    index = []
    for rel, title, category, license_note in MANIFEST:
        src = source_dir / rel
        if not src.exists():
            print(f"  ✗ manca: {rel}")
            continue
        ext = src.suffix.lstrip(".").lower()
        note = license_note or _aurya(src.name)
        # «leggero» non e' solo questione di byte: l'estensione puo'
        # mentire (birds_singing_april.mp3 e' un wav travestito) e allora
        # la durata non si legge. In quel caso passa dalla transcodifica.
        light = (src.stat().st_size <= KEEP_AS_IS_BYTES
                 and _real_ext(src) in ("mp3", "ogg")
                 and _probe_light(src) > 0)
        try:
            if light:
                # gia' compresso e gia' leggero: ricodificarlo perderebbe
                # qualita' senza guadagnare niente
                out = STAGING / f"{_slug(title)}.{ext}"
                shutil.copyfile(src, out)
                dur, gain = _probe_light(src), 0.0
            else:
                out = STAGING / f"{_slug(title)}.m4a"
                with tempfile.TemporaryDirectory() as tmp:
                    raw = Path(tmp) / "raw.wav"
                    _decode_to_wav(src, raw)
                    dur, gain = _measure_and_gain(raw)
                    if abs(gain) >= 0.5:
                        louder = Path(tmp) / "gain.wav"
                        _apply_gain(raw, louder, gain)
                        raw = louder
                    subprocess.run(
                        ["afconvert", "-f", "m4af", "-d", "aac", "-b", str(BITRATE),
                         "-s", "3", str(raw), str(out)],
                        check=True, capture_output=True)
        except Exception as e:                    # un file rotto non ferma la libreria
            print(f"  ✗ {title}: {type(e).__name__} — saltato")
            continue
        index.append({
            "file": out.name, "title": title, "category": category,
            "duration_sec": round(dur, 1), "license_note": note,
            "source_file": rel, "gain_db": gain,
            "size_bytes": out.stat().st_size,
        })
        print(f"  ✓ {title:32} {category:12} {dur:6.0f}s "
              f"{out.stat().st_size / 1048576:6.1f}MB  gain {gain:+.1f} dB")
    (STAGING / INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2))
    tot = sum(i["size_bytes"] for i in index) / 1048576
    print(f"\n{len(index)} basi pronte in {STAGING} ({tot:.0f} MB)")


def _probe_light(src: Path):
    """Durata di un file gia' compresso. afinfo non legge Ogg Vorbis:
    li' la durata si ricava dall'ultima pagina Ogg (granule position)."""
    if src.suffix.lower() == ".ogg":
        return _ogg_duration(src)
    out = subprocess.run(["afinfo", str(src)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if "estimated duration" in line:
            return float(line.split(":")[1].split()[0])
    return 0.0


def _ogg_duration(src: Path):
    data = src.read_bytes()
    head = data.find(b"\x01vorbis")
    if head < 0:
        return 0.0
    sr = int.from_bytes(data[head + 12:head + 16], "little")
    last = data.rfind(b"OggS")
    if last < 0 or not sr:
        return 0.0
    granule = int.from_bytes(data[last + 6:last + 14], "little")
    return round(granule / sr, 1)


def _slug(title: str):
    keep = [c.lower() if c.isalnum() else "-" for c in title]
    s = "".join(keep)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


# ── importazione (gira ovunque) ─────────────────────────────────────────

async def do_import(dry_run: bool):
    from database import audio_assets_collection
    from models.audio_asset import SOUND_CATEGORIES
    from models.common import utc_now

    index = json.loads((STAGING / INDEX_NAME).read_text())
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    nuovi = saltati = 0
    for entry in index:
        if entry["category"] not in SOUND_CATEGORIES:
            print(f"  ✗ categoria sconosciuta: {entry['category']}")
            continue
        gia = await audio_assets_collection.find_one(
            {"source_file": entry["source_file"]}, {"_id": 1})
        if gia:
            saltati += 1
            continue
        ext = entry["file"].rsplit(".", 1)[-1]
        asset_id = str(uuid.uuid4())
        if not dry_run:
            shutil.copyfile(STAGING / entry["file"],
                            AUDIO_DIR / f"{asset_id}.{ext}")
            await audio_assets_collection.insert_one({
                "id": asset_id,
                "owner": "platform",
                "title": entry["title"],
                "category": entry["category"],
                "duration_sec": entry["duration_sec"],
                "size_bytes": entry["size_bytes"],
                "mime": MIME_BY_EXT.get(ext, "audio/mpeg"),
                "stream_url": f"/uploads/audio/{asset_id}.{ext}",
                "license_note": entry["license_note"],
                "source_file": entry["source_file"],
                "uploaded_by": "seed:sound-library",
                "created_at": utc_now(),
            })
        nuovi += 1
        print(f"  + {entry['title']:32} {entry['category']}")
    print(f"\n{nuovi} basi importate, {saltati} gia' presenti"
          + (" (PROVA A VUOTO)" if dry_run else ""))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        src = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else None
        if not src or not src.is_dir():
            sys.exit("uso: prepare <cartella sorgente>")
        prepare(src)
    elif cmd == "import":
        asyncio.run(do_import("--dry-run" in sys.argv))
    else:
        sys.exit(__doc__)

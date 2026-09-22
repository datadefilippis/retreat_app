"""Misure oggettive per allocare le tracce: energia nel tempo (arco),
percussivita' e bpm (autocorrelazione degli onset), brillantezza
(centroide), piattezza spettrale (drone vs melodia). Decodifica via
afconvert (mac)."""
import glob, os, subprocess, sys, tempfile, wave, json
import numpy as np

SR = 22050


def decodifica(path, tmp):
    out = os.path.join(tmp, 'x.wav')
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@22050', '-c', '1', path, out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    w = wave.open(out)
    n = w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    w.close()
    return a


def misura(a):
    dur = len(a) / SR
    hop, win = 512, 2048
    nfr = (len(a) - win) // hop
    if nfr < 50:
        return None
    frames = np.lib.stride_tricks.as_strided(a, shape=(nfr, win), strides=(a.strides[0] * hop, a.strides[0]))
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    # arco: energia media in 5 tratti, in dB relativi al massimo
    tratti = np.array_split(rms, 5)
    arco = [float(20 * np.log10(t.mean() / (rms.max() + 1e-9))) for t in tratti]
    # spettro
    hann = np.hanning(win)
    idx = np.linspace(0, nfr - 1, min(nfr, 400)).astype(int)
    spec = np.abs(np.fft.rfft(frames[idx] * hann, axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(win, 1 / SR)
    centroid = float((spec * freqs).sum(axis=1).mean() / spec.sum(axis=1).mean())
    flat = float(np.exp(np.log(spec).mean(axis=1)).mean() / spec.mean(axis=1).mean())
    # onset strength: differenza positiva dell'inviluppo (log)
    env = np.log(rms + 1e-6)
    onset = np.maximum(env[1:] - env[:-1], 0)
    onset -= onset.mean()
    perc = float(onset.std())
    # bpm: autocorrelazione dell'onset fra 60 e 180 bpm
    fps = SR / hop
    ac = np.correlate(onset, onset, mode='full')[len(onset) - 1:]
    ac /= (ac[0] + 1e-9)
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    seg = ac[lo:hi]
    k = int(np.argmax(seg)) + lo
    bpm = 60 * fps / k
    forza = float(seg.max())
    lfo = float(rms[:len(rms) // 1].std() / (rms.mean() + 1e-9))
    return dict(dur=round(dur), arco=[round(x, 1) for x in arco], centroide=round(centroid),
                piatt=round(flat, 3), perc=round(perc, 3), bpm=round(bpm), bpm_forza=round(forza, 2),
                var_rms=round(lfo, 2))


def main():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for f in sorted(glob.glob(os.path.expanduser('~/Desktop/altri_sound/**/*.mp3'), recursive=True)):
            try:
                m = misura(decodifica(f, tmp))
            except Exception as e:
                m = {'errore': str(e)}
            out[os.path.relpath(f, os.path.expanduser('~/Desktop/altri_sound'))] = m
            print(os.path.relpath(f, os.path.expanduser('~/Desktop/altri_sound'))[:70].ljust(70), json.dumps(m, ensure_ascii=False), flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


main()

"""SO (3/10/2026) — con il singolo opt-in acceso le schermate dicono la cosa
vera: dopo l'iscrizione parte il BENVENUTO (un suo link apre i contenuti),
non l'email «Entro nel Cerchio». I cancelli leggono la modalita' dal server
(lib/cerchio.ultimaModalita) e l'account non parla piu' di «conferma».
Il doppio opt-in (interruttore spento) conserva le parole di sempre.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"
CERCHIO = (FE / "lib" / "cerchio.js").read_text(encoding="utf-8")


class TestCancelli:
    def test_la_modalita_arriva_dal_server(self):
        assert "export const ultimaModalita = () => _ultimaModalita;" in CERCHIO
        assert "const risposta = await api.post('/public/newsletter/subscribe'" in CERCHIO
        assert "_ultimaModalita = risposta?.data?.modalita === 'benvenuto' ? 'benvenuto' : 'conferma';" in CERCHIO
        assert "export function testoAttesa(" in CERCHIO
        assert "Ti abbiamo mandato la prima Lettera del Cerchio: apri l’email e tocca un suo link." in CERCHIO
        assert "apri l’email e clicca «Entro nel Cerchio»" in CERCHIO           # spento: le parole di sempre

    def test_i_tre_cancelli_e_l_account(self):
        med = (FE / "features" / "frequenze" / "MeditazioniPage.js").read_text(encoding="utf-8")
        assert "testoAttesa('con le meditazioni sbloccate')" in med and 'data-testid="med-attesa-conferma"' in med
        assert "clicca «Entro nel Cerchio»" not in med                          # il testo fisso DOI non c'e' piu'
        can = (FE / "features" / "frequenze" / "CancelloLettera.jsx").read_text(encoding="utf-8")
        assert "testoAttesa('con la meditazione intera sbloccata')" in can and 'data-testid="cancello-attesa"' in can
        inv = (FE / "features" / "frequenze" / "InvitoSound.jsx").read_text(encoding="utf-8")
        assert "ultimaModalita() === 'benvenuto'" in inv and "la prima Lettera è in arrivo" in inv
        for f in ("MeditazioniPage.js", "CancelloLettera.jsx", "InvitoSound.jsx"):
            src = (FE / "features" / "frequenze" / f).read_text(encoding="utf-8")
            riga = next(l for l in src.splitlines() if "lib/cerchio" in l and "import" in l)
            assert ("testoAttesa" in riga) or ("ultimaModalita" in riga), f
        acc = (FE / "features" / "account" / "AccountPage.js").read_text(encoding="utf-8")
        assert "Manca solo un clic: apri una delle email del Cerchio" in acc
        assert "defaultValue: 'Rimandami l\\u2019email'" in acc
        assert "'Rimanda l\\u2019email di conferma'" not in acc            # il vecchio bottone non c'e' piu'
        # le chiavi account.guidesPending/guidesResend NON stanno nei locales: vale il
        # defaultValue nel sorgente (se un giorno entrano nei json, vanno aggiornate li')
        import json
        for lang in ("it", "en", "de", "fr"):
            acc_json = json.loads((FE / "locales" / lang / "landings.json").read_text(encoding="utf-8")).get("account", {})
            assert "guidesPending" not in acc_json and "guidesResend" not in acc_json, lang

"""MR5 (8/10/2026, piano refinement meditazioni) — IL DESIGN DELLA CASA.

Testata col saluto, vetrina a tutta larghezza su telefono, card piu' grandi,
«Vedi tutte», ricerca nel foglio su telefono, barra in vetro, scheletri,
stati vuoti, movimento rispettoso.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestDesign:
    def test_pagina(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "const saluto = () =>" in src and "<h1>{saluto()}, <em>{spazio.nome}</em></h1>" in src
        assert 'data-testid="casa-account"' in src and "backcard" not in src
        assert "function Scheletro()" in src and "{items === null ? <Scheletro /> :" in src
        assert "className={`oggi grande tono-" in src
        assert "onTutte && tutteN > n" in src and 'data-testid={`casa-tutte-${id}`}' in src
        assert 'data-testid="casa-cerca-foglio"' in src and 'data-testid="casa-barra-cerca"' in src
        assert 'data-testid="casa-vuoto"' in src and 'data-testid="casa-torna"' in src
        # le righe con «Vedi tutte» portano alla lista intera, non a quella tagliata
        assert "setVista({ titolo: 'Novità', items: tutte })" in src

    def test_css(self):
        css = (FQ / "casa" / "casa.css").read_text()
        for v in ("--raggio:20px", ".fqz.casa .oggi.grande .oggi-corpo{position:absolute",
                  "@media(max-width:899px){.fqz.casa .cerca-inline{display:none}}",
                  "backdrop-filter:blur(18px) saturate(140%)", "@keyframes skel", "@media(prefers-reduced-motion:reduce)"):
            assert v in css, v

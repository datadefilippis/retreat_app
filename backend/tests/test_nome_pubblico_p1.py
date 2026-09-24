"""P1 (24/9/2026, founder) — la PERSONA prima del marchio.

Prima: il profilo era intestato solo a `organizations.name` (obbligatorio
al signup) e 7 profili su 20 in produzione erano marchi impersonali.
Ora: `public_profile.nome_persona` + UNA regola (services/nome_pubblico.py,
specchio in frontend/src/lib/nomePubblico.js) su tutte le superfici.

Tenuto fermo qui:
  1. la regola: «Nome · Marchio», solo persona, solo marchio (= ieri),
     marchio che contiene la persona → il marchio;
  2. il pregresso senza nome_persona e' IDENTICO a prima (invarianza);
  3. whitelist e payload: nome_persona salvabile, GET espone nome_pubblico,
     il profilo pubblico porta nome_persona e marchio separati;
  4. signup: attivita' facoltativa, org.name = persona se manca, e la
     persona entra nel profilo dal primo giorno;
  5. Crea/editor: nome e attivita' nell'essenziale, anteprima composta;
  6. parita' della regola col frontend (stesso separatore, stessa soglia).
"""
import re
from pathlib import Path

from services.nome_pubblico import SEPARATORE, contiene_persona, nome_pubblico, parti_nome

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"
JS = (FE / "lib" / "nomePubblico.js").read_text(encoding="utf-8")
PAGE = (FE / "features" / "settings" / "PublicProfilePage.js").read_text(encoding="utf-8")
HEADER = (FE / "features" / "storefront" / "components" / "OperatorIdentityHeader.jsx").read_text(encoding="utf-8")
LOGIN = (FE / "features" / "account" / "AccountLoginPage.js").read_text(encoding="utf-8")
INLINE = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text(encoding="utf-8")
AUTH = (BACKEND / "services" / "auth_service.py").read_text(encoding="utf-8")
ORGS = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
PUB = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
FREQ = (BACKEND / "routers" / "frequencies.py").read_text(encoding="utf-8")


def _org(name, persona=None, **pp):
    d = {"name": name, "public_profile": dict(pp)}
    if persona is not None:
        d["public_profile"]["nome_persona"] = persona
    return d


class TestRegola:
    def test_persona_e_marchio(self):
        assert nome_pubblico(_org("Brillare | Il Sole Dentro", "Valentina")) == "Valentina · Brillare | Il Sole Dentro"
        assert SEPARATORE == " · "

    def test_solo_persona_e_solo_marchio(self):
        assert nome_pubblico(_org("", "Valentina Rossi")) == "Valentina Rossi"
        assert nome_pubblico(_org("Cerchio Angelico")) == "Cerchio Angelico"
        assert nome_pubblico(_org("Cerchio Angelico", "")) == "Cerchio Angelico"

    def test_il_pregresso_e_identico(self):
        """Nessun nome_persona (tutti i profili di ieri) → org.name, byte per byte."""
        for nome in ("Ilaria", "Metodo Oltre", "Claudia Pietrantuoni - L'Alchimia dell'Essere"):
            assert nome_pubblico({"name": nome}) == nome
            assert nome_pubblico({"name": nome, "public_profile": {"bio": "x"}}) == nome
        assert nome_pubblico({"name": ""}, fallback="store-slug") == "store-slug"

    def test_marchio_che_contiene_la_persona_non_si_doppia(self):
        assert contiene_persona("Claudia Pietrantuoni - L'Alchimia dell'Essere", "Claudia Pietrantuoni")
        assert nome_pubblico(_org("Claudia Pietrantuoni - L'Alchimia dell'Essere", "Claudia Pietrantuoni")) \
            == "Claudia Pietrantuoni - L'Alchimia dell'Essere"
        assert nome_pubblico(_org("Rigveda di Claudia Cannatà", "Claudia Cannatà")) == "Rigveda di Claudia Cannatà"
        assert not contiene_persona("Cerchio Angelico", "Paola Artico")
        # persona = marchio (stessa stringa): una volta sola
        assert nome_pubblico(_org("Seva Kaur", "Seva Kaur")) == "Seva Kaur"
        # domanda del founder (24/9): «Valentina» + «Valentina-brillare» → mai
        # «Valentina · Valentina-brillare», e nemmeno con il cognome
        assert nome_pubblico(_org("Valentina-brillare", "Valentina")) == "Valentina-brillare"
        assert nome_pubblico(_org("Valentina - Brillare", "Valentina Rossi")) == "Valentina - Brillare"
        assert nome_pubblico(_org("Brillare | Il Sole Dentro ~ Valentina", "Valentina")) == "Brillare | Il Sole Dentro ~ Valentina"
        # le particelle corte non contano: «Studio di Ada» non «contiene» «Ada Bianchi»? Ada ha 3 lettere: conta
        assert nome_pubblico(_org("Studio Zenith", "Ada Bianchi")) == "Ada Bianchi · Studio Zenith"

    def test_parti_per_l_intestazione(self):
        p = parti_nome(_org("Casa Coco", "Erika Manzari"))
        assert p == {"persona": "Erika Manzari", "marchio": "Casa Coco", "composto": True,
                     "pubblico": "Erika Manzari · Casa Coco"}
        q = parti_nome(_org("Ilaria"))
        assert q["persona"] is None and q["marchio"] is None and q["pubblico"] == "Ilaria"

    def test_pulizia_e_tetto(self):
        assert nome_pubblico(_org("X", "  Anna   Bianchi ")) == "Anna Bianchi · X"
        assert len(parti_nome(_org("X", "a" * 200))["persona"]) == 80


class TestModelloEPayload:
    def test_whitelist_e_get(self):
        assert '"nome_persona": 80' in ORGS
        # 24/9 sera: composto sul nome EFFETTIVO (profilo, o account se manca)
        assert '"nome_pubblico": nome_pubblico(org_eff)' in ORGS

    def test_tutte_le_superfici_usano_la_regola(self):
        assert PUB.count("_nome_pubblico(") >= 3
        assert '"nome_persona": _parti_nome(org)["persona"]' in PUB and '"marchio": _parti_nome(org)["marchio"]' in PUB
        # niente piu' campo fantasma display_name nel Sound
        assert '"public_profile.display_name"' not in FREQ and 'profile.get("display_name")' not in FREQ
        assert FREQ.count("_np(org") >= 2

    def test_signup_attivita_facoltativa_e_persona_dal_primo_giorno(self):
        assert "f\"{user_data.name}'s Organization\"" not in AUTH
        assert 'org_name = (user_data.organization_name or "").strip() or nome_persona' in AUTH
        assert 'org_doc["public_profile"] = {"nome_persona": nome_persona[:80]}' in AUTH


class TestFrontend:
    def test_parita_della_regola(self):
        assert "export const SEPARATORE = ' · ';" in JS
        assert "export const NOME_PERSONA_MAX = 80;" in JS
        assert "p.length > 2" in JS      # stessa soglia delle particelle («di», «e»)
        assert "parti.some((p) => m.includes(p))" in JS   # una parola basta, come nel backend

    def test_editor_nome_e_attivita_in_alto(self):
        assert 'data-testid="profile-nome-persona"' in PAGE and 'data-testid="profile-marchio"' in PAGE
        assert "nomePubblico(form.nome_persona, orgName)" in PAGE
        assert "'nome_persona'];" in PAGE          # nel payload del Salva
        assert "publicProfile.publicName" not in PAGE

    def test_intestazione_persona_grande_marchio_sotto(self):
        assert "data.nome_persona && data.marchio ? data.nome_persona : data.name" in HEADER
        assert 'data-testid="operator-marchio"' in HEADER

    def test_registrazione_attivita_facoltativa(self):
        blocco = LOGIN.split('data-testid="signup-org"')[0][-900:]
        assert "required" not in blocco.split("<input")[-1]
        assert "Nome della tua attività (facoltativo)" in LOGIN and "Nome e cognome" in LOGIN
        assert 'data-testid="signup-nome-avviso"' in LOGIN
        assert "Nome della tua attività (facoltativo)" in INLINE
        assert re.search(r'<input type="text" value=\{organizationName\}', INLINE)

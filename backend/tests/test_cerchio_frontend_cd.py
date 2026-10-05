"""
Lotto D · Frontend Cerchio (24/9/2026) — le guardie sul sorgente.

docs/PIANO_ESECUZIONE_ADMIN_CERCHIO_2026-09-24.md, Lotto D. Solo guardie
sul sorgente: niente DB, niente backend acceso, niente browser.

  D1 lib/testiConsenso.js + i form (cerchio.js, LeadForm) che mandano
     url/referrer/utm/consenso_versione.
  D2 OGNI superficie del Cerchio mostra il testo corrente da
     lib/testiConsenso.js (non piu' da i18n o da un letterale), tiene il
     link Privacy dove c'era, e nessuna promette piu' un passo di
     conferma («Una conferma via email, poi sei dentro»).
  D3 IscrittiTab rifatta: mappa cliccabile, filtri, colonne a scelta in
     localStorage, scheda coi sei blocchi, azioni con conferma e i
     testid vecchi intatti.
  D4 LeadsTab con `tipo`, «Iscritto» e «Account»; montata due volte.
  Lessico: mai «organizzatori».
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"

TESTI_JS = (FE / "lib" / "testiConsenso.js").read_text()
CERCHIO = (FE / "lib" / "cerchio.js").read_text()
LEADFORM = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text()
ISCRITTI = (FE / "features" / "admin" / "IscrittiTab.js").read_text()
LEADS = (FE / "features" / "admin" / "LeadsTab.js").read_text()
OPERATORI = (FE / "features" / "admin" / "OperatoriPage.js").read_text()
CERCHIO_PAGE = (FE / "features" / "admin" / "CerchioPage.js").read_text()

# le otto superfici con la casella del Cerchio: (file, ha il link Privacy)
SUPERFICI = {
    "features/frequenze/CancelloLettera.jsx": True,
    "features/frequenze/MeditazioniPage.js": True,
    "features/frequenze/InvitoSound.jsx": True,
    "features/prelaunch/NewsletterLandingPage.js": False,   # il link sta in LeadForm
    "features/prelaunch/TravelerLandingPage.js": False,
    "features/network/NetworkHomePage.js": False,
    "features/storefront/components/BlogNewsletterCTA.jsx": False,
    "features/storefront/BlogArticlePage.js": False,
}


def _src(rel: str) -> str:
    return (FE / rel).read_text()


class TestD1FormEProvenienza:
    def test_lo_specchio_dei_testi(self):
        for nome in ("export const TESTI", "export const VERSIONE_CORRENTE",
                     "export function testoConsenso", "export function provenienzaCorrente"):
            assert nome in TESTI_JS, nome
        # la provenienza: url, referrer, i tre utm
        for pezzo in ("window.location.href", "document.referrer",
                      "utm_source", "utm_medium", "utm_campaign"):
            assert pezzo in TESTI_JS, pezzo

    def test_cerchio_js_manda_provenienza_e_versione(self):
        assert "from './testiConsenso'" in CERCHIO
        blocco = CERCHIO[CERCHIO.index("export async function iscriviESblocca"):]
        assert "...provenienzaCorrente()" in blocco
        assert "consenso_versione: VERSIONE_CORRENTE" in blocco
        # gli invarianti dei giri precedenti
        assert "unlock_flow: true" in blocco
        assert "ritiri = null" in CERCHIO

    def test_leadform_manda_provenienza_e_versione(self):
        assert "from '../../lib/testiConsenso'" in LEADFORM
        blocco = LEADFORM[LEADFORM.index("await api.post('/public/newsletter/subscribe'"):]
        blocco = blocco[:blocco.index("});")]
        assert "...provenienzaCorrente()" in blocco
        assert "consenso_versione: VERSIONE_CORRENTE" in blocco
        # il testo di fallback sulle porte del Cerchio e' quello versionato
        assert "subscribe ? testoConsenso().testo" in LEADFORM
        # i letterali che test_newsletter_nw e i cicli precedenti guardano
        for lit in ("experiencesOptIn", "wants_experiences", "PreferenzeRitiri",
                    "setState('error')", "unlock_flow: !!onSbloccato", "giaDentro"):
            assert lit in LEADFORM, lit


class TestD2Superfici:
    def test_ogni_superficie_usa_il_testo_corrente(self):
        for rel, privacy in SUPERFICI.items():
            src = _src(rel)
            assert "lib/testiConsenso'" in src, f"{rel}: non importa lib/testiConsenso"
            assert "testoConsenso().testo" in src, f"{rel}: la casella non usa il testo corrente"
            if privacy:
                assert 'href="/privacy"' in src, f"{rel}: il link Privacy e' sparito"

    def test_nessuna_casella_passa_da_i18n_o_da_un_letterale(self):
        for rel in SUPERFICI:
            src = _src(rel)
            for morto in ("t('nl.consent'", "t('tr.consent'", "t('blogCta.consent'",
                          "Acconsento a ricevere"):
                assert morto not in src, f"{rel}: {morto}"
        # LeadForm: il letterale resta SOLO per la candidatura (form.consent)
        assert LEADFORM.count("Acconsento a") == 1

    def test_nessuna_promessa_di_un_passo_di_conferma(self):
        vietate = ("Una conferma via email, poi sei dentro", "Confermerai dall")
        for p in FE.rglob("*"):
            if p.suffix not in (".js", ".jsx", ".json") or "locales/" in str(p) and "/it/" not in str(p):
                continue
            if p.name == "testiConsenso.js":
                continue        # l'archivio dei testi storici (cerchio-v2) li cita per forza
            src = p.read_text(errors="ignore")
            for v in vietate:
                assert v not in src, f"{p.relative_to(FE)}: «{v}»"
        # e la riga di fiducia dice una cosa vera con o senza doppio opt-in
        for rel in ("features/prelaunch/NewsletterLandingPage.js",
                    "features/prelaunch/TravelerLandingPage.js",
                    "features/network/NetworkHomePage.js"):
            assert "Gratis, e ti cancelli con un clic." in _src(rel), rel

    def test_i_testid_delle_superfici_restano(self):
        c = _src("features/frequenze/CancelloLettera.jsx")
        for t in ("cancello-consenso", "cancello-iscriviti", "cancello-gia-iscritto", "cancello-accedi", "cancello-crea"):
            assert f'data-testid="{t}"' in c, t
        assert 'data-testid="med-consenso"' in _src("features/frequenze/MeditazioniPage.js")
        assert 'data-testid="blog-gate-already"' in _src("features/storefront/BlogArticlePage.js")
        for rel in ("features/prelaunch/NewsletterLandingPage.js", "features/prelaunch/TravelerLandingPage.js",
                    "features/network/NetworkHomePage.js", "features/storefront/components/BlogNewsletterCTA.jsx",
                    "features/storefront/BlogArticlePage.js"):
            assert "experiencesOptIn" in _src(rel) or "wantsExperiencesAlways" in _src(rel), rel


class TestD3IscrittiTab:
    def test_i_testid_vecchi_restano(self):
        for t in ("iscritti-tab", "iscritti-riga", "iscritti-export", "iscritti-totale",
                  "iscritti-f-stato", "iscritti-f-porta", "iscritti-f-fonte", "iscritti-f-ritiri",
                  "iscritti-f-q", "iscritti-dettaglio", "iscritti-disiscrivi"):
            assert f'data-testid="{t}"' in ISCRITTI, t
        assert "data-testid={`iscritti-stato-${status}`}" in ISCRITTI
        assert "/admin/subscribers" in ISCRITTI

    def test_la_mappa_cliccabile(self):
        for k in ("by_budget", "by_travel", "by_canale", "verificati"):
            assert k in ISCRITTI, k
        for t in ("iscritti-rip-budget", "iscritti-rip-dove", "iscritti-rip-canale"):
            assert f'testid="{t}"' in ISCRITTI, t
        assert "toggleFiltro('budget'" in ISCRITTI and "toggleFiltro('travel'" in ISCRITTI \
            and "toggleFiltro('canale'" in ISCRITTI

    def test_i_filtri_nuovi_e_le_tendine_collegate(self):
        for t in ("iscritti-f-canale", "iscritti-f-superficie", "iscritti-f-budget", "iscritti-f-dove",
                  "iscritti-f-regione", "iscritti-f-via", "iscritti-f-verificato", "iscritti-f-dal",
                  "iscritti-f-al", "iscritti-f-tag"):
            assert f'data-testid="{t}"' in ISCRITTI, t
        # cambiare canale azzera la superficie; le etichette vengono dalla risposta
        assert "canale: v, superficie: ''" in ISCRITTI
        assert "l.data.canali" in ISCRITTI and "c.superfici" in ISCRITTI

    def test_le_colonne_a_scelta_in_localstorage(self):
        assert 'data-testid="iscritti-colonne"' in ISCRITTI
        assert "const CHIAVE_COLONNE = 'iscritti-colonne'" in ISCRITTI
        # sia la lettura che la scrittura sono dentro un try (private mode)
        assert "try {\n    const raw = JSON.parse(localStorage.getItem(CHIAVE_COLONNE)" in ISCRITTI
        assert "try { localStorage.setItem(CHIAVE_COLONNE" in ISCRITTI
        # le predefinite, nell'ordine deciso
        blocco = ISCRITTI[ISCRITTI.index("const COLONNE = ["):ISCRITTI.index("const COLONNE_DEFAULT")]
        chiavi = re.findall(r"\{ k: '([\w_]+)', label: '([^']+)'", blocco)
        # 24/9 sera (founder): «Vie» torna fra le predefinite; «Email inviate»
        # dice cosa conta (automatiche mandate, non aperte)
        # ET3 (2/10): «Età» entra fra le predefinite, dopo Budget
        assert [c[1] for c in chiavi[:12]] == ["Email", "Nome", "Stato", "Provenienza", "Iscritto il",
                                                "Budget", "Età", "Dove", "Città", "Avviso ritiri", "Vie", "Email inviate"]
        assert "COLONNE.slice(0, 12)" in ISCRITTI
        assert "Email ricevute" not in ISCRITTI and "function emailDettaglio" in ISCRITTI
        extra = {c[1] for c in chiavi[12:]}
        assert extra == {"Temi", "Lingua", "Confermato il", "Porta", "Campagna",   # MP4: la campagna delle sponsorizzate
                         "Ultima email", "Tag", "Consenso", "Verificato"}

    def test_la_scheda_coi_sei_blocchi_e_la_cronologia(self):
        assert 'data-testid="iscritti-scheda"' in ISCRITTI
        assert "api.get(`/admin/subscribers/${encodeURIComponent(email)}`)" in ISCRITTI
        for titolo in ("Identità", "Consenso", "Provenienza", "Interessi", "Ritiri", "Ciclo di vita", "Cronologia", "Note"):
            assert f'titolo="{titolo}"' in ISCRITTI, titolo
        # il registro del consenso leggibile, con l'ip (solo nella scheda)
        assert "Ha accettato il testo ${c.versione" in ISCRITTI and "IP ${c.ip}" in ISCRITTI
        assert "scheda.cronologia" in ISCRITTI and "scheda.legami" in ISCRITTI

    def test_le_azioni_con_conferma(self):
        for t in ("iscritti-reinvia", "iscritti-conferma", "iscritti-preferenze", "iscritti-nota",
                  "iscritti-tag", "iscritti-disiscrivi", "iscritti-elimina", "iscritti-motivo"):
            assert f'data-testid="{t}"' in ISCRITTI, t
        for rotta in ("/admin/subscribers/reinvia-conferma", "/admin/subscribers/conferma",
                      "/admin/subscribers/disiscrivi", "/preferenze`", "/note`", "/tag`"):
            assert rotta in ISCRITTI, rotta
        # elimina: DELETE col motivo nel corpo, a DUE passi
        assert "api.delete(`/admin/subscribers/${encodeURIComponent(email)}`, { data: { motivo" in ISCRITTI
        assert "setAzione({ ...azione, passo: 2 })" in ISCRITTI
        # conferma a mano ed elimina pretendono il motivo
        assert ISCRITTI.count("(azione.motivo || '').trim().length < 3") == 2
        # niente window.confirm: le conferme sono finestre vere
        assert "window.confirm" not in ISCRITTI


class TestD4Leads:
    def test_leadstab_tipo_iscritto_account(self):
        assert "const LeadsTab = ({ tipo = undefined })" in LEADS
        assert "rows.filter((r) => (r.type || 'traveler') === tipo)" in LEADS
        assert "<TableHead>Iscritto</TableHead>" in LEADS and "<TableHead>Account</TableHead>" in LEADS
        assert "r.iscritto" in LEADS and "r.organizzazione_id" in LEADS
        assert 'data-testid="leads-iscritto"' in LEADS and 'data-testid="leads-account"' in LEADS
        assert "listSubscribers" not in LEADS       # un posto solo per gli iscritti

    def test_montata_due_volte_filtrata(self):
        assert '<LeadsTab tipo="operator" />' in OPERATORI
        assert "Contatti dalle landing (professionisti)" in OPERATORI
        assert "value: 'account'" in OPERATORI and "<UsersTab />" in OPERATORI
        assert '<LeadsTab tipo="traveler" />' in CERCHIO_PAGE
        assert "<SequenzeTab />" in CERCHIO_PAGE

    def test_il_link_account_apre_la_scheda(self):
        assert "tab=organizzazioni&org=" in LEADS
        org_tab = (FE / "features" / "admin" / "OrganizationsTab.js").read_text()
        assert "get('org')" in org_tab and "apriScheda(org)" in org_tab


class TestLessico:
    def test_mai_organizzatori(self):
        for src, nome in ((ISCRITTI, "IscrittiTab"), (LEADS, "LeadsTab"), (OPERATORI, "OperatoriPage"),
                          (CERCHIO_PAGE, "CerchioPage"), (TESTI_JS, "testiConsenso")):
            assert "organizzator" not in src.lower(), nome

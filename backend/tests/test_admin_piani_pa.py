"""
CICLO PA (30/8/2026) — l'admin parla la lingua dell'offerta.

Il founder: «in Details vedo elementi di AI chat che non esistono,
nomi di abbonamenti AFianco, cashflow e cazzi vari — voglio la
verita' di Aurya e basta.» Piano in
docs/ADMIN_PIANI_CONSOLIDAMENTO_2026-08.md.

La verita': 4 piani (Gratis, Pro 19, Founding e Partner — leve del
founder 4-5/7, riservati), trial inesistente (Pro trial_days: 0),
zero add-on. Il motore del provisioning (moduli) resta ma si
RIPIEGA: mai piu' in prima linea.
"""
from pathlib import Path

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
ADMIN = FE / "features" / "admin"


class TestPa1FonteUnica:
    def test_i_quattro_piani_col_loro_nome(self):
        src = (ADMIN / "pianiAurya.js").read_text()
        for slug, nome in (("retreat_free", "Gratis"), ("retreat_pro", "Pro"),
                           ("retreat_founding", "Founding"),
                           ("retreat_partner", "Partner")):
            assert slug in src and f"'{nome}'" in src
        # i riservati portano il cartellino
        assert src.count("riservato: true") == 2
        assert "STATI" in src and "'in prova'" in src

    def test_il_badge_passa_dalla_fonte(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        assert "nomePiano(" in src and "classePiano(" in src
        for estinto in ("enterprise:", "starter:", "core:"):
            assert estinto not in src, f"palette di piani estinti: {estinto}"


class TestPa3MotoreRipiegato:
    def test_commercial_e_sync_fuori_dalla_prima_linea(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        assert "OrgCommercialStateDialog" not in src
        assert "setCommercialStateOpen" not in src
        assert "<TableHead>Sync</TableHead>" not in src
        assert "SyncBadge" not in src

    def test_lo_stato_tecnico_e_un_details(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        assert 'data-testid="org-stato-tecnico"' in src
        assert "reprovisionOrg" in src, "il riallineamento resta possibile"

    def test_il_banner_parla_solo_coi_problemi(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        assert "{anyIssue && (" in src
        assert "Catalog in sync" not in src, "il verde permanente era rumore"


class TestPa4AzioniVere:
    def test_i_pannelli_fantasma_sono_usciti(self):
        src = (ADMIN / "AdminOrgBillingActions.jsx").read_text()
        for fantasma in ("CustomPlanPanel", "AddonsPanel", "ExtendTrialPanel",
                         "Custom Plan", "Extend Trial"):
            assert fantasma not in src, f"pannello fuori scope: {fantasma}"
        assert "UsagePanel" in src and "ImpersonatePanel" in src

    def test_l_utilizzo_dice_solo_cio_che_esiste(self):
        """Le metriche dei moduli spenti (l'AI chat) non si mostrano;
        quelle vive hanno il nome vero, non module.key."""
        src = (ADMIN / "AdminOrgBillingActions.jsx").read_text()
        assert "m.status !== 'off'" in src.replace('"', "'")
        assert "nomeMetrica(m.module, m.key)" in src
        fonte = (ADMIN / "pianiAurya.js").read_text()
        assert "Movimenti registrati" in fonte and "Voci a listino" in fonte


class TestPa5Briciole:
    def test_niente_conversazioni_ai_nell_eliminazione(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        assert "conversazioni AI" not in src
        assert "Tracce e condivisioni di Aurya Sound" in src

    def test_la_pagina_parla_italiano(self):
        src = (ADMIN / "OrganizationsTab.js").read_text()
        for voce in ("Dettagli", "Sospendi", "Cambia piano", "Aggiorna"):
            assert voce in src
        assert "Change Commercial Plan" not in src
        assert "re-provisions all module subscriptions" not in src

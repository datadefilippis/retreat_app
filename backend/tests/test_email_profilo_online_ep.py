"""EP (19/9/2026) — l'email «La tua pagina è online» rifatta con il founder.

- I canali della rete: bacheca Telegram, supporto tecnico e digitale,
  Instagram, con il link scritto per esteso. I link Telegram vengono
  dall'ambiente (TELEGRAM_BACHECA_URL, TELEGRAM_SUPPORTO_URL; il vecchio
  TELEGRAM_GRUPPO_URL vale come bacheca); senza nessun link Telegram
  l'email torna a «rispondi con il tuo nome Telegram» e non mostra t.me.
- I ritiri: come funzionano, i tempi, il programma; la caparra/IBAN solo a
  chi l'IBAN non l'ha ancora messo.
- La consulenza a pagamento: info@aurya.life, in privato.
- Niente più articoli del Magazine, niente «rispondi con il tuo numero».
"""
import importlib

BACHECA = "https://t.me/+bacheca-test"
SUPPORTO = "https://t.me/+supporto-test"


def _mod():
    import services.email_sequenze as T
    return importlib.reload(T)


def _ctx(iban: bool):
    return {"nome": "Martina Rossi", "email": "m@example.com",
            "stato": {"online": True, "ritiro": False, "slug": "martina", "iban": iban}}


class TestCanali:
    def test_con_i_link_i_tre_canali_sono_scritti_per_esteso(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BACHECA_URL", BACHECA)
        monkeypatch.setenv("TELEGRAM_SUPPORTO_URL", SUPPORTO)
        monkeypatch.delenv("INSTAGRAM_URL", raising=False)
        T = _mod()
        oggetto, c = T.op_profilo_online(_ctx(iban=False))
        assert oggetto == "La tua pagina è online: ecco il link"
        assert "Tre posti, tre usi diversi" in c
        for url in (BACHECA, SUPPORTO, "https://www.instagram.com/aurya.life"):
            assert f'<a href="{url}">{url}</a>' in c, url          # link visibile, non solo ancorato
        assert "Bacheca Aurya" in c and "Supporto tecnico e digitale" in c and "Instagram" in c
        assert "tutto quello che succede nel mondo Aurya" in c
        assert "rispondi a questa email con il tuo numero" not in c
        assert "nome Telegram" not in c

    def test_senza_link_telegram_si_chiede_l_invito_e_non_si_mostra_t_me(self, monkeypatch):
        for v in ("TELEGRAM_BACHECA_URL", "TELEGRAM_SUPPORTO_URL", "TELEGRAM_GRUPPO_URL"):
            monkeypatch.delenv(v, raising=False)
        T = _mod()
        _, c = T.op_profilo_online(_ctx(iban=False))
        assert "t.me/" not in c
        assert "nome Telegram" in c and "Telegram" in c
        assert "instagram.com/aurya.life" in c            # Instagram resta sempre

    def test_il_vecchio_gruppo_unico_vale_come_bacheca(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BACHECA_URL", raising=False)
        monkeypatch.delenv("TELEGRAM_SUPPORTO_URL", raising=False)
        monkeypatch.setenv("TELEGRAM_GRUPPO_URL", BACHECA)
        T = _mod()
        _, c = T.op_profilo_online(_ctx(iban=True))
        assert BACHECA in c and "Bacheca Aurya" in c and "Due posti, due usi diversi" in c
        assert "Supporto tecnico" not in c


class TestRitiriEConsulenza:
    def test_la_caparra_solo_a_chi_non_ha_l_iban(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BACHECA_URL", BACHECA)
        monkeypatch.setenv("TELEGRAM_SUPPORTO_URL", SUPPORTO)
        T = _mod()
        _, senza = T.op_profilo_online(_ctx(iban=False))
        _, con = T.op_profilo_online(_ctx(iban=True))
        assert "IBAN" in senza and "La caparra" in senza and "Tre cose che fanno la differenza" in senza
        assert "IBAN" not in con and "La caparra" not in con and "Due cose che fanno la differenza" in con
        for c in (senza, con):
            assert "I tempi" in c and "Il programma" in c and "Se pubblichi un ritiro" in c

    def test_la_consulenza_e_privata_a_pagamento_e_niente_articoli(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BACHECA_URL", BACHECA)
        monkeypatch.setenv("TELEGRAM_SUPPORTO_URL", SUPPORTO)
        monkeypatch.delenv("CONSULENZA_EMAIL", raising=False)
        T = _mod()
        _, c = T.op_profilo_online(_ctx(iban=True))
        assert 'href="mailto:info@aurya.life"' in c and "consulenza a pagamento" in c
        assert "in privato" in c and "Aurya affianca chi organizza un ritiro" in c
        assert "/blog/" not in c
        assert c.count('class="btn"') == 1 and "Apri la tua pagina" in c
        assert "la legge Valentina" in c and "Valentina e Davide" in c


class TestPromemoriaInterno:
    def test_il_promemoria_a_noi_non_esiste_piu(self):
        """PE1 (24/9, founder): «Da 2 giorni su Aurya» era l'email piu'
        inviata di tutte e non serviva. La coda di lavoro vive in admin."""
        T = _mod()
        assert not hasattr(T, "op_g2_admin")
        import pathlib
        assert "Da 2 giorni su Aurya" not in pathlib.Path(T.__file__).read_text(encoding="utf-8")

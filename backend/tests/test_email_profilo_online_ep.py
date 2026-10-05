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
    """FL3 (5/10/2026, founder): i canali hanno un'email propria (op_canali), il
    giro dopo la pagina online. Ogni link scritto per esteso; senza Telegram
    si chiede il nome, mai un link che non c'e'."""

    def test_con_i_link_i_tre_canali_sono_scritti_per_esteso(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BACHECA_URL", BACHECA)
        monkeypatch.setenv("TELEGRAM_SUPPORTO_URL", SUPPORTO)
        monkeypatch.delenv("INSTAGRAM_URL", raising=False)
        T = _mod()
        oggetto, c = T.op_canali(_ctx(iban=False))
        assert oggetto == "I canali della rete Aurya"
        for url in (BACHECA, SUPPORTO, "https://www.instagram.com/aurya.life"):
            assert f'<a href="{url}">{url}</a>' in c, url          # link visibile, non solo ancorato
        assert "Bacheca Aurya" in c and "Supporto" in c and "Instagram" in c
        assert "nome Telegram" not in c
        _, pagina = T.op_profilo_online(_ctx(iban=False))        # la pagina online non li ripete
        assert "Telegram" not in pagina and "t.me/" not in pagina

    def test_senza_link_telegram_si_chiede_l_invito_e_non_si_mostra_t_me(self, monkeypatch):
        for v in ("TELEGRAM_BACHECA_URL", "TELEGRAM_SUPPORTO_URL", "TELEGRAM_GRUPPO_URL"):
            monkeypatch.delenv(v, raising=False)
        T = _mod()
        _, c = T.op_canali(_ctx(iban=False))
        assert "t.me/" not in c
        assert "nome Telegram" in c and "Telegram" in c
        assert "instagram.com/aurya.life" in c            # Instagram resta sempre

    def test_il_vecchio_gruppo_unico_vale_come_bacheca(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BACHECA_URL", raising=False)
        monkeypatch.delenv("TELEGRAM_SUPPORTO_URL", raising=False)
        monkeypatch.setenv("TELEGRAM_GRUPPO_URL", BACHECA)
        T = _mod()
        _, c = T.op_canali(_ctx(iban=True))
        assert BACHECA in c and "Bacheca Aurya" in c
        assert "Supporto" not in c


class TestRitiriEConsulenza:
    """FL3 (5/10/2026, founder): la pagina online fa UNA cosa (il link e il
    listino). Niente caparra/IBAN, niente consulenza a pagamento qui: i
    ritiri hanno la loro email (op_r14)."""

    def test_la_pagina_online_fa_una_cosa(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BACHECA_URL", BACHECA)
        monkeypatch.setenv("TELEGRAM_SUPPORTO_URL", SUPPORTO)
        T = _mod()
        for iban in (False, True):
            _, c = T.op_profilo_online(_ctx(iban=iban))
            assert "IBAN" not in c and "consulenza" not in c and "mailto:" not in c and "/blog/" not in c
            assert c.count('class="btn"') == 1 and "Apri la tua pagina" in c
            assert "la legge Valentina" in c and "Valentina e Davide" in c
        assert T._blocco_ritiri(False) == "" and T._blocco_ritiri(True) == ""


class TestPromemoriaInterno:
    def test_il_promemoria_a_noi_non_esiste_piu(self):
        """PE1 (24/9, founder): «Da 2 giorni su Aurya» era l'email piu'
        inviata di tutte e non serviva. La coda di lavoro vive in admin."""
        T = _mod()
        assert not hasattr(T, "op_g2_admin")
        import pathlib
        assert "Da 2 giorni su Aurya" not in pathlib.Path(T.__file__).read_text(encoding="utf-8")

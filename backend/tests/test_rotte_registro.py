"""RS (26/8/2026) — IL REGISTRO DELLE ROTTE: la guardia che tiene l'ordine.

Prima di questo file la stessa conoscenza viveva in cinque posti —
App.js, nginx, la shell, la sitemap, robots — e nessuno li teneva
allineati. Il prezzo l'abbiamo pagato due volte in un giorno:
/meditazioni e /costi, pagine pubbliche (una nel menu!), servivano ai
crawler 46 caratteri e il titolo di luglio, perche' nessuno le aveva
aggiunte all'elenco di nginx.

Non era un bug di codice: era un bug di ORGANIZZAZIONE. E i bug di
organizzazione non si risolvono ricordandosi meglio — si risolvono
rendendo IMPOSSIBILE dimenticare.

Da qui in avanti: chi aggiunge una rotta in App.js e non la classifica
nel registro trova questa suite rossa. Non un mese dopo in Search
Console.
"""
import json
import os
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

RADICE = BACKEND_DIR.parent
REGISTRO = RADICE / "config" / "rotte.json"
APP_JS = RADICE / "frontend" / "src" / "App.js"
NGINX = RADICE / "deploy" / "nginx" / "nginx.conf"

# i percorsi che non sono "segmenti" e vivono di regole proprie in
# nginx: la radice, il catch-all di React, e la pagina link /@slug
FUORI_SCALA = {"*", "/", ""}


def _registro():
    return json.loads(REGISTRO.read_text(encoding="utf-8"))


def _segmenti_registro():
    d = _registro()
    return set(d["pubblica"]) | set(d["servizio"]) | set(d["app"])


def _segmenti_app_js():
    src = APP_JS.read_text(encoding="utf-8")
    rotte = re.findall(r'<Route\s+path="([^"]+)"', src)
    return {p.strip("/").split("/")[0] for p in rotte} - FUORI_SCALA


class TestRegistroRotte:

    def test_ogni_rotta_del_sito_e_classificata(self):
        """LA GUARDIA CENTRALE. Se qualcuno aggiunge una pagina e non
        dice che tipo e', questo test lo ferma — perche' una rotta non
        classificata oggi risponde 404 (non e' nel registro, quindi per
        nginx non esiste): il difetto si vedrebbe subito, ma meglio
        vederlo qui che in produzione."""
        mancanti = sorted(_segmenti_app_js() - _segmenti_registro())
        assert not mancanti, (
            f"rotte in App.js non classificate in config/rotte.json: "
            f"{mancanti}\nAggiungile fra 'pubblica', 'servizio' o 'app', "
            f"poi rigenera nginx: python3 scripts/genera_rotte_nginx.py --scrivi")

    def test_il_registro_non_inventa_rotte(self):
        """L'altro verso: un segmento nel registro che App.js non ha
        piu' e' una porta aperta su una stanza demolita."""
        fantasmi = sorted(_segmenti_registro() - _segmenti_app_js())
        assert not fantasmi, (
            f"nel registro ma non piu' in App.js: {fantasmi}")

    def test_una_rotta_sta_in_una_categoria_sola(self):
        d = _registro()
        for a, b in (("pubblica", "servizio"), ("pubblica", "app"),
                     ("servizio", "app")):
            doppi = set(d[a]) & set(d[b])
            assert not doppi, f"{sorted(doppi)} sia in {a} che in {b}"

    def test_nginx_combacia_col_registro(self):
        """nginx si GENERA dal registro: se qualcuno lo modifica a mano,
        o cambia il registro senza rigenerare, i due divergono in
        silenzio — ed e' esattamente cosi' che nascono le pagine mute."""
        sys.path.insert(0, str(BACKEND_DIR / "scripts"))
        import genera_rotte_nginx as gen
        b1, b2 = gen.blocchi()
        conf = NGINX.read_text(encoding="utf-8")
        assert b1 in conf, ("il blocco ROTTE-RENDERER non combacia. "
                            "Rigenera: python3 scripts/genera_rotte_nginx.py --scrivi")
        assert b2 in conf, "il blocco ROTTE-APP non combacia"

    def test_l_ignoto_risponde_404_e_non_riempie_la_memoria(self):
        """Il catch-all manda a UN endpoint solo, non al percorso
        richiesto: la shell cacha per percorso, e indirizzi arbitrari
        sarebbero una cache senza fine — un modo per esaurire la
        memoria del server scrivendo URL a caso."""
        conf = NGINX.read_text(encoding="utf-8")
        coda = conf.split("Tutto il resto NON ESISTE")[1]
        assert "/__seo/404" in coda
        assert "$request_uri" not in coda.split("location /")[1][:400], (
            "il catch-all passa il percorso richiesto: cache illimitata")
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '@router.get("/404")' in shell
        assert "status_code=404" in shell

    def test_gli_asset_non_finiscono_nel_404(self):
        """js, css, font e immagini non hanno un segmento nel registro:
        senza una regola loro, il catch-all li 404-erebbe e il sito
        resterebbe senza vestiti."""
        conf = NGINX.read_text(encoding="utf-8")
        # la regex DEVE stare fra virgolette: nginx legge le graffe
        # come delimitatori di blocco e senza quelle non parte proprio
        # (loop di riavvio, sito giu' — successo il 26/8)
        assert 'location ~* "\\.[A-Za-z0-9]{1,6}$"' in conf
        # e la regola deve venire PRIMA del catch-all
        assert (conf.index('location ~* "\\.[A-Za-z0-9]{1,6}$"')
                < conf.index("Tutto il resto NON ESISTE"))

    def test_il_deploy_prova_nginx_prima_di_riavviarlo(self):
        """26/8 — una regex con le graffe non quotate ha fatto morire
        nginx all'avvio: siccome il deploy RIAVVIA (il bind-mount non
        rilegge col reload), il container e' entrato in loop e il sito
        e' sparito. `nginx -t` costa un secondo e risponde alla sola
        domanda che conta: questa configurazione parte? Se non parte ci
        si ferma prima, coi container vecchi ancora in piedi."""
        sh = (BACKEND_DIR.parent / "deploy" / "deploy-prod.sh").read_text()
        assert "nginx -t" in sh, "il deploy puo' ancora spegnere il sito"
        assert sh.index("nginx -t") < sh.index("restart nginx-proxy"), \
            "la prova deve venire PRIMA del riavvio"
        # fra la prova e il riavvio ci dev'essere l'uscita: senza,
        # il deploy stampa l'errore e riavvia lo stesso.
        # NB: si lavora con gli INDICI e non con split() — «nginx -t»
        # compare tre volte (commento + due chiamate) e split tagliava
        # prima dell'exit, facendo fallire una guardia corretta.
        fra = sh[sh.index("nginx -t"):sh.index("restart nginx-proxy")]
        assert "exit 1" in fra, \
            "se la config e' rotta il deploy deve FERMARSI, non proseguire"

    def test_le_pubbliche_hanno_davvero_delle_meta(self):
        """Una rotta dichiarata pubblica ma senza un ramo nella shell
        riceve meta generiche: funziona, ma e' una pagina che non dice
        chi e'. Qui si elencano quelle ancora scoperte, cosi' il debito
        e' visibile invece che dimenticato."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        scoperte = [s for s in _registro()["pubblica"]
                    if f'"{s}"' not in shell and f"'{s}'" not in shell]
        assert not scoperte, (
            f"pubbliche senza meta proprie nella shell: {sorted(scoperte)}")

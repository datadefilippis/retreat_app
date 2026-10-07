#!/usr/bin/env python3
"""Sblocco dell'Accademia — Termini v2.13 (AC4, 7/10/2026).

Decisione del founder (6/10): i Termini passano a v2.13 SOLO allo sblocco
dell'Accademia, cosi' gli operatori ri-accettano una volta sola. Fino ad
allora i numeri vivono su /costi (nessun bump) e questo script resta
PRONTO ma non applicato.

Cosa fa (idempotente, a secco di default):
  1. Termini IT/EN/DE/FR, art. 6.4 e 7.2: la Commissione di piattaforma
     copre anche i Corsi online (stesse regole dei Prodotti: riga per
     riga, al netto degli sconti, restituita pro-quota nei rimborsi).
  2. core/legal_versions.py: CURRENT_VERSION_TAG v2.12 → v2.13, voce di
     changelog, CURRENT_VERSION_HASH ricalcolato sul bundle IT.
  3. locales/{it,en,de,fr}/legal.json: «Cosa e' cambiato» della v2.13.
  4. features/accademia/stato.js: ACCADEMIA_UI_PRONTA = true.
  Poi stampa i pin dei test da aggiornare (v2.12 → v2.13, hash).

Uso:
  python3 scripts/sblocco_accademia_v213.py            # prova a secco: mostra cosa cambierebbe
  python3 scripts/sblocco_accademia_v213.py --applica  # scrive davvero

Dopo --applica: suite, commit, giro di deploy backend+frontend (il bump
innesca il re-consent degli operatori al primo accesso).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FE = ROOT / "frontend" / "src"

# ── 1. i Termini: (file, [ (ancora esatta, sostituzione) ]) ──────────────────
TERMINI = {
    "it": [
        ("Sui soli **Prodotti** venduti dalla pagina pubblica dell'Operatore (prodotti digitali e fisici) il Fornitore trattiene",
         "Sui soli **Prodotti** venduti dalla pagina pubblica dell'Operatore (prodotti digitali e fisici) e sui **Corsi online** il Fornitore trattiene"),
        ("La Commissione di piattaforma si applica **esclusivamente ai Prodotti** (digitali e fisici) venduti dalla pagina pubblica dell'Operatore",
         "La Commissione di piattaforma si applica **esclusivamente ai Prodotti** (digitali e fisici) **e ai Corsi online** venduti dalla pagina pubblica dell'Operatore"),
    ],
    "en": [
        ("Only on **Products** sold from the Operator's public page (digital and physical products) does the Provider withhold",
         "Only on **Products** sold from the Operator's public page (digital and physical products) and on **Online courses** does the Provider withhold"),
        ("The Platform fee applies **exclusively to Products** (digital and physical) sold from the Operator's public page",
         "The Platform fee applies **exclusively to Products** (digital and physical) **and Online courses** sold from the Operator's public page"),
    ],
    "de": [
        ("Nur auf **Produkte**, die über die öffentliche Seite des Veranstalters verkauft werden (digitale und physische Produkte), behält",
         "Nur auf **Produkte**, die über die öffentliche Seite des Veranstalters verkauft werden (digitale und physische Produkte), und auf **Online-Kurse** behält"),
        ("Die Plattformgebühr gilt **ausschließlich für Produkte** (digitale und physische), die über die öffentliche Seite des Veranstalters verkauft",
         "Die Plattformgebühr gilt **ausschließlich für Produkte** (digitale und physische) **und Online-Kurse**, die über die öffentliche Seite des Veranstalters verkauft"),
    ],
    "fr": [
        ("Seuls les **Produits** vendus depuis la page publique de l'Opérateur (produits numériques et physiques) donnent lieu",
         "Seuls les **Produits** vendus depuis la page publique de l'Opérateur (produits numériques et physiques) et les **Cours en ligne** donnent lieu"),
        ("La Commission de plateforme s'applique **exclusivement aux Produits** (numériques et physiques) vendus depuis la page publique de l'Opérateur",
         "La Commission de plateforme s'applique **exclusivement aux Produits** (numériques et physiques) **et aux Cours en ligne** vendus depuis la page publique de l'Opérateur"),
    ],
}

# ── 3. «Cosa e' cambiato» ────────────────────────────────────────────────────
COSA_CAMBIA = {
    "it": "Versione 2.13: arriva l'Accademia, i corsi online venduti dalla tua pagina. I Termini dicono che la commissione di Aurya vale anche sui corsi, con le stesse regole dei prodotti: 15% nel Gratis e zero col Pro, riga per riga, restituita in proporzione nei rimborsi. Ritiri, eventi e servizi restano senza commissione. La Privacy non cambia.",
    "en": "Version 2.13: the Academy arrives, online courses sold from your page. The Terms now say Aurya's fee also applies to courses, with the same rules as products: 15% on Free and zero on Pro, row by row, refunded proportionally. Retreats, events and services remain fee-free. The Privacy Policy is unchanged.",
    "de": "Version 2.13: Die Akademie kommt, Online-Kurse, die über Ihre Seite verkauft werden. Die AGB sagen jetzt, dass die Gebühr von Aurya auch für Kurse gilt, mit denselben Regeln wie für Produkte: 15 % im Gratis-Plan und 0 % im Pro-Plan, zeilenweise, bei Rückerstattungen anteilig zurückgegeben. Retreats, Veranstaltungen und Dienstleistungen bleiben gebührenfrei. Die Datenschutzerklärung bleibt unverändert.",
    "fr": "Version 2.13 : l'Académie arrive, les cours en ligne vendus depuis votre page. Les Conditions précisent que la commission d'Aurya s'applique aussi aux cours, avec les mêmes règles que les produits : 15 % avec le plan Gratuit et zéro avec le Pro, ligne par ligne, restituée au prorata en cas de remboursement. Retraites, événements et services restent sans commission. La Politique de confidentialité ne change pas.",
}

CHANGELOG = '''  - v2.13 (AC4 Accademia, sblocco) — Termini 6.4 e 7.2: la Commissione
    di piattaforma copre anche i Corsi online venduti dalla pagina
    pubblica dell'Operatore, con le stesse regole dei Prodotti (misura su
    /costi per Piano, riga per riga, pro-quota nei rimborsi). Nessun
    cambio alla Privacy. Stesse modifiche EN/DE/FR. Bump deciso dal
    founder allo sblocco dell'Accademia (una sola ri-accettazione).
'''


def _hash_bundle(priv: str, terms: str) -> str:
    return hashlib.sha256((priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()).hexdigest()[:16]


def pianifica() -> tuple[list[tuple[Path, str]], list[str]]:
    """Calcola tutte le scritture senza toccare il disco. Restituisce
    (scritture, problemi): se problemi non e' vuoto, non si applica nulla."""
    scritture: list[tuple[Path, str]] = []
    problemi: list[str] = []

    # 1. Termini
    terms_it_nuovo = None
    for lingua, coppie in TERMINI.items():
        p = BACKEND / "legal" / f"terms_{lingua}.md"
        s = p.read_text(encoding="utf-8")
        for ancora, nuovo in coppie:
            if nuovo in s:
                continue                      # gia' applicata
            if s.count(ancora) != 1:
                problemi.append(f"{p.name}: ancora non trovata o doppia: {ancora[:60]}…")
                continue
            s = s.replace(ancora, nuovo)
        scritture.append((p, s))
        if lingua == "it":
            terms_it_nuovo = s

    # 2. versione + hash
    lv = BACKEND / "core" / "legal_versions.py"
    s = lv.read_text(encoding="utf-8")
    priv = (BACKEND / "legal" / "privacy_it.md").read_text(encoding="utf-8")
    nuovo_hash = _hash_bundle(priv, terms_it_nuovo or "")
    if 'CURRENT_VERSION_TAG: Final[str] = "v2.12"' in s:
        s = s.replace('CURRENT_VERSION_TAG: Final[str] = "v2.12"', 'CURRENT_VERSION_TAG: Final[str] = "v2.13"')
        s = s.replace("History:\n", "History:\n" + CHANGELOG, 1)
    elif 'CURRENT_VERSION_TAG: Final[str] = "v2.13"' not in s:
        problemi.append("legal_versions.py: tag corrente inatteso (ne' v2.12 ne' v2.13)")
    vecchio_hash = re.search(r'CURRENT_VERSION_HASH: Final\[str\] = "([0-9a-f]{16})"', s)
    if not vecchio_hash:
        problemi.append("legal_versions.py: CURRENT_VERSION_HASH non trovato")
    else:
        s = s.replace(vecchio_hash.group(0), f'CURRENT_VERSION_HASH: Final[str] = "{nuovo_hash}"')
    scritture.append((lv, s))

    # 3. legal.json
    for lingua, testo in COSA_CAMBIA.items():
        p = FE / "locales" / lingua / "legal.json"
        s = p.read_text(encoding="utf-8")
        m = re.search(r'("what_changed_body":\s*")(.*?)(")', s)
        if not m:
            problemi.append(f"{lingua}/legal.json: what_changed_body non trovato")
            continue
        s = s[:m.start(2)] + testo.replace('"', '\\"') + s[m.end(2):]
        scritture.append((p, s))

    # 4. lo sblocco della UI
    st = FE / "features" / "accademia" / "stato.js"
    s = st.read_text(encoding="utf-8")
    if "export const ACCADEMIA_UI_PRONTA = false;" in s:
        s = s.replace("export const ACCADEMIA_UI_PRONTA = false;", "export const ACCADEMIA_UI_PRONTA = true;")
    elif "export const ACCADEMIA_UI_PRONTA = true;" not in s:
        problemi.append("stato.js: ACCADEMIA_UI_PRONTA non trovato")
    scritture.append((st, s))
    return scritture, problemi


def pin_da_aggiornare() -> list[str]:
    """I test che inchiodano v2.12 o l'hash corrente: dopo --applica vanno
    portati a v2.13 e al nuovo hash (si trovano con grep)."""
    out = []
    for p in sorted((BACKEND / "tests").glob("test_*.py")):
        s = p.read_text(encoding="utf-8")
        if "v2.12" in s or "69137d1e3f451f81" in s:
            out.append(p.name)
    return out


def main() -> int:
    applica = "--applica" in sys.argv
    scritture, problemi = pianifica()
    if problemi:
        print("NON applicabile, ancore mancanti:")
        for x in problemi:
            print("  -", x)
        return 1
    cambiate = [(p, s) for p, s in scritture if p.read_text(encoding="utf-8") != s]
    if not cambiate:
        print("Niente da fare: v2.13 gia' applicata.")
        return 0
    print(("APPLICO" if applica else "PROVA A SECCO") + f" — {len(cambiate)} file cambierebbero:")
    for p, _ in cambiate:
        print("  -", p.relative_to(ROOT))
    if applica:
        for p, s in cambiate:
            p.write_text(s, encoding="utf-8")
        print("Scritto. Ora: aggiorna i pin, suite, commit, deploy backend+frontend.")
    pins = pin_da_aggiornare()
    if pins:
        print("Pin dei test da portare a v2.13 / nuovo hash:", ", ".join(pins))
    return 0


if __name__ == "__main__":
    sys.exit(main())

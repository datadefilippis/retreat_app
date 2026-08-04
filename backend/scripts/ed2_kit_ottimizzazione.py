# -*- coding: utf-8 -*-
"""ED2 — ottimizzazione chirurgica della guida riservata (il kit).

VERDETTO PRIMA DEL BISTURI. La guida e' buona: struttura
cosa-fai/cosa-senti/cosa-va-storto, fonti vere (Balban 2023, Goyal
2014, Bratman 2015, Emmons & McCullough), FAQ che salvano abbandoni.
NON si riscrive. Si correggono quattro difetti puntuali:

1. COLPO D'OCCHIO — 2.556 parole senza mappa. Una guida che si riapre
   piu' volte merita un indice esperienziale: pratica, durata, quando
   usarla, in sette righe subito dopo l'introduzione.
2. QUATTRO «COSA VA STORTO» MANCANTI — le pratiche 4 (cinque sensi),
   5 (camminata), 6 (scrittura) e 7 (mezz'ora senza telefono)
   saltavano l'ingrediente che distingue il kit. Aggiunti, con gli
   inciampi veri.
3. FONTI LINKATE (standard SE5) — Balban su doi.org (Cell Reports
   Medicine 2023, 10.1016/j.xcrm.2022.100895), Bratman su doi.org
   (PNAS 2015, 10.1073/pnas.1510459112), Emmons & McCullough su
   doi.org (J Pers Soc Psychol 2003, 10.1037/0022-3514.84.2.377).
4. REFUSI — apostrofi dritti nell'ultima riga (piu'/e').

Idempotente; da rieseguire in prod al lancio.

    venv/bin/python scripts/ed2_kit_ottimizzazione.py [--dry-run]
"""
import asyncio
import os
import sys

SLUG = "kit-pratiche-quotidiane-15-minuti"

CAMBI = [
    # ── 1. il colpo d'occhio, dopo l'introduzione ────────────────────
    ("Nessuna richiede attrezzatura, un maestro o un posto silenzioso.",
     "Nessuna richiede attrezzatura, un maestro o un posto silenzioso.\n\n"
     "## Il kit in un colpo d'occhio\n\n"
     "- **Il respiro che spegne l'allarme** · 2 minuti · mentre la cosa "
     "sta succedendo\n"
     "- **Cinque minuti seduti** · 5 minuti · il lavoro di fondo, "
     "ogni giorno\n"
     "- **Il giro del corpo** · 3 minuti · la sera, o quando sei "
     "«solo testa»\n"
     "- **Cinque cose che vedi** · 1 minuto · in mezzo agli altri, a "
     "occhi aperti\n"
     "- **Dieci minuti a piedi** · 10 minuti · se stare fermo non fa "
     "per te\n"
     "- **Tre minuti di scrittura** · 3 minuti · prima di dormire\n"
     "- **La mezz'ora che non guardi** · 0 minuti · appena sveglio\n\n"
     "Sette pratiche, ma il punto non è farle tutte: è trovarne una."),

    # ── 2a. cosa va storto: cinque sensi ─────────────────────────────
    ("**Perché funziona.** L'attenzione sensoriale interrompe la ruminazione",
     "**Cosa va storto.** Farla come una lista della spesa: contare "
     "cinque oggetti senza guardarne davvero nessuno. Il conteggio è "
     "solo l'impalcatura; il lavoro lo fa il secondo speso su ogni "
     "cosa. Se arrivi in fondo e non ricordi niente di ciò che hai "
     "«visto», rifalla dandoti il doppio del tempo.\n\n"
     "**Perché funziona.** L'attenzione sensoriale interrompe la ruminazione"),

    # ── 2b. cosa va storto: scrittura ────────────────────────────────
    ("**Una variante che ha dei numeri alle spalle.**",
     "**Cosa va storto.** Due modi. Il primo: rileggere e giudicare "
     "quello che è uscito, che trasforma lo svuotamento in un esame. "
     "Il secondo: lasciare che le due domande diventino una lista di "
     "cose da fare per domani, che è il contrario dello scopo. Se ti "
     "accorgi che stai pianificando, chiudi la frase e torna a «cosa "
     "lascio qui».\n\n"
     "**Una variante che ha dei numeri alle spalle.**"),

    # ── 2c. cosa va storto: mezz'ora senza telefono ──────────────────
    ("**Perché è nel kit.** Cominciare la giornata dentro il proprio filo,",
     "**Cosa va storto.** La sostituzione: niente telefono ma la tv "
     "accesa, o il tablet «solo per le notizie». Lo schermo cambiato "
     "non è lo schermo tolto. E l'eccezione che si allarga: «controllo "
     "solo se mi ha scritto» il lunedì diventa la rassegna stampa "
     "completa il giovedì. La mezz'ora funziona quando è intera, e se "
     "un giorno salta, riparte domani senza processi.\n\n"
     "**Perché è nel kit.** Cominciare la giornata dentro il proprio filo,"),

    # ── 2d. cosa va storto: camminata (l'audit ha trovato che mancava
    #        anche qui, non solo su 4/6/7) ──────────────────────────────
    ("**Cosa dice la ricerca.** L'attività fisica leggera e regolare",
     "**Cosa va storto.** Trasformarla in una commissione: la camminata "
     "con destinazione e lista mentale è un'altra cosa, utile ma "
     "diversa. E il telefono «solo per le mappe»: dopo le mappe arriva "
     "tutto il resto. Se il percorso ti serve, guardalo prima di "
     "uscire; per dieci minuti si può anche sbagliare strada.\n\n"
     "**Cosa dice la ricerca.** L'attività fisica leggera e regolare"),

    # ── 3. fonti linkate ─────────────────────────────────────────────
    ("questo pattern, chiamato *cyclic sighing*, è risultato il più "
     "efficace nel migliorare l'umore e abbassare la frequenza "
     "respiratoria a riposo, con cinque minuti al giorno (Balban e "
     "colleghi, *Cell Reports Medicine*, 2023).",
     "questo pattern, chiamato *cyclic sighing*, è risultato il più "
     "efficace nel migliorare l'umore e abbassare la frequenza "
     "respiratoria a riposo, con cinque minuti al giorno ([Balban e "
     "colleghi, *Cell Reports Medicine*, 2023]"
     "(https://doi.org/10.1016/j.xcrm.2022.100895))."),

    ("e farla in un ambiente naturale amplifica l'effetto sulla "
     "ruminazione (Bratman e colleghi, *PNAS*, 2015).",
     "e farla in un ambiente naturale amplifica l'effetto sulla "
     "ruminazione ([Bratman e colleghi, *PNAS*, 2015]"
     "(https://doi.org/10.1073/pnas.1510459112))."),

    ("Gli studi di Emmons e McCullough sulla gratitudine mostrano "
     "effetti misurabili su benessere percepito e qualità del sonno "
     "quando la pratica è regolare.",
     "Gli [studi di Emmons e McCullough sulla gratitudine]"
     "(https://doi.org/10.1037/0022-3514.84.2.377) mostrano effetti "
     "misurabili su benessere percepito e qualità del sonno quando la "
     "pratica è regolare."),

    # ── 4. refusi di apostrofo nell'ultima riga ──────────────────────
    ("E se dopo queste settimane una pratica ti chiama piu' delle "
     "altre, [la mappa delle discipline](/blog/discipline-olistiche-la-mappa) "
     "e' il posto dove capire dove porta.",
     "E se dopo queste settimane una pratica ti chiama più delle "
     "altre, [la mappa delle discipline](/blog/discipline-olistiche-la-mappa) "
     "è il posto dove capire dove porta."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    d = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "content": 1})
    assert d, "kit assente"
    c = d["content"]

    fatti = gia = persi = 0
    for vecchio, nuovo in CAMBI:
        if nuovo in c:
            gia += 1
            continue
        if vecchio not in c:
            print(f"  NON TROVATO: {vecchio[:60]!r}")
            persi += 1
            continue
        c = c.replace(vecchio, nuovo, 1)
        fatti += 1

    print(f"cambi: fatti={fatti} gia'={gia} persi={persi}")
    assert persi == 0, "ancore non trovate: contenuto divergente"

    # audit: ogni pratica ha ora il suo 'Cosa va storto'
    n_storto = c.count("**Cosa va storto.**")
    print(f"'Cosa va storto' presenti: {n_storto} (attesi 7)")
    assert n_storto == 7
    # fonti: 4 link esterni su domini fidati
    import re
    esterni = re.findall(r"\]\((https://[^)\s]+)\)", c)
    print(f"link esterni: {len(esterni)}")
    assert all("doi.org" in u or "pubmed" in u for u in esterni)
    assert len(esterni) == 4
    print(f"parole: {len(c.split())}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return
    from datetime import datetime, timezone
    await db.articles.update_one(
        {"slug": SLUG},
        {"$set": {"content": c,
                  "updated_at": datetime.now(timezone.utc)}})
    print("scritto (updated_at aggiornato: freschezza onesta)")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))

"""Discipline olistiche (ciclo DI, founder 14/8/2026) — fonte unica.

L'operatore DICHIARA le discipline che pratica sul profilo pubblico
(multi-selezione, max 10): non sostituiscono le categorie derivate dai
prodotti (SW5), le affiancano — "cosa so fare" vs "cosa vendo ora".
Alimentano il filtro Disciplina di /esplora-operatori e i badge su
profilo e card.

ORDINE E FAMIGLIE. La lista e' COMPLETA ma non casinara (richiesta
esplicita del founder): ~40 voci in 6 famiglie tematiche, cosi' il
selettore si legge a colpo d'occhio. Le chiavi sono slug stabili
(vivranno negli URL dei filtri); le label sono italiane e definitive
(dal 2/8 i contenuti nuovi non si traducono). Lo specchio frontend e'
frontend/src/lib/disciplines.js: una guardia impone la parita'.
"""

# (slug famiglia, label famiglia, [(slug, label), ...])
DISCIPLINE_FAMILIES = (
    ("corpo", "Corpo & Movimento", [
        ("yoga", "Yoga"),
        ("pilates", "Pilates"),
        ("tai-chi", "Tai Chi"),
        ("qi-gong", "Qi Gong"),
        ("danzaterapia", "Danzaterapia"),
        ("bioenergetica", "Bioenergetica"),
        ("feldenkrais", "Feldenkrais"),
        ("biodanza", "Biodanza"),
        ("danze-sacre", "Danze sacre & Danza della Dea"),
        # 29/9/2026 (founder): l'allineamento della colonna come lavoro sul corpo
        ("allineamento", "Allineamento (colonna & postura)"),
    ]),
    ("mente", "Meditazione & Mente", [
        ("meditazione", "Meditazione"),
        ("mindfulness", "Mindfulness"),
        ("breathwork", "Breathwork"),
        ("training-autogeno", "Training autogeno"),
        ("ipnosi", "Ipnosi & Rilassamento guidato"),
        # 2/10/2026 (founder): la regressione alle vite passate, generica (il
        # metodo di marchio resta un sinonimo: regola DI6)
        ("regressione-vite-passate", "Regressione & Vite passate"),
        # 29/9/2026 (founder): visualizzazione guidata del futuro desiderato
        ("mind-movie", "Mind movie"),
    ]),
    ("massaggio", "Massaggio & Bodywork", [
        # 29/9/2026 (founder): il massaggio senza aggettivi, accanto all'olistico
        ("massaggio", "Massaggio"),
        ("massaggio-olistico", "Massaggio olistico"),
        ("shiatsu", "Shiatsu"),
        ("massaggio-ayurvedico", "Massaggio ayurvedico"),
        ("massaggio-thai", "Massaggio thai"),
        ("riflessologia", "Riflessologia"),
        ("craniosacrale", "Craniosacrale"),
        ("linfodrenaggio", "Linfodrenaggio"),
        ("hot-stone", "Hot stone"),
    ]),
    ("energia", "Energia & Vibrazione", [
        ("reiki", "Reiki"),
        ("pranoterapia", "Pranoterapia"),
        ("cristalloterapia", "Cristalloterapia"),
        # 29/9/2026 (founder): pulizia e purificazione energetica (aura, ambienti)
        ("pulizia-energetica", "Pulizia energetica"),
        # 24/9/2026 (founder): due voci sui chakra, generiche e non di
        # marchio, come da regola DI6. «Linfodrenaggio» c'era gia'.
        ("allineamento-chakra", "Allineamento chakra"),
        ("lavoro-energetico-chakra", "Lavoro energetico coi chakra"),
        ("sound-healing", "Sound healing & Campane tibetane"),
        ("theta-healing", "Theta healing"),
        ("access-bars", "Access Bars"),
        ("kinesiologia", "Kinesiologia"),
    ]),
    ("natura", "Natura & Rimedi", [
        ("naturopatia", "Naturopatia"),
        ("aromaterapia", "Aromaterapia"),
        ("floriterapia", "Floriterapia & Fiori di Bach"),
        ("erboristeria", "Erboristeria"),
        ("alimentazione-olistica", "Alimentazione olistica"),
        ("bagni-di-bosco", "Bagni di bosco"),
        ("consulenza-ayurvedica", "Consulenza ayurvedica"),
    ]),
    # 24/9/2026 (founder): si iscrive uno psicoterapeuta. Le professioni
    # psicologiche sono regolamentate (albo): famiglia propria, voci
    # generiche, nessun metodo di marchio (regola DI6).
    ("psiche", "Psicologia & Psicoterapia", [
        ("psicologia", "Psicologia"),
        ("psicoterapia", "Psicoterapia"),
        ("sostegno-psicologico", "Sostegno psicologico"),
        ("psicologia-perinatale", "Psicologia perinatale"),
    ]),
    ("anima", "Anima & Percorsi interiori", [
        ("costellazioni-familiari", "Costellazioni familiari"),
        ("counseling-olistico", "Counseling olistico"),
        # 24/9/2026 (founder): il counselor a indirizzo Gestalt (approccio,
        # non marchio: regola DI6 rispettata)
        # 1/10/2026 (founder): l'etichetta diventa «Gestalt counseling», lo slug resta
        ("counseling-gestalt", "Gestalt counseling"),
        ("coaching-olistico", "Coaching olistico"),
        ("cerchi-di-donne", "Cerchi di donne"),
        ("sacro-femminile", "Sacro femminile & Ciclicità"),
        ("sciamanesimo", "Pratiche sciamaniche"),
        # 25/9/2026 (founder): la ricerca spirituale come pratica accompagnata
        ("percorsi-spirituali", "Percorsi spirituali"),
        # 1/10/2026 (founder): due voci di crescita, personale e spirituale
        ("crescita-personale", "Crescita personale"),
        ("crescita-spirituale", "Crescita spirituale"),
        ("astrologia", "Astrologia"),
        ("numerologia", "Numerologia"),
        ("tarocchi-evolutivi", "Tarocchi evolutivi"),
    ]),
)

# slug → label, piatto: validazione PATCH e risoluzione label nei payload.
# DV1 (2/10/2026): le liste delle famiglie e questo dizionario sono MUTABILI
# di proposito — services/discipline_vive.py vi aggiunge in place le voci
# create dalla regia (registro `discipline_extra`), cosi' ogni consumatore
# vede l'unione senza cambiare una riga. Le voci di codice non si toccano.
DISCIPLINES = {
    slug: label
    for _fslug, _flabel, items in DISCIPLINE_FAMILIES
    for slug, label in items
}
# gli slug nati nel codice: mai sovrascritti ne' rimossi dal registro vivo
DISCIPLINE_CODICE = frozenset(DISCIPLINES)

# tetto della multi-selezione: dieci discipline dicono gia' tutto,
# oltre il profilo diventa un elenco telefonico
DISCIPLINES_MAX = 10


def clean_disciplines(raw) -> list:
    """Lista di slug validi, dedup nell'ordine di arrivo, max 10."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, str) and item in DISCIPLINES and item not in out:
            out.append(item)
        if len(out) >= DISCIPLINES_MAX:
            break
    return out

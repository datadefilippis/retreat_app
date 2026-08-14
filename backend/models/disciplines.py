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
    ("corpo", "Corpo & Movimento", (
        ("yoga", "Yoga"),
        ("pilates", "Pilates"),
        ("tai-chi", "Tai Chi"),
        ("qi-gong", "Qi Gong"),
        ("danzaterapia", "Danzaterapia"),
        ("bioenergetica", "Bioenergetica"),
        ("feldenkrais", "Feldenkrais"),
    )),
    ("mente", "Meditazione & Mente", (
        ("meditazione", "Meditazione"),
        ("mindfulness", "Mindfulness"),
        ("breathwork", "Breathwork"),
        ("training-autogeno", "Training autogeno"),
        ("ipnosi", "Ipnosi & Rilassamento guidato"),
    )),
    ("massaggio", "Massaggio & Bodywork", (
        ("massaggio-olistico", "Massaggio olistico"),
        ("shiatsu", "Shiatsu"),
        ("massaggio-ayurvedico", "Massaggio ayurvedico"),
        ("massaggio-thai", "Massaggio thai"),
        ("riflessologia", "Riflessologia"),
        ("craniosacrale", "Craniosacrale"),
        ("linfodrenaggio", "Linfodrenaggio"),
        ("hot-stone", "Hot stone"),
    )),
    ("energia", "Energia & Vibrazione", (
        ("reiki", "Reiki"),
        ("pranoterapia", "Pranoterapia"),
        ("cristalloterapia", "Cristalloterapia"),
        ("sound-healing", "Sound healing & Campane tibetane"),
        ("theta-healing", "Theta healing"),
        ("access-bars", "Access Bars"),
    )),
    ("natura", "Natura & Rimedi", (
        ("naturopatia", "Naturopatia"),
        ("aromaterapia", "Aromaterapia"),
        ("floriterapia", "Floriterapia & Fiori di Bach"),
        ("erboristeria", "Erboristeria"),
        ("alimentazione-olistica", "Alimentazione olistica"),
        ("bagni-di-bosco", "Bagni di bosco"),
    )),
    ("anima", "Anima & Percorsi interiori", (
        ("costellazioni-familiari", "Costellazioni familiari"),
        ("counseling-olistico", "Counseling olistico"),
        ("coaching-olistico", "Coaching olistico"),
        ("cerchi-di-donne", "Cerchi di donne"),
        ("sciamanesimo", "Pratiche sciamaniche"),
        ("astrologia", "Astrologia"),
        ("numerologia", "Numerologia"),
        ("tarocchi-evolutivi", "Tarocchi evolutivi"),
    )),
)

# slug → label, piatto: validazione PATCH e risoluzione label nei payload
DISCIPLINES = {
    slug: label
    for _fslug, _flabel, items in DISCIPLINE_FAMILIES
    for slug, label in items
}

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

"""PL2 — il pezzo piu' linkato del sito diventa il pilastro che era gia'.

LO STATO DI FATTO. "Come capire se un operatore e' serio" raccoglie
tredici link in entrata, piu' di ogni altro articolo, e ne aveva
milletrecento di parole. E' il territorio del brand — la tesi di Aurya
e' che la fiducia si costruisce chiedendo — e finora era un buon
articolo dentro un ruolo da pilastro.

COSA SI AGGIUNGE, e sono le cose che mancavano davvero.

1. LE SIGLE, DECIFRATE. E' quello che le persone cercano quando
   arrivano qui, e in italiano non lo spiega quasi nessuno. Le tre
   famiglie sono diverse fra loro e vengono confuse: associazioni
   professionali della legge 4/2013, enti di promozione sportiva
   riconosciuti dal CONI, scuole private. Un diploma di insegnante
   yoga rilasciato da un ente sportivo e' una qualifica sportiva
   valida nel suo campo, e non e' un titolo sanitario. Saperlo cambia
   il peso di un logo.

   Le sigle non le nomino una per una: cambiano, e un elenco vecchio
   e' peggio di nessun elenco. Racconto le famiglie e dove si
   verifica.

2. LA VERIFICA IN DIECI MINUTI. Un procedimento, non un principio:
   cosa cercare, dove, in che ordine.

3. LA FATTURA. E' il segnale di regolarita' piu' concreto che esista
   e nessuno lo scrive, perche' parlare di soldi sembra volgare in
   questo mondo. Chi lavora in regola emette un documento fiscale.

4. IL CONSENSO AL TOCCO. In pratiche a mediazione corporea e' la
   cosa che protegge di piu', e si scrive di rado.

5. CHI E' PIU' ESPOSTO. Le persone in un momento fragile sono quelle
   su cui l'approfittarsi funziona meglio. Dirlo e' un servizio.

    venv/bin/python scripts/pl2_pilastro_scegliere.py [--dry-run]
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

SLUG = "come-capire-se-un-operatore-olistico-e-serio"
TITOLO = "Come capire se un operatore olistico è serio: la guida completa"
DESCRIZIONE = (
    "Cosa dice la legge, cosa valgono sigle e attestati, come verificare in "
    "dieci minuti, le domande da fare e il confine che nessuno può superare."
)

REIKI = "/blog/reiki-cose-come-funziona-una-sessione"
COST = "/blog/costellazioni-familiari-cosa-sono-come-funzionano"
BREATH = "/blog/breathwork-cose-tecniche-benefici"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"
AYU = "/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"

CONTENUTO = f"""\
Cerchi [«reiki»]({REIKI}) o [«costellazioni familiari»]({COST}) nella tua città e trovi trenta profili. Hanno tutti foto curate, tutti parlano di ascolto e di percorso, molti espongono una sigla che non hai mai sentito. Nessuno sta mentendo, e proprio per questo non sai come scegliere: mancano gli appigli, non la buona fede.

Questa guida mette in fila gli appigli che esistono. Alla fine non ci sarà un nome consigliato: ci saranno le domande da fare e il modo di leggere le risposte.

## Perché è difficile: in Italia non c'è un albo

Le professioni olistiche in Italia rientrano fra le **professioni non organizzate in ordini o collegi**, disciplinate dalla **legge 4 del 14 gennaio 2013**. È la stessa cornice di molte altre attività: significa che non esiste un albo da consultare, né un esame di Stato, né un ente pubblico che verifichi la competenza di chi la esercita.

La legge però qualcosa la stabilisce, ed è utile conoscerlo.

**Chi esercita deve dichiararlo.** In ogni documento e in ogni comunicazione verso il pubblico, un professionista che rientra in questa legge deve indicare gli estremi della norma. Se trovi scritto «professionista di cui alla legge n. 4 del 14 gennaio 2013», stai leggendo una persona che sa in quale cornice lavora: è un segnale piccolo ma reale.

**Le associazioni possono essere in un elenco pubblico.** Le associazioni professionali che rispettano certi requisiti vengono iscritte in un elenco tenuto dal ministero competente e consultabile online. Un'associazione presente in quell'elenco è verificabile; una sigla che non compare da nessuna parte è solo una sigla.

**L'attestato riguarda i servizi, non la persona.** Le associazioni iscritte possono rilasciare un'attestazione di qualità e qualificazione professionale dei servizi. È una cosa diversa da un'abilitazione: non certifica che quella persona sia brava, certifica che rispetta gli standard dichiarati da quell'associazione. Sapere questa differenza cambia il peso che dai a un logo su un sito.

**Alcune regioni hanno regole proprie.** Un paio di regioni italiane hanno legiferato sulle cosiddette discipline bio-naturali, con elenchi regionali e requisiti formativi. Valgono nel territorio di quella regione e non sono un albo nazionale, ma dove esistono sono un riferimento in più da controllare.

## Le sigle, decifrate

È la domanda con cui la maggior parte delle persone arriva qui, e la risposta utile non è un elenco di nomi — cambiano, e un elenco vecchio confonde più di nessun elenco. La risposta utile è che gli attestati in circolazione appartengono a **tre famiglie diverse**, che si somigliano nel logo e non nel significato.

**Le associazioni professionali della legge 4/2013.** Sono associazioni private che riuniscono chi esercita una certa professione, definiscono standard formativi e deontologici e rilasciano l'attestazione di cui sopra. Le più solide sono iscritte nell'elenco ministeriale, hanno uno statuto pubblico, un codice deontologico e una procedura per le segnalazioni. Cosa attestano: che quella persona rispetta gli standard di quella associazione. Cosa non attestano: un'abilitazione riconosciuta dallo Stato, che per queste professioni non esiste.

**Gli enti di promozione sportiva.** Sono enti riconosciuti dal CONI, e rilasciano diplomi tecnici sportivi. È la via da cui passa la maggior parte degli insegnanti di [yoga]({YOGA}) in Italia, per una ragione pratica: consente di insegnare in palestre e associazioni sportive con una cornice fiscale e assicurativa definita. Il punto da capire è questo: **un diploma di questa famiglia è una qualifica sportiva, valida nel suo campo, e non è un titolo sanitario**. Non è un difetto — è semplicemente un'altra cosa da quella che il logo lascia intuire a chi non conosce il sistema.

**Le scuole private.** Chiunque può aprire una scuola e rilasciare un attestato di frequenza. Ce ne sono di eccellenti, con anni di percorso, tirocinio e supervisione, e ce ne sono che vendono un fine settimana. L'attestato in sé non distingue le une dalle altre: lo distingue la durata dichiarata, chi insegna, e se la scuola esiste da abbastanza tempo da avere ex allievi rintracciabili.

Due parole meritano una riga a parte, perché generano più equivoci di tutte.

**Naturopata** non è un titolo riconosciuto dallo Stato italiano: non esiste un albo, non esiste un percorso universitario abilitante, e chi si definisce così sta indicando una formazione privata, che può essere lunga e seria o breve e no.

**Counselor** indica una relazione di aiuto che **non è psicoterapia**. Un counselor non tratta disturbi psicologici e non può farlo: quello è terreno di psicologi e psicoterapeuti iscritti al proprio albo. Chi confonde le due cose, o lascia che tu le confonda, ti sta dando un'informazione.

## Il confine che nessuno può superare

C'è una linea che vale per tutti, e conoscerla protegge chi cerca più di qualsiasi attestato.

**Nessun operatore olistico può fare diagnosi, prescrivere terapie o dirti di sospendere una cura.** Sono atti riservati alle professioni sanitarie; esercitarli senza titolo è un reato (articolo 348 del codice penale). Allo stesso modo, «counseling» e «terapia» sono cose diverse: la psicoterapia è riservata a chi è iscritto all'albo degli psicologi o dei medici con specializzazione.

Se qualcuno ti dice che puoi ridurre un farmaco, che una pratica cura una malattia, o che il tuo disturbo ha una causa energetica precisa, **quella persona ha superato il confine**. Non è una questione di scuole di pensiero: è la sola cosa in questa guida che non ammette sfumature.

Vale anche per le mappe simboliche: spiegare un sintomo con un [chakra]({CHAKRA}) o con uno squilibrio dei dosha dell'[ayurveda]({AYU}) è un uso improprio di strumenti che nelle loro tradizioni servono ad altro.

## I segnali che contano

**Dichiara dove si è formata, con chi e per quanto.** «Formata in reiki» dice poco. «Tre anni di formazione presso X, con Y come insegnante di riferimento» dice tutto: puoi verificare, e chi scrive così sa che lo puoi fare.

**Ha una supervisione o un aggiornamento in corso.** Chi lavora con le persone e continua a formarsi e a confrontarsi con qualcuno più esperto è in un altro campionato rispetto a chi ha finito un corso nel 2016 e da allora ripete.

**Parla dei limiti prima che glieli chieda tu.** «Questo non è indicato se…», «in questo caso ti mando da…». È il segnale più affidabile di tutti, perché va contro l'interesse immediato di chi lo dice.

**Ti chiede la tua storia prima di cominciare.** Salute, farmaci, percorsi in corso, gravidanza. Se questa conversazione manca, manca la cosa più importante.

**È chiara su prezzi, durata e disdetta.** Prima, per iscritto, senza che tu debba chiedere.

**Emette un documento fiscale.** È il segnale più concreto e il meno citato, perché in questo mondo parlare di soldi sembra fuori luogo. Chi lavora in regola ha una partita IVA e rilascia fattura o ricevuta. Se ti viene chiesto di pagare in contanti senza alcun documento, quella persona sta lavorando fuori dalle regole in un modo che riguarda anche te: senza documento non hai prova di nulla, e nessuna assicurazione copre quello che non risulta.

**Racconta il metodo, non i risultati degli altri.** «Lavoriamo così, ci vuole questo tempo» è un'informazione. Le testimonianze di trasformazioni straordinarie sono una vetrina.

## I segnali che sembrano dire qualcosa e non dicono niente

**Il numero di follower.** Misura la capacità di comunicare, che è un mestiere diverso.

**Un sito bello.** Costa poche centinaia di euro e non ha alcun rapporto con la qualità della pratica.

**«Certificato» senza dire da chi.** La parola da sola è vuota. Certificato da quale ente, in che anno, con quale percorso.

**I master di un fine settimana.** Alcune tecniche si trasmettono in tempi brevi, ed è legittimo — vale per esempio per certe pratiche di [respirazione]({BREATH}). Ma un fine settimana non forma la capacità di stare con una persona che si commuove sul lettino: quella la dà la pratica accompagnata, negli anni.

**Le liste di benefici.** Più sono lunghe, meno sono utili: una pratica che promette di risolvere ansia, insonnia, digestione, autostima e relazioni sta descrivendo un desiderio, non un metodo.

## Come si verifica in dieci minuti

Un procedimento, in ordine. Serve una connessione e nient'altro.

**1. Cerca il nome e cognome, non il nome dello studio.** Se la persona esiste professionalmente, esiste anche fuori dal proprio sito: un profilo su un'associazione, una scuola che la cita fra i diplomati, un'intervista, un articolo.

**2. Cerca la scuola dove dice di essersi formata.** Esiste? Da quanto? Ha un programma pubblico con le ore dichiarate? Una scuola che non ha un sito con il piano di studi è già una risposta.

**3. Controlla la sigla nell'elenco ministeriale.** Se l'associazione è iscritta, la trovi. Se non c'è, non significa automaticamente che sia poco seria — significa che quel logo non ti sta dando la garanzia che pensavi.

**4. Guarda da quanto esiste la sua presenza pubblica.** Un profilo social aperto tre mesi fa, con foto di repertorio e nessuna interazione locale, è diverso da uno con quattro anni di post e persone che commentano con il proprio nome.

**5. Cerca l'indirizzo dello studio.** Esiste come luogo? È un'associazione, uno studio condiviso, una casa privata? Nessuna di queste è squalificante, ma è utile saperlo prima di suonare a un campanello.

**6. Chiedi la partita IVA o l'intestazione della ricevuta.** Una domanda normale, che si fa a qualsiasi professionista. La reazione dice quasi tutto.

## Le domande da fare al primo contatto

Sono cinque, si fanno in un messaggio, e la qualità delle risposte vale più di qualsiasi recensione.

1. **Dove ti sei formato e per quanto tempo?**
2. **Cosa succede in una sessione, passo per passo?**
3. **In quali casi mi diresti che questa pratica non fa per me?**
4. **Quanto costa, quanto dura, e come funziona se devo disdire?**
5. **Con che altre figure lavori, se serve?**

La terza è quella che separa. Chi risponde con precisione ha pensato ai propri limiti; chi risponde «è adatta a tutti» ti ha appena detto qualcosa di importante.

Sulla quinta: un professionista inserito in una rete di colleghi — medici, psicologi, fisioterapisti — è quasi sempre più affidabile di uno che lavora isolato, perché sa quando non tocca a lui.

Se quello che stai valutando è un ritiro e non una sessione, le domande diventano di più e riguardano anche soldi, gruppo e giornata: le abbiamo raccolte in [cosa chiedere prima di prenotare]({DOMANDE}).

## Il primo incontro: cosa dovrebbe succedere

Le prime volte non si giudica una pratica, si giudica un contesto. Quattro cose che in una sala che lavora bene ci sono.

**Un colloquio prima di toccarti.** Non un modulo firmato in fretta: qualche minuto in cui racconti perché sei lì e in cui ti viene chiesto della tua salute.

**Il consenso al contatto fisico.** Nelle pratiche a mediazione corporea è la cosa che protegge di più, ed è quella di cui si parla meno. Ti viene detto dove verrai toccato e ti viene chiesto se va bene, **prima**. Ti viene detto che puoi dire di no in qualsiasi momento, anche a metà. Se il contatto arriva senza che sia stato nominato, hai tutto il diritto di fermare la sessione.

**Un ambiente in cui puoi uscire.** La porta non è chiusa a chiave, sai dove sei, il telefono ce l'hai.

**Nessuna pressione all'uscita.** Un professionista serio ti saluta. Chi ti propone un pacchetto di dieci sedute mentre ti stai rimettendo le scarpe sta lavorando su di te nel momento in cui sei più aperto.

## Chi è più esposto

Vale la pena dirlo, perché è il punto in cui le cose vanno storte.

Le persone che si affidano peggio non sono le più ingenue: sono quelle che stanno attraversando un momento in cui **hanno bisogno che qualcosa funzioni**. Un lutto, una separazione, una diagnosi, un periodo in cui la vita si è fermata.

In quei momenti tre cose si abbassano insieme: la capacità di fare domande scomode, la voglia di sentirsi dire di no, e la soglia oltre cui una spesa sembra troppa. Chi approfitta di questo mondo lo sa, e non lavora sui creduloni: lavora su chi sta male.

Se ti riconosci in un momento così, il criterio più utile è delegare una parte del giudizio: fai leggere la conversazione a qualcuno di cui ti fidi prima di pagare. È un accorgimento banale ed è quello che funziona meglio.

## Le bandiere rosse, in ordine di gravità

**Vai via subito.** Ti dice di ridurre o sospendere un farmaco. Sostiene di curare una patologia. Ti scoraggia dal parlarne con il tuo medico. Ti tocca senza averlo nominato prima. Fa pressione perché tu paghi un percorso lungo oggi.

**Chiedi chiarimenti prima di proseguire.** Non sa dirti dove si è formato. Non ha condizioni scritte. Non emette ricevuta. Non ti ha chiesto nulla della tua salute. Ti risponde in modo vago sulle controindicazioni.

**Notalo e tienilo presente.** Parla molto dei suoi risultati e poco del metodo. Usa un linguaggio che ti fa sentire in difetto se non capisci. Ha una sola recensione, entusiasta e generica.

## Quando la risposta non è un operatore olistico

Ci sono situazioni in cui la prima porta è un'altra, e dirlo fa parte del servizio.

Se stai attraversando un disturbo del sonno persistente, un dolore che non passa, un calo di peso che non hai cercato, pensieri di farti del male, un lutto che ti impedisce di funzionare, o se stai gestendo una malattia diagnosticata: **la prima conversazione è con il tuo medico, o con uno psicologo**.

Questo non esclude una pratica olistica: molte persone le portano avanti insieme, e i professionisti seri lo incoraggiano. Ma l'ordine conta, e nessuna pratica di benessere sostituisce una cura.

## Una cosa da tenere per ultima

Tutti i segnali di questa guida servono a ridurre il rischio, non ad azzerarlo. Alla fine resta una parte che nessun criterio copre: come ti senti quando parli con quella persona.

Se dopo il primo contatto ti senti messo fretta, valutato, o vagamente in colpa per le domande che hai fatto, quello è un dato. Vale quanto un attestato, e arriva prima.

## Domande frequenti

**Esiste un albo degli operatori olistici in Italia?**
No. Rientrano nella legge 4/2013 sulle professioni non organizzate: esistono associazioni professionali, alcune iscritte in un elenco ministeriale, ma nessun albo.

**Cosa vale un attestato rilasciato da un'associazione?**
Attesta che quella persona rispetta gli standard di quell'associazione per i servizi che offre. Non è un'abilitazione e non certifica la competenza individuale. Il valore dipende da quanto è verificabile l'associazione.

**Che differenza c'è fra un attestato di un'associazione e un diploma di un ente sportivo?**
Il primo riguarda una professione non organizzata e attesta standard di servizio; il secondo è una qualifica tecnica sportiva, che consente di insegnare in contesti sportivi. Nessuno dei due è un titolo sanitario.

**«Naturopata» è un titolo riconosciuto?**
No, non dallo Stato italiano. Indica una formazione privata, che può essere lunga e strutturata o breve. Alcune regioni hanno elenchi propri per le discipline bio-naturali, validi nel loro territorio.

**Un counselor può curare l'ansia?**
No. Il counseling è una relazione di aiuto e non è psicoterapia: il trattamento dei disturbi psicologici spetta a psicologi e psicoterapeuti iscritti all'albo.

**Un operatore olistico può dirmi di sospendere un farmaco?**
Mai. È un atto medico, e chi lo fa senza titolo commette un reato. È il motivo più solido per interrompere un percorso.

**Devo per forza ricevere una ricevuta?**
Chi lavora in regola emette un documento fiscale, e chiederlo è normale. Un pagamento in contanti senza alcun documento ti lascia senza prova e fuori da qualsiasi copertura assicurativa.

**Quanto dovrebbe costare una sessione?**
Dipende da pratica, città e durata: la forbice reale è ampia. Il criterio utile è un altro, ed è che il prezzo sia dichiarato prima, insieme a durata e regole di disdetta.

**Le recensioni online sono affidabili?**
Sono un indizio, non una prova, e vanno lette per come sono scritte: quelle che raccontano cosa è successo valgono più di quelle che dicono «esperienza fantastica». Una recensione legata a una prenotazione verificata vale più di una anonima.

**Posso chiedere di parlare prima di prenotare?**
Sì, ed è consigliabile. La disponibilità a una conversazione preliminare gratuita di dieci minuti è già una risposta. Se stai valutando un ritiro, abbiamo raccolto [le domande da fare prima di prenotare]({DOMANDE}).

**Cosa faccio se qualcosa è andato storto?**
Se c'è stato un danno o un comportamento scorretto, il primo passo è scriverlo alla persona e all'associazione a cui aderisce, se ce n'è una: le associazioni serie hanno una procedura per le segnalazioni. Nei casi che riguardano la salute o la sfera personale, la strada è quella ordinaria di una denuncia.
"""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    doc = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "content": 1})
    if not doc:
        print(f"ASSENTE: {SLUG}")
        return
    print(f"{TITOLO}\n  prima: {len(doc['content'].split())} parole"
          f"\n  dopo:  {len(CONTENUTO.split())} parole"
          f"\n  descrizione: {len(DESCRIZIONE)} caratteri")
    if CONTENUTO == doc["content"]:
        print("\ngia' aggiornato")
        return
    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return
    await db.articles.update_one({"slug": SLUG}, {"$set": {
        "title": TITOLO, "description": DESCRIZIONE, "content": CONTENUTO,
        "author_name": "Aurya",
        "related_slugs": [DOMANDE.split("/blog/")[1],
                          "reiki-cose-come-funziona-una-sessione",
                          "chakra-cosa-sono-i-sette-come-si-usano"],
        "updated_at": datetime.now(timezone.utc),
    }})
    print("\naggiornato (slug e data di pubblicazione invariati)")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))

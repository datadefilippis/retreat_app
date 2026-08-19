import React from 'react';
import { PERCORSO, BANDE, APPROFONDIMENTI, GLOSSARIO } from './content/guida';
import { PRO_ENTRY } from './links';

/*
 * Aurya Sound — Le fondamenta.
 *
 * Una guida, non una griglia di schede: sei sezioni in progressione, dal
 * fenomeno («che cosa sono le onde cerebrali») fino all'invito a esplorare.
 * Lettura a tre livelli — la frase semplice, la spiegazione, e solo dove
 * serve l'approfondimento facoltativo che si apre nel popup gia' esistente.
 *
 * Questo componente non tocca l'audio, non tocca la biblioteca e non tocca
 * Crea: legge contenuti e chiama due callback (`onExplore`, `onLearn`).
 */

const goTo = (id) => {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

function Deep({ k, onLearn }) {
  const a = APPROFONDIMENTI[k];
  if (!a) return null;
  return (
    <button type="button" className="gd-deep" onClick={() => onLearn(a)}>
      Approfondisci →
    </button>
  );
}

function Guida({ onExplore, onLearn, proCta }) {
  return (
    <div className="gd" data-testid="fqz-guida">

      {/* micro-navigazione: discreta, scorre alle sezioni */}
      <nav className="gd-nav" data-testid="fqz-guida-nav">
        {PERCORSO.map((s) => (
          <button key={s.id} type="button" onClick={() => goTo(s.id)}>
            <i>{s.n}</i> {s.short}
          </button>
        ))}
      </nav>

      {/* la mappa del percorso: il primo passo e' il punto di partenza */}
      <ol className="gd-path" data-testid="fqz-guida-path">
        {PERCORSO.map((s, i) => (
          <li key={s.id} className={i === 0 ? 'first' : undefined}>
            <button type="button" onClick={() => goTo(s.id)}>
              <span className="n">{s.n}</span>
              <span className="txt">
                <b>{s.kicker}</b>
                <em>{s.t}</em>
              </span>
              {i === 0 && <span className="start">si parte da qui</span>}
            </button>
          </li>
        ))}
      </ol>

      {/* ── 01 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-cervello">
        <div className="gd-head">
          <span className="gd-n">01</span>
          <div>
            <h3>Che cosa sono le onde cerebrali</h3>
            <p className="gd-kick">Il ritmo dell'attività elettrica del cervello</p>
          </div>
        </div>

        <p className="gd-lead">Il cervello non è mai completamente fermo.</p>
        <p>
          Miliardi di neuroni generano attività elettrica che può mostrare organizzazione
          ritmica. Con l'elettroencefalogramma (EEG) possiamo registrare questa attività e
          analizzarne la distribuzione nel tempo e nelle diverse frequenze.
        </p>
        <p>
          L'<b>Hertz</b> (Hz) indica quanti cicli avvengono in un secondo. Quando analizziamo
          l'EEG, possiamo osservare quanta attività cade in diverse gamme di frequenza.
        </p>

        <div className="gd-spectrum" data-testid="fqz-guida-bande">
          <div className="gd-strip">
            {BANDE.map((b) => (
              <span key={b.t} style={{ flexGrow: b.w }} title={`${b.t} · ${b.hz}`}>
                <i>{b.t}</i>
              </span>
            ))}
          </div>
          <div className="gd-scale"><span>0,5 Hz</span><span>scala logaritmica</span><span>60 Hz</span></div>
          <dl className="gd-bands">
            {BANDE.map((b) => (
              <div key={b.t}>
                <dt>{b.t}<em>{b.hz}</em></dt>
                <dd>{b.d}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="gd-box">
          <b>Non sono equivalenze</b>
          <p>
            Queste bande sono categorie utili per descrivere lo spettro dell'EEG, ma non
            corrispondono ciascuna a un singolo stato mentale. I ritmi cerebrali cambiano
            con il compito, l'età, lo stato di veglia, la regione cerebrale e molti altri
            fattori.
          </p>
        </div>

        <p className="gd-note">
          Le soglie possono variare leggermente tra studi e protocolli EEG.
          <Deep k="soglie" onLearn={onLearn} />
        </p>

        <button type="button" className="gd-cta" onClick={() => onExplore('Bande cerebrali')}>
          Esplora le bande →
        </button>
      </section>

      {/* ── 02 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-entrainment">
        <div className="gd-head">
          <span className="gd-n">02</span>
          <div>
            <h3>Che cos'è l'entrainment</h3>
            <p className="gd-kick">Quando un ritmo esterno incontra un sistema ritmico</p>
          </div>
        </div>

        <p>
          Molti sistemi biologici mostrano attività ritmica. Quando vengono esposti a stimoli
          periodici, possono comparire risposte sincronizzate o variazioni dell'attività in
          relazione al ritmo dello stimolo. In neuroscienza, il termine <i>entrainment</i>
          {' '}viene utilizzato per descrivere alcuni fenomeni di sincronizzazione tra
          un'attività neurale e uno stimolo ritmico.
        </p>
        <p>
          Nel suono, questo principio viene studiato attraverso stimoli periodici come battiti
          binaurali, battiti monaurali, toni isocronici e altre forme di modulazione ritmica.
        </p>

        <div className="gd-box strong" data-testid="fqz-guida-distinzione">
          <b>Una distinzione fondamentale</b>
          <div className="gd-neq">
            <span>percepire un ritmo</span>
            <i>≠</i>
            <span>dimostrare un cambiamento cerebrale</span>
          </div>
          <p>
            Il fatto che un battito sia chiaramente percepibile non significa automaticamente
            che il cervello venga portato stabilmente alla stessa frequenza. La ricerca sugli
            stimoli uditivi ritmici è reale, ma i risultati variano in funzione del metodo,
            della frequenza, del protocollo e della persona.
          </p>
        </div>

        <p>
          Per questo un battito a 6 Hz non «invita verso theta»: appartiene alla gamma di
          frequenze comunemente associata alla banda Theta, e la ricerca studia se e in quale
          misura stimoli ritmici di questo tipo possano modulare l'attività neurale.
          <Deep k="ricerca" onLearn={onLearn} />
        </p>
      </section>

      {/* ── 03 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-metodi">
        <div className="gd-head">
          <span className="gd-n">03</span>
          <div>
            <h3>Tre modi di creare un ritmo</h3>
            <p className="gd-kick">
              La differenza non è solo nel nome: è nel modo in cui il suono viene costruito.
            </p>
          </div>
        </div>

        <div className="gd-three" data-testid="fqz-guida-metodi">
          <div className="gd-m">
            <span className="gd-mn">Binaurale</span>
            <b>Due toni. Due orecchie.</b>
            <p>
              Un tono viene inviato a ciascun orecchio. Se le frequenze sono leggermente
              diverse, il sistema uditivo percepisce una pulsazione corrispondente alla
              differenza tra i due toni.
            </p>
            <span className="gd-hp on">Cuffie necessarie</span>
          </div>
          <div className="gd-m">
            <span className="gd-mn">Monaurale</span>
            <b>Due toni. Un battito già nel segnale.</b>
            <p>
              Le due frequenze vengono combinate prima della riproduzione, producendo una
              modulazione di ampiezza che è già fisicamente presente nello stimolo.
            </p>
            <span className="gd-hp">Cuffie non necessarie</span>
          </div>
          <div className="gd-m">
            <span className="gd-mn">Isocronico</span>
            <b>Un tono. Una pulsazione regolare.</b>
            <p>
              Il suono viene modulato ritmicamente, creando una sequenza di impulsi
              chiaramente percepibile.
            </p>
            <span className="gd-hp">Cuffie non necessarie</span>
          </div>
        </div>

        <div className="gd-fourth">
          <span className="gd-mn">Bilaterale</span>
          <b>Il ritmo si sposta tra destra e sinistra.</b>
          <p>
            Una tecnica di distribuzione spaziale del suono attraverso i due canali stereo.
            <span className="gd-hp soft">Cuffie consigliate</span>
          </p>
        </div>

        <p className="gd-note">
          Questi metodi non sono semplicemente versioni più o meno potenti dello stesso
          fenomeno. Producono stimoli acustici diversi e la ricerca non consente di stabilire
          una gerarchia universale di efficacia.
          <Deep k="fisica" onLearn={onLearn} />
        </p>

        <button type="button" className="gd-cta" onClick={() => onExplore('Metodi')}>
          Esplora i metodi →
        </button>
      </section>

      {/* ── 04 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-ascolto">
        <div className="gd-head">
          <span className="gd-n">04</span>
          <div>
            <h3>Cuffie o altoparlanti?</h3>
            <p className="gd-kick">
              La scelta dipende dal metodo e dall'esperienza che vuoi costruire.
            </p>
          </div>
        </div>

        <div className="gd-two" data-testid="fqz-guida-ascolto">
          <div>
            <span className="gd-mn">Cuffie</span>
            <b>Ideali quando</b>
            <ul>
              <li>vuoi separazione precisa tra destra e sinistra;</li>
              <li>utilizzi battiti binaurali;</li>
              <li>vuoi un ascolto individuale e immersivo.</li>
            </ul>
          </div>
          <div>
            <span className="gd-mn">Altoparlanti</span>
            <b>Ideali quando</b>
            <ul>
              <li>la sessione è condivisa;</li>
              <li>vuoi integrare musica e paesaggio sonoro nell'ambiente;</li>
              <li>utilizzi metodi che non richiedono separazione binaurale.</li>
            </ul>
          </div>
        </div>

        <div className="gd-box">
          <b>Regola semplice</b>
          <p>
            Se utilizzi un battito binaurale, la separazione dei canali è parte del metodo:
            per questo servono cuffie o auricolari stereo. Con gli altoparlanti, i due toni si
            diffondono nell'ambiente e raggiungono entrambe le orecchie: il segnale non è più
            presentato come stimolo binaurale classico.
          </p>
        </div>

        <p className="gd-note">Le schede della biblioteca indicano il requisito di ascolto.</p>
      </section>

      {/* ── 05 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-sessione">
        <div className="gd-head">
          <span className="gd-n">05</span>
          <div>
            <h3>Come si costruisce una buona sessione</h3>
            <p className="gd-kick">
              Non è solo una questione di frequenza. È una questione di arco, transizioni e contesto.
            </p>
          </div>
        </div>

        <p>
          Una sessione sonora efficace non nasce necessariamente dalla scelta di una singola
          frequenza. Durata, volume, transizioni, musica, ambiente, modalità di ascolto e
          intenzione contribuiscono tutti all'esperienza.
        </p>

        <div className="gd-arc" data-testid="fqz-guida-arco">
          <span>Ingresso</span><i>→</i><span>Transizione</span><i>→</i>
          <span>Profondità</span><i>→</i><span>Rientro</span>
        </div>
        <p className="gd-note">
          Questo è un esempio di struttura sonora, non una prescrizione neuroscientifica.
        </p>

        <ol className="gd-steps">
          <li>
            <span className="n">01</span>
            <div>
              <b>Ingresso <em>— portare continuità</em></b>
              <p>
                Una fase iniziale relativamente semplice e stabile permette all'ascoltatore di
                entrare nell'esperienza senza cambiamenti bruschi.
              </p>
            </div>
          </li>
          <li>
            <span className="n">02</span>
            <div>
              <b>Transizione <em>— cambiare gradualmente</em></b>
              <p>
                Se scegli di modificare la frequenza durante una sessione, una transizione
                progressiva può risultare più naturale e meno brusca di un cambio improvviso.
              </p>
            </div>
          </li>
          <li>
            <span className="n">03</span>
            <div>
              <b>Profondità <em>— lasciare spazio</em></b>
              <p>
                La parte centrale può essere mantenuta più stabile, lasciando tempo
                all'ascoltatore di vivere l'esperienza senza continui cambiamenti.
              </p>
            </div>
          </li>
          <li>
            <span className="n">04</span>
            <div>
              <b>Rientro <em>— quando serve, tornare</em></b>
              <p>
                Se la sessione termina dopo una fase particolarmente lenta o immersiva, una
                transizione graduale verso uno stimolo più attivo può rendere la conclusione
                più naturale.
              </p>
            </div>
          </li>
        </ol>

        <div className="gd-box strong wide" data-testid="fqz-guida-contesto">
          <b>Il suono non lavora da solo</b>
          <p>
            Una frequenza non determina da sola l'esperienza. Il risultato percepito dipende
            anche dal volume, dalla durata, dal contenuto musicale, dal contesto,
            dall'ambiente, dall'attenzione e dalle caratteristiche individuali
            dell'ascoltatore.
          </p>
        </div>
      </section>

      {/* ── 06 ─────────────────────────────────────────────────── */}
      <section className="gd-sec" id="gd-precisione">
        <div className="gd-head">
          <span className="gd-n">06</span>
          <div>
            <h3>Quanto è accurato ciò che ascolti?</h3>
            <p className="gd-kick">
              Precisione del segnale e incertezza dell'esperienza sono due cose diverse.
            </p>
          </div>
        </div>

        <p>
          Le frequenze generate digitalmente vengono definite matematicamente nel segnale
          audio. Se un parametro è impostato a 6 Hz, la modulazione viene costruita a 6 cicli
          al secondo secondo i parametri del sistema.
        </p>
        <p>
          Quando una frequenza cambia nel corso di una sessione, il motore fa avanzare la fase
          in modo continuo invece di ricominciare da capo: le transizioni si sentono come un
          movimento unico, e gli attacchi e le chiusure di ogni livello sono raccordati con
          brevi dissolvenze per evitare il click.
        </p>

        <div className="gd-box">
          <b>Dove finisce la precisione</b>
          <p>
            La precisione del segnale digitale non significa che ogni persona percepirà la
            stessa esperienza. La risposta dipende anche dal sistema di riproduzione, dal
            volume e dall'ascoltatore.
          </p>
        </div>

        <p className="gd-note">
          <Deep k="segnale" onLearn={onLearn} />
        </p>
      </section>

      {/* ── badge ──────────────────────────────────────────────── */}
      <section className="gd-sec gd-badges" data-testid="fqz-guida-badge">
        <h3>Un sistema di onestà</h3>
        <p className="gd-kick">Come leggere i badge della biblioteca</p>
        <p>
          Il badge non misura quanto una frequenza sia potente. Indica quanto sono solide le
          evidenze relative alle affermazioni che la accompagnano.
        </p>
        <dl className="gd-grades">
          <div className="ga"><dt><b>A</b> Evidenza solida</dt>
            <dd>Fenomeno o conoscenza ben documentata.</dd></div>
          <div className="gb"><dt><b>B</b> Ricerca in corso</dt>
            <dd>Esistono studi e risultati interessanti, ma le conclusioni non sono ancora definitive.</dd></div>
          <div className="gc"><dt><b>C</b> Tradizione e simbolismo</dt>
            <dd>L'associazione appartiene soprattutto alla tradizione, alla cultura sonora o a usi
              contemporanei non supportati da evidenze fisiologiche solide.</dd></div>
        </dl>
        <p className="gd-note">
          Un badge C non significa che il suono sia falso o inutile. Significa che Aurya non
          presenta come fatto scientifico ciò che la ricerca non ha dimostrato.
        </p>
      </section>

      {/* ── chiusura ───────────────────────────────────────────── */}
      <section className="gd-end" data-testid="fqz-guida-end">
        <h3>Ora puoi esplorare</h3>
        <p>
          Non serve conoscere tutto prima di iniziare. Ora sai distinguere una banda cerebrale
          da una frequenza sonora, una frequenza da un metodo e un fenomeno documentato da
          un'attribuzione tradizionale.
        </p>
        <div className="gd-ways">
          <button type="button" onClick={() => onExplore('Bande cerebrali')}>
            <b>Bande cerebrali</b>
            <span>Scopri i ritmi dell'attività EEG.</span>
          </button>
          <button type="button" onClick={() => onExplore('Altre frequenze')}>
            <b>Altre frequenze</b>
            <span>Esplora fenomeni fisici, accordature e tradizioni sonore.</span>
          </button>
          <button type="button" onClick={() => onExplore('Metodi')}>
            <b>Metodi</b>
            <span>Scopri come vengono costruiti gli stimoli.</span>
          </button>
        </div>
        <button type="button" className="gd-final" data-testid="fqz-guida-cta"
          onClick={() => onExplore('Bande cerebrali')}>
          Esplora Aurya Sound
        </button>
        {proCta && (
          /* SP3 — per il pubblico la chiusura ha una seconda uscita:
             gli operatori ascoltano e costruiscono */
          <p className="gd-pro" data-testid="fqz-cta-guida">
            Gli operatori possono ascoltare frequenze e metodi, combinarli e costruire
            le proprie esperienze sonore.{' '}
            <a href={PRO_ENTRY}>Scopri Aurya Sound per operatori →</a>
          </p>
        )}
      </section>
    </div>
  );
}

function Glossario({ onExplore }) {
  return (
    <div className="gd gd-gloss" data-testid="fqz-glossario">
      {GLOSSARIO.map((g) => (
        <div key={g.fam} className="gl-fam">
          <div className="gl-famtitle"><span>{g.fam}</span></div>
          <dl>
            {g.voci.map((v) => (
              <div key={v.t}>
                <dt>{v.t}</dt>
                <dd>
                  {v.d}
                  {v.go && (
                    <button type="button" className="gl-go" onClick={() => onExplore(v.go)}>
                      Scopri nella biblioteca →
                    </button>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}

export default function GuidaView({ tab, onExplore, onLearn, proCta = false }) {
  return tab === 'Glossario'
    ? <Glossario onExplore={onExplore} />
    : <Guida onExplore={onExplore} onLearn={onLearn} proCta={proCta} />;
}

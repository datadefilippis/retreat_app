/**
 * /sound/lab — LA SALA (LU1+LU3, 28/8/2026).
 *
 * La porta del laboratorio, ripensata per chi entra a freddo (la
 * diagnosi del founder: «io stesso che sono neofita non capisco
 * nulla»). Niente strumenti qui: la Sala ACCOGLIE — dice cos'e'
 * questo posto in tre righe, mostra le stanze come carte (ognuna con
 * la DOMANDA a cui risponde e cosa ci farai), offre il «da dove
 * parto?» per profili e i percorsi guidati. Gli strumenti vivono
 * nelle stanze, ognuna col suo indirizzo.
 */
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import StanzeSound from '../StanzeSound';
import TriggerStudio from '../TriggerStudio';
import Percorsi from './Percorsi';
import '../frequenze.css';
import './lab.css';

const STANZE = [
  {
    via: '/sound/lab/banco', nome: 'Il Banco',
    domanda: 'Com’è fatto un suono?',
    cosa: 'Generi un’onda e la guardi mentre suona: due voci, interferenza, la geometria degli intervalli in XY.',
  },
  {
    via: '/sound/lab/orecchio', nome: 'L’Orecchio',
    domanda: 'Che nota è? Che suono fa il mondo?',
    cosa: 'Il microfono entra nel banco: accordatore di precisione, e le letture mostrano la tua voce, un bicchiere, la stanza.',
  },
  {
    via: '/sound/lab/ritratto', nome: 'Il Ritratto',
    domanda: 'Di cosa è fatto il suono del mio oggetto?',
    cosa: 'Sei secondi di registrazione e ne esce la carta d’identità acustica, poi il banco la rifonde e la confronti con l’originale.',
  },
  {
    via: '/sound/lab/meraviglie', nome: 'Le Meraviglie',
    domanda: 'Cosa sa fare davvero il suono?',
    cosa: 'Tredici fenomeni veri col cartellino: vortici attorno alla testa, suoni che l’orecchio inventa, scale infinite, rumori colorati.',
  },
  {
    via: '/sound/lab/risonanze', nome: 'Le Risonanze',
    domanda: 'A quale frequenza canta il mio oggetto?',
    cosa: 'Lo sweep interroga, il microfono ascolta, la curva mostra i picchi: il primo passo della cimatica, col quaderno di banco.',
  },
];

const PROFILI = [
  ['Sono curioso, parto da zero',
    'Segui «Misura la tua bottiglia»: in cinque minuti attraversi mezzo laboratorio con un oggetto di casa.',
    null],
  ['Suono o canto',
    'L’accordatore ti aspetta: canta una nota e guardala, poi scopri nello spettrogramma com’è fatta la tua voce.',
    '/sound/lab/orecchio'],
  ['Lavoro col suono (campane, gong, voce)',
    'Fai il Ritratto del tuo strumento: la sua carta d’identità acustica, e la rifusione da far sentire ai clienti.',
    '/sound/lab/ritratto'],
];

export default function LabSala() {
  useEffect(() => {
    document.title = 'Aurya Sound Lab: il laboratorio del suono';
  }, []);
  return (
    <div className="fqz lab" data-testid="lab-page">
      <SoundTopbar firma="Lab" qui="/sound/lab" />
      <header>
        <div>
          <h1>Il <em>Laboratorio</em></h1>
          <div className="sub">Genera un segnale. Osservalo. Misuralo.</div>
          <p className="sld-parentela">
            La biblioteca spiega il suono: qui il suono si tocca. Un vero
            laboratorio nel tuo dispositivo, niente registrazioni,
            niente trucchi: ogni onda che senti è calcolata mentre la
            ascolti, e ogni affermazione si misura con gli strumenti.
          </p>
        </div>
        <StanzeSound attiva="lab" />
      </header>
      <main>
        {/* LE STANZE: ognuna risponde a una domanda, ognuna ha il suo
            indirizzo, si entra dove porta la propria curiosita' */}
        <div className="lab-sala-stanze" data-testid="lab-sala-stanze">
          {STANZE.map((s) => (
            <Link key={s.via} to={s.via} className="lab-sala-carta"
              data-testid={`lab-carta-${s.via.split('/').pop()}`}>
              <h2>{s.nome}</h2>
              <p className="lab-sala-domanda">{s.domanda}</p>
              <p className="lab-sala-cosa">{s.cosa}</p>
              <span className="lab-sala-entra">Entra →</span>
            </Link>
          ))}
        </div>

        {/* DA DOVE PARTO, la mano tesa per profilo */}
        <section className="lab-card lab-sala-profili" data-testid="lab-sala-profili">
          <div className="lab-chead">
            <h2>Da dove parto?</h2>
            <span className="lab-cnote">tre strade, per come arrivi qui</span>
          </div>
          {PROFILI.map(([chi, come, via]) => (
            <div key={chi} className="lab-sala-profilo">
              <b>{chi}</b>
              <span>
                {come}{via && <>{' '}<Link to={via}>Vai →</Link></>}
              </span>
            </div>
          ))}
        </section>

        <Percorsi />

        <p className="lab-arrivo" data-testid="lab-arrivo">
          Un laboratorio onesto: quello che senti è quello che vedi,
          misurato mentre accade, e quello che non è dimostrato porta
          il suo cartellino.
        </p>
        {/* NV5, il funnel professionale anche nel Lab */}
        <TriggerStudio />
      </main>
      <footer className="fqzfoot">
        <a href="/sound">← Aurya Sound</a>
        <a href="/sound/esplora">La biblioteca</a>
        <a href="/sound/impara">Le fondamenta</a>
      </footer>
    </div>
  );
}

/**
 * CP2 (20/8/2026) — la lettera di Aurya dentro il gestionale.
 *
 * Prima l'operatore poteva iscriversi solo dalle pagine pubbliche, e
 * se non aveva anche il cappello cliente non sapeva DA NESSUNA PARTE
 * se fosse iscritto: lo stato viveva solo in /account, cioe' nel mondo
 * dei clienti. Qui c'e' lo stato della SUA email e l'azione coerente —
 * niente marketing, niente ridigitare l'indirizzo.
 *
 * Backend: GET/POST /api/auth/letter (riusano i flussi pubblici, double
 * opt-in incluso: da qui non esistono scorciatoie).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Mail } from 'lucide-react';
import api from '../../../api/client';
import { Button } from '../../../components/ui/button';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '../../../components/ui/card';

export default function LetterCard() {
  const { t } = useTranslation('settings');
  const [state, setState] = React.useState(null);   // none|pending|confirmed|unsubscribed
  const [indirizzo, setIndirizzo] = React.useState(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    let alive = true;
    api.get('/auth/letter')
      .then((r) => {
        if (!alive) return;
        setState(r.data?.state || 'none');
        setIndirizzo(r.data?.email || null);
      })
      .catch(() => { if (alive) setState('none'); });
    return () => { alive = false; };
  }, []);

  const toggle = async (subscribe) => {
    setBusy(true);
    try {
      const r = await api.post('/auth/letter', { subscribe });
      setState(r.data?.state || (subscribe ? 'pending' : 'unsubscribed'));
    } catch { /* lo stato resta quello di prima */ }
    finally { setBusy(false); }
  };

  const body = {
    confirmed: t('letter.confirmed', { defaultValue: 'Ricevi la lettera di Aurya su questo indirizzo.' }),
    pending: t('letter.pending', { defaultValue: 'Manca solo la conferma: apri l’email che ti abbiamo mandato e clicca il link.' }),
    unsubscribed: t('letter.unsubscribed', { defaultValue: 'Non ricevi la lettera. Puoi riattivarla quando vuoi.' }),
    none: t('letter.none', { defaultValue: 'La lettera racconta le persone della rete e le pratiche, ogni tanto. Nessuna pubblicità.' }),
  }[state || 'none'];

  return (
    <Card className="border border-border" data-testid="settings-letter">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Mail className="h-5 w-5" aria-hidden />
          {t('letter.title', { defaultValue: 'La lettera di Aurya' })}
        </CardTitle>
        <CardDescription>
          {body}
          {/* NL-bis (20/8) — su QUALE indirizzo stiamo guardando: senza
              dirlo, chi si e' iscritto con un'altra email legge «non
              ricevi la lettera» e si iscrive una seconda volta. */}
          {indirizzo && (
            <span className="block mt-1 text-xs text-muted-foreground"
              data-testid="letter-address">
              {t('letter.address', { email: indirizzo, defaultValue: 'Stiamo guardando l’indirizzo {{email}}.' })}
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {state === null ? null : state === 'confirmed' ? (
          <Button variant="outline" disabled={busy} onClick={() => toggle(false)}
            data-testid="letter-unsubscribe">
            {t('letter.unsubscribeCta', { defaultValue: 'Disiscrivimi' })}
          </Button>
        ) : state === 'pending' ? (
          <Button variant="outline" disabled={busy} onClick={() => toggle(true)}
            data-testid="letter-resend">
            {t('letter.resendCta', { defaultValue: 'Rimanda l’email di conferma' })}
          </Button>
        ) : (
          <Button disabled={busy} onClick={() => toggle(true)}
            data-testid="letter-subscribe">
            {t('letter.subscribeCta', { defaultValue: 'Iscrivimi alla lettera' })}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

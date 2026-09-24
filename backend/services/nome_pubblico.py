"""IL NOME PUBBLICO dell'operatore (P1, 24/9/2026, founder).

Il problema: il profilo era intestato SOLO all'organizzazione
(`organizations.name`, obbligatorio alla registrazione), quindi chi non ha
un marchio se ne inventava uno («Cerchio Angelico», «Casa Coco») e la
persona spariva. 7 profili su 20 in produzione erano cosi'.

La regola, in un posto solo (il frontend ha lo specchio in
frontend/src/lib/nomePubblico.js, guardia di parita'):

  persona + marchio diversi  → «Valentina · Brillare | Il Sole Dentro»
  solo persona               → «Valentina»
  solo marchio (il pregresso, senza nome_persona) → il marchio, IDENTICO a oggi
  marchio che contiene gia' la persona («Claudia Pietrantuoni - L'Alchimia»)
                             → il marchio cosi' com'e', senza doppiare

`nome_persona` vive in public_profile (whitelist, max 80). Lo slug non
cambia mai da qui. Il separatore e' il punto mediano (decisione founder).
(services/identita.py e' un'altra cosa: l'identita' del BRAND Aurya.)
"""
from typing import Dict, Optional

SEPARATORE = " · "
NOME_PERSONA_MAX = 80


def _pulito(s: Optional[str]) -> str:
    return " ".join((s or "").split()).strip()


def contiene_persona(marchio: str, persona: str) -> bool:
    """Il marchio contiene gia' la persona? Basta UNA parola del nome
    (di almeno 3 lettere) dentro il marchio: «Valentina - Brillare» con
    «Valentina Rossi» NON deve diventare «Valentina Rossi · Valentina -
    Brillare» (domanda del founder, 24/9). Un marchio che porta il nome
    di chi lo firma e' gia' personale: si mostra com'e'."""
    m = _pulito(marchio).casefold()
    parti = [p for p in _pulito(persona).casefold().split() if len(p) > 2]
    return bool(parti) and any(p in m for p in parti)


def parti_nome(org: dict, fallback: str = "") -> Dict[str, object]:
    """{persona, marchio, composto, pubblico}: cio' che serve a chi
    disegna l'intestazione (persona grande, marchio sotto) e a chi
    vuole solo la stringa."""
    pp = (org or {}).get("public_profile") or {}
    persona = _pulito(pp.get("nome_persona"))[:NOME_PERSONA_MAX]
    marchio = _pulito((org or {}).get("name")) or _pulito(fallback)
    composto = bool(persona and marchio
                    and persona.casefold() != marchio.casefold()
                    and not contiene_persona(marchio, persona))
    if composto:
        pubblico = f"{persona}{SEPARATORE}{marchio}"
    elif persona and marchio:
        # stessa stringa, o marchio che contiene gia' la persona: il marchio
        # com'e' («Claudia Pietrantuoni - L'Alchimia dell'Essere»)
        pubblico = marchio
    elif persona:
        pubblico = persona
    else:
        pubblico = marchio
    return {"persona": persona or None, "marchio": marchio if composto else None,
            "composto": composto, "pubblico": pubblico}


def nome_pubblico(org: dict, fallback: str = "") -> str:
    """La stringa che il pubblico vede: card, pagina, link, titolo SEO."""
    return str(parti_nome(org, fallback)["pubblico"])

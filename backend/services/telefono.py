"""IL TELEFONO dell'operatore (P3, 24/9/2026, founder).

Chiesto alla registrazione del professionista perche' Aurya deve poterlo
raggiungere (9 operatori su 20 in produzione non ne avevano uno), ma
PRIVATO: vive in public_profile.public_phone e compare sul profilo solo
con `show_contacts`, che resta spento finche' l'operatore non lo accende.

Forma canonica: solo cifre, con il «+» iniziale se c'era; da 8 a 15
cifre (E.164). Spazi, punti, trattini e parentesi si buttano.
"""
import re
from typing import Optional

CIFRE_MIN, CIFRE_MAX = 8, 15


def normalizza_telefono(raw: Optional[str]) -> Optional[str]:
    """«+39 366 371 3543» → «+393663713543»; «366.3713543» → «3663713543»;
    non valido → None."""
    s = (raw or "").strip()
    if not s:
        return None
    piu = s.startswith("+")
    cifre = re.sub(r"\D", "", s)
    if not (CIFRE_MIN <= len(cifre) <= CIFRE_MAX):
        return None
    return ("+" if piu else "") + cifre


def telefono_valido(raw: Optional[str]) -> bool:
    return normalizza_telefono(raw) is not None

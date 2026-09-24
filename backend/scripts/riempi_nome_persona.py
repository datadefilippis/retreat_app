"""24/9/2026 sera — il pregresso eredita il nome dall'account.

Ogni organizzazione senza `public_profile.nome_persona` lo prende dal
nome di chi si e' registrato (primo admin), ripulito. Chi ce l'ha gia'
non si tocca. Idempotente: si puo' rilanciare.

Uso:
  python3 scripts/riempi_nome_persona.py --prova     # mostra prima/dopo, non scrive
  python3 scripts/riempi_nome_persona.py             # scrive
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.nome_persona import riempi_pregresso  # noqa: E402


async def main(prova: bool) -> None:
    e = await riempi_pregresso(prova=prova)
    for r in e["righe"]:
        cambia = "" if r["prima"] == r["dopo"] else "   ← cambia sul pubblico"
        print(f"  {r['org'][:34]:34} | nome persona: {r['nome_persona'][:26]:26} | {r['dopo']}{cambia}")
    print(f"{'PROVA' if prova else 'SCRITTE'}: {e['scritte']} | gia' piene: {e['gia_piene']} | senza account: {e['senza_account']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prova", action="store_true")
    asyncio.run(main(ap.parse_args().prova))

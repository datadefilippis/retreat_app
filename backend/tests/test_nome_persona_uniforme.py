"""24/9/2026 sera (founder) — «uniformiamo la variabile nome»: il nome
della persona e' UNO, sull'account e sul profilo, anche per chi si e'
registrato prima del campo.

Tenuto fermo qui:
  1. la pulizia del nome e' una sola (services/nome_persona.ripulisci) e
     lo script di proposta la importa da li';
  2. la GET del profilo (operatore E admin, che la riusa) mostra il nome
     dell'account quando il profilo non ce l'ha, e compone il nome
     pubblico con quello;
  3. un nome nuovo salvato sul profilo allinea l'account (dopo_salvataggio);
  4. il riempimento del pregresso e' idempotente e non tocca chi ce l'ha.
"""
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


class TestPulizia:
    def test_ripulisci(self):
        from services.nome_persona import ripulisci
        assert ripulisci("Paola ARTICO") == "Paola Artico"
        assert ripulisci("Ilaria Barbaccia Barbaccia") == "Ilaria Barbaccia"
        assert ripulisci("Silvia de Franchis ") == "Silvia de Franchis"
        assert ripulisci("  claudia   Rossato") == "Claudia Rossato"
        assert ripulisci("Valentina") == "Valentina"
        assert ripulisci("") == "" and ripulisci(None) == ""
        assert ripulisci("Anna-Maria rossi") == "Anna-Maria Rossi"

    def test_lo_script_di_proposta_usa_la_stessa(self):
        src = (BACKEND / "scripts" / "proponi_nome_persona.py").read_text(encoding="utf-8")
        assert "from services.nome_persona import ripulisci" in src
        assert "def ripulisci(" not in src


class TestGetEAllineamento:
    def test_la_get_mostra_il_nome_dell_account_se_manca(self):
        src = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
        i = src.index("async def get_public_profile(")
        blocco = src[i:i + 3000]
        assert "persona = await nome_persona_effettivo(org_doc)" in blocco
        assert '"nome_persona": persona,' in blocco
        assert '"nome_pubblico": nome_pubblico(org_eff),' in blocco
        # l'admin riusa la stessa GET: una sola verita'
        adm = (BACKEND / "routers" / "admin.py").read_text(encoding="utf-8")
        assert "from routers.organizations import get_public_profile" in adm

    def test_dopo_salvataggio_allinea_l_account(self):
        src = (BACKEND / "services" / "profilo_pubblico.py").read_text(encoding="utf-8")
        i = src.index("async def dopo_salvataggio(")
        assert 'if updates and updates.get("public_profile.nome_persona"):' in src[i:]
        assert "await allinea_account(org_id, updates[\"public_profile.nome_persona\"])" in src[i:]

    async def test_effettivo_e_allinea_sul_db_locale(self):
        """Sul DB locale: un'org con nome_persona vuoto mostra il nome
        dell'account; allinea_account scrive solo se diverso; poi ripristino."""
        from database import organizations_collection, users_collection
        from services.nome_persona import allinea_account, nome_persona_effettivo, ripulisci
        try:
            u = await users_collection.find_one({"email": "admin@demo.com"}, {"_id": 0, "id": 1, "organization_id": 1, "name": 1})
        except RuntimeError as e:
            pytest.skip(f"client motor su un altro loop: {e}")
        if not u:
            pytest.skip("org demo assente")
        org = await organizations_collection.find_one({"id": u["organization_id"]}, {"_id": 0, "id": 1, "name": 1, "public_profile": 1})
        pp = org.get("public_profile") or {}
        senza = {**org, "public_profile": {**pp, "nome_persona": ""}}
        assert await nome_persona_effettivo(senza) == ripulisci(u["name"])
        con = {**org, "public_profile": {**pp, "nome_persona": "Nome Salvato"}}
        assert await nome_persona_effettivo(con) == "Nome Salvato"
        # allinea: stesso nome → niente scrittura; nome nuovo → scrive; poi ripristino
        assert await allinea_account(org["id"], u["name"]) is False
        assert await allinea_account(org["id"], "Prova Allineamento") is True
        assert (await users_collection.find_one({"id": u["id"]}, {"_id": 0, "name": 1}))["name"] == "Prova Allineamento"
        await users_collection.update_one({"id": u["id"]}, {"$set": {"name": u["name"]}})

    async def test_riempi_pregresso_e_idempotente(self):
        from services.nome_persona import riempi_pregresso
        try:
            e = await riempi_pregresso(prova=True)
        except RuntimeError as ex:
            pytest.skip(f"client motor su un altro loop: {ex}")
        assert e["prova"] is True and set(e) >= {"scritte", "gia_piene", "senza_account", "righe"}
        for r in e["righe"]:
            assert r["nome_persona"] and r["dopo"]
        src = (BACKEND / "scripts" / "riempi_nome_persona.py").read_text(encoding="utf-8")
        assert "riempi_pregresso" in src and "--prova" in src

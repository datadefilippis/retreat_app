"""AC3 (7/10/2026) — Il pubblico: la pagina del corso, le anteprime gratuite
(video di presentazione + lezioni segnate), i corsi nel profilo, il legacy
/co e /courses dismessi."""
import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestBackendPubblico:
    def test_rotte_pubbliche_e_senza_guid(self):
        src = (BACKEND / "routers" / "public.py").read_text()
        assert '@router.get("/corso/{org_slug}/{slug}", response_model=PublicCorsoLanding)' in src
        assert '@router.post("/corso/{org_slug}/{slug}/anteprima/{lesson_id}/play-url")' in src
        # anteprima: limite per IP, URL breve, nessun watermark
        corpo = src.split("async def anteprima_corso_play_url")[1].split("\nasync def ")[0]
        assert 'customer_email=None, ttl_seconds=3600' in corpo
        assert '/play-url")\n@limiter.limit("30/minute")\nasync def anteprima_corso_play_url' in src
        # solo il trailer o una lezione is_preview E pronta E video
        assert 'if not l or not l.get("is_preview") or not _lezione_pronta(l) or (l.get("tipo") or "video") != "video":' in corpo
        # la landing: il programma non porta GUID
        landing = src.split("async def get_corso_landing")[1].split("\n@router")[0]
        assert '"guid"' not in landing
        assert '"is_preview": bool(l.get("is_preview")) and _lezione_pronta(l)' in landing
        # i corsi nel profilo: solo pubblicati con almeno una lezione pronta
        corsi = src.split("async def _operator_corsi")[1].split("\nclass ")[0]
        assert '"item_type": "course", "is_published": True, "is_active": True' in corsi
        assert "if not pronte:" in corsi
        assert '"corsi": await _operator_corsi(org_id)' in src

    def test_trailer_nel_gestionale_e_nel_webhook(self):
        acc = (BACKEND / "routers" / "accademia.py").read_text()
        for r in ('@router.post("/{course_id}/trailer")', '@router.get("/{course_id}/trailer")', '@router.delete("/{course_id}/trailer")'):
            assert r in acc, r
        assert '"00 · Presentazione"' in acc                      # il titolo su Bunny, prima delle lezioni
        assert 'await _cancella_video_bunny(org_id, finto)          # un trailer per corso' in acc
        assert '"trailer": _riga_video(course_doc.get("trailer"), firma)' in acc
        wh = (BACKEND / "routers" / "webhooks_bunny.py").read_text()
        assert '{"modules.lessons.video.guid": video_guid}, {"trailer.guid": video_guid}' in wh
        assert 'return {"esito": "aggiornata", "trailer": True, "stato": stato}' in wh
        from models.course import Course
        assert "trailer" in Course.model_fields

    def test_seo_shell_sitemap_e_registro(self):
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert "async def _meta_corso(" in shell and 'if head == "corso" and len(parts) >= 3:' in shell
        assert '"@type": "Course"' in shell
        assert "co" not in re.search(r"_PRODUCT_KINDS\s*=\s*\(([^)]*)\)", shell).group(1).replace('"', "").split(", ")
        seo = (BACKEND / "routers" / "seo.py").read_text()
        assert '"course": "corso"' in seo
        rotte = json.loads((BACKEND / "config" / "rotte.json").read_text())
        assert "corso" in rotte["pubblica"] and "corso" in rotte["solo_con_slug"]
        assert "co" not in rotte["pubblica"] and "courses" not in rotte["app"]
        assert "co" in rotte["servizio"] and "courses" in rotte["servizio"]      # rimandi della SPA, 301 per nginx
        assert rotte["rimandi_prefisso"]["co"] == "/corso$1" and rotte["rimandi_prefisso"]["courses"] == "/accademia"
        nginx = (BACKEND.parent / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "corso" in nginx


class TestFrontendPubblico:
    def test_pagina_del_corso(self):
        p = (FRONTEND / "features" / "storefront" / "CorsoLandingPage.js").read_text()
        for t in ("corso-landing", "corso-trailer-play", "corso-landing-programma", "corso-landing-compra",
                  "corso-landing-condividi", "corso-landing-barra", "corso-landing-404", "corso-anteprima"):
            assert f'data-testid="{t}"' in p or f"data-testid={{`{t}" in p, t
        assert "Guarda gratis" in p and "Guarda la presentazione" in p
        assert "item_type: 'course'" in p and "InlineProdottoCheckout" in p
        assert "storefrontAPI.anteprimaCorsoPlayUrl(orgSlug, slug, lessonId)" in p
        api = (FRONTEND / "api" / "storefront.js").read_text()
        assert "/api/public/corso/${orgSlug}/${slug}`" in api
        assert "/api/public/corso/${orgSlug}/${slug}/anteprima/${lessonId}/play-url" in api

    def test_profilo_e_checkout(self):
        prof = (FRONTEND / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-corsi"' in prof and "data.corsi" in prof
        assert "`/corso/${org_slug}/${cr.slug || cr.product_id}`" in prof
        assert "row={{ product_id: cr.product_id, item_type: 'course', slug: cr.slug }}" in prof
        chk = (FRONTEND / "features" / "storefront" / "components" / "checkout" / "InlineProdottoCheckout.jsx").read_text()
        assert "«I miei corsi»" in chk

    def test_gestionale_trailer_e_condividi(self):
        cp = (FRONTEND / "features" / "accademia" / "CorsoPage.js").read_text()
        assert "<TrailerEditor corso={c} ricarica={load} />" in cp
        assert 'prefisso="corso" cosa="corso"' in cp
        te = (FRONTEND / "features" / "accademia" / "TrailerEditor.js").read_text()
        assert "accademiaAPI.trailerPrepara(corso.id" in te and "caricaVideo(file, cred" in te
        api = (FRONTEND / "api" / "accademia.js").read_text()
        for m in ("trailerPrepara", "trailerStato", "trailerTogli"):
            assert m in api
        ui = (FRONTEND / "features" / "prodotti" / "ui.js").read_text()
        assert "export function urlPagina(orgSlug, slug, prefisso = 'prodotto')" in ui
        lista = (FRONTEND / "features" / "accademia" / "AccademiaPage.js").read_text()
        assert "urlPagina(data?.public_slug, c.slug, 'corso')" in lista

    def test_rotte_e_legacy_dismesso(self):
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/corso/:org_slug/:slug"' in app and "<CorsoLandingPage />" in app
        assert 'path="/co/:org_slug/:product_slug" element={<RedirectCoLegacy />}' in app
        assert 'path="/account/courses/:enrollment_id" element={<RedirectCorsoLegacy />}' in app
        assert 'path="/courses" element={<Navigate to="/accademia" replace />}' in app
        assert 'path="/courses/new" element={<Navigate to="/accademia/nuovo" replace />}' in app
        for morto in ('import("./features/storefront/CourseLandingPage")', 'import("./features/courses/CoursesPage")',
                      'import("./features/courses/CourseEditor")', 'import("./features/customer-portal/pages/CoursesIndexPage")',
                      'import("./features/customer-portal/pages/CoursePlayerPage")',
                      "import CustomerProtectedRoute from", "import CustomerLayout from"):
            assert morto not in app, morto
        assert "<CustomerLayout />" not in app and "<CustomerProtectedRoute>" not in app
        layout = (FRONTEND / "components" / "Layout.js").read_text()
        assert "href: '/courses'" not in layout

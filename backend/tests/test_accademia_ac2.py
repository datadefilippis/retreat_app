"""AC2 (7/10/2026) — Lo studente: «I miei corsi» e il player sull'account Aurya."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestRouterStudente:
    def test_rotte_montate_e_scoped(self):
        src = (BACKEND / "routers" / "platform_corsi.py").read_text()
        assert 'router = APIRouter(prefix="/platform/me/corsi"' in src
        for r in ('@router.get("")', '@router.get("/{enrollment_id}")',
                  '@router.post("/{enrollment_id}/lezioni/{lesson_id}/play-url")', '@router.post("/{enrollment_id}/progresso")'):
            assert r in src, r
        # l'account e' DENTRO la query, mai un controllo dopo
        assert '{"id": enrollment_id, "platform_account_id": account_id}' in src
        assert '{"platform_account_id": account["id"]}' in src
        # rate limit su play-url e progresso; il GUID non esce mai
        assert '@limiter.limit("60/minute")' in src and '@limiter.limit("120/minute")' in src
        assert '"play_url": firmato.play_url' in src
        # la proiezione per lo studente non ha una chiave «guid» in uscita
        proiezione = src.split("def _proietta")[1].split("def _stats")[0]
        assert '"guid":' not in proiezione and '"has_video": bool(' in proiezione
        server = (BACKEND / "server.py").read_text()
        assert 'app.include_router(platform_corsi_router.router, prefix="/api")' in server

    def test_stati_e_progresso(self):
        from routers.platform_corsi import _stato, _stats, _proietta, _scaduta
        now = datetime.now(timezone.utc)
        assert _stato({"revoked_at": now}, now) == "revocato"
        assert _stato({"expires_at": (now - timedelta(days=1)).isoformat()}, now) == "scaduto"
        assert _stato({"expires_at": (now + timedelta(days=1)).isoformat()}, now) == "attivo"
        assert _stato({"completed_at": now}, now) == "completato"
        assert not _scaduta({"expires_at": None}, now)
        corso = {"modules": [{"order": 0, "lessons": [
            {"id": "a", "order": 0, "title": "A", "tipo": "testo", "testo": "ciao"},
            {"id": "b", "order": 1, "title": "B", "tipo": "video", "video": {"guid": "g" * 36, "stato": "pronto", "duration_seconds": 15}},
            {"id": "c", "order": 2, "title": "C", "tipo": "video", "video": {"guid": "h" * 36, "stato": "codifica"}},
        ]}]}
        s = _stats(corso, {"a": {"completed_at": now}, "zz": {"completed_at": now}})
        assert s == {"lessons_completed": 1, "total_lessons": 3, "percentage": 33}
        p = _proietta(corso)
        lez = p["modules"][0]["lessons"]
        assert lez[0]["tipo"] == "testo" and lez[0]["testo"] == "ciao" and lez[0]["has_video"] is False
        assert lez[1]["video_pronto"] is True and lez[1]["duration_seconds"] == 15 and "guid" not in lez[1]
        assert lez[2]["video_pronto"] is False and lez[2]["has_video"] is True
        # il corso completato si scrive UNA volta (nel router)
        src = (BACKEND / "routers" / "platform_corsi.py").read_text()
        assert 'upd["completed_at"] = now' in src and 'not enr.get("completed_at")' in src


class TestEmailEAccount:
    def test_email_del_corso(self):
        e = (BACKEND / "services" / "order_email_service.py").read_text()
        assert 'f"/account/corsi/{enrollment_id}"' in e and "/account/courses/{enrollment_id}" not in e
        assert 'tipi <= {"course"}' in e and '_t("order_confirmed_body_corso"' in e
        it = (BACKEND / "services" / "email_service.py").read_text()
        assert '"order_confirmed_body_corso": "Il pagamento è andato a buon fine e il tuo corso è pronto.' in it
        assert '"order_confirmed_cta_corsi": "Vai ai miei corsi"' in it

    def test_frontend(self):
        api = (FRONTEND / "api" / "corsi.js").read_text()
        for n in ("getMyCourses", "getCourseDetail", "getPlayUrl", "sendProgress", "/platform/me/corsi"):
            assert n in api, n
        player = (FRONTEND / "features" / "customer-portal" / "course-player" / "components" / "LessonPlayer.jsx").read_text()
        assert "api = customerPortalAPI," in player and "await api.getPlayUrl(" in player and "await api.sendProgress(" in player
        pagina = (FRONTEND / "features" / "account" / "CorsoStudentePage.js").read_text()
        for n in ("corsiAPI", "<LessonPlayer", "<CourseSidebar", "<LessonActionBar", "useLessonNavigation", 'data-testid="lezione-testo"',
                  'data-testid="corso-completato"', 'data-testid="video-in-arrivo"', "api={corsiAPI}"):
            assert n in pagina, n
        account = (FRONTEND / "features" / "account" / "AccountPage.js").read_text()
        assert "/platform/me/corsi" in account and 'data-testid="account-corsi"' in account and 'data-testid="account-corso-continua"' in account
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/account/corsi/:enrollment_id"' in app and "CorsoStudentePage" in app

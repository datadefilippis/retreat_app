/**
 * /account/corsi/:enrollment_id — IL PLAYER dello studente (AC2, 7/10/2026).
 *
 * Riusa i componenti del player legacy (LessonPlayer, CourseSidebar,
 * LessonActionBar, LessonDetails, HelpCheatsheet, useLessonNavigation) con il
 * client dell'account Aurya (api/corsi.js). In piu': le lezioni di TESTO,
 * il «percorso completato», il guscio del sito (MarketplaceShell) invece
 * del portale legacy.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { ArrowLeft, CheckCircle2, FileText, X as XIcon } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import { corsiAPI } from '../../api/corsi';
import LessonPlayer from '../customer-portal/course-player/components/LessonPlayer';
import LessonActionBar from '../customer-portal/course-player/components/LessonActionBar';
import LessonDetails from '../customer-portal/course-player/components/LessonDetails';
import CourseSidebar from '../customer-portal/course-player/components/CourseSidebar';
import CoursePlayerSkeleton from '../customer-portal/course-player/components/CoursePlayerSkeleton';
import HelpCheatsheet from '../customer-portal/course-player/components/HelpCheatsheet';
import useLessonNavigation from '../customer-portal/course-player/hooks/useLessonNavigation';

const ERRORI = {
  not_found: ['Questo corso non è tra i tuoi.', 'Forse l’acquisto è su un altro account, o il link non è completo.'],
  revoked: ['L’accesso a questo corso è stato revocato.', 'Se pensi sia un errore, scrivi a chi lo ha pubblicato: lo trovi nel tuo account.'],
  expired: ['Il tuo accesso a questo corso è scaduto.', 'Il periodo di accesso previsto è finito. Chi lo ha pubblicato può rinnovarlo.'],
  course_unavailable: ['Questo corso non è più disponibile.', 'Chi lo ha pubblicato lo ha tolto. Il tuo acquisto resta registrato nell’account.'],
  generic: ['Qualcosa non ha funzionato.', 'Riprova fra un momento.'],
};

function Errore({ kind }) {
  const [titolo, testo] = ERRORI[kind] || ERRORI.generic;
  return (
    <div className="mx-auto max-w-md px-4 py-16 text-center" data-testid="corso-studente-errore">
      <h1 className="font-display text-2xl text-gray-900">{titolo}</h1>
      <p className="mt-2 text-sm text-gray-600">{testo}</p>
      <Link to="/account" className="mt-6 inline-flex rounded-full bg-[#2f5749] px-5 py-2.5 text-sm font-semibold text-white">Vai al tuo account</Link>
    </div>
  );
}

export default function CorsoStudentePage() {
  const { enrollment_id: enrollmentId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation('customer_portal');
  const [me, setMe] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  const [lessonsDrawerOpen, setLessonsDrawerOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    let tk = null;
    try { tk = localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { /* private mode */ }
    if (!tk) { navigate(`/accedi?next=${encodeURIComponent(`/account/corsi/${enrollmentId}`)}`, { replace: true }); return; }
    platformApi.get('/platform/me', { headers: { Authorization: `Bearer ${tk}` } }).then(r => setMe(r.data)).catch(() => {});
  }, [enrollmentId, navigate]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const { data } = await corsiAPI.getCourseDetail(enrollmentId);
      setData(data);
      const all = (data?.course?.modules || []).flatMap(m => m.lessons || []);
      const hash = typeof window !== 'undefined' ? window.location.hash : '';
      const hashId = hash.startsWith('#lesson-') ? hash.slice('#lesson-'.length) : null;
      const fromHash = hashId ? all.find(l => l.id === hashId) : null;
      const firstIncomplete = all.find(l => !data?.progress?.[l.id]?.completed_at);
      setSelectedLessonId((fromHash || firstIncomplete || all[0])?.id || null);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const code = typeof detail === 'object' ? detail.error : null;
      if (status === 401) { navigate(`/accedi?next=${encodeURIComponent(`/account/corsi/${enrollmentId}`)}`, { replace: true }); return; }
      if (status === 404) setError({ kind: 'not_found' });
      else if (status === 403 && code === 'enrollment_revoked') setError({ kind: 'revoked' });
      else if (status === 403 && code === 'enrollment_expired') setError({ kind: 'expired' });
      else if (status === 410) setError({ kind: 'course_unavailable' });
      else setError({ kind: 'generic' });
    } finally { setLoading(false); }
  }, [enrollmentId, navigate]);
  useEffect(() => { load(); }, [load]);

  const course = data?.course;
  useSeoMeta({ title: course ? `${course.title} | Aurya` : 'Il tuo corso | Aurya', noindex: true });
  const progress = data?.progress || {};
  const progressStats = data?.progress_stats || {};
  const flatLessons = useMemo(() => (course?.modules || []).flatMap(m => (m.lessons || []).map(l => ({ ...l, module_id: m.id, module_title: m.title }))), [course]);
  const selectedLesson = flatLessons.find(l => l.id === selectedLessonId) || null;
  const isCurrentCompleted = !!(selectedLessonId && progress?.[selectedLessonId]?.completed_at);

  const handleProgressUpdate = useCallback((resp) => {
    if (!resp?.lesson_id) return;
    setData(prev => {
      if (!prev) return prev;
      const np = { ...(prev.progress || {}) };
      np[resp.lesson_id] = { watched_seconds: resp.watched_seconds, completed_at: resp.completed_at };
      const enrollment = resp.corso_completato && !prev.enrollment?.completed_at
        ? { ...prev.enrollment, completed_at: new Date().toISOString(), stato: 'completato' } : prev.enrollment;
      return { ...prev, progress: np, progress_stats: resp.progress_stats || prev.progress_stats, enrollment };
    });
    if (resp.completato_ora) toast.success('Percorso completato. Complimenti.');
  }, []);
  const handleAccessRevoked = useCallback((code) => {
    toast.error(code === 'enrollment_expired' ? 'Il tuo accesso a questo corso è scaduto.' : 'L’accesso a questo corso è stato revocato.');
    navigate('/account');
  }, [navigate]);
  const segna = useCallback(async (lessonId, silenzioso = false) => {
    const lessonDef = flatLessons.find(l => l.id === lessonId);
    if (!lessonDef) return;
    try {
      const { data: resp } = await corsiAPI.sendProgress(enrollmentId, { lesson_id: lessonId, watched_seconds: lessonDef.duration_seconds || 0, completed: true });
      handleProgressUpdate(resp);
      if (!silenzioso) toast.success('Lezione completata.');
    } catch (err) {
      const code = err?.response?.data?.detail?.error;
      if (code === 'enrollment_revoked' || code === 'enrollment_expired') { handleAccessRevoked(code); return; }
      if (!silenzioso) toast.error('Non sono riuscito a salvare il progresso.');
    }
  }, [enrollmentId, flatLessons, handleProgressUpdate, handleAccessRevoked]);
  const handleMarkCompleted = useCallback(() => { if (selectedLessonId) segna(selectedLessonId); }, [selectedLessonId, segna]);
  const handleLessonEnded = useCallback(() => {
    if (!selectedLessonId || data?.progress?.[selectedLessonId]?.completed_at) return;
    segna(selectedLessonId, true);
  }, [selectedLessonId, data, segna]);
  const { handlePrev, handleNext, hasPrev, hasNext } = useLessonNavigation({ flatLessons, selectedLessonId, setSelectedLessonId, isCurrentCompleted, onMarkCompleted: handleMarkCompleted });
  const handleLessonSelect = (id) => { setSelectedLessonId(id); setLessonsDrawerOpen(false); };

  let corpo;
  if (!loading && error) corpo = <Errore kind={error.kind} />;
  else if (loading || !data || !course) corpo = <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6"><CoursePlayerSkeleton /></div>;
  else {
    const sidebar = (
      <CourseSidebar course={course} progress={progress} progressStats={progressStats} enrollment={data.enrollment}
                     selectedLessonId={selectedLessonId} onLessonSelect={handleLessonSelect} />
    );
    corpo = (
      <div className="mx-auto max-w-6xl space-y-3 px-4 py-5 sm:px-6 sm:py-8" data-testid="corso-studente">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Link to="/account" className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"><ArrowLeft className="h-4 w-4" aria-hidden /> I miei corsi</Link>
            <h1 className="mt-1 truncate font-display text-2xl text-gray-900">{course.title}</h1>
          </div>
          {data.enrollment?.completed_at && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800" data-testid="corso-completato">
              <CheckCircle2 className="h-4 w-4" aria-hidden /> Percorso completato
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <aside className="hidden space-y-2 lg:block">{sidebar}</aside>
          <main className="min-w-0 space-y-4">
            {selectedLesson ? (
              selectedLesson.tipo === 'testo' ? (
                <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7" data-testid="lezione-testo">
                  <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-500"><FileText className="h-3.5 w-3.5" aria-hidden /> Lezione di testo</p>
                  <h2 className="mt-1 font-display text-xl text-gray-900">{selectedLesson.title}</h2>
                  <div className="mt-4 whitespace-pre-line text-[16px] leading-relaxed text-gray-700">{selectedLesson.testo}</div>
                </div>
              ) : selectedLesson.video_pronto ? (
                <LessonPlayer enrollmentId={enrollmentId} lesson={selectedLesson} customerEmail={me?.email || null}
                              onProgressUpdate={handleProgressUpdate} onAccessRevoked={handleAccessRevoked} onLessonEnded={handleLessonEnded}
                              api={corsiAPI} />
              ) : (
                <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-2xl border border-gray-200 bg-white px-6 text-center shadow-sm" data-testid="video-in-arrivo">
                  <p className="text-sm font-semibold text-gray-900">Il video di questa lezione sta arrivando.</p>
                  <p className="text-xs text-gray-600">Chi ha pubblicato il corso lo sta ancora caricando: torna fra poco.</p>
                </div>
              )
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-2xl border border-gray-200 bg-white px-6 text-center shadow-sm">
                <p className="text-sm font-semibold text-gray-900">{flatLessons.length ? 'Scegli una lezione per cominciare.' : 'Le lezioni arrivano a breve.'}</p>
                {flatLessons.length > 0 && (
                  <button type="button" onClick={() => handleLessonSelect(flatLessons[0].id)} className="mt-2 rounded-full bg-[#2f5749] px-4 py-1.5 text-xs font-semibold text-white">Comincia dalla prima</button>
                )}
              </div>
            )}
            {selectedLesson && (
              <LessonActionBar lesson={selectedLesson} isCompleted={isCurrentCompleted} hasPrev={hasPrev} hasNext={hasNext}
                               onMarkCompleted={handleMarkCompleted} onPrev={handlePrev} onNext={handleNext} onOpenLessons={() => setLessonsDrawerOpen(true)} />
            )}
            {selectedLesson && selectedLesson.tipo !== 'testo' && <LessonDetails lesson={selectedLesson} completedAt={progress?.[selectedLesson.id]?.completed_at} />}
            {course.instructor_name && (
              <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="text-base font-semibold text-gray-900">{course.instructor_name}</h3>
                {course.instructor_bio && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-700">{course.instructor_bio}</p>}
              </div>
            )}
          </main>
        </div>
        <button type="button" onClick={() => setHelpOpen(true)} className="fixed bottom-4 right-4 z-30 hidden h-10 w-10 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white shadow-lg hover:bg-gray-800 lg:flex"
                title={t('customer_portal:player.shortcutsTitle')} aria-label={t('customer_portal:player.shortcutsAria')}>?</button>
        <HelpCheatsheet open={helpOpen} onClose={() => setHelpOpen(false)} />
        {lessonsDrawerOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button type="button" aria-label="Chiudi" onClick={() => setLessonsDrawerOpen(false)} className="absolute inset-0 cursor-default bg-black/50" />
            <div className="absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col rounded-t-2xl bg-white shadow-2xl">
              <div className="shrink-0 border-b border-gray-100 px-4 pb-3 pt-2">
                <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-gray-300" aria-hidden />
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-gray-900">Le lezioni</h2>
                  <button type="button" onClick={() => setLessonsDrawerOpen(false)} className="-mr-1.5 rounded-md p-1.5 hover:bg-gray-100" aria-label="Chiudi"><XIcon className="h-4 w-4 text-gray-700" /></button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-3">{sidebar}</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <MarketplaceShell noSearch>
      <div className="min-h-screen bg-[#faf8f3]">{corpo}</div>
    </MarketplaceShell>
  );
}

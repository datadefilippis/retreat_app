/**
 * ProductSalesStats — i numeri di UN prodotto, qualunque anima (CG3).
 *
 * Montato nei dashboard Service/Physical/Digital: 3 StatCard dal
 * kit (venduto 12m, ricavo 12m, extra per anima) e, per i servizi,
 * le prossime sessioni con il promemoria appuntamento a un click
 * (ContactActions, contesto appointment_reminder — template già
 * in library.json, finora mai cablato).
 *
 * Fonte: GET /products/{id}/sales-stats (cache 60s server-side).
 * Empty state onesti: zero vendite = zeri, non skeleton infiniti.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Receipt, Package, CalendarClock, Download, Users } from 'lucide-react';
import api from '../../../api/client';
import { StatCard } from '../../../components/charts';
import ContactActions from '../../../components/ContactActions';
import { formatCurrency } from '../../../lib/utils';
import { useCurrency } from '../../../context/AuthContext';

function dayLabel(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang, { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return iso; }
}

export default function ProductSalesStats({ productId, productName, stockQuantity }) {
  const { t, i18n } = useTranslation('products');
  const currency = useCurrency();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!productId) return undefined;
    let alive = true;
    api.get(`/products/${productId}/sales-stats`)
      .then((res) => { if (alive) setStats(res.data); })
      .catch(() => { /* blocco invisibile in caso d'errore */ });
    return () => { alive = false; };
  }, [productId]);

  if (!stats) return null;
  const fmt = (n) => formatCurrency(n || 0, currency);
  const itype = stats.item_type;

  return (
    <div className="space-y-3" data-testid="product-sales-stats">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <StatCard
          icon={Receipt}
          label={t('salesStats.revenue', { defaultValue: 'Ricavo (12 mesi)' })}
          value={fmt(stats.revenue_12m)}
        />
        <StatCard
          icon={Package}
          label={itype === 'service'
            ? t('salesStats.sessionsSold', { defaultValue: 'Sessioni vendute (12 mesi)' })
            : t('salesStats.units', { defaultValue: 'Unità vendute (12 mesi)' })}
          value={String(stats.units_12m ?? 0)}
        />
        {itype === 'service' && (
          <StatCard
            icon={CalendarClock}
            label={t('salesStats.upcoming', { defaultValue: 'Sessioni in agenda' })}
            value={String(stats.upcoming_count ?? 0)}
          />
        )}
        {itype === 'digital' && (
          <StatCard
            icon={Download}
            label={t('salesStats.deliveries', { defaultValue: 'Consegne emesse' })}
            value={String(stats.deliveries_12m ?? 0)}
          />
        )}
        {itype === 'physical' && stockQuantity != null && (
          <StatCard
            icon={Package}
            label={t('salesStats.stock', { defaultValue: 'Giacenza attuale' })}
            value={String(stockQuantity)}
            accent={Number(stockQuantity) <= 0}
          />
        )}
        {itype === 'course' && stats.enrollments && (
          <StatCard
            icon={Users}
            label={t('salesStats.enrollments', { defaultValue: 'Iscritti attivi' })}
            value={String(stats.enrollments.active ?? 0)}
            sublabel={t('salesStats.enrollmentsExpired', {
              defaultValue: '{{count}} scaduti', count: stats.enrollments.expired ?? 0,
            })}
          />
        )}
      </div>

      {/* servizio: le prossime sessioni sono un'agenda azionabile */}
      {itype === 'service' && (stats.upcoming_sessions || []).length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            {t('salesStats.upcomingTitle', { defaultValue: 'Prossime sessioni — il promemoria è già scritto' })}
          </p>
          <ul className="divide-y divide-border">
            {stats.upcoming_sessions.map((s2, i) => (
              <li key={i} className="flex items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{s2.holder_name || '—'}</p>
                  <p className="text-xs text-muted-foreground">
                    {dayLabel(s2.booking_date, i18n.language)} · {s2.booking_start_time}
                  </p>
                </div>
                <ContactActions
                  name={s2.holder_name}
                  email={s2.holder_email}
                  phone={s2.holder_phone}
                  context="appointment"
                  vars={{
                    retreat_name: productName ? ` ("${productName}")` : '',
                    start_date: `${dayLabel(s2.booking_date, i18n.language)}, ${s2.booking_start_time}`,
                  }}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

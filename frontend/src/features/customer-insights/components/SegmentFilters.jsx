/**
 * SegmentFilters — chip-style segment selector with all-segments default.
 *
 * The pie chart slice click in SegmentDistribution.jsx triggers the
 * same callback so the two interactions stay in sync.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../components/ui/button';

// F4 — 'lead' = clienti senza acquisti (es. iscritti newsletter).
const SEGMENTS = ['top', 'active', 'occasional', 'inactive', 'new', 'lead'];
const STATUSES = ['healthy', 'watch', 'atRisk', 'lost'];

export const SegmentFilters = ({
  selectedSegment,
  onSegmentChange,
  selectedStatus,
  onStatusChange,
  // CI-admin-vis: tri-state filters for the new columns.
  //   null  = "Tutti"            (no filter applied)
  //   true  = only registered / only opted-in
  //   false = only guest / only NOT opted-in
  // The parent page (CustomerInsightsPage) owns the state; we just
  // render the chips and emit setter calls.
  selectedHasAccount = null,
  onHasAccountChange,
  selectedMarketingOptedIn = null,
  onMarketingOptedInChange,
}) => {
  const { t } = useTranslation('customerInsights');

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-medium text-muted-foreground mr-2">
          {t('filters.segmentLabel')}
        </span>
        <ChipButton
          active={!selectedSegment}
          label={t('segment.all')}
          onClick={() => onSegmentChange(null)}
        />
        {SEGMENTS.map((seg) => (
          <ChipButton
            key={seg}
            active={selectedSegment === seg}
            label={t(`segment.${seg}`)}
            onClick={() => onSegmentChange(seg)}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-medium text-muted-foreground mr-2">
          {t('filters.statusLabel')}
        </span>
        <ChipButton
          active={!selectedStatus}
          label={t('status.all')}
          onClick={() => onStatusChange(null)}
        />
        {STATUSES.map((s) => (
          <ChipButton
            key={s}
            active={selectedStatus === toServerStatus(s)}
            label={t(`status.${s}`)}
            onClick={() => onStatusChange(toServerStatus(s))}
          />
        ))}
      </div>
      {/* CI-admin-vis: Account filter row. Hidden by default if the
          parent page doesn't wire the setter (backward compat — the
          two rows below render only when a setter prop is provided
          so legacy consumers of <SegmentFilters /> are unaffected). */}
      {onHasAccountChange && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground mr-2">
            {t('filters.accountLabel', { defaultValue: 'Account:' })}
          </span>
          <ChipButton
            active={selectedHasAccount === null}
            label={t('filters.accountAll', { defaultValue: 'Tutti' })}
            onClick={() => onHasAccountChange(null)}
          />
          <ChipButton
            active={selectedHasAccount === true}
            label={t('filters.accountRegistered', { defaultValue: 'Registrati' })}
            onClick={() => onHasAccountChange(true)}
          />
          <ChipButton
            active={selectedHasAccount === false}
            label={t('filters.accountGuest', { defaultValue: 'Solo guest' })}
            onClick={() => onHasAccountChange(false)}
          />
        </div>
      )}
      {onMarketingOptedInChange && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground mr-2">
            {t('filters.marketingLabel', { defaultValue: 'Marketing:' })}
          </span>
          <ChipButton
            active={selectedMarketingOptedIn === null}
            label={t('filters.marketingAll', { defaultValue: 'Tutti' })}
            onClick={() => onMarketingOptedInChange(null)}
          />
          <ChipButton
            active={selectedMarketingOptedIn === true}
            label={t('filters.marketingOptedIn', { defaultValue: 'Iscritti' })}
            onClick={() => onMarketingOptedInChange(true)}
          />
          <ChipButton
            active={selectedMarketingOptedIn === false}
            label={t('filters.marketingNotOptedIn', { defaultValue: 'Non iscritti' })}
            onClick={() => onMarketingOptedInChange(false)}
          />
        </div>
      )}
    </div>
  );
};

// Camel-case statuses (atRisk) to backend snake_case (at_risk).
function toServerStatus(uiStatus) {
  return uiStatus === 'atRisk' ? 'at_risk' : uiStatus;
}

function ChipButton({ active, label, onClick }) {
  return (
    <Button
      size="sm"
      variant={active ? 'default' : 'outline'}
      className="h-7 text-xs px-2.5"
      onClick={onClick}
    >
      {label}
    </Button>
  );
}

export default SegmentFilters;

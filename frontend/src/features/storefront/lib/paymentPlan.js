/**
 * paymentPlan.js — calcoli lato client del piano di pagamento (Fase 2 S2).
 *
 * SPECCHIO di backend/services/payment_schedule_service.py: stessi
 * arrotondamenti (half-up sui centesimi), stessa regola last-minute,
 * stesso collasso sotto il minimo Stripe. Qui si calcola SOLO per
 * mostrare; l'importo autoritativo resta server-side (il client non
 * viene mai creduto sul denaro).
 */

const MIN_CHARGE_MINOR = 50;

// half-up sui centesimi, senza float: lavora in minor units
function roundHalfUpMinor(totalMinor, percent) {
  return Math.floor((totalMinor * percent * 2 + 100) / 200);
}

export function toMinor(eur) {
  return Math.round(Number(eur) * 100);
}

/**
 * Ritorna il piano EFFETTIVO per un totale e una data di inizio:
 *   { mode: 'full' } — pagamento unico (anche per collasso last-minute/minimo)
 *   { mode: 'deposit', depositMinor, balanceMinor, balanceDueDate: Date, installments }
 * plan è product.metadata.payment_plan (può essere null/undefined).
 */
export function effectivePlan(plan, totalEur, startAtIso, now = new Date()) {
  if (!plan || plan.mode === 'full' || !totalEur || !startAtIso) {
    return { mode: 'full' };
  }
  const start = new Date(startAtIso);
  const dueDays = Number(plan.balance_due_days_before || 30);
  const deadline = new Date(start.getTime() - dueDays * 86400000);
  if (now >= deadline) return { mode: 'full', collapsed: true };

  const totalMinor = toMinor(totalEur);
  let depositMinor = plan.deposit_type === 'fixed'
    ? Number(plan.deposit_value)                       // già minor units
    : roundHalfUpMinor(totalMinor, Number(plan.deposit_value));
  depositMinor = Math.max(1, Math.min(depositMinor, totalMinor - 1));
  const balanceMinor = totalMinor - depositMinor;
  if (depositMinor < MIN_CHARGE_MINOR || balanceMinor < MIN_CHARGE_MINOR) {
    return { mode: 'full', collapsed: true };
  }
  return {
    mode: 'deposit',
    depositMinor,
    balanceMinor,
    balanceDueDate: deadline,
    installments: plan.mode === 'deposit_installments'
      ? Number(plan.installments_count || 3) : null,
  };
}

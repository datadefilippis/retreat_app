/**
 * Password strength meter — Sprint 3 W3.1 (parity React AuthPage).
 *
 * Pure function port del React storefront `computePasswordStrength`
 * (frontend/src/features/customer-portal/auth/AuthPage.jsx:442-454).
 * Zero deps, deterministic, side-effect-free.
 *
 * Criteri valutati (4 categorie + 1 bonus):
 *   1. length >= 8     (minimum requirement, gate del backend)
 *   2. length >= 12    (recommended strong)
 *   3. uppercase       (almeno 1 char [A-Z])
 *   4. lowercase       (almeno 1 char [a-z])
 *   5. digit           (almeno 1 char [0-9])
 *   6. symbol          (bonus: 1 char non alnum)
 *
 * Output:
 *   - score:  0-5 numerico (sum dei criteri soddisfatti escluso length>=8
 *             che e' minimum gate)
 *   - level:  'too_short' | 'weak' | 'fair' | 'good' | 'strong'
 *   - checks: dict booleani per ogni criterio (per render checklist UX)
 */

export type PasswordLevel =
  | 'too_short'
  | 'weak'
  | 'fair'
  | 'good'
  | 'strong';


export interface PasswordStrengthResult {
  score: number;        // 0-5
  level: PasswordLevel;
  checks: {
    minLength: boolean;       // >=8
    recommendedLength: boolean; // >=12
    uppercase: boolean;
    lowercase: boolean;
    digit: boolean;
    symbol: boolean;
  };
}


const MIN_LENGTH = 8;
const RECOMMENDED_LENGTH = 12;


export function computePasswordStrength(
  password: string | null | undefined,
): PasswordStrengthResult {
  const pwd = password ?? '';
  const checks = {
    minLength: pwd.length >= MIN_LENGTH,
    recommendedLength: pwd.length >= RECOMMENDED_LENGTH,
    uppercase: /[A-Z]/.test(pwd),
    lowercase: /[a-z]/.test(pwd),
    digit: /[0-9]/.test(pwd),
    symbol: /[^A-Za-z0-9]/.test(pwd),
  };

  // Length<MIN bypassa lo scoring (level forzato 'too_short')
  if (!checks.minLength) {
    return { score: 0, level: 'too_short', checks };
  }

  // Score = somma criteri soddisfatti (max 5: length recommended +
  // upper + lower + digit + symbol)
  let score = 0;
  if (checks.recommendedLength) score += 1;
  if (checks.uppercase) score += 1;
  if (checks.lowercase) score += 1;
  if (checks.digit) score += 1;
  if (checks.symbol) score += 1;

  let level: PasswordLevel;
  if (score <= 1) level = 'weak';
  else if (score === 2) level = 'fair';
  else if (score === 3 || score === 4) level = 'good';
  else level = 'strong';

  return { score, level, checks };
}


/**
 * UX helper: ritorna colore (hex) e label per il livello.
 * Tailwind-friendly, mirror del React StrengthBar.
 */
export function levelMeta(level: PasswordLevel): {
  color: string;
  label: string;
} {
  switch (level) {
    case 'too_short':
      return { color: '#9ca3af', label: 'Troppo corta' };
    case 'weak':
      return { color: '#ef4444', label: 'Debole' };
    case 'fair':
      return { color: '#f59e0b', label: 'Discreta' };
    case 'good':
      return { color: '#3b82f6', label: 'Buona' };
    case 'strong':
      return { color: '#10b981', label: 'Forte' };
  }
}

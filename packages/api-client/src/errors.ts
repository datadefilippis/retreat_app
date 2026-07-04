/**
 * Errori canonici emessi da @afianco/api-client.
 */

export class AfiancoApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: unknown,
    message?: string,
  ) {
    super(message ?? `afianco API ${status}`);
    this.name = 'AfiancoApiError';
  }
}

/** 401/403 — token mancante, expired, o cross-tenant */
export class AfiancoAuthError extends AfiancoApiError {
  constructor(status: number, detail: unknown) {
    super(status, detail, `afianco API auth error ${status}`);
    this.name = 'AfiancoAuthError';
  }
}

/** 429 — rate limit (con `retry_after` opzionale) */
export class AfiancoRateLimitError extends AfiancoApiError {
  constructor(
    public readonly retryAfterSeconds: number | null,
    detail: unknown,
  ) {
    super(429, detail, `afianco API rate limit (retry-after=${retryAfterSeconds ?? 'n/a'})`);
    this.name = 'AfiancoRateLimitError';
  }
}

/** 400 con error code (return_url_rejected, cart_empty, signup_failed, ecc.) */
export class AfiancoValidationError extends AfiancoApiError {
  constructor(
    public readonly errorCode: string | null,
    detail: unknown,
  ) {
    super(400, detail, `afianco API validation failed (code=${errorCode ?? 'n/a'})`);
    this.name = 'AfiancoValidationError';
  }
}

/**
 * Sprint 3 W3.2 — 423 Locked (Onda 29 account lockout dopo N tentativi
 * falliti). Backend ritorna detail:
 *   { code: 'ACCOUNT_LOCKED', message, unlock_at: iso8601 }
 * Widget intercetta + mostra countdown live fino a unlock_at.
 */
export class AfiancoLockedError extends AfiancoApiError {
  constructor(
    public readonly unlockAtIso: string | null,
    detail: unknown,
  ) {
    super(423, detail, `afianco account locked (unlock_at=${unlockAtIso ?? 'n/a'})`);
    this.name = 'AfiancoLockedError';
  }
}

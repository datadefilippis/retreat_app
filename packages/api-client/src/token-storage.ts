/**
 * Pluggable storage per il customer JWT.
 *
 * Default: localStorage prefixed per merchant slug (es. key
 * "afianco_token_bottega-demo"). Merchant con stricter security puo'
 * passare un'implementazione custom (es. memory-only volatile, o
 * sessionStorage).
 *
 * Nessun cookie (third-party cookie phaseout safe).
 */

export interface TokenStorage {
  /** Returns the token or null. */
  get(): string | null;
  /** Persist the token. */
  set(token: string): void;
  /** Remove the token (logout). */
  clear(): void;
}

/**
 * localStorage implementation con key prefix per merchant.
 * Falls back gracefully a null in ambienti dove localStorage non
 * esiste (SSR, sandboxed iframe).
 */
export class LocalStorageTokenStorage implements TokenStorage {
  constructor(private readonly key: string) {}

  get(): string | null {
    try {
      if (typeof localStorage === 'undefined') return null;
      return localStorage.getItem(this.key);
    } catch {
      return null;
    }
  }

  set(token: string): void {
    try {
      if (typeof localStorage === 'undefined') return;
      localStorage.setItem(this.key, token);
    } catch {
      // quota exceeded / disabled — fail silent (caller potrebbe degradare
      // a guest checkout)
    }
  }

  clear(): void {
    try {
      if (typeof localStorage === 'undefined') return;
      localStorage.removeItem(this.key);
    } catch {
      // ignore
    }
  }
}

/**
 * In-memory volatile implementation. Token perso al reload.
 * Util per ambienti dove localStorage non e' affidabile (incognito
 * Safari blocca tutto su 3rd-party storage) o per high-security mode.
 */
export class MemoryTokenStorage implements TokenStorage {
  private token: string | null = null;

  get(): string | null {
    return this.token;
  }

  set(token: string): void {
    this.token = token;
  }

  clear(): void {
    this.token = null;
  }
}

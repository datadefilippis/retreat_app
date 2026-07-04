/**
 * Newsletter form — tipi condivisi (F2, modulo Newsletter).
 *
 * Mirror TypeScript dei modelli Pydantic backend (models/newsletter.py).
 * Usati dal web component `<afianco-newsletter-form>` e dall'admin UI (F3).
 */

export type NewsletterFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'email'
  | 'tel'
  | 'select'
  | 'checkbox';

export interface NewsletterFieldConfig {
  id: string;
  label: string;
  type: NewsletterFieldType;
  required: boolean;
  placeholder?: string | null;
  help_text?: string | null;
  /** Solo per type='select'. */
  options?: string[] | null;
  sort_order: number;
}

/** Personalizzazione colori del form (F7). */
export interface NewsletterTheme {
  primary_color?: string | null;
  primary_text_color?: string | null;
}

/** Config public-safe restituita da GET /public/embed/newsletter/{form_id}. */
export type NewsletterLayout = 'vertical' | 'horizontal' | 'inline';

export interface NewsletterFormPublic {
  id: string;
  name: string;
  collect_name: boolean;
  collect_phone: boolean;
  field_configs: NewsletterFieldConfig[];
  consent_text?: string | null;
  privacy_required: boolean;
  success_message?: string | null;
  redirect_url?: string | null;
  /** F8 — layout del form (vertical | horizontal | inline). */
  layout?: NewsletterLayout | null;
  /** F7 — colori personalizzati (mappati a CSS custom properties). */
  theme?: NewsletterTheme | null;
  /** F7 — URL privacy policy risolto lato server (link nel consenso). */
  privacy_policy_url?: string | null;
}

/** Payload POST /public/embed/newsletter/{form_id}/submit. */
export interface NewsletterSubmitRequest {
  email: string;
  name?: string | null;
  phone?: string | null;
  fields_data?: Record<string, unknown>;
  consent_privacy: boolean;
  /** Tracciamento sorgente (D7) lato client. */
  source_url?: string | null;
  source_referrer?: string | null;
  source_label?: string | null;
  /** Honeypot anti-bot: deve restare vuoto. */
  hp?: string | null;
}

export interface NewsletterSubmitResponse {
  success: boolean;
  message: string;
  subscriber_id?: string | null;
}

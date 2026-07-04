/**
 * OrderCustomerCard — customer contact block for the admin order detail panel.
 *
 * Renders name + email + phone with click-to-action (mailto:, tel:) and
 * inline copy affordance. Graceful on missing data (common on legacy orders
 * pre-F2 Onda 9) — falls back to GET /api/orders/{id} customer enrichment.
 */

import { User, Mail, Phone } from 'lucide-react';
import CopyButton from './CopyButton';

export default function OrderCustomerCard({ order, t }) {
  if (!order) return null;

  const name = order.customer_name || '';
  const email = order.customer_email || '';
  const phone = order.contact_phone || '';
  const anyData = name || email || phone;

  const placeholder = t?.('detail.customer_no_contact', {
    defaultValue: 'Nessun contatto cliente disponibile',
  });

  return (
    <div className="rounded-lg border bg-card/40 p-3 space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
        <User className="h-3.5 w-3.5" />
        {t?.('detail.customer', { defaultValue: 'Cliente' })}
      </div>

      {!anyData && (
        <p className="text-xs text-muted-foreground italic">{placeholder}</p>
      )}

      {name && (
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium truncate flex-1">{name}</span>
          <CopyButton value={name} title={t?.('detail.copy_name', { defaultValue: 'Copia nome' })} />
        </div>
      )}

      {email && (
        <div className="flex items-center gap-2 text-sm">
          <Mail className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <a
            href={`mailto:${email}`}
            className="text-primary hover:underline truncate flex-1"
            title={email}
          >
            {email}
          </a>
          <CopyButton value={email} title={t?.('detail.copy_email', { defaultValue: 'Copia email' })} />
        </div>
      )}

      {phone && (
        <div className="flex items-center gap-2 text-sm">
          <Phone className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <a
            href={`tel:${phone.replace(/\s+/g, '')}`}
            className="text-primary hover:underline truncate flex-1"
          >
            {phone}
          </a>
          <CopyButton value={phone} title={t?.('detail.copy_phone', { defaultValue: 'Copia telefono' })} />
        </div>
      )}
    </div>
  );
}

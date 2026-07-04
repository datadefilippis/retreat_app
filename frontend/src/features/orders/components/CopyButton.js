/**
 * CopyButton — tiny inline copy-to-clipboard affordance.
 *
 * Renders next to identifiers (order number, email, phone, issued codes).
 * Provides brief visual feedback on success. Falls back to execCommand when
 * navigator.clipboard is unavailable (iframe / insecure context).
 */

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CopyButton({ value, title, className = '' }) {
  const [copied, setCopied] = useState(false);

  if (!value) return null;

  const handleCopy = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(String(value));
      } else {
        const ta = document.createElement('textarea');
        ta.value = String(value);
        ta.setAttribute('readonly', '');
        ta.style.position = 'absolute';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Silently fail — user can still select and copy manually.
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={title || 'Copia'}
      className={`inline-flex items-center justify-center h-5 w-5 rounded hover:bg-muted transition-colors ${className}`}
    >
      {copied ? (
        <Check className="h-3 w-3 text-emerald-600" />
      ) : (
        <Copy className="h-3 w-3 text-muted-foreground" />
      )}
    </button>
  );
}

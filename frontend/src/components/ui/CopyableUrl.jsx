/**
 * CopyableUrl — micro-component for an inline URL with a copy button.
 *
 * Renders the URL as a small link (target=_blank) followed by a copy
 * icon. Clicking the icon copies the URL to the clipboard and shows a
 * 1.5s confirmation via the icon swap (Copy → Check). Also surfaces
 * a Sonner toast so the action is unambiguous on assistive devices.
 *
 * Designed for the store-card use-case where the storefront URL must
 * be visible AND easy to share — without taking too much vertical
 * space. Pure presentational + 1 small useState; no new deps.
 *
 * Props
 * -----
 * - ``url``         (string, required) absolute URL
 * - ``displayText`` (string, optional) what to show instead of full URL
 *                   (the URL is still what gets copied). Defaults to url.
 * - ``className``   (string, optional) merged onto the wrapper
 * - ``size``        ("sm" | "md") affects icon + text size; default "sm"
 */

import React, { useState, useCallback } from 'react';
import { ExternalLink, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from './tooltip';


export default function CopyableUrl({
  url,
  displayText,
  className = '',
  size = 'sm',
}) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const text = displayText ?? url;
  const iconSize = size === 'md' ? 'h-3.5 w-3.5' : 'h-3 w-3';
  const textSize = size === 'md' ? 'text-sm' : 'text-xs';

  const handleCopy = useCallback(async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success(t('common:copied', 'Copiato negli appunti'));
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API blocked (insecure context / permissions).
      // Fallback: select the text via execCommand. If that also fails,
      // surface an error toast so the user knows to copy manually.
      try {
        const ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        toast.success(t('common:copied', 'Copiato negli appunti'));
        setTimeout(() => setCopied(false), 1500);
      } catch {
        toast.error(t('common:copy_failed', 'Impossibile copiare'));
      }
    }
  }, [url, t]);

  return (
    <TooltipProvider delayDuration={300}>
      <span className={`inline-flex items-center gap-1.5 min-w-0 ${className}`}>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className={`${textSize} text-primary hover:underline truncate min-w-0`}
          title={url}
        >
          {text}
        </a>
        <ExternalLink className={`${iconSize} text-muted-foreground shrink-0`} />
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={handleCopy}
              aria-label={t('common:copy_url', 'Copia URL')}
              className="inline-flex items-center justify-center rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
            >
              {copied
                ? <Check className={`${iconSize} text-emerald-600`} />
                : <Copy className={iconSize} />
              }
            </button>
          </TooltipTrigger>
          <TooltipContent side="top">
            {copied
              ? t('common:copied', 'Copiato!')
              : t('common:copy_url', 'Copia URL')
            }
          </TooltipContent>
        </Tooltip>
      </span>
    </TooltipProvider>
  );
}

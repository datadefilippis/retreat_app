/**
 * UnsavedChangesDialog — drop-in alert for the useUnsavedChangesPrompt
 * blocker state.
 *
 * 2026-05-20 — Standardised dialog that wraps the Radix AlertDialog and
 * exposes a tiny, predictable API:
 *
 *   <UnsavedChangesDialog
 *     open={blocker.state === 'blocked'}
 *     onConfirm={() => blocker.proceed()}
 *     onCancel={() => blocker.reset()}
 *   />
 *
 * All wizards use the same copy + same i18n keys (under ``wizards.common
 * .unsaved.*``) so the merchant sees a consistent prompt regardless of
 * which create-flow they're in.
 *
 * Localisation: receives ``t`` optionally — if omitted, falls back to
 * Italian-only strings (acceptable: this prompt is rare, and the IT
 * fallback matches the primary market).
 */

import React from 'react';
import { useTranslation } from 'react-i18next';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './alert-dialog';


export function UnsavedChangesDialog({ open, onConfirm, onCancel }) {
  // useTranslation is safe in any namespace; we just read the common
  // wizards bucket. Falls back to defaultValue when keys are missing
  // so the dialog never renders raw key paths.
  const { t } = useTranslation('products');

  return (
    <AlertDialog open={open} onOpenChange={(o) => { if (!o) onCancel?.(); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {t('wizards.common.unsaved.title', {
              defaultValue: 'Modifiche non salvate',
            })}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {t('wizards.common.unsaved.message', {
              defaultValue:
                'Se esci ora perderai i dati inseriti nel form. Vuoi uscire comunque?',
            })}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>
            {t('wizards.common.unsaved.stay', { defaultValue: 'Resta qui' })}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            {t('wizards.common.unsaved.leave', { defaultValue: 'Esci e scarta' })}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}


export default UnsavedChangesDialog;

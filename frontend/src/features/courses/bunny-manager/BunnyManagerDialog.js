/**
 * BunnyManagerDialog — modal variant of the unified Bunny manager.
 *
 * Used from "external" entry points (ProductsPage TypePicker,
 * CoursesGrid header button, CourseEditor sidebar widget) where the
 * Bunny manager is a side affordance not the primary content.
 *
 * Identical body to `BunnyManagerCard` — same modes, same actions,
 * same data flow. The only difference is the modal chrome.
 *
 * Lifecycle:
 *   - `open=true` mounts the dialog and triggers an initial fetch
 *     via the hook (loads on every open so the data is fresh)
 *   - `onClose` fires when the user clicks outside / presses ESC /
 *     clicks the close button
 *
 * The dialog stays open through internal mode transitions (list →
 * edit → list, migrate → list). The ONLY way to close is through
 * `onClose` from the parent — internal actions never close.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../../components/ui/dialog';
import BunnyManagerBody from './BunnyManagerBody';
import useBunnyManager from './useBunnyManager';


export default function BunnyManagerDialog({ open, onClose }) {
  const { t } = useTranslation('products');
  // Always mount the hook (it short-circuits when open is false via
  // the unmount in the conditional render below). React's StrictMode
  // double-renders are a no-op for the network call thanks to the
  // hook's effect deps.
  const manager = useBunnyManager();

  return (
    <Dialog open={!!open} onOpenChange={(v) => { if (!v) onClose?.(); }}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('dashboards.course.bunnyManager.dialogTitle')}</DialogTitle>
        </DialogHeader>
        <div className="py-2">
          <BunnyManagerBody manager={manager} />
        </div>
      </DialogContent>
    </Dialog>
  );
}

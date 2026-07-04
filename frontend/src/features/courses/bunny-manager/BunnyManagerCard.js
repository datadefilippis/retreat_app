/**
 * BunnyManagerCard — inline card variant of the unified Bunny manager.
 *
 * Used in `/courses` admin page where the manager is the primary
 * surface (always visible, no modal trigger needed). For "trigger from
 * elsewhere" entry points (Products page, CourseEditor sidebar), use
 * `BunnyManagerDialog` instead.
 *
 * Both share the same body (`BunnyManagerBody`) + the same hook
 * (`useBunnyManager`), so the rendered content is identical — only
 * the surrounding chrome differs (Card has a wrapper, Dialog has
 * modal chrome).
 */

import React from 'react';
import BunnyManagerBody from './BunnyManagerBody';
import useBunnyManager from './useBunnyManager';


export default function BunnyManagerCard() {
  const manager = useBunnyManager();

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4">
      <BunnyManagerBody manager={manager} />
    </div>
  );
}

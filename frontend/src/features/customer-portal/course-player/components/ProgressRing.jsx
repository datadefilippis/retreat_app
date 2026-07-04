/**
 * ProgressRing — circular SVG progress indicator.
 *
 * Used in the course sidebar Riepilogo card as the visual hero
 * replacing the previous thin progress bar. Designed for "readable
 * at a glance" — the customer should see their % at a single look,
 * not by scanning rows of text.
 *
 * Pure SVG with stroke-dasharray trick:
 *   - Background ring  — full circumference, gray-200
 *   - Progress arc     — dasharray = circumference * pct/100, rotated
 *                        -90° so the dash starts at 12 o'clock
 *   - Center label     — big % number; emerald at 100%, gray-900 < 100%
 *
 * Animation: `transition` smooths progress jumps after marking a
 * lesson complete, giving a small "earned this" feeling.
 *
 * Extracted from the 1392-line monolith during the Fase 4
 * architectural split.
 */

import React from 'react';


export default function ProgressRing({ value = 0, size = 72, stroke = 6 }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = (pct / 100) * circumference;
  const isDone = pct >= 100;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          fill="transparent"
          className="stroke-gray-200"
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          fill="transparent"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          className={`transition-all duration-500 ${
            isDone ? 'stroke-emerald-500' : 'stroke-gray-900'
          }`}
        />
      </svg>
      <span
        className={`absolute text-sm font-bold tabular-nums ${
          isDone ? 'text-emerald-700' : 'text-gray-900'
        }`}
        // a11y: parent should aria-label the surrounding container
        // ("X% completato"). The number itself is decorative here.
        aria-hidden
      >
        {pct}%
      </span>
    </div>
  );
}

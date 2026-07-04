/**
 * fieldConfigUtils — shared helpers for handling FieldConfig[] payloads
 * before sending them to the backend.
 *
 * Invariant enforced: the backend model `FieldConfig.label` has
 * `min_length=1`. A single row with an empty label is enough to blow up
 * the entire public catalog endpoint via Pydantic validation. Every
 * wizard / dashboard that mutates attendee_fields or order_fields must
 * call `pruneFieldConfigs(list)` right before including the array in a
 * POST/PATCH body, so admin mis-clicks ("+ Aggiungi campo" followed by
 * Save without typing a label) can't corrupt the product document.
 */


/**
 * Drop entries whose label is missing, null, or whitespace-only.
 * Preserves order and returns a fresh array (never mutates input).
 */
export function pruneFieldConfigs(fields) {
  if (!Array.isArray(fields)) return [];
  return fields.filter((f) => {
    if (!f) return false;
    const label = f.label;
    return typeof label === 'string' && label.trim().length > 0;
  });
}

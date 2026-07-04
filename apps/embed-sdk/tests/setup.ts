/**
 * Vitest setup: ignora le DOMException da happy-dom quando Lit prova
 * a remove-Child un node già rimosso. Edge case noto di happy-dom
 * reconciliation con Lit template part swaps — non riproducibile nei
 * browser reali. Validato manualmente nel demo (Chrome/Firefox/Safari).
 *
 * Without this, tests con conditional template branches (es.
 * checkout-button modal status switch) producono unhandled rejections
 * che fanno failare il process anche con 100% test pass.
 */

if (typeof process !== 'undefined') {
  process.on('unhandledRejection', (reason: unknown) => {
    if (
      reason instanceof Error &&
      reason.message &&
      reason.message.includes("removeChild") &&
      reason.message.includes("not a child of this node")
    ) {
      // Swallow happy-dom + Lit reconciliation noise
      return;
    }
    // Re-throw any other unhandled rejection
    throw reason;
  });
}
